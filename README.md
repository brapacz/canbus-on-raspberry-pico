# Pico CAN Python - CANopen Implementation

A minimalistic CANopen implementation for MicroPython on Raspberry Pi Pico, built on top of the MCP2515 CAN controller driver.

## Original CAN Driver

This project extends the original Raspberry Pico CAN bus example code for the Waveshare Pico CAN module (<https://www.waveshare.com/pico-can-b.htm>). The base CAN driver functionality is preserved and enhanced with CANopen protocol support.

## Features

### Core CANopen Services

- **NMT (Network Management)**: Node state control and monitoring
- **SDO (Service Data Object)**: Object dictionary access for configuration and monitoring
- **PDO (Process Data Object)**: Real-time process data exchange
- **Heartbeat**: Node presence monitoring
- **Object Dictionary**: Standardized data storage and access

### Hardware Support

- Raspberry Pi Pico with MCP2515 CAN controller
- SPI communication interface
- Configurable CAN bus speeds (5K to 1M bps)

## Files

- `candriver.py` - Low-level MCP2515 CAN controller driver and CanFrame class
- `canopen.py` - Minimalistic CANopen protocol implementation
- `canopen_examples.py` - Example applications and usage patterns
- `main.py` - Main application with both basic CAN and CANopen modes
- `can_config.py` - Node configuration (NODE_ID)

## Quick Start

### Basic Usage

```python
from candriver import MCP2515
from canopen import CANopenNode, create_simple_io_node
from can_config import NODE_ID

# Initialize CAN interface
can = MCP2515()
can.Init(speed="250KBPS")

# Create CANopen node
node, tpdo1, rpdo1 = create_simple_io_node(NODE_ID, can)
node.start()

# Main loop
while True:
    node.update()  # Handle CANopen protocol
    # Your application code here
```

### Object Dictionary Access

```python
# Set object values
node.od.set_object(0x2000, 42)           # Integer
node.od.set_object(0x2001, "Hello")      # String
node.od.set_object(0x2002, [1,2,3,4])    # Array

# Get object values
value = node.od.get_object(0x2000)
```

### PDO Communication

```python
# Transmit PDO
tpdo1.data[0] = sensor_value
tpdo1.transmit()

# Receive PDO (automatically processed in node.update())
output_value = rpdo1.data[0]
```

### NMT Commands

```python
# Send NMT commands (from master)
frame = CanFrame(id=0x000, payload=[0x01, node_id])  # Start node
can.Send(frame)

frame = CanFrame(id=0x000, payload=[0x80, node_id])  # Pre-operational
can.Send(frame)
```

## CANopen Object Dictionary

### Standard Objects

- `0x1000` - Device Type
- `0x1001` - Error Register
- `0x1018` - Identity Object (Vendor ID, Product Code, etc.)
- `0x1200` - SDO Server Parameter
- `0x1400+` - RPDO Parameters
- `0x1800+` - TPDO Parameters

### Custom Application Objects

- `0x2000+` - Application-specific data

## Communication Objects

### Function Codes

- `0x000` - NMT
- `0x080` - SYNC/Emergency
- `0x180+node_id` - TPDO1
- `0x200+node_id` - RPDO1
- `0x580+node_id` - SDO Response (TX)
- `0x600+node_id` - SDO Request (RX)
- `0x700+node_id` - Heartbeat

## Examples

### 1\. Simple I/O Node

```bash
python canopen_examples.py
# or modify main.py and set USE_CANOPEN = True
```

### 2\. SDO Communication

Demonstrates object dictionary read/write operations.

### 3\. Master/Client Example

Shows how to control other CANopen nodes.

## Hardware Connections

### MCP2515 to Pico

- VCC → 3.3V
- GND → GND
- CS → GPIO 5
- SCK → GPIO 6
- MOSI → GPIO 7
- MISO → GPIO 4
- INT → (optional) GPIO for interrupts

### CAN Bus

- CANH/CANL to CAN transceiver (e.g., TJA1050)
- 120Ω termination resistors at bus ends
- Twisted pair cable for longer distances

## Configuration

### Node ID

Edit `can_config.py` to set your node ID (1-127):

```python
NODE_ID = 1  # Change this for each node
```

### CAN Speed

Supported speeds in `candriver.py`:

- 5KBPS, 10KBPS, 20KBPS, 50KBPS
- 100KBPS, 125KBPS, 250KBPS, 500KBPS
- 800KBPS, 1000KBPS

## Protocol Details

### NMT States

- **Initializing** (0x00) - Node starting up
- **Pre-operational** (0x7F) - Configuration mode
- **Operational** (0x05) - Normal operation
- **Stopped** (0x04) - Emergency stop

### SDO Transfer Types

- **Expedited** - Data ≤ 4 bytes in single frame
- **Segmented** - Larger data in multiple frames (basic support)

### Error Handling

- Automatic frame validation
- Timeout handling for SDO transfers
- NMT state management
- Object dictionary bounds checking

## Limitations

This is a minimalistic implementation focusing on:

- Basic CANopen functionality
- Small memory footprint for microcontrollers
- Educational and simple application use

Missing features:

- Full segmented SDO transfers
- SYNC producer/consumer
- Emergency objects
- Complex PDO mapping
- Layer Setting Services (LSS)
- Comprehensive error handling

## License

Based on the original candriver.py from: <https://github.com/wojciech-kochanski/raspberry-pico-can-bus>

## Contributing

Feel free to extend this implementation with additional CANopen features as needed for your applications.
