from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

KAFKA_BOOTSTRAP = "localhost:9092"
TOPIC = "error-events"

producer: Optional[AIOKafkaProducer] = None


class StackFrame(BaseModel):
    file: str
    function: str
    line: Optional[int] = None
    in_app: bool = False


class ErrorEvent(BaseModel):
    event_id: UUID
    # Temporary: taken from the payload. Later these come from the API key / DSN,
    # because a client must not be trusted to say which project it belongs to.
    workspace_id: UUID
    project_id: UUID
    occurred_at: datetime
    exception_type: str
    message: str = ""
    stack_frames: list[StackFrame] = Field(default_factory=list)  # oldest to newest
    event_type: Literal["error", "message"] = "error"
    level: Literal["error", "warning", "fatal"] = "error"
    service: Optional[str] = None
    route_template: Optional[str] = None
    http_method: Optional[str] = None
    status_code: Optional[int] = None
    environment: Optional[str] = None
    release: Optional[str] = None
    user_hash: Optional[str] = None
    context: dict = Field(default_factory=dict)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await producer.start()
    yield
    await producer.stop()


app = FastAPI(lifespan=lifespan)


@app.post("/api/v1/events", status_code=202)
async def ingest_event(event: ErrorEvent):
    try:
        # Keyed by project so one project's events stay in order on one partition.
        await producer.send_and_wait(
            TOPIC,
            value=event.model_dump_json().encode(),
            key=str(event.project_id).encode(),
        )
    except Exception:
        raise HTTPException(status_code=503, detail="Event could not be queued")
    return {"event_id": str(event.event_id), "status": "accepted"}