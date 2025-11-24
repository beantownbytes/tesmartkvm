"""TESmart KVM control library.

A Python library for controlling TESmart KVM switches over TCP/IP.
Supports port switching, buzzer control, LCD timeout configuration,
and auto input detection.
"""

from .client import TESmartKVM
from .config import Config, Connection, load_config
from .exceptions import (
    TESmartError,
    CommunicationError,
    InvalidResponseError,
    InvalidPortError,
    InvalidValueError,
)

__version__ = "0.1.0"
__all__ = [
    "TESmartKVM",
    "Config",
    "Connection",
    "load_config",
    "TESmartError",
    "CommunicationError",
    "InvalidResponseError",
    "InvalidPortError",
    "InvalidValueError",
]
