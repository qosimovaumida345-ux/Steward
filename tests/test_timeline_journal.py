"""
Unit tests for Dual-Indexed Timeline Journal and Reconnect Catch-Up.
"""

from pathlib import Path
import pytest
from steward.config.constants import EventType
from steward.core.timeline_journal import TimelineJournal
from steward.storage.sqlite_store import SQLiteStore


def test_timeline_journal_indexing_and_audit(tmp_path: Path):
    db_file = tmp_path / "journal_test.db"
    store = SQLiteStore(db_file)
    store.create_session("sess_alpha", "Test Session")

    journal = TimelineJournal("sess_alpha", store, audit_file_dir=tmp_path)

    listener_events = []
    journal.add_listener(lambda ev: listener_events.append(ev))

    # Record 5 sequential events
    for i in range(1, 6):
        seq = journal.record_event(
            EventType.STEP_STARTED,
            {"step_id": i, "desc": f"Doing step {i}"},
        )
        assert seq == i

    assert len(listener_events) == 5

    # Check JSONL audit file written
    audit_file = tmp_path / "timeline.jsonl"
    assert audit_file.exists()
    lines = audit_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5

    # Test Catch-Up Replay query (seq > 2)
    catchup = journal.get_events_after(last_seq=2, limit=10)
    assert len(catchup) == 3
    assert [e["seq"] for e in catchup] == [3, 4, 5]

    store.close()
