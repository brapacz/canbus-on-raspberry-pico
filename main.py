from candriver import MCP2515
from canopen import CANopenNode, create_simple_io_node
import time
from machine import unique_id, Pin
from can_config import NODE_ID


def main():
    """CANopen node application"""
    print("=== CANopen Node ===")
    print("Hardware ID 0x%s" % unique_id().hex().upper())
    print("Node ID 0x%02X" % NODE_ID)

    # Initialize CAN interface
    print("Initializing CAN interface...")
    can = MCP2515()
    can.Init(speed="250KBPS")
    print("CAN interface ready")

    # Create CANopen node with I/O PDOs
    print(f"Creating CANopen node with ID {NODE_ID}")
    node, tpdo1, rpdo1 = create_simple_io_node(NODE_ID, can)

    # Set identity information based on hardware
    hw_id_bytes = unique_id()
    serial_number = int.from_bytes(hw_id_bytes[:4], "little")
    node.od.set_object(0x1018, 0x12345678, 0x01)  # Vendor ID
    node.od.set_object(0x1018, 0x00000001, 0x02)  # Product Code
    node.od.set_object(0x1018, 0x00010001, 0x03)  # Revision
    node.od.set_object(0x1018, serial_number, 0x04)  # Serial Number

    # Add some custom application objects
    node.od.set_object(0x2000, 0)  # Digital inputs status
    node.od.set_object(0x2001, 0)  # Digital outputs control
    node.od.set_object(0x2002, time.ticks_ms())  # System uptime

    # Start the node
    node.start()
    print("CANopen node started in Pre-Operational state")
    print("Send NMT Start command (0x01) to enter Operational state")

    # Setup LED if available
    try:
        led = Pin("LED", Pin.OUT)
        led_available = True
        print("LED available")
    except:
        led_available = False
        print("No LED available")

    counter = 0
    last_tpdo_time = time.ticks_ms()

    print("Entering main loop...")
    print("CANopen services:")
    print("- Heartbeat: Node status broadcast")
    print("- SDO: Object dictionary access")
    print("- PDO: Process data exchange")
    print("- NMT: Network management")

    while True:
        # Update CANopen node (handles all protocol services)
        node.update()

        # Application logic
        current_time = time.ticks_ms()

        # Update system uptime in object dictionary
        node.od.set_object(0x2002, current_time)

        # Check for received RPDO (digital outputs)
        if rpdo1.data[0] != node.od.get_object(0x2001):
            digital_outputs = rpdo1.data[0]
            node.od.set_object(0x2001, digital_outputs)
            print(f"Digital outputs updated: 0x{digital_outputs:02X}")

            # Control LED based on bit 0 of outputs
            if led_available:
                if digital_outputs & 0x01:
                    led.on()
                else:
                    led.off()

        # Send TPDO periodically when in operational state
        if node.state == 0x05:  # NMT_STATE_OPERATIONAL
            if time.ticks_diff(current_time, last_tpdo_time) >= 1000:  # Every 1 second
                # Simulate digital inputs (could be real GPIO reads)
                digital_inputs = (counter % 8) << 0  # Simulate some changing inputs
                node.od.set_object(0x2000, digital_inputs)

                # Prepare TPDO data
                tpdo1.data[0] = digital_inputs
                tpdo1.data[1] = counter & 0xFF
                tpdo1.data[2] = (current_time >> 8) & 0xFF  # Timestamp high byte
                tpdo1.data[3] = current_time & 0xFF  # Timestamp low byte

                # Send TPDO
                tpdo1.transmit()
                print(
                    f"TPDO1 sent - inputs: 0x{digital_inputs:02X}, counter: {counter}"
                )

                counter += 1
                last_tpdo_time = current_time

        time.sleep_ms(10)  # Small delay for system stability


if __name__ == "__main__":
    main()
