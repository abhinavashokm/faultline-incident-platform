import pytest
from faultline.dsn import Dsn, DsnError, parse_dsn


def test_parse_valid_https_dsn():
    dsn = parse_dsn("https://proj_api_key_123@errors.example.com")
    assert dsn.api_key == "proj_api_key_123"
    assert dsn.ingest_url == "https://errors.example.com/api/v1/events"
    assert dsn.raw_dsn == "https://proj_api_key_123@errors.example.com"


def test_parse_valid_http_dsn_with_port():
    dsn = parse_dsn("http://dev_key@localhost:8000")
    assert dsn.api_key == "dev_key"
    assert dsn.ingest_url == "http://localhost:8000/api/v1/events"


def test_parse_valid_dsn_with_trailing_slash():
    dsn = parse_dsn("https://my_key@faultline.corp.local/")
    assert dsn.api_key == "my_key"
    assert dsn.ingest_url == "https://faultline.corp.local/api/v1/events"


def test_parse_valid_dsn_with_subpath():
    dsn = parse_dsn("https://my_key@faultline.corp.local/subpath")
    assert dsn.api_key == "my_key"
    assert dsn.ingest_url == "https://faultline.corp.local/subpath/api/v1/events"


def test_parse_valid_dsn_with_full_path():
    dsn = parse_dsn("https://my_key@faultline.corp.local/api/v1/events")
    assert dsn.api_key == "my_key"
    assert dsn.ingest_url == "https://faultline.corp.local/api/v1/events"


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

