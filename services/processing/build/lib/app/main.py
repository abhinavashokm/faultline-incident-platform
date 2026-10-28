import asyncio
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

import asyncpg
from aiokafka import AIOKafkaConsumer

KAFKA_BOOTSTRAP = "localhost:9092"
TOPIC = "error-events"
GROUP_ID = "processing-errors-v4"
DB_DSN = "postgresql://faultline:faultline@localhost:5432/processing"

FINGERPRINT_VERSION = 1

# Creates the issue if it is new. The no-op DO UPDATE is only there so that
# RETURNING id works for an existing issue too. Counters are NOT touched here.
UPSERT_ISSUE = """
INSERT INTO processing.issues (
    id, workspace_id, project_id, fingerprint, fingerprint_version,
    title, exception_type, culprit, level,
    first_seen_at, last_seen_at, first_release, last_release
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $10, $11, $11)
ON CONFLICT (project_id, fingerprint)
DO UPDATE SET fingerprint = EXCLUDED.fingerprint
RETURNING id
"""

# The primary key on id is the dedup key. A redelivered event inserts nothing.
INSERT_EVENT = """
INSERT INTO processing.error_events (
    id, workspace_id, project_id, issue_id, fingerprint, event_type, level,
    exception_type, message, stack_frames, service, route_template, http_method,
    status_code, environment, release, user_hash, context, occurred_at
)
VALUES (
    $1, $2, $3, $4, $5, $6, $7,
    $8, $9, $10::jsonb, $11, $12, $13,
    $14, $15, $16, $17, $18::jsonb, $19
)
ON CONFLICT (id) DO NOTHING
RETURNING id
"""

# Only runs when the event insert succeeded, so duplicates never inflate counts.
UPDATE_ISSUE_COUNTERS = """
UPDATE processing.issues
SET occurrence_count = occurrence_count + 1,
    first_seen_at = LEAST(first_seen_at, $2),
    last_seen_at = GREATEST(last_seen_at, $2),
    last_release = CASE WHEN $2 >= last_seen_at THEN COALESCE($3, last_release)
                        ELSE last_release END,
    updated_at = now()
WHERE id = $1
"""


class InvalidEvent(Exception):
    """Payload is malformed. Retrying will never fix it (DLQ comes later)."""


def parse_event(raw: dict) -> dict:
    try:
        occurred_at = datetime.fromisoformat(raw["occurred_at"].replace("Z", "+00:00"))
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        return {
            "id": uuid.UUID(raw["event_id"]),
            "workspace_id": uuid.UUID(raw["workspace_id"]),
            "project_id": uuid.UUID(raw["project_id"]),
            "occurred_at": occurred_at,
            "exception_type": raw["exception_type"],
            "message": (raw.get("message") or "")[:2000],
            "stack_frames": raw.get("stack_frames") or [],
            "event_type": raw.get("event_type", "error"),
            "level": raw.get("level", "error"),
            "service": raw.get("service"),
            "route_template": raw.get("route_template"),
            "http_method": raw.get("http_method"),
            "status_code": raw.get("status_code"),
            "environment": raw.get("environment"),
            "release": raw.get("release"),
            "user_hash": raw.get("user_hash"),
            "context": raw.get("context") or {},
        }
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise InvalidEvent(str(exc)) from exc


def pick_frame(frames: list) -> dict | None:
    """Frames are ordered oldest to newest, so the last one is where it was raised.
    Prefer the application's own code over library code."""
    candidates = [f for f in frames if f.get("in_app")] or frames
    return candidates[-1] if candidates else None


def make_fingerprint(exception_type: str, message: str, frames: list) -> tuple[str, str | None]:
    """Same error type + same place in the code = same issue.
    Line numbers are left out on purpose, so a code change that shifts lines
    does not split one issue into two. Returns (fingerprint, culprit)."""
    frame = pick_frame(frames)
    if frame:
        location = f"{frame.get('file')}:{frame.get('function')}"
        culprit = f"{frame.get('function')} in {frame.get('file')}"[:255]
    else:
        location = re.sub(r"\d+", "N", message)  # no stack: use the message shape
        culprit = None
    raw = f"v{FINGERPRINT_VERSION}|{exception_type}|{location}"
    return hashlib.sha256(raw.encode()).hexdigest(), culprit


async def handle_event(pool: asyncpg.Pool, raw: dict) -> str:
    e = parse_event(raw)
    fingerprint, culprit = make_fingerprint(e["exception_type"], e["message"], e["stack_frames"])
    title = f"{e['exception_type']}: {e['message']}"[:500]

    async with pool.acquire() as conn:
        async with conn.transaction():
            issue_id = await conn.fetchval(
                UPSERT_ISSUE,
                uuid.uuid4(), e["workspace_id"], e["project_id"], fingerprint,
                FINGERPRINT_VERSION, title, e["exception_type"], culprit, e["level"],
                e["occurred_at"], e["release"],
            )
            inserted = await conn.fetchval(
                INSERT_EVENT,
                e["id"], e["workspace_id"], e["project_id"], issue_id, fingerprint,
                e["event_type"], e["level"], e["exception_type"], e["message"],
                json.dumps(e["stack_frames"]), e["service"], e["route_template"],
                e["http_method"], e["status_code"], e["environment"], e["release"],
                e["user_hash"], json.dumps(e["context"]), e["occurred_at"],
            )
            if inserted is None:
                return "duplicate, skipped"
            await conn.execute(UPDATE_ISSUE_COUNTERS, issue_id, e["occurred_at"], e["release"])
            return f"saved, issue {issue_id}"


async def main():
    pool = await asyncpg.create_pool(DB_DSN)

    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    print("Waiting for events...")
    try:
        async for msg in consumer:
            try:
                raw = json.loads(msg.value)
                result = await handle_event(pool, raw)
                print(f"{raw.get('event_id')}: {result}")
            except (InvalidEvent, json.JSONDecodeError) as exc:
                # Bad payload: log and move on. Later this goes to the DLQ topic.
                print(f"Skipped invalid event at offset {msg.offset}: {exc}")
            # Any other error (e.g. database down) is raised on purpose,
            # so the service stops instead of silently dropping events.
    finally:
        await consumer.stop()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())