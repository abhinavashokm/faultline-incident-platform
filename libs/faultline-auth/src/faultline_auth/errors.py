class InvalidToken(Exception):
    """Raised when a token is invalid, expired, malformed, or missing required claims."""


class KeysUnavailable(Exception):
    """Raised when key provider cannot obtain keys to verify a token."""

