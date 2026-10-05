"""
Unit tests for Dual-Tier Persistence and Outbox Worker Offline Fallback.
"""

from pathlib import Path
import pytest
from steward.storage.sqlite_store import SQLiteStore
from steward.storage.sync_outbox import SyncOutboxWorker
from steward.storage.render_postgres import RenderPostgresClient


@pytest.mark.asyncio
async def test_outbox_queue_offline_fallback(tmp_path: Path):
    db_file = tmp_path / "sync_test.db"
    store = SQLiteStore(db_file)
    store.create_session("sess_sync", "Sync Test")

    # Record event - should atomically insert into sync_outbox
    seq, eid = store.record_event("sess_sync", "file_modified", {"file": "main.py"})
    assert seq == 1

    pending = store.fetch_pending_outbox_items()
    assert len(pending) == 1
    assert pending[0]["event_type"] == "file_modified"
    assert pending[0]["status"] == "pending"

    # Worker configured without Postgres DSN (offline fallback mode)
    dummy_pg = RenderPostgresClient(dsn=None)
    worker = SyncOutboxWorker(store, dummy_pg)

    # Flush should return 0 synced and not throw exceptions
    flushed = await worker.flush_once()
    assert flushed == 0

    # Local events remain intact in pending status
    pending_after = store.fetch_pending_outbox_items()
    assert len(pending_after) == 1

    # Mark synced manually
    store.mark_outbox_items_synced([pending[0]["outbox_id"]])
    assert len(store.fetch_pending_outbox_items()) == 0

    store.close()
