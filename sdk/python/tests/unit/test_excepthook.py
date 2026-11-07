import sys
import threading
from unittest.mock import MagicMock
import pytest

from faultline.client import Client, set_client
from faultline.config import Config
from faultline.integrations.excepthook import install_excepthooks, uninstall_excepthooks


@pytest.fixture(autouse=True)
def clean_excepthooks():
    uninstall_excepthooks()
    yield
    uninstall_excepthooks()
    set_client(None)


def test_sys_excepthook_chains_and_captures():
    previous_hook_called = False

    def dummy_previous_hook(exc_type, exc_val, exc_tb):
        nonlocal previous_hook_called
        previous_hook_called = True

    sys.excepthook = dummy_previous_hook

    mock_client = MagicMock()
    set_client(mock_client)

    install_excepthooks()

    try:
        raise ValueError("unhandled error")
    except ValueError as exc:
        exc_info = sys.exc_info()
        sys.excepthook(exc_info[0], exc_info[1], exc_info[2])

    assert previous_hook_called is True
    assert mock_client.capture_exception.called
    args, kwargs = mock_client.capture_exception.call_args
    assert isinstance(args[0], ValueError)
    assert kwargs.get("level") == "fatal"


def test_threading_excepthook_chains_and_captures():
    previous_hook_called = False

    def dummy_thread_hook(args):
        nonlocal previous_hook_called
        previous_hook_called = True

    if hasattr(threading, "excepthook"):
        threading.excepthook = dummy_thread_hook

    mock_client = MagicMock()
    set_client(mock_client)

    install_excepthooks()

    if hasattr(threading, "excepthook"):
        mock_args = MagicMock()
        mock_args.exc_value = RuntimeError("thread error")
        threading.excepthook(mock_args)

        assert previous_hook_called is True
        assert mock_client.capture_exception.called
        args, kwargs = mock_client.capture_exception.call_args
        assert isinstance(args[0], RuntimeError)
        assert kwargs.get("level") == "fatal"

