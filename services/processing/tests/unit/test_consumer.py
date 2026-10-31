import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from aiokafka import TopicPartition

from app.core.config import settings
from app.messaging.consumer import PermanentError, run_consumer


class FakeRecord:
    def __init__(
        self,
        topic: str,
        partition: int,
        offset: int,
        value: bytes,
        key: bytes = b"",
    ) -> None:
        self.topic = topic
        self.partition = partition
        self.offset = offset
        self.value = value
        self.key = key


class FakeAIOKafkaConsumer:
    def __init__(self, records: list[FakeRecord]) -> None:
        self.records = records
        self.position = 0
        self.committed_offsets: dict[TopicPartition, int] = {}
        self.seek_history: list[tuple[TopicPartition, int]] = []
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def getone(self) -> FakeRecord:
        if self.position < len(self.records):
            rec = self.records[self.position]
            self.position += 1
            return rec
        # When all records have been read, yield to loop
        await asyncio.sleep(0.05)
        raise asyncio.TimeoutError()

    def seek(self, partition: TopicPartition, offset: int) -> None:
        self.seek_history.append((partition, offset))
        for i, rec in enumerate(self.records):
            if (
                rec.topic == partition.topic
                and rec.partition == partition.partition
                and rec.offset == offset
            ):
                self.position = i
                return
        self.position = offset

    async def commit(self, offsets: dict[TopicPartition, int] | None = None) -> None:
        if offsets:
            self.committed_offsets.update(offsets)


def make_valid_message(event_id: str | None = None) -> bytes:
    eid = event_id or str(uuid.uuid4())
    payload = {
        "schema_version": 1,
        "event_id": eid,
        "workspace_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "event_id": eid,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "exception_type": "RuntimeError",
            "message": "failure",
            "stack_frames": [],
            "event_type": "error",
            "level": "error",
        },
    }
    return json.dumps(payload).encode("utf-8")


@pytest.mark.asyncio
async def test_offset_committed_only_after_service_call_succeeds(monkeypatch):
    monkeypatch.setattr(settings, "backoff_base", 0.01)
    monkeypatch.setattr(settings, "backoff_cap", 0.05)

    rec = FakeRecord(topic="error-events", partition=0, offset=10, value=make_valid_message())
    consumer = FakeAIOKafkaConsumer([rec])
    stop_event = asyncio.Event()

    processed: list[int] = []

    async def handler(raw: bytes, topic: str, partition: int, offset: int) -> None:
        processed.append(offset)
        # Stop loop after processing
        stop_event.set()

    await run_consumer(
        topic="error-events",
        group_id="test-group",
        handler=handler,
        bootstrap_servers="localhost:9092",
        stop_event=stop_event,
        consumer=consumer,
    )

    tp = TopicPartition("error-events", 0)
    assert processed == [10]
    assert consumer.committed_offsets.get(tp) == 11
    assert consumer.stopped is True


@pytest.mark.asyncio
async def test_poison_message_offset_committed_and_next_message_processed(monkeypatch):
    monkeypatch.setattr(settings, "backoff_base", 0.01)
    monkeypatch.setattr(settings, "backoff_cap", 0.05)

    # Message 0: invalid flat poison message
    poison_raw = b'{"legacy": true}'
    rec0 = FakeRecord(topic="error-events", partition=0, offset=0, value=poison_raw)
    # Message 1: valid message
    rec1 = FakeRecord(topic="error-events", partition=0, offset=1, value=make_valid_message())

    consumer = FakeAIOKafkaConsumer([rec0, rec1])
    stop_event = asyncio.Event()
    processed_offsets: list[int] = []

    async def handler(raw: bytes, topic: str, partition: int, offset: int) -> None:
        if offset == 0:
            raise PermanentError("Poison pill invalid schema")
        processed_offsets.append(offset)
        stop_event.set()

    await run_consumer(
        topic="error-events",
        group_id="test-group",
        handler=handler,
        bootstrap_servers="localhost:9092",
        stop_event=stop_event,
        consumer=consumer,
    )

    tp = TopicPartition("error-events", 0)
    # Offset 1 (poison skipped) and offset 2 (valid processed) both committed
    assert consumer.committed_offsets.get(tp) == 2
    assert processed_offsets == [1]


@pytest.mark.asyncio
async def test_transient_error_offset_not_committed_and_reprocessed(monkeypatch):
    monkeypatch.setattr(settings, "backoff_base", 0.01)
    monkeypatch.setattr(settings, "backoff_cap", 0.05)

    rec = FakeRecord(topic="error-events", partition=0, offset=5, value=make_valid_message())
    consumer = FakeAIOKafkaConsumer([rec])
    stop_event = asyncio.Event()

    attempts = 0

    async def handler(raw: bytes, topic: str, partition: int, offset: int) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            # Simulate transient DB connection failure
            raise ConnectionError("DB connection dropped")
        # Second attempt succeeds
        stop_event.set()

    await run_consumer(
        topic="error-events",
        group_id="test-group",
        handler=handler,
        bootstrap_servers="localhost:9092",
        stop_event=stop_event,
        consumer=consumer,
    )

    tp = TopicPartition("error-events", 0)
    assert attempts == 2
    assert (tp, 5) in consumer.seek_history
    assert consumer.committed_offsets.get(tp) == 6


@pytest.mark.asyncio
async def test_shutdown_signal_stops_cleanly():
    stop_event = asyncio.Event()
    consumer = FakeAIOKafkaConsumer([])

    # Immediately set stop event
    stop_event.set()

    async def handler(raw: bytes, topic: str, partition: int, offset: int) -> None:
        pass

    await run_consumer(
        topic="error-events",
        group_id="test-group",
        handler=handler,
        bootstrap_servers="localhost:9092",
        stop_event=stop_event,
        consumer=consumer,
    )

    assert consumer.started is True
    assert consumer.stopped is True

