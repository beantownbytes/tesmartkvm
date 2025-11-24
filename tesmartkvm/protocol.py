"""Protocol implementation for TESmart KVM communication."""

from typing import Tuple


# Protocol constants
PREAMBLE = bytes([0xAA, 0xBB, 0x03])
TERMINATOR = 0xEE
RESPONSE_TOKEN = 0x11

# Command tokens
CMD_SET_PORT = 0x01
CMD_SET_BUZZER = 0x02
CMD_SET_LCD_TIMEOUT = 0x03
CMD_SET_AUTO_DETECT = 0x81
CMD_GET_PORT = 0x10


def encode_command(token: int, value: int) -> bytes:
    """Encode a command to send to the KVM.

    Args:
        token: Command token (e.g., CMD_SET_PORT)
        value: Command value

    Returns:
        Encoded command bytes in format: AABB03<token><value>EE
    """
    return PREAMBLE + bytes([token, value, TERMINATOR])


def decode_response(response: bytes) -> int:
    """Decode a response from the KVM.

    The KVM may return responses in different formats:
    - 4 bytes: AABB03 <value>
    - 5 bytes: AABB03 11 <value>
    - 6 bytes: AABB03 11 <value> <terminator>

    Args:
        response: Raw response bytes from the KVM

    Returns:
        The response value byte

    Raises:
        ValueError: If the response format is invalid
    """
    if len(response) < 4:
        raise ValueError(f"Response too short: expected at least 4 bytes, got {len(response)}")

    # Check preamble
    if response[:3] != PREAMBLE:
        raise ValueError(f"Invalid preamble: expected {PREAMBLE.hex()}, got {response[:3].hex()}")

    # Extract the value byte based on response length
    # The bash script uses: echo $response | cut -c 9-10
    # Which extracts byte index 4 from hex string (positions 9-10 = 5th byte)
    if len(response) >= 5:
        # Standard format: AABB03 11 <value> [EE]
        return response[4]
    else:
        # Short format: AABB03 <value>
        return response[3]


def get_port_command() -> bytes:
    """Create a command to get the current active port."""
    return encode_command(CMD_GET_PORT, 0x00)


def set_port_command(port: int) -> bytes:
    """Create a command to set the active port.

    Args:
        port: Port number (1-16)

    Returns:
        Encoded command bytes
    """
    # Port is 1-indexed in the API, but 0-indexed in the protocol
    return encode_command(CMD_SET_PORT, port)


def set_buzzer_command(enabled: bool) -> bytes:
    """Create a command to enable/disable the buzzer.

    Args:
        enabled: True to enable buzzer, False to disable

    Returns:
        Encoded command bytes
    """
    return encode_command(CMD_SET_BUZZER, 0x01 if enabled else 0x00)


def set_lcd_timeout_command(timeout: int) -> bytes:
    """Create a command to set the LCD timeout.

    Args:
        timeout: Timeout in seconds (0 for disabled, 10, or 30)

    Returns:
        Encoded command bytes

    Raises:
        ValueError: If timeout is not a valid value
    """
    timeout_map = {
        0: 0x00,
        10: 0x0A,
        30: 0x1E,
    }

    if timeout not in timeout_map:
        raise ValueError(f"Invalid timeout: {timeout}. Must be 0, 10, or 30")

    return encode_command(CMD_SET_LCD_TIMEOUT, timeout_map[timeout])


def set_auto_detect_command(enabled: bool) -> bytes:
    """Create a command to enable/disable auto input detection.

    Args:
        enabled: True to enable auto detection, False to disable

    Returns:
        Encoded command bytes
    """
    return encode_command(CMD_SET_AUTO_DETECT, 0x01 if enabled else 0x00)
