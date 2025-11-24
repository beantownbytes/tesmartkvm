"""Configuration management for TESmart KVM library."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "tesmartkvm" / "config.toml"

DEFAULT_CONNECTION_CONFIG = {
    "host": "10.1.99.1",
    "port": 5000,
    "timeout": 5.0,
    "delay": 1.0,
    "num_ports": 16,
    "port_names": {},
}


class Connection:
    """Represents a single KVM connection configuration."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize a connection.

        Args:
            name: Connection name
            config: Connection configuration dictionary
        """
        self.name = name
        self.host = config.get("host", DEFAULT_CONNECTION_CONFIG["host"])
        self.port = config.get("port", DEFAULT_CONNECTION_CONFIG["port"])
        self.timeout = config.get("timeout", DEFAULT_CONNECTION_CONFIG["timeout"])
        self.delay = config.get("delay", DEFAULT_CONNECTION_CONFIG["delay"])
        self.num_ports = config.get("num_ports", DEFAULT_CONNECTION_CONFIG["num_ports"])
        self.port_names = config.get("port_names", {})

    def resolve_port(self, port_identifier: str) -> Optional[int]:
        """Resolve a port identifier (name or number) to a port number.

        Args:
            port_identifier: Port name or number (as string)

        Returns:
            Port number if valid, None if invalid
        """
        # Try to parse as integer first
        try:
            port_num = int(port_identifier)
            if 1 <= port_num <= self.num_ports:
                return port_num
            return None
        except ValueError:
            # Not a number, try as a name
            return self.port_names.get(port_identifier.lower())

    def get_port_name(self, port_number: int) -> Optional[str]:
        """Get the friendly name for a port number.

        Args:
            port_number: Port number

        Returns:
            Port name if defined, None otherwise
        """
        for name, num in self.port_names.items():
            if num == port_number:
                return name
        return None

    def __repr__(self) -> str:
        """String representation."""
        return f"Connection(name='{self.name}', host='{self.host}', port={self.port})"


class Config:
    """Configuration manager for TESmart KVM.

    Configuration format:
        default_connection = "home"

        [connections.home]
        host = "192.168.1.10"
        port = 5000
        num_ports = 16

        [connections.home.ports]
        proxmox = 1
        workstation = 2

        [connections.work]
        host = "10.1.99.1"
        port = 5000
        num_ports = 8

        [connections.work.ports]
        laptop = 1
        desktop = 2
    """

    def __init__(self, config_path: Optional[Path] = None, connection_name: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Path to config file (default: ~/.config/tesmartkvm/config.toml)
            connection_name: Name of connection to use (overrides default_connection)
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._connections: Dict[str, Connection] = {}
        self._default_connection_name: Optional[str] = None
        self._requested_connection_name = connection_name
        self._load_config()

    def _load_config(self):
        """Load configuration from TOML file."""
        if not self.config_path.exists():
            # No config file, use defaults
            self._connections["default"] = Connection("default", DEFAULT_CONNECTION_CONFIG)
            self._default_connection_name = "default"
            return

        if tomllib is None:
            import warnings
            warnings.warn(
                "TOML library not available. Install 'tomli' for Python < 3.11 "
                "to use configuration files. Using default configuration.",
                UserWarning
            )
            self._connections["default"] = Connection("default", DEFAULT_CONNECTION_CONFIG)
            self._default_connection_name = "default"
            return

        try:
            with open(self.config_path, "rb") as f:
                toml_config = tomllib.load(f)

            # Require multi-connection format
            if "connections" not in toml_config:
                raise ValueError(
                    f"Invalid config format in {self.config_path}. "
                    "Missing [connections] section. "
                    "See config.toml.example for the correct format."
                )

            self._load_multi_connection_config(toml_config)

        except Exception as e:
            import warnings
            warnings.warn(
                f"Failed to load config from {self.config_path}: {e}. "
                "Using default configuration.",
                UserWarning
            )
            self._connections["default"] = Connection("default", DEFAULT_CONNECTION_CONFIG)
            self._default_connection_name = "default"

    def _load_multi_connection_config(self, toml_config: Dict[str, Any]):
        """Load multi-connection configuration format."""
        self._default_connection_name = toml_config.get("default_connection")

        connections_config = toml_config["connections"]

        for conn_name, conn_data in connections_config.items():
            config = DEFAULT_CONNECTION_CONFIG.copy()

            if "host" in conn_data:
                config["host"] = str(conn_data["host"])
            if "port" in conn_data:
                config["port"] = int(conn_data["port"])
            if "timeout" in conn_data:
                config["timeout"] = float(conn_data["timeout"])
            if "delay" in conn_data:
                config["delay"] = float(conn_data["delay"])
            if "num_ports" in conn_data:
                config["num_ports"] = int(conn_data["num_ports"])

            if "ports" in conn_data:
                config["port_names"] = self._parse_port_names(
                    conn_data["ports"],
                    config["num_ports"]
                )

            self._connections[conn_name] = Connection(conn_name, config)

        if not self._default_connection_name and self._connections:
            self._default_connection_name = list(self._connections.keys())[0]

    def _parse_port_names(self, ports_dict: Dict[str, Any], num_ports: int) -> Dict[str, int]:
        """Parse and validate port name mappings.

        Args:
            ports_dict: Dictionary of port names to numbers
            num_ports: Maximum number of ports

        Returns:
            Validated port name mappings
        """
        port_names = {}
        for name, port_num in ports_dict.items():
            try:
                port_num = int(port_num)
                if 1 <= port_num <= num_ports:
                    port_names[str(name).lower()] = port_num
                else:
                    import warnings
                    warnings.warn(
                        f"Port name '{name}' has invalid port number {port_num}. "
                        f"Must be between 1 and {num_ports}. Ignoring.",
                        UserWarning
                    )
            except (ValueError, TypeError):
                import warnings
                warnings.warn(
                    f"Port name '{name}' has invalid value. Ignoring.",
                    UserWarning
                )
        return port_names

    @property
    def active_connection(self) -> Connection:
        """Get the active connection.

        Returns:
            Active Connection instance

        Raises:
            ValueError: If requested connection doesn't exist
        """
        if self._requested_connection_name:
            if self._requested_connection_name not in self._connections:
                available = ", ".join(self._connections.keys())
                raise ValueError(
                    f"Connection '{self._requested_connection_name}' not found. "
                    f"Available connections: {available}"
                )
            return self._connections[self._requested_connection_name]

        if self._default_connection_name and self._default_connection_name in self._connections:
            return self._connections[self._default_connection_name]

        if self._connections:
            return list(self._connections.values())[0]

        # Should not happen, but return a default connection
        return Connection("default", DEFAULT_CONNECTION_CONFIG)

    @property
    def connection_names(self) -> list[str]:
        """Get list of configured connection names."""
        return list(self._connections.keys())

    @property
    def default_connection_name(self) -> Optional[str]:
        """Get the default connection name."""
        return self._default_connection_name

    # Convenience properties that delegate to active connection
    @property
    def host(self) -> str:
        """Get configured host for active connection."""
        return self.active_connection.host

    @property
    def port(self) -> int:
        """Get configured port for active connection."""
        return self.active_connection.port

    @property
    def timeout(self) -> float:
        """Get configured timeout for active connection."""
        return self.active_connection.timeout

    @property
    def delay(self) -> float:
        """Get configured delay for active connection."""
        return self.active_connection.delay

    @property
    def num_ports(self) -> int:
        """Get configured number of ports for active connection."""
        return self.active_connection.num_ports

    @property
    def port_names(self) -> Dict[str, int]:
        """Get port name mappings for active connection."""
        return self.active_connection.port_names

    def resolve_port(self, port_identifier: str) -> Optional[int]:
        """Resolve a port identifier for active connection."""
        return self.active_connection.resolve_port(port_identifier)

    def get_port_name(self, port_number: int) -> Optional[str]:
        """Get the friendly name for a port number in active connection."""
        return self.active_connection.get_port_name(port_number)

    def get_connection_params(self) -> Dict[str, Any]:
        """Get all connection parameters for TESmartKVM.

        Returns:
            Dictionary with host, port, timeout, delay, num_ports
        """
        conn = self.active_connection
        return {
            "host": conn.host,
            "port": conn.port,
            "timeout": conn.timeout,
            "delay": conn.delay,
            "num_ports": conn.num_ports,
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Config(path='{self.config_path}', "
            f"connections={list(self._connections.keys())}, "
            f"active='{self.active_connection.name}')"
        )


def load_config(config_path: Optional[Path] = None, connection_name: Optional[str] = None) -> Config:
    """Load configuration from file.

    Args:
        config_path: Path to config file (default: ~/.config/tesmartkvm/config.toml)
        connection_name: Name of connection to use

    Returns:
        Config instance
    """
    return Config(config_path, connection_name)
