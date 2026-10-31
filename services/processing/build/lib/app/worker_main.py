import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Ensure service root is in sys.path when executed directly as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.errors.consumer import build_handler
from app.errors.service import ErrorsService
from app.messaging.consumer import run_consumer

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


async def run_errors_worker(stop_event: asyncio.Event | None = None) -> None:
    """Run errors consumer worker with graceful shutdown and database cleanup."""
    if stop_event is None:
        stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: stop_event.set())
        except (NotImplementedError, RuntimeError):
            pass

    service = ErrorsService(SessionLocal)
    handler = build_handler(service)

    try:
        await run_consumer(
            topic=settings.error_events_topic,
            group_id=settings.errors_consumer_group,
            handler=handler,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            stop_event=stop_event,
        )
    finally:
        logger.info("Disposing database engine...")
        await engine.dispose()
        logger.info("Database engine disposed.")


def main() -> None:
    role = os.getenv("ROLE", "errors").strip().lower()

    if role == "perf":
        setup_logging()
        logger.info("Performance module (ROLE=perf) is not implemented yet. Exiting.")
        sys.exit(0)
    elif role == "errors":
        setup_logging()
        logger.info("Starting Processing Service worker with ROLE=errors")
        asyncio.run(run_errors_worker())
    else:
        setup_logging()
        logger.error("Unknown ROLE: %r. Valid roles are: 'errors', 'perf'", role)
        sys.exit(1)


if __name__ == "__main__":
    main()
