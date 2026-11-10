from dataclasses import dataclass
from urllib.parse import urlsplit

from faultline.constants import EVENTS_ENDPOINT, PERFORMANCE_ENDPOINT


class DsnError(ValueError):
    """Raised when a Faultline DSN is malformed."""
    pass


@dataclass(frozen=True)
class Dsn:
    """Parsed Faultline DSN containing authentication key and endpoint URLs."""
    raw_dsn: str
    api_key: str
    ingest_url: str
    performance_url: str


def parse_dsn(dsn_str: str) -> Dsn:
    """Parse a Faultline DSN string into a Dsn object.

    Expected format: https://<project_api_key>@<host>
    Returns Dsn object with api_key, ingest_url (POST /api/v1/events),
    and performance_url (POST /api/v1/ingest/performance).
    Raises DsnError if the DSN is malformed.
    """
    if not dsn_str or not isinstance(dsn_str, str):
        raise DsnError("Faultline DSN must be a non-empty string")

    dsn_str = dsn_str.strip()
    try:
        parsed = urlsplit(dsn_str)
    except Exception as exc:
        raise DsnError(f"Invalid Faultline DSN format: {exc}") from exc

    if parsed.scheme not in ("http", "https"):
        raise DsnError(
            f"Invalid DSN scheme '{parsed.scheme}'. Scheme must be 'http' or 'https'."
        )

    if not parsed.netloc:
        raise DsnError("Invalid DSN: missing network location/host")

    if "@" not in parsed.netloc:
        raise DsnError(
            "Invalid DSN: missing project API key. Expected format: https://<project_api_key>@<host>"
        )

    api_key, host_part = parsed.netloc.split("@", 1)
    if not api_key:
        raise DsnError("Invalid DSN: project API key cannot be empty")

    if not host_part:
        raise DsnError("Invalid DSN: host cannot be empty")

    # Construct the base ingest URL (/api/v1/events) and performance URL (/api/v1/ingest/performance)
    base_path = parsed.path.rstrip("/")
    if base_path.endswith(EVENTS_ENDPOINT):
        ingest_url = f"{parsed.scheme}://{host_part}{base_path}"
        prefix = base_path[:-len(EVENTS_ENDPOINT)]
        performance_url = f"{parsed.scheme}://{host_part}{prefix}{PERFORMANCE_ENDPOINT}"
    elif base_path:
        ingest_url = f"{parsed.scheme}://{host_part}{base_path}{EVENTS_ENDPOINT}"
        performance_url = f"{parsed.scheme}://{host_part}{base_path}{PERFORMANCE_ENDPOINT}"
    else:
        ingest_url = f"{parsed.scheme}://{host_part}{EVENTS_ENDPOINT}"
        performance_url = f"{parsed.scheme}://{host_part}{PERFORMANCE_ENDPOINT}"

    return Dsn(
        raw_dsn=dsn_str,
        api_key=api_key,
        ingest_url=ingest_url,
        performance_url=performance_url,
    )
