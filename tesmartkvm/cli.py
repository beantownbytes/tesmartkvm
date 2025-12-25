"""Command-line interface for TESmart KVM control."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .client import TESmartKVM
from .config import Config, load_config
from .exceptions import (
    CommunicationError,
    InvalidPortError,
    InvalidValueError,
    TESmartError,
)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="teskvm",
        description="Control TESmart KVM switches over TCP/IP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  teskvm get port               Get current active port
  teskvm list                   List configured port names
  teskvm set port 3             Switch to port 3
  teskvm set port workstation   Switch to port by name (from config)
  teskvm set buzzer off         Disable buzzer
  teskvm set buzzer on          Enable buzzer
  teskvm set lcd 10             Set LCD timeout to 10 seconds
  teskvm set lcd off            Disable LCD timeout
  teskvm set auto on            Enable auto input detection
  teskvm set auto off           Disable auto input detection

Configuration:
  Settings can be stored in ~/.config/tesmartkvm/config.toml
  Use --host, --port, etc. to override config file values.
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--host",
        type=str,
        help="KVM IP address (overrides config file)",
    )

    parser.add_argument(
        "--port",
        type=int,
        help="KVM TCP port (overrides config file)",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        help="Socket timeout in seconds (overrides config file)",
    )

    parser.add_argument(
        "--delay",
        type=float,
        help="Delay between commands in seconds (overrides config file)",
    )

    parser.add_argument(
        "--num-ports",
        type=int,
        choices=[8, 16],
        help="Number of ports on the KVM (overrides config file)",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config file (default: ~/.config/tesmartkvm/config.toml)",
    )

    parser.add_argument(
        "--connection",
        "-c",
        type=str,
        help="Connection name to use (from config file)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    subparsers.add_parser(
        "list",
        help="List configured port names",
    )

    get_parser = subparsers.add_parser(
        "get",
        help="Get current settings",
    )
    get_parser.add_argument(
        "property",
        choices=["port"],
        help="Property to get (only 'port' is supported by the KVM protocol)",
    )

    set_parser = subparsers.add_parser(
        "set",
        help="Set KVM settings",
    )
    set_subparsers = set_parser.add_subparsers(dest="property", help="Property to set")

    set_port_parser = set_subparsers.add_parser("port", help="Set active port")
    set_port_parser.add_argument(
        "value",
        type=str,
        help="Port number (1-16) or friendly name from config",
    )

    set_buzzer_parser = set_subparsers.add_parser("buzzer", help="Set buzzer state")
    set_buzzer_parser.add_argument(
        "value",
        choices=["on", "off", "1", "0"],
        help="Buzzer state (on/off or 1/0)",
    )

    set_lcd_parser = set_subparsers.add_parser("lcd", help="Set LCD timeout")
    set_lcd_parser.add_argument(
        "value",
        choices=["off", "0", "10", "30"],
        help="Timeout in seconds (off/0, 10, or 30)",
    )

    set_auto_parser = set_subparsers.add_parser("auto", help="Set auto input detection")
    set_auto_parser.add_argument(
        "value",
        choices=["on", "off", "1", "0"],
        help="Auto detection state (on/off or 1/0)",
    )

    return parser


def handle_list(config: Config) -> int:
    """Handle the 'list' command to show port name mappings.

    Args:
        config: Config instance

    Returns:
        Exit code (0 for success)
    """
    if not config.port_names:
        print("No port names configured")
        print(f"Add port names to {config.config_path}")
        print("\nExample:")
        print("[ports]")
        print("workstation = 1")
        print("server = 2")
        return 0

    print("Configured port names:")
    sorted_ports = sorted(config.port_names.items(), key=lambda x: x[1])
    max_name_len = max(len(name) for name in config.port_names.keys())
    for name, port_num in sorted_ports:
        print(f"  {name:<{max_name_len}} = {port_num}")
    return 0


def handle_get_port(kvm: TESmartKVM, config: Config) -> int:
    """Handle the 'get port' command.

    Args:
        kvm: TESmartKVM instance
        config: Config instance for resolving port names

    Returns:
        Exit code (0 for success)
    """
    try:
        port = kvm.get_port()
        port_name = config.get_port_name(port)
        if port_name:
            print(f"{port} ({port_name})")
        else:
            print(f"{port} (NO_ALIAS)")
        return 0
    except TESmartError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_set_port(kvm: TESmartKVM, port_identifier: str, config: Config) -> int:
    """Handle the 'set port' command.

    Args:
        kvm: TESmartKVM instance
        port_identifier: Port number or friendly name
        config: Config instance for resolving port names

    Returns:
        Exit code (0 for success)
    """
    port = config.resolve_port(port_identifier)
    if port is None:
        print(f"Error: Invalid port '{port_identifier}'", file=sys.stderr)
        print(f"Must be a number (1-{config.num_ports}) or a configured port name", file=sys.stderr)
        if config.port_names:
            print(f"Available port names: {', '.join(sorted(config.port_names.keys()))}", file=sys.stderr)
        return 1

    try:
        result = kvm.set_port(port)
        new_port = result['new_port']
        port_name = config.get_port_name(new_port)
        if port_name:
            port_display = f"{new_port} ({port_name})"
        else:
            port_display = f"{new_port} (NO_ALIAS)"
        if result["changed"]:
            print(f"Switched to port {port_display}")
        else:
            print(f"Already on port {port_display}")
        return 0
    except InvalidPortError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except TESmartError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_set_buzzer(kvm: TESmartKVM, state: str) -> int:
    """Handle the 'set buzzer' command.

    Args:
        kvm: TESmartKVM instance
        state: Buzzer state (on/off/1/0)

    Returns:
        Exit code (0 for success)
    """
    try:
        enabled = state in ["on", "1"]
        kvm.set_buzzer(enabled)
        print(f"Buzzer {'enabled' if enabled else 'disabled'}")
        return 0
    except TESmartError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_set_lcd(kvm: TESmartKVM, timeout: str) -> int:
    """Handle the 'set lcd' command.

    Args:
        kvm: TESmartKVM instance
        timeout: Timeout value (off/0/10/30)

    Returns:
        Exit code (0 for success)
    """
    try:
        timeout_value = 0 if timeout in ["off", "0"] else int(timeout)
        kvm.set_lcd_timeout(timeout_value)
        if timeout_value == 0:
            print("LCD timeout disabled")
        else:
            print(f"LCD timeout set to {timeout_value} seconds")
        return 0
    except (InvalidValueError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except TESmartError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_set_auto(kvm: TESmartKVM, state: str) -> int:
    """Handle the 'set auto' command.

    Args:
        kvm: TESmartKVM instance
        state: Auto detection state (on/off/1/0)

    Returns:
        Exit code (0 for success)
    """
    try:
        enabled = state in ["on", "1"]
        kvm.set_auto_detect(enabled)
        print(f"Auto input detection {'enabled' if enabled else 'disabled'}")
        return 0
    except TESmartError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (default: sys.argv[1:])

    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    config_path = args.config if args.config is not None else None
    connection_name = args.connection if args.connection is not None else None

    try:
        config = load_config(config_path, connection_name)
        # Eagerly validate connection exists by accessing active_connection
        _ = config.active_connection
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    kvm_params = {}
    if args.host is not None:
        kvm_params["host"] = args.host
    if args.port is not None:
        kvm_params["port"] = args.port
    if args.timeout is not None:
        kvm_params["timeout"] = args.timeout
    if args.delay is not None:
        kvm_params["delay"] = args.delay
    if args.num_ports is not None:
        kvm_params["num_ports"] = args.num_ports
    if config_path is not None:
        kvm_params["config_path"] = config_path

    try:
        kvm = TESmartKVM(**kvm_params)
    except Exception as e:
        print(f"Error initializing KVM connection: {e}", file=sys.stderr)
        return 1

    if args.command == "list":
        return handle_list(config)
    elif args.command == "get":
        if args.property == "port":
            return handle_get_port(kvm, config)
        else:
            print(f"Error: Cannot get '{args.property}' - not supported by KVM protocol", file=sys.stderr)
            return 1
    elif args.command == "set":
        if not args.property:
            parser.print_help()
            return 1
        if args.property == "port":
            return handle_set_port(kvm, args.value, config)
        elif args.property == "buzzer":
            return handle_set_buzzer(kvm, args.value)
        elif args.property == "lcd":
            return handle_set_lcd(kvm, args.value)
        elif args.property == "auto":
            return handle_set_auto(kvm, args.value)
        else:
            parser.print_help()
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
