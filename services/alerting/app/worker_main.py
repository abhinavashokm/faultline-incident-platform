import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Ensure service root is in sys.path when executed directly as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.alerts.consumer_handler import build_alerts_consumer_handler
from app.alerts.evaluation_service import AlertEvaluationService
from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.delivery.outbox_processor import OutboxDeliveryService
from app.messaging.consumer import run_consumer

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _register_shutdown_handlers(stop_event: asyncio.Event) -> None:
    """Set `stop_event` when SIGINT or SIGTERM is received.

    Enables graceful shutdown so in-flight work can finish and resources
    (e.g. the DB engine) are cleaned up before exit. Silently skips
    registration where unsupported (e.g. Windows or a non-main thread),
    since the worker can still run without it.

    Must be called from within a running event loop.
    """
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass


async def run_alerts_worker(stop_event: asyncio.Event | None = None) -> None:
    """Run alert evaluation consumer for issue-events."""
    if stop_event is None:
        stop_event = asyncio.Event()

    _register_shutdown_handlers(stop_event)

    evaluation_service = AlertEvaluationService(SessionLocal)
    handler = build_alerts_consumer_handler(evaluation_service)

    try:
        await run_consumer(
            topic=settings.issue_events_topic,
            group_id=settings.alerts_consumer_group,
            handler=handler,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            stop_event=stop_event,
        )
    finally:
        logger.info("Disposing database engine...")
        await engine.dispose()
        logger.info("Database engine disposed.")


async def run_delivery_worker(stop_event: asyncio.Event | None = None) -> None:
    """Run notification delivery outbox poller."""
    if stop_event is None:
        stop_event = asyncio.Event()

    _register_shutdown_handlers(stop_event)

    delivery_service = OutboxDeliveryService(SessionLocal)
    logger.info("Starting delivery worker outbox loop...")
    try:
        while not stop_event.is_set():
            try:
                processed_count = await delivery_service.process_batch(limit=50)
                if processed_count > 0:
                    logger.debug("Processed %d outbox deliveries", processed_count)
                    # Don't sleep if there might be more immediate work
                    continue
            except Exception as exc:
                logger.error("Error processing delivery outbox batch: %s", exc)

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=settings.delivery_poll_interval_seconds)
            except asyncio.TimeoutError:
                pass
    finally:
        logger.info("Disposing database engine...")
        await engine.dispose()
        logger.info("Delivery worker stopped.")


def main() -> None:
    role = os.getenv("ROLE", settings.role).strip().lower()
    setup_logging()

    if role == "alerts":
        logger.info("Starting Alerting Service worker with ROLE=alerts")
        asyncio.run(run_alerts_worker())
    elif role == "delivery":
        logger.info("Starting Alerting Service worker with ROLE=delivery")
        asyncio.run(run_delivery_worker())
    else:
        logger.error("Unknown ROLE: %r. Valid roles are: 'alerts', 'delivery'", role)
        sys.exit(1)


if __name__ == "__main__":
    main()
