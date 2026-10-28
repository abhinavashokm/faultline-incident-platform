import asyncio
import logging
import os
from collections.abc import Awaitable, Callable

from app.core.config import settings
from app.core.db import SessionLocal
from app.errors.consumer import build_handler
from app.errors.service import ErrorsService
from app.messaging.consumer import run_consumer

logger = logging.getLogger(__name__)


async def run_errors_worker() -> None:
    service = ErrorsService(SessionLocal)
    handler = build_handler(service)
    await run_consumer(
        topic=settings.error_events_topic,
        group_id=settings.errors_consumer_group,
        handler=handler,
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )


ROLES: dict[str, Callable[[], Awaitable[None]]] = {
    "errors": run_errors_worker,
    # "perf": run_perf_worker,  # perf comes in Week 2
}


def main() -> None:
    role = os.getenv("ROLE", "errors")
    if role not in ROLES:
        raise ValueError(f"Unknown ROLE: {role!r}. Valid roles: {list(ROLES.keys())}")

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting processing worker with ROLE=%s", role)

    worker_fn = ROLES[role]
    asyncio.run(worker_fn())


if __name__ == "__main__":
    main()

