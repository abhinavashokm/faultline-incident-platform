import pytest
from faultline.constants import EVENTS_ENDPOINT
from faultline.dsn import Dsn, DsnError, parse_dsn


def test_parse_valid_https_dsn():
    dsn = parse_dsn("https://proj_api_key_123@errors.example.com")
    assert dsn.api_key == "proj_api_key_123"
    assert dsn.ingest_url == f"https://errors.example.com{EVENTS_ENDPOINT}"
    assert dsn.raw_dsn == "https://proj_api_key_123@errors.example.com"


def test_parse_valid_http_dsn_with_port():
    dsn = parse_dsn("http://dev_key@localhost:8000")
    assert dsn.api_key == "dev_key"
    assert dsn.ingest_url == f"http://localhost:8000{EVENTS_ENDPOINT}"


def test_parse_valid_dsn_with_trailing_slash():
    dsn = parse_dsn("https://my_key@faultline.corp.local/")
    assert dsn.api_key == "my_key"
    assert dsn.ingest_url == f"https://faultline.corp.local{EVENTS_ENDPOINT}"


def test_parse_valid_dsn_with_subpath():
    dsn = parse_dsn("https://my_key@faultline.corp.local/subpath")
    assert dsn.api_key == "my_key"
    assert dsn.ingest_url == f"https://faultline.corp.local/subpath{EVENTS_ENDPOINT}"


def test_parse_valid_dsn_with_full_path():
    dsn = parse_dsn(f"https://my_key@faultline.corp.local{EVENTS_ENDPOINT}")
    assert dsn.api_key == "my_key"
    assert dsn.ingest_url == f"https://faultline.corp.local{EVENTS_ENDPOINT}"


@pytest.mark.parametrize(
    "invalid_dsn",
    [
        "",
        None,
        123,
        "not_a_url",
        "ftp://key@errors.example.com",
        "https://errors.example.com",
        "https://@errors.example.com",
        "https://key@",
        "http://",
    ],
)
def test_parse_invalid_dsn(invalid_dsn):
    with pytest.raises(DsnError):
        parse_dsn(invalid_dsn)

