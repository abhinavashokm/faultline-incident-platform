import json
import logging
import queue
import threading
import time
from typing import Any
import urllib.error
import urllib.request

from faultline._internal import logger
from faultline.config import Config

_SENTINEL = object()


class Transport:
    """Asynchronous background transport using a bounded queue and single daemon thread."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=config.max_queue_size)
        # Set by close(); send() rejects new events, but the worker keeps draining the queue.
        self._closed = False
        # Set by close() after the flush attempt; tells the worker to exit and wakes any retry backoff.
        self._stop_event = threading.Event()

        # In-flight task tracking for timed flush
        self._lock = threading.Lock()
        self._empty_condition = threading.Condition(self._lock)
        self._pending_count = 0

        # Background worker thread
        self._thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="faultline-transport",
        )
        self._thread.start()

    def send(self, payload: dict[str, Any], url: str | None = None) -> bool:
        """Enqueue an event payload for background transmission.

        Returns True if enqueued, False if dropped due to queue being full or transport closed.
        Never blocks the caller.
        """
        if self._closed or self._stop_event.is_set():
            logger.warning("Faultline transport is closed; dropping event.")
            return False

        target_url = url or self.config.dsn.ingest_url

        with self._lock:
            if self._queue.full():
                logger.warning("Faultline event queue is full; dropping event.")
                return False
            self._pending_count += 1

        try:
            self._queue.put_nowait((target_url, payload))
            return True
        except queue.Full:
            with self._lock:
                self._pending_count -= 1
                if self._pending_count == 0:
                    self._empty_condition.notify_all()
            logger.warning("Faultline event queue is full; dropping event.")
            return False

    def _worker_loop(self) -> None:
        """Single background daemon thread processing items from the queue."""
        while not self._stop_event.is_set():
            try:
                try:
                    item = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                if item is _SENTINEL:
                    self._queue.task_done()
                    break

                target_url, payload = item
                try:
                    self._send_with_retry(target_url, payload)
                except Exception as exc:
                    logger.error("Unexpected error in Faultline transport worker: %s", exc, exc_info=True)
                finally:
                    self._queue.task_done()
                    with self._lock:
                        self._pending_count -= 1
                        if self._pending_count == 0:
                            self._empty_condition.notify_all()
            except Exception as loop_exc:
                logger.error("Critical error in Faultline transport thread loop: %s", loop_exc, exc_info=True)

    def _send_with_retry(self, url: str, payload: dict[str, Any]) -> bool:
        """Send payload to URL with limited retries and exponential backoff.

        Rules:
          - Bounded payload size check.
          - Never retry on 4xx, except 429 (with capped backoff).
          - Drop and log on 401/403.
          - Retry transient 5xx and network errors with backoff up to max_retries.
        """
        try:
            body_bytes = json.dumps(payload, default=str).encode("utf-8")
        except Exception as exc:
            logger.error("Failed to serialize event payload to JSON: %s; dropping event.", exc)
            return False

        if len(body_bytes) > self.config.max_payload_bytes:
            logger.warning(
                "Event payload exceeds maximum allowed size (%d > %d bytes); dropping event.",
                len(body_bytes),
                self.config.max_payload_bytes,
            )
            return False

        headers = {
            "Content-Type": "application/json",
            "X-Faultline-Key": self.config.dsn.api_key,
            "X-Project-Key": self.config.dsn.api_key,
            "User-Agent": "faultline-python-sdk/0.1.0",
        }

        for attempt in range(self.config.max_retries):
            if self._stop_event.is_set():
                return False

            req = urllib.request.Request(
                url,
                data=body_bytes,
                headers=headers,
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                    status = getattr(resp, "status", resp.getcode())
                    if 200 <= status < 300:
                        return True
            except urllib.error.HTTPError as exc:
                code = exc.code
                if code in (401, 403):
                    logger.error(
                        "Faultline project key invalid or revoked (HTTP %d); dropping event.",
                        code,
                    )
                    return False

                if code == 429:
                    retry_after_hdr = exc.headers.get("Retry-After")
                    delay = 1.0
                    if retry_after_hdr:
                        try:
                            delay = float(retry_after_hdr)
                        except ValueError:
                            pass
                    delay = min(max(delay, 0.1), self.config.max_retry_after)
                    logger.warning(
                        "Faultline rate limit exceeded (HTTP 429); backing off for %.1fs (attempt %d/%d).",
                        delay,
                        attempt + 1,
                        self.config.max_retries,
                    )
                    if attempt < self.config.max_retries - 1:
                        if self._stop_event.wait(delay):
                            return False
                        continue
                    return False

                if 400 <= code < 500:
                    logger.error(
                        "Faultline ingestion rejected event (HTTP %d); dropping event.",
                        code,
                    )
                    return False

                # 5xx server error
                delay = min(0.2 * (2 ** attempt), 2.0)
                logger.warning(
                    "Faultline server error (HTTP %d); retrying in %.1fs (attempt %d/%d).",
                    code,
                    delay,
                    attempt + 1,
                    self.config.max_retries,
                )
                if attempt < self.config.max_retries - 1:
                    if self._stop_event.wait(delay):
                        return False
                    continue
                return False

            except (urllib.error.URLError, TimeoutError, OSError) as net_err:
                delay = min(0.2 * (2 ** attempt), 2.0)
                logger.warning(
                    "Faultline transport network error: %s; retrying in %.1fs (attempt %d/%d).",
                    net_err,
                    delay,
                    attempt + 1,
                    self.config.max_retries,
                )
                if attempt < self.config.max_retries - 1:
                    if self._stop_event.wait(delay):
                        return False
                    continue
                return False

        return False

    def flush(self, timeout: float | None = None) -> bool:
        """Wait until all pending events in the queue are sent or until timeout expires.

        Returns True if all pending events completed, False if timed out.
        """
        wait_timeout = timeout if timeout is not None else self.config.flush_timeout
        end_time = time.monotonic() + wait_timeout

        with self._lock:
            while self._pending_count > 0:
                remaining = end_time - time.monotonic()
                if remaining <= 0:
                    return False
                self._empty_condition.wait(timeout=remaining)
            return True

    def close(self, timeout: float | None = None) -> None:
        """Flush pending items and cleanly shut down the background transport thread."""
        if self._closed:
            return
        self._closed = True

        close_timeout = timeout if timeout is not None else self.config.flush_timeout
        half_timeout = max(close_timeout / 2.0, 0.1)

        # 1. Attempt to flush pending events
        self.flush(timeout=half_timeout)

        # 2. Signal stop and unblock worker
        self._stop_event.set()
        try:
            self._queue.put_nowait(_SENTINEL)
        except queue.Full:
            pass

        # 3. Wait for background thread to exit within remaining timeout
        remaining_timeout = max(close_timeout - half_timeout, 0.1)
        self._thread.join(timeout=remaining_timeout)

