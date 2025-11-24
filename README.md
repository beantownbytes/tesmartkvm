# TESmart KVM Python Library

A Python library for controlling TESmart KVM switches over TCP/IP. This library provides a clean, Pythonic interface to interact with TESmart 8-port and 16-port HDMI KVM switches.

## Features

- **Configuration file support** - Store settings in `~/.config/tesmartkvm/config.toml`
- Port switching with automatic validation
- Buzzer control
- LCD timeout configuration
- Auto input detection control
- Automatic retry logic for reliable communication
- Context manager support
- Type hints for better IDE support
- Comprehensive error handling

## Installation

Install directly from source:

```bash
pip install -e .
```

This will install both the Python library and the `teskvm` CLI tool.

## Command-Line Interface (CLI)

The `teskvm` command provides a convenient way to control your TESmart KVM from the terminal.

### CLI Usage

```bash
# Get current active port
teskvm get port

# Set active port by number
teskvm set port 3

# Set active port by friendly name (requires config with port names)
teskvm set port desktop

# Control buzzer
teskvm set buzzer on
teskvm set buzzer off

# Control LCD timeout
teskvm set lcd 0      # Disable
teskvm set lcd 10     # 10 seconds
teskvm set lcd 30     # 30 seconds

# Control auto input detection
teskvm set auto on
teskvm set auto off

# List all port name mappings (requires config with port names)
teskvm list

# Use a different connection (requires multi-connection config)
teskvm -c office get port
teskvm --connection lab set port 5
```

### CLI Configuration

The CLI uses the same configuration file as the library. To use friendly port names and multiple connections, set up your config file at `~/.config/tesmartkvm/config.toml`:

**Multi-Connection Config Example:**

```toml
default_connection = "home"

[connections.home]
host = "192.168.1.10"
port = 5000
num_ports = 16

[connections.home.ports]
workstation = 1
server = 2
laptop = 3
gaming = 4

[connections.office]
host = "192.168.1.20"
port = 5000
num_ports = 8

[connections.office.ports]
desktop = 1
laptop = 2
```

With this configuration, you can use friendly names:

```bash
# Switch using friendly name
teskvm set port workstation

# Or use the number directly
teskvm set port 1

# Use a different connection
teskvm -c office set port laptop
```

### CLI Help

For full CLI help, run:

```bash
teskvm --help
teskvm get --help
teskvm set --help
```

## Configuration

The library supports loading default settings from a configuration file located at `~/.config/tesmartkvm/config.toml`. This allows you to set your KVM's IP address and other preferences once, instead of passing them every time.

### Creating a Configuration File

1. Create the configuration directory:
```bash
mkdir -p ~/.config/tesmartkvm
```

2. Create the config file `~/.config/tesmartkvm/config.toml`:
```toml
[connection]
host = "192.168.1.10"
port = 5000
timeout = 5.0
delay = 1.0

[device]
num_ports = 16
```

3. Use the library without specifying parameters:
```python
from tesmartkvm import TESmartKVM

# Automatically uses config file settings
kvm = TESmartKVM()
current_port = kvm.get_port()
```

### Configuration Options

| Section | Key | Type | Default | Description |
|---------|-----|------|---------|-------------|
| `connection` | `host` | string | `"192.168.1.10"` | IP address of the KVM |
| `connection` | `port` | integer | `5000` | TCP port number |
| `connection` | `timeout` | float | `5.0` | Socket timeout in seconds |
| `connection` | `delay` | float | `1.0` | Delay between commands (for stability) |
| `device` | `num_ports` | integer | `16` | Number of ports (8 or 16) |

### Overriding Configuration

You can override config file values by passing parameters explicitly:

```python
from tesmartkvm import TESmartKVM

# Config file has host="192.168.1.10"
# but temporarily connect to a different KVM
kvm = TESmartKVM(host="192.168.1.20")
```

### Example Configuration File

See `config.toml.example` in the repository for a complete example.

## Quick Start

```python
from tesmartkvm import TESmartKVM

# Connect to the KVM
kvm = TESmartKVM(host="192.168.1.10", port=5000)

# Get the current active port
current_port = kvm.get_port()
print(f"Current port: {current_port}")

# Switch to port 3
result = kvm.set_port(3)
print(f"Switched from port {result['old_port']} to {result['new_port']}")

# Disable the buzzer
kvm.set_buzzer(False)

# Set LCD timeout to 10 seconds
kvm.set_lcd_timeout(10)

# Enable auto input detection
kvm.set_auto_detect(True)
```

## Usage

### Basic Usage

```python
from tesmartkvm import TESmartKVM

# Uses config file settings if available, otherwise defaults (192.168.1.10:5000)
kvm = TESmartKVM()

# Or specify custom host and port (overrides config file)
kvm = TESmartKVM(host="192.168.1.10", port=5000)

# For 8-port KVM
kvm = TESmartKVM(num_ports=8)

# Use a custom config file location
kvm = TESmartKVM(config_path="/path/to/custom/config.toml")
```

### Context Manager

```python
from tesmartkvm import TESmartKVM

with TESmartKVM(host="192.168.1.10") as kvm:
    current_port = kvm.get_port()
    kvm.set_port(5)
```

### Port Management

```python
# Get current port (returns 1-16 for 16-port KVM)
current_port = kvm.get_port()

# Set port
result = kvm.set_port(3)
print(result)
# {'old_port': 1, 'new_port': 3, 'changed': True}

# Setting to the same port again won't send unnecessary commands
result = kvm.set_port(3)
print(result)
# {'old_port': 3, 'new_port': 3, 'changed': False}
```

### Buzzer Control

```python
# Enable buzzer
kvm.set_buzzer(True)

# Disable buzzer
kvm.set_buzzer(False)
```

### LCD Timeout

```python
# Disable LCD timeout
kvm.set_lcd_timeout(0)

# Set to 10 seconds
kvm.set_lcd_timeout(10)

# Set to 30 seconds
kvm.set_lcd_timeout(30)

# Invalid values raise InvalidValueError
try:
    kvm.set_lcd_timeout(15)
except InvalidValueError as e:
    print(f"Error: {e}")
```

### Auto Input Detection

```python
# Enable auto input detection
kvm.set_auto_detect(True)

# Disable auto input detection
kvm.set_auto_detect(False)
```

### Error Handling

```python
from tesmartkvm import (
    TESmartKVM,
    CommunicationError,
    InvalidPortError,
    InvalidValueError,
)

kvm = TESmartKVM(host="192.168.1.10")

try:
    # Try to set an invalid port
    kvm.set_port(99)
except InvalidPortError as e:
    print(f"Port error: {e}")

try:
    # Try to communicate with unreachable KVM
    current_port = kvm.get_port()
except CommunicationError as e:
    print(f"Communication failed: {e}")

try:
    # Try to set invalid LCD timeout
    kvm.set_lcd_timeout(15)
except InvalidValueError as e:
    print(f"Invalid value: {e}")
```

## API Reference

### TESmartKVM Class

#### Constructor

```python
TESmartKVM(
    host: str = "192.168.1.10",
    port: int = 5000,
    timeout: float = 5.0,
    delay: float = 1.0,
    num_ports: int = 16
)
```

**Parameters:**
- `host`: IP address of the KVM (default: "192.168.1.10")
- `port`: TCP port number (default: 5000)
- `timeout`: Socket timeout in seconds (default: 5.0)
- `delay`: Delay between commands in seconds for stability (default: 1.0)
- `num_ports`: Number of ports on the KVM, 8 or 16 (default: 16)

#### Methods

##### get_port(retries: int = 3) -> int

Get the currently active port.

**Returns:** Current active port number (1-indexed)

**Raises:** `CommunicationError`, `InvalidResponseError`

##### set_port(port: int) -> dict

Set the active port.

**Parameters:**
- `port`: Port number to activate (1 to num_ports)

**Returns:** Dictionary with 'old_port', 'new_port', and 'changed' keys

**Raises:** `InvalidPortError`, `CommunicationError`

##### set_buzzer(enabled: bool) -> None

Enable or disable the buzzer.

**Parameters:**
- `enabled`: True to enable, False to disable

**Raises:** `CommunicationError`

##### set_lcd_timeout(timeout: int) -> None

Set the LCD timeout.

**Parameters:**
- `timeout`: Timeout in seconds (0, 10, or 30)

**Raises:** `InvalidValueError`, `CommunicationError`

##### set_auto_detect(enabled: bool) -> None

Enable or disable auto input detection.

**Parameters:**
- `enabled`: True to enable, False to disable

**Raises:** `CommunicationError`

### Exceptions

All exceptions inherit from `TESmartError`:

- `TESmartError`: Base exception for all library errors
- `CommunicationError`: Communication with the KVM failed
- `InvalidResponseError`: KVM returned an invalid response
- `InvalidPortError`: Invalid port number specified
- `InvalidValueError`: Invalid value provided for a setting

## Advanced Configuration

### Custom Timeouts and Delays

```python
# Increase timeout for slow networks
kvm = TESmartKVM(
    host="192.168.1.10",
    timeout=10.0,  # 10 second timeout
    delay=2.0      # 2 second delay between commands
)
```

### Retry Configuration

```python
# Get port with custom retry count
current_port = kvm.get_port(retries=5)
```

## Protocol Details

The library implements the TESmart KVM protocol:

- **Preamble:** `0xAA 0xBB 0x03`
- **Command Format:** `PREAMBLE + TOKEN + VALUE + 0xEE`
- **Response Format:** `PREAMBLE + 0x11 + VALUE + TERMINATOR`

### Supported Commands

| Token | Value | Description |
|-------|-------|-------------|
| 0x01 | 0x01-0x10 | Set active port (1-16) |
| 0x02 | 0x00-0x01 | Set buzzer off/on |
| 0x03 | 0x00/0x0A/0x1E | Set LCD timeout (0/10s/30s) |
| 0x81 | 0x00-0x01 | Disable/Enable auto input detection |
| 0x10 | 0x00 | Get active port number |

## Requirements

- Python 3.7 or higher

