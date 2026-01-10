"""
Minimalistic CANopen implementation for MicroPython
Based on candriver.py CanFrame and MCP2515 classes
"""

from candriver import CanFrame
import time

# CANopen Object Dictionary Indices
OD_DEVICE_TYPE = 0x1000
OD_ERROR_REGISTER = 0x1001
OD_MANUFACTURER_STATUS = 0x1002
OD_IDENTITY_OBJECT = 0x1018
OD_SDO_SERVER_PARAMETER = 0x1200
OD_RPDO1_PARAMETER = 0x1400
OD_TPDO1_PARAMETER = 0x1800

# CANopen Function Codes
FC_NMT = 0x000
FC_SYNC = 0x080
FC_EMERGENCY = 0x080
FC_TPDO1 = 0x180
FC_RPDO1 = 0x200
FC_TPDO2 = 0x280
FC_RPDO2 = 0x300
FC_TPDO3 = 0x380
FC_RPDO3 = 0x400
FC_TPDO4 = 0x480
FC_RPDO4 = 0x500
FC_SDO_TX = 0x580
FC_SDO_RX = 0x600
FC_HEARTBEAT = 0x700

# NMT Command Specifiers
NMT_START_REMOTE_NODE = 0x01
NMT_STOP_REMOTE_NODE = 0x02
NMT_ENTER_PRE_OPERATIONAL = 0x80
NMT_RESET_NODE = 0x81
NMT_RESET_COMMUNICATION = 0x82

# NMT States
NMT_STATE_INITIALIZING = 0x00
NMT_STATE_RESET_NODE = 0x01
NMT_STATE_RESET_COMMUNICATION = 0x02
NMT_STATE_STOPPED = 0x04
NMT_STATE_OPERATIONAL = 0x05
NMT_STATE_PRE_OPERATIONAL = 0x7F


# SDO Command Specifiers
SDO_CMD_DOWNLOAD_INITIATE = 0x20
SDO_CMD_DOWNLOAD_SEGMENT = 0x00
SDO_CMD_UPLOAD_INITIATE = 0x40
SDO_CMD_UPLOAD_SEGMENT = 0x60
SDO_CMD_ABORT = 0x80

# SDO Response Specifiers
SDO_RESP_DOWNLOAD_INITIATE = 0x60
SDO_RESP_DOWNLOAD_SEGMENT = 0x20
SDO_RESP_UPLOAD_INITIATE = 0x40
SDO_RESP_UPLOAD_SEGMENT = 0x00


class CANopenException(Exception):
    """Base exception for CANopen errors"""

    pass


class ObjectDictionary:
    """Simple Object Dictionary implementation"""

    def __init__(self):
        self.objects = {}

        # Initialize mandatory objects
        self.objects[OD_DEVICE_TYPE] = 0x00000000
        self.objects[OD_ERROR_REGISTER] = 0x00
        self.objects[OD_MANUFACTURER_STATUS] = 0x00000000

        # Identity Object (0x1018)
        self.objects[0x1018] = {
            0x00: 4,  # Number of entries
            0x01: 0x00000000,  # Vendor ID
            0x02: 0x00000000,  # Product Code
            0x03: 0x00000000,  # Revision Number
            0x04: 0x00000000,  # Serial Number
        }

    def get_object(self, index, subindex=0):
        """Get object from dictionary"""
        if index in self.objects:
            obj = self.objects[index]
            if isinstance(obj, dict):
                return obj.get(subindex)
            else:
                return obj if subindex == 0 else None
        return None

    def set_object(self, index, value, subindex=0):
        """Set object in dictionary"""
        if index not in self.objects:
            self.objects[index] = {}

        if isinstance(self.objects[index], dict):
            self.objects[index][subindex] = value
        else:
            if subindex == 0:
                self.objects[index] = value


class SDO:
    """Service Data Object implementation"""

    def __init__(self, node_id, can_interface, object_dict):
        self.node_id = node_id
        self.can = can_interface
        self.od = object_dict
        self.tx_cob_id = FC_SDO_TX + node_id
        self.rx_cob_id = FC_SDO_RX + node_id

    def create_download_initiate(self, index, subindex, data):
        """Create SDO download initiate frame"""
        if len(data) <= 4:
            # Expedited transfer
            cmd = SDO_CMD_DOWNLOAD_INITIATE | 0x02  # Expedited
            if len(data) < 4:
                cmd |= (4 - len(data)) << 2  # Size indication

            payload = [cmd, index & 0xFF, (index >> 8) & 0xFF, subindex]
            payload.extend(data[:4])
            payload.extend([0] * (8 - len(payload)))  # Pad to 8 bytes
        else:
            # Segmented transfer (simplified - not fully implemented)
            cmd = SDO_CMD_DOWNLOAD_INITIATE
            payload = [cmd, index & 0xFF, (index >> 8) & 0xFF, subindex]
            payload.extend(
                [
                    len(data) & 0xFF,
                    (len(data) >> 8) & 0xFF,
                    (len(data) >> 16) & 0xFF,
                    (len(data) >> 24) & 0xFF,
                ]
            )

        return CanFrame(id=self.rx_cob_id, payload=payload)

    def create_upload_initiate(self, index, subindex):
        """Create SDO upload initiate frame"""
        cmd = SDO_CMD_UPLOAD_INITIATE
        payload = [cmd, index & 0xFF, (index >> 8) & 0xFF, subindex, 0, 0, 0, 0]
        return CanFrame(id=self.rx_cob_id, payload=payload)

    def process_request(self, frame):
        """Process incoming SDO request"""
        if len(frame.payload) < 4:
            return None

        cmd = frame.payload[0]
        index = frame.payload[1] | (frame.payload[2] << 8)
        subindex = frame.payload[3]

        if cmd & 0x20:  # Download (write)
            if cmd & 0x02:  # Expedited
                data_len = 4 - ((cmd >> 2) & 0x03) if (cmd & 0x01) else 4
                data = frame.payload[4 : 4 + data_len]

                # Store in object dictionary
                if data_len == 1:
                    value = data[0]
                elif data_len == 2:
                    value = data[0] | (data[1] << 8)
                elif data_len == 4:
                    value = data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)
                else:
                    value = bytes(data)

                self.od.set_object(index, value, subindex)

                # Send response
                response_payload = [
                    SDO_RESP_DOWNLOAD_INITIATE,
                    index & 0xFF,
                    (index >> 8) & 0xFF,
                    subindex,
                    0,
                    0,
                    0,
                    0,
                ]
                return CanFrame(id=self.tx_cob_id, payload=response_payload)

        elif cmd & 0x40:  # Upload (read)
            value = self.od.get_object(index, subindex)
            if value is not None:
                if isinstance(value, int):
                    if value <= 0xFF:
                        data = [value]
                    elif value <= 0xFFFF:
                        data = [value & 0xFF, (value >> 8) & 0xFF]
                    else:
                        data = [
                            value & 0xFF,
                            (value >> 8) & 0xFF,
                            (value >> 16) & 0xFF,
                            (value >> 24) & 0xFF,
                        ]
                else:
                    data = list(value) if isinstance(value, (list, bytes)) else [value]

                # Expedited transfer
                cmd_resp = SDO_RESP_UPLOAD_INITIATE | 0x02  # Expedited
                if len(data) < 4:
                    cmd_resp |= (4 - len(data)) << 2  # Size indication

                response_payload = [
                    cmd_resp,
                    index & 0xFF,
                    (index >> 8) & 0xFF,
                    subindex,
                ]
                response_payload.extend(data[:4])
                response_payload.extend([0] * (8 - len(response_payload)))

                return CanFrame(id=self.tx_cob_id, payload=response_payload)

        return None


class PDO:
    """Process Data Object implementation"""

    def __init__(self, node_id, can_interface, pdo_number=1, is_tx=True):
        self.node_id = node_id
        self.can = can_interface
        self.pdo_number = pdo_number
        self.is_tx = is_tx

        if is_tx:
            self.cob_id = (FC_TPDO1 + (pdo_number - 1) * 0x100) + node_id
        else:
            self.cob_id = (FC_RPDO1 + (pdo_number - 1) * 0x100) + node_id

        self.data = [0] * 8
        self.mapping = []  # List of (index, subindex, size_bits) tuples

    def map_object(self, index, subindex=0, size_bits=8):
        """Map an object to this PDO"""
        self.mapping.append((index, subindex, size_bits))

    def transmit(self, data=None):
        """Transmit PDO"""
        if data is None:
            data = self.data
        frame = CanFrame(id=self.cob_id, payload=data[:8])
        self.can.Send(frame)

    def process_receive(self, frame):
        """Process received PDO"""
        if frame.id == self.cob_id and not self.is_tx:
            self.data = frame.payload[:8]
            return True
        return False


class CANopenNode:
    """CANopen Node implementation"""

    def __init__(self, node_id, can_interface):
        self.node_id = node_id
        self.can = can_interface
        self.state = NMT_STATE_INITIALIZING
        self.od = ObjectDictionary()
        self.sdo = SDO(node_id, can_interface, self.od)

        # PDOs
        self.tpdos = {}
        self.rpdos = {}

        # Heartbeat
        self.heartbeat_time = 0
        self.heartbeat_interval = 1000  # ms

    def add_tpdo(self, pdo_number=1):
        """Add Transmit PDO"""
        pdo = PDO(self.node_id, self.can, pdo_number, is_tx=True)
        self.tpdos[pdo_number] = pdo
        return pdo

    def add_rpdo(self, pdo_number=1):
        """Add Receive PDO"""
        pdo = PDO(self.node_id, self.can, pdo_number, is_tx=False)
        self.rpdos[pdo_number] = pdo
        return pdo

    def send_heartbeat(self):
        """Send heartbeat message"""
        frame = CanFrame(id=FC_HEARTBEAT + self.node_id, payload=[self.state])
        self.can.Send(frame)

    def process_nmt(self, frame):
        """Process NMT command"""
        if len(frame.payload) >= 2 and (
            frame.payload[1] == 0 or frame.payload[1] == self.node_id
        ):
            cmd = frame.payload[0]

            if cmd == NMT_START_REMOTE_NODE:
                self.state = NMT_STATE_OPERATIONAL
            elif cmd == NMT_STOP_REMOTE_NODE:
                self.state = NMT_STATE_STOPPED
            elif cmd == NMT_ENTER_PRE_OPERATIONAL:
                self.state = NMT_STATE_PRE_OPERATIONAL
            elif cmd == NMT_RESET_NODE:
                self.reset()
            elif cmd == NMT_RESET_COMMUNICATION:
                self.reset_communication()

    def reset(self):
        """Reset node"""
        self.state = NMT_STATE_INITIALIZING
        # Perform reset operations
        time.sleep_ms(100)
        self.state = NMT_STATE_PRE_OPERATIONAL

    def reset_communication(self):
        """Reset communication"""
        self.state = NMT_STATE_INITIALIZING
        # Reset communication parameters
        time.sleep_ms(50)
        self.state = NMT_STATE_PRE_OPERATIONAL

    def process_frame(self, frame):
        """Process incoming CAN frame"""
        # NMT
        if frame.id == FC_NMT:
            self.process_nmt(frame)
            return True

        # SDO
        elif frame.id == self.sdo.rx_cob_id:
            response = self.sdo.process_request(frame)
            if response:
                self.can.Send(response)
            return True

        # PDOs
        for pdo in self.rpdos.values():
            if pdo.process_receive(frame):
                return True

        return False

    def update(self):
        """Update node (call regularly in main loop)"""
        current_time = time.ticks_ms()

        # Process received frames
        while self.can.CheckReceiveBuffer():
            frame = self.can.Receive()
            self.process_frame(frame)

        # Send heartbeat
        if self.heartbeat_interval > 0:
            if (
                time.ticks_diff(current_time, self.heartbeat_time)
                >= self.heartbeat_interval
            ):
                self.send_heartbeat()
                self.heartbeat_time = current_time

    def start(self):
        """Start the node"""
        self.state = NMT_STATE_PRE_OPERATIONAL
        self.heartbeat_time = time.ticks_ms()

    def set_operational(self):
        """Set node to operational state"""
        self.state = NMT_STATE_OPERATIONAL


# Example usage functions
def create_simple_io_node(node_id, can_interface):
    """Create a simple I/O node with basic PDOs"""
    node = CANopenNode(node_id, can_interface)

    # Add TPDO1 for digital inputs
    tpdo1 = node.add_tpdo(1)

    # Add RPDO1 for digital outputs
    rpdo1 = node.add_rpdo(1)

    # Set some identity information
    node.od.set_object(0x1018, 0x12345678, 0x01)  # Vendor ID
    node.od.set_object(0x1018, 0x00000001, 0x02)  # Product Code
    node.od.set_object(0x1018, 0x00010001, 0x03)  # Revision
    node.od.set_object(0x1018, node_id, 0x04)  # Serial Number

    return node, tpdo1, rpdo1
