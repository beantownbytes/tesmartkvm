"""Custom exceptions for TESmart KVM library."""


class TESmartError(Exception):
    """Base exception for all TESmart KVM errors."""
    pass


class CommunicationError(TESmartError):
    """Raised when communication with the KVM device fails."""
    pass


class InvalidResponseError(TESmartError):
    """Raised when the KVM returns an invalid or unexpected response."""
    pass


class InvalidPortError(TESmartError):
    """Raised when an invalid port number is specified."""
    pass


class InvalidValueError(TESmartError):
    """Raised when an invalid value is provided for a setting."""
    pass
