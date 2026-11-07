import os
from unittest.mock import MagicMock, patch
import pytest

import faultline
from faultline.client import Client, get_client, set_client
from faultline.config import Config
from faultline.dsn import DsnError


def test_init_sets_global_client():
    client = faultline.init(
        dsn="https://test_key@errors.example.com",
        release="v1.8.0",
        environment="staging",
        service="backend-api",
        install_sys_excepthook=False,
    )
    assert get_client() is client
    assert client.config.release == "v1.8.0"
    assert client.config.environment == "staging"
    assert client.config.service == "backend-api"
    faultline.close()
    assert get_client() is None


def test_init_reads_app_release_env_var(monkeypatch):
    monkeypatch.setenv("APP_RELEASE", "v2.0.0-git-sha")
    client = faultline.init(
        dsn="https://test_key@errors.example.com",
        install_sys_excepthook=False,
    )
    assert client.config.release == "v2.0.0-git-sha"
    faultline.close()


def test_init_raises_on_malformed_dsn():
    with pytest.raises(DsnError):
        faultline.init(dsn="not_valid_dsn", install_sys_excepthook=False)


def test_capture_before_init_does_not_crash():
    set_client(None)
    # Should safely return None without throwing
    res_exc = faultline.capture_exception(ValueError("test"))
    res_msg = faultline.capture_message("test message")
    assert res_exc is None
    assert res_msg is None
    assert faultline.flush() is True
    faultline.close()


def test_sdk_internal_exceptions_never_reach_host_app():
    """Proves that unexpected exceptions within SDK capture methods never crash host app."""
    faultline.init(
        dsn="https://test_key@errors.example.com",
        install_sys_excepthook=False,
    )
    client = get_client()
    assert client is not None

    # Force an unexpected internal error inside client.transport.send
    with patch.object(client.transport, "send", side_effect=RuntimeError("Simulated SDK explosion")):
        # Must return None and NOT raise RuntimeError
        result = faultline.capture_exception(Exception("host app error"))
        assert result is None

        result_msg = faultline.capture_message("host app message")
        assert result_msg is None

        # Flush error inside transport
        with patch.object(client.transport, "flush", side_effect=ZeroDivisionError("Boom")):
            flushed = faultline.flush()
            # Transport exception is caught by client and returns False
            assert flushed is False

        # Direct client flush error is caught by @safe_call and returns None
        with patch.object(client, "flush", side_effect=RuntimeError("Direct client crash")):
            flushed_direct = faultline.flush()
            assert flushed_direct is None

    faultline.close()
