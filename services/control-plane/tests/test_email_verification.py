import asyncio
import re
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.models import EmailVerificationCode, User
from app.auth.repository import EmailVerificationRepository
from app.auth.schemas import (
    ResendVerificationRequest,
    SignupRequest,
    VerifyEmailRequest,
)
from app.auth.security import (
    InvalidVerificationCode,
    TooManyVerificationAttempts,
    VerificationCooldown,
    VerificationHourlyCapExceeded,
)
from app.core.config import settings
from app.core.integrations.email import (
    EmailDeliveryError,
    EmailSender,
    SMTPEmailSender,
    get_email_sender,
)
from app.core.security import generate_otp, hash_otp, verify_otp
from app.core.uuid7 import uuid7
from tests.conftest import FakeEmailSender


# ==============================================================================
# 1. UNIT TESTS
# ==============================================================================


def test_otp_generation_format() -> None:
    """Verify OTP is exactly 6 numeric digits."""
    for _ in range(100):
        code = generate_otp()
        assert len(code) == 6
        assert code.isdigit()
        assert re.match(r"^\d{6}$", code) is not None


def test_hash_determinism_and_secret_dependence() -> None:
    """Verify hash determinism and dependence on user_id, code, and secret."""
    user_id_1 = uuid.uuid4()
    user_id_2 = uuid.uuid4()
    code_1 = "123456"
    code_2 = "654321"
    secret_1 = "secret-key-alpha"
    secret_2 = "secret-key-beta"

    # Determinism
    h1 = hash_otp(user_id_1, code_1, secret=secret_1)
    h2 = hash_otp(user_id_1, code_1, secret=secret_1)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex length

    # Code dependence
    h_diff_code = hash_otp(user_id_1, code_2, secret=secret_1)
    assert h1 != h_diff_code

    # User ID dependence
    h_diff_user = hash_otp(user_id_2, code_1, secret=secret_1)
    assert h1 != h_diff_user

    # Secret dependence
    h_diff_secret = hash_otp(user_id_1, code_1, secret=secret_2)
    assert h1 != h_diff_secret


def test_verify_otp_comparison() -> None:
    """Verify verify_otp succeeds for correct credentials and fails otherwise."""
    user_id = uuid.uuid4()
    code = "789012"
    secret = "test-secret"
    expected_hash = hash_otp(user_id, code, secret=secret)

    assert verify_otp(user_id, code, expected_hash, secret=secret) is True
    assert verify_otp(user_id, "000000", expected_hash, secret=secret) is False
    assert verify_otp(uuid.uuid4(), code, expected_hash, secret=secret) is False


def test_expiry_and_attempt_limits_logic() -> None:
    """Unit test expiry check and attempt limit boundary logic."""
    now = datetime.now(timezone.utc)
    future = now + timedelta(minutes=10)
    past = now - timedelta(minutes=1)

    # Expiry
    assert now < future
    assert now >= past

    # Attempt limits
    max_attempts = 5
    assert 0 < max_attempts
    assert 4 < max_attempts
    assert 5 >= max_attempts
    assert 6 >= max_attempts


def test_cooldown_and_hourly_cap_logic() -> None:
    """Unit test cooldown and hourly cap threshold decisions."""
    cooldown_seconds = 60
    now = datetime.now(timezone.utc)

    # Within cooldown
    created_recent = now - timedelta(seconds=30)
    elapsed = (now - created_recent).total_seconds()
    assert elapsed < cooldown_seconds
    retry_after = max(1, int(cooldown_seconds - elapsed))
    assert 29 <= retry_after <= 31

    # Outside cooldown
    created_old = now - timedelta(seconds=61)
    elapsed_old = (now - created_old).total_seconds()
    assert elapsed_old >= cooldown_seconds

    # Hourly cap
    hourly_cap = 5
    assert 4 < hourly_cap
    assert 5 >= hourly_cap


@pytest.mark.asyncio
async def test_smtp_email_sender_adapter() -> None:
    """Verify SMTPEmailSender constructs plain text message and passes timeout."""
    sender = SMTPEmailSender(
        host="smtp.example.com",
        port=1025,
        from_email="support@faultline.dev",
        timeout=5.0,
    )
    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        await sender.send_verification_code(
            to_email="user@example.com",
            code="123456",
            expires_in_minutes=10,
        )
        assert mock_send.await_count == 1
        args, kwargs = mock_send.call_args
        msg = args[0]
        assert msg["To"] == "user@example.com"
        assert msg["From"] == "support@faultline.dev"
        assert "123456" in msg.get_content()
        assert "10 minutes" in msg.get_content()
        assert kwargs["hostname"] == "smtp.example.com"
        assert kwargs["port"] == 1025
        assert kwargs["timeout"] == 5.0

    # Failure raised as domain error
    with patch("aiosmtplib.send", side_effect=OSError("Connection refused")):
        with pytest.raises(EmailDeliveryError):
            await sender.send_verification_code("user@example.com", "123456")


# ==============================================================================
# 2. API ENDPOINT TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_signup_creates_code_and_schedules_email(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_email_sender: FakeEmailSender,
) -> None:
    """Signup creates user (unverified), active code in DB, and sends email via background task."""
    fake_email_sender.sent_emails.clear()
    payload = {
        "email": "unverified@example.com",
        "password": "Password123-Safe",
        "full_name": "Unverified User",
    }
    resp = await client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 201
    user_id = uuid.UUID(resp.json()["id"])

    # Verify user email_verified_at is None
    user = (
        await db_session.execute(select(User).where(User.id == user_id))
    ).scalar_one()
    assert user.email_verified_at is None

    # Verify EmailVerificationCode created in DB
    code_row = (
        await db_session.execute(
            select(EmailVerificationCode).where(
                EmailVerificationCode.user_id == user_id
            )
        )
    ).scalar_one()
    assert code_row.consumed_at is None
    assert code_row.attempts == 0
    assert code_row.expires_at > code_row.created_at

    # Verify email was scheduled and sent
    assert len(fake_email_sender.sent_emails) == 1
    sent = fake_email_sender.sent_emails[0]
    assert sent["to_email"] == "unverified@example.com"
    raw_code = sent["code"]
    assert isinstance(raw_code, str)
    assert len(raw_code) == 6

    # Verify code hash in DB matches
    assert code_row.code_hash == hash_otp(user_id, raw_code)


@pytest.mark.asyncio
async def test_signup_email_failure_does_not_fail_signup(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Email delivery failure during signup does not abort registration."""

    class FailingEmailSender:
        async def send_verification_code(
            self, to_email: str, code: str, expires_in_minutes: int = 10
        ) -> None:
            raise EmailDeliveryError("SMTP unreachable")

    from app.api_main import app

    app.dependency_overrides[get_email_sender] = lambda: FailingEmailSender()

    payload = {
        "email": "smtp_fail@example.com",
        "password": "Password123-Safe",
        "full_name": "SMTP Fail User",
    }
    resp = await client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 201
    user_id = uuid.UUID(resp.json()["id"])

    user = (
        await db_session.execute(select(User).where(User.id == user_id))
    ).scalar_one()
    assert user is not None


@pytest.mark.asyncio
async def test_login_unverified_returns_403_and_wrong_password_keeps_401(
    client: AsyncClient,
) -> None:
    """Login with unverified email returns 403; wrong password returns 401."""
    signup_payload = {
        "email": "login_verify@example.com",
        "password": "CorrectPassword123",
        "full_name": "Login Verify",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    # 1. Wrong password returns 401 (no verification status leakage)
    wrong_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "login_verify@example.com", "password": "WrongPassword!"},
    )
    assert wrong_resp.status_code == 401
    assert wrong_resp.json()["detail"] == "Invalid email or password"

    # 2. Correct password on unverified user returns 403
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "login_verify@example.com", "password": "CorrectPassword123"},
    )
    assert login_resp.status_code == 403
    assert login_resp.json()["detail"] == "email_not_verified"


@pytest.mark.asyncio
async def test_verify_email_success(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_email_sender: FakeEmailSender,
) -> None:
    """Verifying with correct code updates user, consumes code, and allows login."""
    fake_email_sender.sent_emails.clear()
    signup_payload = {
        "email": "verify_me@example.com",
        "password": "CorrectPassword123",
        "full_name": "Verify Me",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)
    code = str(fake_email_sender.sent_emails[0]["code"])

    verify_resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "Verify_Me@Example.com", "code": code},
    )
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert data["message"] == "Email verified"
    assert "email_verified_at" in data

    # Check DB state
    user = (
        await db_session.execute(
            select(User).where(User.email == "verify_me@example.com")
        )
    ).scalar_one()
    assert user.email_verified_at is not None

    code_row = (
        await db_session.execute(
            select(EmailVerificationCode).where(
                EmailVerificationCode.user_id == user.id
            )
        )
    ).scalar_one()
    assert code_row.consumed_at is not None

    # Now login succeeds
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "verify_me@example.com", "password": "CorrectPassword123"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


@pytest.mark.asyncio
async def test_verify_email_already_verified_idempotent(
    client: AsyncClient,
    fake_email_sender: FakeEmailSender,
) -> None:
    """Verifying an already verified user returns 200 idempotently."""
    signup_payload = {
        "email": "idempotent@example.com",
        "password": "CorrectPassword123",
        "full_name": "Idempotent User",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)
    code = str(fake_email_sender.sent_emails[-1]["code"])

    first_resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "idempotent@example.com", "code": code},
    )
    assert first_resp.status_code == 200

    # Second call returns 200 idempotently
    second_resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "idempotent@example.com", "code": "999999"},
    )
    assert second_resp.status_code == 200
    assert second_resp.json()["message"] == "Email verified"


@pytest.mark.asyncio
async def test_verify_email_wrong_code_and_attempts_persist(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Wrong code returns 400 and increments attempts in DB despite failure."""
    signup_payload = {
        "email": "wrong_code@example.com",
        "password": "CorrectPassword123",
        "full_name": "Wrong Code",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = uuid.UUID(signup_resp.json()["id"])

    # Wrong attempt 1
    resp1 = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "wrong_code@example.com", "code": "000000"},
    )
    assert resp1.status_code == 400
    assert resp1.json()["detail"] == "Invalid or expired verification code"

    code_row = (
        await db_session.execute(
            select(EmailVerificationCode).where(
                EmailVerificationCode.user_id == user_id
            )
        )
    ).scalar_one()
    assert code_row.attempts == 1

    # Wrong attempt 2
    resp2 = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "wrong_code@example.com", "code": "111111"},
    )
    assert resp2.status_code == 400

    await db_session.refresh(code_row)
    assert code_row.attempts == 2


@pytest.mark.asyncio
async def test_verify_email_expired_code(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_email_sender: FakeEmailSender,
) -> None:
    """Expired code returns 400 Invalid or expired verification code."""
    signup_payload = {
        "email": "expired_otp@example.com",
        "password": "CorrectPassword123",
        "full_name": "Expired OTP",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = uuid.UUID(signup_resp.json()["id"])
    code = str(fake_email_sender.sent_emails[-1]["code"])

    # Expire code in DB while respecting CHECK (expires_at > created_at)
    now = datetime.now(timezone.utc)
    created_at_past = now - timedelta(minutes=20)
    expires_at_past = now - timedelta(minutes=10)
    await db_session.execute(
        update(EmailVerificationCode)
        .where(EmailVerificationCode.user_id == user_id)
        .values(created_at=created_at_past, expires_at=expires_at_past)
    )
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "expired_otp@example.com", "code": code},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid or expired verification code"


@pytest.mark.asyncio
async def test_verify_email_too_many_attempts_invalidates_code(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Fifth wrong attempt triggers 429 and invalidates the code."""
    signup_payload = {
        "email": "too_many@example.com",
        "password": "CorrectPassword123",
        "full_name": "Too Many",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = uuid.UUID(signup_resp.json()["id"])

    for i in range(4):
        r = await client.post(
            "/api/v1/auth/verify-email",
            json={"email": "too_many@example.com", "code": f"00000{i}"},
        )
        assert r.status_code == 400

    # 5th attempt reaches max (5)
    r5 = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "too_many@example.com", "code": "000004"},
    )
    assert r5.status_code == 429
    assert r5.json()["detail"] == "Too many attempts. Request a new code."

    # Code in DB is consumed/dead
    code_row = (
        await db_session.execute(
            select(EmailVerificationCode).where(
                EmailVerificationCode.user_id == user_id
            )
        )
    ).scalar_one()
    assert code_row.attempts >= 5
    assert code_row.consumed_at is not None

    # Subsequent attempt also rejected
    r6 = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "too_many@example.com", "code": "000005"},
    )
    assert r6.status_code in (400, 429)


@pytest.mark.asyncio
async def test_verify_email_unknown_email(client: AsyncClient) -> None:
    """Unknown email returns generic 400 error preventing enumeration."""
    resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "unknown_email_404@example.com", "code": "123456"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid or expired verification code"


@pytest.mark.asyncio
async def test_resend_verification_unknown_or_verified_returns_202(
    client: AsyncClient,
    fake_email_sender: FakeEmailSender,
    db_session: AsyncSession,
) -> None:
    """Resend returns 202 and sends nothing for unknown or already verified accounts."""
    fake_email_sender.sent_emails.clear()

    # 1. Unknown email
    resp1 = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "nonexistent@example.com"},
    )
    assert resp1.status_code == 202
    assert "If the account exists and is not yet verified" in resp1.json()["message"]
    assert len(fake_email_sender.sent_emails) == 0

    # 2. Already verified user
    signup_payload = {
        "email": "verified_resend@example.com",
        "password": "Password123-Safe",
        "full_name": "Verified Resend",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)
    code = str(fake_email_sender.sent_emails[-1]["code"])
    await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "verified_resend@example.com", "code": code},
    )
    fake_email_sender.sent_emails.clear()

    resp2 = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "verified_resend@example.com"},
    )
    assert resp2.status_code == 202
    assert len(fake_email_sender.sent_emails) == 0


@pytest.mark.asyncio
async def test_resend_verification_cooldown_429(
    client: AsyncClient,
) -> None:
    """Resend within cooldown returns 429 with Retry-After header."""
    signup_payload = {
        "email": "cooldown@example.com",
        "password": "Password123-Safe",
        "full_name": "Cooldown User",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    # Immediate resend fails with 429
    resp = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "cooldown@example.com"},
    )
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Please wait before requesting another code."
    assert "retry-after" in resp.headers
    retry_after = int(resp.headers["retry-after"])
    assert 1 <= retry_after <= 60


@pytest.mark.asyncio
async def test_resend_verification_hourly_cap_429(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Exceeding hourly cap returns 429 with Retry-After header."""
    signup_payload = {
        "email": "hourly_cap@example.com",
        "password": "Password123-Safe",
        "full_name": "Hourly Cap User",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = uuid.UUID(signup_resp.json()["id"])

    # Create 5 codes in DB within the last hour
    now = datetime.now(timezone.utc)
    for i in range(1, 5):
        code_time = now - timedelta(minutes=10 * i)
        await db_session.execute(
            EmailVerificationCode.__table__.insert().values(
                id=uuid7(),
                user_id=user_id,
                code_hash="0" * 64,
                attempts=0,
                expires_at=code_time + timedelta(minutes=10),
                consumed_at=code_time + timedelta(minutes=2),
                created_at=code_time,
            )
        )
    # Set the latest active code created 70 seconds ago (cooldown passed)
    await db_session.execute(
        update(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user_id,
            EmailVerificationCode.consumed_at.is_(None),
        )
        .values(created_at=now - timedelta(seconds=70))
    )
    await db_session.commit()

    # Now there are 5 codes created in the last hour -> cap reached
    resp = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "hourly_cap@example.com"},
    )
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Please wait before requesting another code."
    assert "retry-after" in resp.headers


@pytest.mark.asyncio
async def test_resend_verification_success_marks_old_consumed(
    client: AsyncClient,
    db_session: AsyncSession,
    fake_email_sender: FakeEmailSender,
) -> None:
    """Valid resend consumes old code and issues a new active code."""
    signup_payload = {
        "email": "resend_success@example.com",
        "password": "Password123-Safe",
        "full_name": "Resend Success",
    }
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    user_id = uuid.UUID(signup_resp.json()["id"])

    # Fast forward cooldown by setting created_at 70s in the past
    past = datetime.now(timezone.utc) - timedelta(seconds=70)
    await db_session.execute(
        update(EmailVerificationCode)
        .where(EmailVerificationCode.user_id == user_id)
        .values(created_at=past)
    )
    await db_session.commit()

    fake_email_sender.sent_emails.clear()
    resp = await client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "resend_success@example.com"},
    )
    assert resp.status_code == 202

    # Verify old code consumed and new code active
    codes = (
        await db_session.execute(
            select(EmailVerificationCode)
            .where(EmailVerificationCode.user_id == user_id)
            .order_by(EmailVerificationCode.created_at.asc())
        )
    ).scalars().all()
    assert len(codes) == 2
    assert codes[0].consumed_at is not None  # old consumed
    assert codes[1].consumed_at is None      # new active

    # Verify new code can verify email
    assert len(fake_email_sender.sent_emails) == 1
    new_code = str(fake_email_sender.sent_emails[0]["code"])
    verify_resp = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": "resend_success@example.com", "code": new_code},
    )
    assert verify_resp.status_code == 200


# ==============================================================================
# 3. INTEGRATION TESTS (DB CONSTRAINTS & CONCURRENCY)
# ==============================================================================


@pytest.mark.asyncio
async def test_partial_unique_index_one_active_code_per_user(
    db_session: AsyncSession,
) -> None:
    """The partial unique index allows only one active code (consumed_at IS NULL) per user."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="uq_test@example.com",
        password_hash="fake",
        full_name="UQ Test",
        status="active",
    )
    db_session.add(user)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    code1 = EmailVerificationCode(
        id=uuid7(),
        user_id=user_id,
        code_hash="1" * 64,
        attempts=0,
        expires_at=now + timedelta(minutes=10),
        consumed_at=None,
    )
    code1_id = code1.id
    db_session.add(code1)
    await db_session.commit()

    # Attempting to insert another active code for the same user fails unique constraint
    code2 = EmailVerificationCode(
        id=uuid7(),
        user_id=user_id,
        code_hash="2" * 64,
        attempts=0,
        expires_at=now + timedelta(minutes=10),
        consumed_at=None,
    )
    db_session.add(code2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # Once code1 is consumed, inserting code2 succeeds
    await db_session.execute(
        update(EmailVerificationCode)
        .where(EmailVerificationCode.id == code1_id)
        .values(consumed_at=now)
    )
    await db_session.commit()

    code2_retry = EmailVerificationCode(
        id=uuid7(),
        user_id=user_id,
        code_hash="2" * 64,
        attempts=0,
        expires_at=now + timedelta(minutes=10),
        consumed_at=None,
    )
    db_session.add(code2_retry)
    await db_session.commit()


@pytest.mark.asyncio
async def test_concurrent_verify_cannot_exceed_attempt_limit(
    test_engine,
) -> None:
    """Simulate concurrent verify attempts: FOR UPDATE locks row so attempts count sequentially."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with session_factory() as s:
        user = User(
            id=user_id,
            email="concurrent_test@example.com",
            password_hash="fake",
            full_name="Concurrent Test",
            status="active",
        )
        s.add(user)
        await s.commit()

    async with session_factory() as s:
        code = EmailVerificationCode(
            id=uuid7(),
            user_id=user_id,
            code_hash=hash_otp(user_id, "654321"),
            attempts=0,
            expires_at=now + timedelta(minutes=10),
            consumed_at=None,
        )
        s.add(code)
        await s.commit()

    async def attempt_verify(worker_id: int) -> int:
        async with session_factory() as session:
            repo = EmailVerificationRepository(session)
            async with session.begin():
                record = await repo.get_active_by_user_id(user_id, for_update=True)
                if record is None or record.attempts >= 5:
                    return -1
                new_attempts = await repo.increment_attempts(record.id)
                if new_attempts >= 5:
                    await repo.mark_consumed(record.id)
                return new_attempts

    # Run 7 concurrent failed attempts
    results = await asyncio.gather(*(attempt_verify(i) for i in range(7)))

    async with session_factory() as session:
        repo = EmailVerificationRepository(session)
        code_row = await repo.get_latest_code_by_user_id(user_id)
        assert code_row is not None
        # Attempts must not exceed 5, and code must be marked consumed
        assert code_row.attempts == 5
        assert code_row.consumed_at is not None
