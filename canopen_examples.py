"""
Example usage of the minimalistic CANopen implementation
"""

from candriver import MCP2515, CanFrame
from canopen import CANopenNode, create_simple_io_node
from can_config import NODE_ID
import time
from machine import Pin


def simple_canopen_example():
    """Simple CANopen node example"""

    # Initialize CAN interface
    print("Initializing CAN interface...")
    can = MCP2515()
    can.Init(speed="250KBPS")
    print("CAN interface ready")

    # Create CANopen node
    print(f"Creating CANopen node with ID {NODE_ID}")
    node, tpdo1, rpdo1 = create_simple_io_node(NODE_ID, can)

    # Start the node
    node.start()
    print("CANopen node started in Pre-Operational state")

    # Simulate some I/O
    digital_inputs = 0x00
    digital_outputs = 0x00

    # LED for output indication (if available)
    try:
        led = Pin("LED", Pin.OUT)  # Raspberry Pi Pico onboard LED
    except:
        led = None

    counter = 0

    print("Entering main loop...")
    print("Send NMT command 0x01 to node", NODE_ID, "to enter Operational state")

    while True:
        # Update node (processes incoming messages, sends heartbeat)
        node.update()

        # Check if we received RPDO data (digital outputs)
        if rpdo1.data[0] != digital_outputs:
            digital_outputs = rpdo1.data[0]
            print(f"Digital outputs updated: 0x{digital_outputs:02X}")

            # Control LED based on bit 0
            if led and (digital_outputs & 0x01):
                led.on()
            elif led:
                led.off()

        # Send TPDO data (digital inputs) periodically when operational
        if node.state == 0x05:  # Operational state
            counter += 1
            if counter >= 10:  # Every 10 cycles (1 second)
                # Simulate changing digital inputs
                digital_inputs = (digital_inputs + 1) % 256
                tpdo1.data[0] = digital_inputs
                tpdo1.data[1] = counter & 0xFF
                tpdo1.transmit()
                print(f"Sent TPDO1: inputs=0x{digital_inputs:02X}, counter={counter}")
                counter = 0

        time.sleep_ms(100)


def canopen_sdo_example():
    """Example showing SDO communication"""

    # Initialize CAN interface
    can = MCP2515()
    can.Init(speed="250KBPS")

    # Create CANopen node
    node = CANopenNode(NODE_ID, can)

    # Add some custom objects to the object dictionary
    node.od.set_object(0x2000, 42)  # Custom integer value
    node.od.set_object(0x2001, "Hello")  # Custom string value
    node.od.set_object(0x2002, [1, 2, 3, 4])  # Custom array

    node.start()

    print("CANopen SDO example running...")
    print(f"Node ID: {NODE_ID}")
    print("Try reading/writing objects using CANopen master:")
    print("- Object 0x2000: Integer value (42)")
    print("- Object 0x2001: String value ('Hello')")
    print("- Object 0x2002: Array value ([1,2,3,4])")
    print("- Object 0x1018 sub 1-4: Identity object")

    while True:
        node.update()
        time.sleep_ms(50)


def canopen_master_example():
    """Example of simple CANopen master functionality"""

    # Initialize CAN interface
    can = MCP2515()
    can.Init(speed="250KBPS")

    target_node_id = 2  # Node we want to communicate with

    print(f"CANopen Master Example - communicating with node {target_node_id}")

    # Send NMT commands
    def send_nmt_command(cmd, node_id=0):
        """Send NMT command (0 = broadcast)"""
        frame = CanFrame(id=0x000, payload=[cmd, node_id])
        can.Send(frame)
        print(f"Sent NMT command 0x{cmd:02X} to node {node_id}")

    # Send SDO read request
    def send_sdo_read(node_id, index, subindex=0):
        """Send SDO upload (read) request"""
        cob_id = 0x600 + node_id
        payload = [0x40, index & 0xFF, (index >> 8) & 0xFF, subindex, 0, 0, 0, 0]
        frame = CanFrame(id=cob_id, payload=payload)
        can.Send(frame)
        print(
            f"Sent SDO read request to node {node_id}: index=0x{index:04X}, sub={subindex}"
        )

    # Send SDO write request
    def send_sdo_write(node_id, index, subindex, data):
        """Send SDO download (write) request"""
        cob_id = 0x600 + node_id
        cmd = 0x22 | ((4 - len(data)) << 2)  # Expedited transfer with size
        payload = [cmd, index & 0xFF, (index >> 8) & 0xFF, subindex]
        payload.extend(data[:4])
        payload.extend([0] * (8 - len(payload)))
        frame = CanFrame(id=cob_id, payload=payload)
        can.Send(frame)
        print(
            f"Sent SDO write request to node {node_id}: index=0x{index:04X}, sub={subindex}, data={data}"
        )

    # Example sequence
    time.sleep(1)

    # Reset all nodes
    send_nmt_command(0x82, 0)  # Reset communication
    time.sleep(1)

    # Start specific node
    send_nmt_command(0x01, target_node_id)  # Start remote node
    time.sleep(1)

    # Read identity object
    send_sdo_read(target_node_id, 0x1018, 1)  # Vendor ID
    time.sleep(0.5)

    send_sdo_read(target_node_id, 0x1018, 2)  # Product code
    time.sleep(0.5)

    # Write a custom value
    send_sdo_write(target_node_id, 0x2000, 0, [123])
    time.sleep(0.5)

    # Read it back
    send_sdo_read(target_node_id, 0x2000, 0)

    # Monitor responses
    print("Monitoring responses...")
    start_time = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start_time) < 10000:  # 10 seconds
        while can.CheckReceiveBuffer():
            frame = can.Receive()
            print(f"Received: {frame}")

        time.sleep_ms(100)


if __name__ == "__main__":
    print("CANopen Examples")
    print("1. Simple I/O Node")
    print("2. SDO Example")
    print("3. Master Example")
    print()

    # Run the simple example by default
    # Change this to try different examples:

    # simple_canopen_example()
    # canopen_sdo_example()
    # canopen_master_example()

    # Default: simple I/O node
    simple_canopen_example()
