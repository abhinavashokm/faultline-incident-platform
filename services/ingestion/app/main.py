from contextlib import asynccontextmanager
from typing import Optional

from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

KAFKA_BOOTSTRAP = "localhost:9092"
TOPIC = "error-events"

producer: Optional[AIOKafkaProducer] = None


class ErrorEvent(BaseModel):
    event_id: str
    exception_type: str
    message: str
    stack_trace: Optional[str] = None
    release: Optional[str] = None
    environment: Optional[str] = None


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
        await producer.send_and_wait(TOPIC, event.model_dump_json().encode())
    except Exception:
        raise HTTPException(status_code=503, detail="Event could not be queued")
    return {"event_id": event.event_id, "status": "accepted"}
