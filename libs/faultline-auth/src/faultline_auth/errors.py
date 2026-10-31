class InvalidToken(Exception):
    """Raised when a token is invalid, expired, malformed, or missing required claims."""


class InvalidWorkspaceClaim(InvalidToken):
    """Raised when the workspace_id claim is present but not a valid UUID."""


class KeysUnavailable(Exception):
    """Raised when key provider cannot obtain keys to verify a token."""

