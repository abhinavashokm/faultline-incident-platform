from faultline.redaction import redact_headers, redact_sensitive_data


def test_redact_sensitive_keys():
    data = {
        "password": "secretpassword",
        "user_token": "abc123xyz",
        "api_key": "live_key_999",
        "auth_header": "Bearer secret",
        "normal_key": "safe_value",
        "nested": {
            "credit_card": "1234",
            "safe": 42,
        },
    }
    redacted = redact_sensitive_data(data)
    assert redacted["password"] == "[REDACTED]"
    assert redacted["user_token"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["auth_header"] == "[REDACTED]"
    assert redacted["normal_key"] == "safe_value"
    assert redacted["nested"]["credit_card"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == 42


def test_redact_card_numbers_in_strings():
    text = "Payment received from card 4111-2222-3333-4444 on file"
    redacted = redact_sensitive_data(text)
    assert "[REDACTED]" in redacted
    assert "4111-2222-3333-4444" not in redacted


def test_redact_bearer_tokens_in_strings():
    text = "Request header had Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test"
    redacted = redact_sensitive_data(text)
    assert "Bearer [REDACTED]" in redacted


def test_redact_circular_structures():
    cyclic = {"key": "val"}
    cyclic["self"] = cyclic
    redacted = redact_sensitive_data(cyclic)
    assert redacted["key"] == "val"
    assert redacted["self"] == "[CIRCULAR]"


def test_redact_headers():
    headers = {
        "authorization": "Bearer token123",
        "cookie": "session=abc; secure",
        "x-api-key": "secret-123",
        "content-type": "application/json",
        "user-agent": "test-agent",
    }
    cleaned = redact_headers(headers)
    assert cleaned["authorization"] == "[REDACTED]"
    assert cleaned["cookie"] == "[REDACTED]"
    assert cleaned["x-api-key"] == "[REDACTED]"
    assert cleaned["content-type"] == "application/json"
    assert cleaned["user-agent"] == "test-agent"

