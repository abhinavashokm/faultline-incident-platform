import pytest
from app.delivery.email import mask_email, strip_crlf


def test_mask_email():
    assert mask_email("alerts@faultline.io") == "a***s@faultline.io"
    assert mask_email("me@domain.com") == "m***@domain.com"
    assert mask_email("a@domain.com") == "a***@domain.com"
    assert mask_email("invalid-email") == "***"


def test_strip_crlf():
    dirty_subject = "Test Channel\r\nBcc: hacker@example.com\r"
    clean_subject = strip_crlf(dirty_subject)
    assert "\r" not in clean_subject
    assert "\n" not in clean_subject
    assert clean_subject == "Test ChannelBcc: hacker@example.com"
