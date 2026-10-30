import uuid
import pytest

from app.adapters.key_resolver import (
    FakeProjectKeyResolver,
    InvalidKeyError,
    KeyResolverUnavailableError,
)
from app.adapters.redis_limiter import FakeRateLimiter


@pytest.mark.asyncio
async def test_fake_rate_limiter_exceeded():
    limiter = FakeRateLimiter(limit=3, window_seconds=60)
    project_id = uuid.uuid4()

    # 3 allowed
    for _ in range(3):
        allowed, retry_after = await limiter.is_allowed(project_id)
        assert allowed is True
        assert retry_after == 0

    # 4th blocked
    allowed, retry_after = await limiter.is_allowed(project_id)
    assert allowed is False
    assert retry_after == 60


@pytest.mark.asyncio
async def test_rate_limiter_fails_open():
    limiter = FakeRateLimiter(limit=1, window_seconds=60)
    limiter.should_fail_open = True
    project_id = uuid.uuid4()

    # Even over limit, fail open returns (True, 0)
    for _ in range(5):
        allowed, retry_after = await limiter.is_allowed(project_id)
        assert allowed is True
        assert retry_after == 0


@pytest.mark.asyncio
async def test_fake_key_resolver():
    resolver = FakeProjectKeyResolver()
    proj_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    resolver.add_key("valid-key", project_id=proj_id, workspace_id=ws_id, revoked=False)
    resolver.add_key("revoked-key", project_id=proj_id, workspace_id=ws_id, revoked=True)

    # Valid key
    resolved = await resolver.resolve("valid-key")
    assert resolved.project_id == proj_id
    assert resolved.workspace_id == ws_id

    # Revoked key
    with pytest.raises(InvalidKeyError):
        await resolver.resolve("revoked-key")

    # Unknown key
    with pytest.raises(InvalidKeyError):
        await resolver.resolve("unknown-key")

    # Outage / service unavailable
    resolver.simulate_unreachable = True
    with pytest.raises(KeyResolverUnavailableError):
        await resolver.resolve("valid-key")

