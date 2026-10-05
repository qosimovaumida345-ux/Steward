"""
Asynchronous Outbox Replication Worker.
Transfers local timeline transactions to Render PostgreSQL with backoff and jitter.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from ..brain.rate_limiter import BackoffStrategy
from .render_postgres import RenderPostgresClient
from .sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class SyncOutboxWorker:
    """
    Background worker that continuously flushes SQLite sync_outbox to Cloud PostgreSQL.
    Ensures zero-latency offline operation when cloud connection is absent or sleeping.
    """

    def __init__(
        self,
        sqlite_store: SQLiteStore,
        postgres_client: Optional[RenderPostgresClient] = None,
        poll_interval: float = 3.0,
        batch_size: int = 50,
    ) -> None:
        self.sqlite = sqlite_store
        self.pg = postgres_client or RenderPostgresClient()
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.backoff = BackoffStrategy(base_seconds=2.0, max_seconds=60.0, jitter=True)

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._failure_streak = 0

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("SyncOutboxWorker started.")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("SyncOutboxWorker stopped.")

    async def flush_once(self) -> int:
        """
        Attempt a single batch flush of pending outbox items.
        Returns the number of successfully synchronized events.
        """
        if not self.pg.is_configured():
            return 0

        pending_items = self.sqlite.fetch_pending_outbox_items(limit=self.batch_size)
        if not pending_items:
            return 0

        try:
            # Sync session records first
            session_ids = list({item["session_id"] for item in pending_items})
            for sid in session_ids:
                s_data = self.sqlite.get_session(sid)
                if s_data:
                    await self.pg.upsert_session(s_data)

            # Sync timeline events
            await self.pg.batch_insert_events(pending_items)

            # Mark all synced in local sqlite
            outbox_ids = [item["outbox_id"] for item in pending_items]
            self.sqlite.mark_outbox_items_synced(outbox_ids)

            self._failure_streak = 0
            logger.info("Synced %d events to Render Cloud PostgreSQL", len(outbox_ids))
            return len(outbox_ids)

        except Exception as e:
            self._failure_streak += 1
            err_msg = str(e)
            logger.warning("Cloud outbox replication failed (streak=%d): %s", self._failure_streak, err_msg)
            for item in pending_items:
                self.sqlite.record_outbox_failure(item["outbox_id"], err_msg)
            return 0

    async def _run_loop(self) -> None:
        while self._running:
            try:
                flushed = await self.flush_once()
                if self._failure_streak > 0:
                    delay = self.backoff.compute_delay(self._failure_streak)
                    await asyncio.sleep(delay)
                elif flushed == 0:
                    await asyncio.sleep(self.poll_interval)
                else:
                    # If we flushed a full batch, check immediately for more
                    if flushed >= self.batch_size:
                        await asyncio.sleep(0.1)
                    else:
                        await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected error in Outbox sync loop: %s", e)
                await asyncio.sleep(self.poll_interval)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    from ..config.settings import get_settings
    settings = get_settings()
    logger.info("Starting Steward Background Outbox Worker...")
    logger.info("PostgreSQL target: %s", "Configured" if settings.render_postgres_dsn else "Disabled/Unset")

    sqlite = SQLiteStore(db_path=settings.sqlite_path)
    pg = RenderPostgresClient(dsn=settings.render_postgres_dsn)
    worker = SyncOutboxWorker(sqlite_store=sqlite, postgres_client=pg)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(worker.start())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        loop.run_until_complete(worker.stop())
        sqlite.close()


if __name__ == "__main__":
    main()

