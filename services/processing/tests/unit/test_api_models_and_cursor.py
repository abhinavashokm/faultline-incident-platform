from datetime import datetime, timezone
import uuid

import pytest
from pydantic import ValidationError

from app.errors.cursor import (
    decode_event_cursor,
    decode_issue_cursor,
    encode_event_cursor,
    encode_issue_cursor,
)
from app.errors.schemas import UpdateIssueStatusRequest


def test_cursor_round_trip():
    dt = datetime(2026, 10, 31, 12, 30, 45, tzinfo=timezone.utc)
    item_id = uuid.uuid4()

    # Issue cursor
    issue_encoded = encode_issue_cursor(dt, item_id)
    assert isinstance(issue_encoded, str)
    decoded_dt, decoded_id = decode_issue_cursor(issue_encoded)
    assert decoded_dt == dt
    assert decoded_id == item_id

    # Event cursor
    event_encoded = encode_event_cursor(dt, item_id)
    assert isinstance(event_encoded, str)
    decoded_ev_dt, decoded_ev_id = decode_event_cursor(event_encoded)
    assert decoded_ev_dt == dt
    assert decoded_ev_id == item_id


def test_malformed_and_tampered_cursor():
    # 1. Non-base64
    with pytest.raises(Exception):
        decode_issue_cursor("!!!not_base64!!!")

    # 2. Base64 but invalid JSON
    import base64

    bad_json = base64.urlsafe_b64encode(b"not_json").decode("ascii")
    with pytest.raises(Exception):
        decode_issue_cursor(bad_json)

    # 3. Valid JSON but missing required fields
    missing_fields = base64.urlsafe_b64encode(b'{"last_seen_at": "2026-10-31T00:00:00Z"}').decode("ascii")
    with pytest.raises(Exception):
        decode_issue_cursor(missing_fields)

    # 4. Tampered cursor with invalid UUID
    tampered_id = base64.urlsafe_b64encode(b'{"last_seen_at": "2026-10-31T00:00:00Z", "id": "not-a-uuid"}').decode("ascii")
    with pytest.raises(Exception):
        decode_issue_cursor(tampered_id)

    # 5. Tampered cursor with invalid date
    tampered_date = base64.urlsafe_b64encode(f'{{"last_seen_at": "not-a-date", "id": "{uuid.uuid4()}"}}'.encode("ascii")).decode("ascii")
    with pytest.raises(Exception):
        decode_issue_cursor(tampered_date)


def test_patch_request_model_validation():
    # 1. Valid resolved request with release
    req = UpdateIssueStatusRequest(status="resolved", resolved_in_release="v1.2.0")
    assert req.status == "resolved"
    assert req.resolved_in_release == "v1.2.0"

    # 2. Valid ignored request
    req2 = UpdateIssueStatusRequest(status="ignored")
    assert req2.status == "ignored"
    assert req2.resolved_in_release is None

    # 3. Unknown field forbidden
    with pytest.raises(ValidationError) as exc_info:
        UpdateIssueStatusRequest.model_validate({"status": "resolved", "unknown_field": "val"})
    assert "extra_forbidden" in str(exc_info.value)

    # 4. resolved_in_release forbidden with status != resolved
    with pytest.raises(ValidationError) as exc_info:
        UpdateIssueStatusRequest(status="ignored", resolved_in_release="v1.0.0")
    assert "resolved_in_release is allowed only together with status 'resolved'" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        UpdateIssueStatusRequest(status="unresolved", resolved_in_release="v1.0.0")
    assert "resolved_in_release is allowed only together with status 'resolved'" in str(exc_info.value)

    # 5. Empty or whitespace-only resolved_in_release rejected
    with pytest.raises(ValidationError) as exc_info:
        UpdateIssueStatusRequest(status="resolved", resolved_in_release="   ")
    assert "cannot be empty" in str(exc_info.value)

    # 6. Over-long resolved_in_release (> 150 chars) rejected
    with pytest.raises(ValidationError) as exc_info:
        UpdateIssueStatusRequest(status="resolved", resolved_in_release="a" * 151)
    assert "at most 150 characters" in str(exc_info.value)

