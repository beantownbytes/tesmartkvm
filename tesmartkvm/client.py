"""TESmart KVM client implementation."""

import socket
import time
from pathlib import Path
from typing import Optional

from .config import load_config
from .exceptions import (
    CommunicationError,
    InvalidPortError,
    InvalidResponseError,
    InvalidValueError,
)
from .protocol import (
    decode_response,
    get_port_command,
    set_auto_detect_command,
    set_buzzer_command,
    set_lcd_timeout_command,
    set_port_command,
)


class TESmartKVM:
    """Client for controlling TESmart KVM switches over TCP/IP.

    This class provides a high-level interface for controlling TESmart KVM
    switches using the network protocol. It supports port switching, buzzer
    control, LCD timeout configuration, and auto input detection.

    Configuration is loaded from ~/.config/tesmartkvm/config.toml if it exists.
    Explicit parameters override configuration file values.

    Args:
        host: IP address of the KVM (default: from config or 10.1.99.1)
        port: TCP port number (default: from config or 5000)
        timeout: Socket timeout in seconds (default: from config or 5.0)
        delay: Delay between commands in seconds for stability (default: from config or 1.0)
        num_ports: Number of ports on the KVM (default: from config or 16)
        config_path: Path to config file (default: ~/.config/tesmartkvm/config.toml)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: Optional[float] = None,
        delay: Optional[float] = None,
        num_ports: Optional[int] = None,
        config_path: Optional[Path] = None,
    ):
        config = load_config(config_path)

        self.host = host if host is not None else config.host
        self.port = port if port is not None else config.port
        self.timeout = timeout if timeout is not None else config.timeout
        self.delay = delay if delay is not None else config.delay
        self.num_ports = num_ports if num_ports is not None else config.num_ports

    def _send_command_no_response(self, command: bytes) -> None:
        """Send a command to the KVM without expecting a response.

        Used for commands like buzzer, LCD timeout, and auto-detect where
        the KVM's responses are unreliable or non-standard.

        Args:
            command: Raw command bytes to send

        Raises:
            CommunicationError: If communication fails
        """
        try:
            if hasattr(self, '_command_sent'):
                time.sleep(self.delay)
            self._command_sent = True

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
                sock.sendall(command)
                # Don't wait for response - just close connection

        except socket.timeout as e:
            raise CommunicationError(f"Connection timed out: {e}")
        except socket.error as e:
            raise CommunicationError(f"Socket error: {e}")
        except Exception as e:
            raise CommunicationError(f"Unexpected error: {e}")

    def _send_command(self, command: bytes, retries: int = 1) -> int:
        """Send a command to the KVM and return the response value.

        Args:
            command: Raw command bytes to send
            retries: Number of retry attempts (default: 1)

        Returns:
            Response value byte from the KVM

        Raises:
            CommunicationError: If communication fails after all retries
            InvalidResponseError: If the response format is invalid
        """
        last_error = None

        for attempt in range(retries):
            try:
                # Add delay for stability (except on first command)
                if attempt > 0 or hasattr(self, '_command_sent'):
                    time.sleep(self.delay)
                self._command_sent = True

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(self.timeout)
                    sock.connect((self.host, self.port))
                    sock.sendall(command)

                    # Read response - typically 5-6 bytes
                    # Format: AABB03 11 <value> [terminator]
                    # Need at least 5 bytes to get the value
                    response = b""
                    while len(response) < 6:
                        chunk = sock.recv(6 - len(response))
                        if not chunk:
                            break
                        response += chunk
                        # Need at least 5 bytes for a valid response with value
                        if len(response) >= 5:
                            try:
                                return decode_response(response)
                            except ValueError:
                                # Not enough data yet, continue reading
                                continue

                    if not response:
                        raise CommunicationError("No response received from KVM")

                    # Final decode attempt with whatever we got
                    return decode_response(response)

            except socket.timeout as e:
                last_error = CommunicationError(f"Connection timed out: {e}")
            except socket.error as e:
                last_error = CommunicationError(f"Socket error: {e}")
            except ValueError as e:
                last_error = InvalidResponseError(f"Invalid response format: {e}")
            except Exception as e:
                last_error = CommunicationError(f"Unexpected error: {e}")

        raise last_error

    def get_port(self, retries: int = 3) -> int:
        """Get the currently active port.

        Args:
            retries: Number of retry attempts (default: 3)

        Returns:
            Current active port number (1-indexed)

        Raises:
            CommunicationError: If communication fails
            InvalidResponseError: If the response is invalid
        """
        response = self._send_command(get_port_command(), retries=retries)
        # Response is 0-indexed, convert to 1-indexed
        return response + 1

    def set_port(self, port: int) -> dict:
        """Set the active port.

        This method checks if the port is already active before switching.
        If the port is already active, no command is sent.

        Args:
            port: Port number to activate (1 to num_ports)

        Returns:
            Dictionary with 'old_port' and 'new_port' keys

        Raises:
            InvalidPortError: If port is out of range
            CommunicationError: If communication fails
        """
        if not (1 <= port <= self.num_ports):
            raise InvalidPortError(
                f"Invalid port: {port}. Must be between 1 and {self.num_ports}"
            )

        old_port = self.get_port()

        if old_port == port:
            return {"old_port": old_port, "new_port": old_port, "changed": False}

        # Send set port command (port is 1-indexed, protocol uses hex value directly)
        # Convert to hex value for the command
        self._send_command(set_port_command(port))

        # Verify the port was changed
        new_port = self.get_port()

        return {"old_port": old_port, "new_port": new_port, "changed": old_port != new_port}

    def set_buzzer(self, enabled: bool) -> None:
        """Enable or disable the buzzer.

        Args:
            enabled: True to enable buzzer, False to disable

        Raises:
            CommunicationError: If communication fails
        """
        self._send_command_no_response(set_buzzer_command(enabled))

    def set_lcd_timeout(self, timeout: int) -> None:
        """Set the LCD timeout.

        Args:
            timeout: Timeout in seconds (0 to disable, or 10, or 30)

        Raises:
            InvalidValueError: If timeout is not a valid value
            CommunicationError: If communication fails
        """
        try:
            command = set_lcd_timeout_command(timeout)
        except ValueError as e:
            raise InvalidValueError(str(e))

        self._send_command_no_response(command)

    def set_auto_detect(self, enabled: bool) -> None:
        """Enable or disable auto input detection.

        Args:
            enabled: True to enable auto detection, False to disable

        Raises:
            CommunicationError: If communication fails
        """
        self._send_command_no_response(set_auto_detect_command(enabled))

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Reset command tracking
        if hasattr(self, '_command_sent'):
            delattr(self, '_command_sent')
        return False

    def __repr__(self) -> str:
        """String representation of the KVM client."""
        return f"TESmartKVM(host='{self.host}', port={self.port}, num_ports={self.num_ports})"
