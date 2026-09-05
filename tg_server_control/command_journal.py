"""Durable command receipts. Never store tokens, message text or helper output."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class CommandJournal:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        path.chmod(0o600)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS commands (
            update_id INTEGER PRIMARY KEY, user_id INTEGER, command TEXT,
            received_at REAL NOT NULL, updated_at REAL NOT NULL,
            execution TEXT NOT NULL, delivery TEXT NOT NULL,
            helper TEXT, helper_result TEXT)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS helper_events (
            update_id INTEGER NOT NULL, at REAL NOT NULL, action TEXT NOT NULL, result TEXT NOT NULL)""")
        with self.db:
            # The process may have died before or after an external side effect.
            self.db.execute("UPDATE commands SET execution='unknown', updated_at=? "
                            "WHERE execution='running'", (time.time(),))
        self.last_prune = 0.0

    def claim(self, update_id: int, user_id: int | None, command: str) -> bool:
        now = time.time()
        with self.db:
            cursor = self.db.execute(
                "INSERT OR IGNORE INTO commands VALUES (?, ?, ?, ?, ?, 'running', 'pending', NULL, NULL)",
                (update_id, user_id, command, now, now),
            )
        return cursor.rowcount == 1

    def helper(self, update_id: int, action: str, result: str):
        with self.db:
            self.db.execute("INSERT INTO helper_events VALUES (?, ?, ?, ?)",
                            (update_id, time.time(), action, result))
            self.db.execute("UPDATE commands SET helper=?, helper_result=?, updated_at=? WHERE update_id=?",
                            (action, result, time.time(), update_id))

    def finish(self, update_id: int, execution: str, delivery: str):
        with self.db:
            self.db.execute("UPDATE commands SET execution=?, delivery=?, updated_at=? WHERE update_id=?",
                            (execution, delivery, time.time(), update_id))

    def prune(self, acknowledged_offset: int | None):
        now = time.time()
        if acknowledged_offset is None or now - self.last_prune < 86400:
            return
        with self.db:
            self.db.execute("DELETE FROM helper_events WHERE update_id IN "
                            "(SELECT update_id FROM commands WHERE updated_at<? AND update_id<? "
                            "AND execution NOT IN ('unknown','running'))",
                            (now - 90 * 86400, acknowledged_offset))
            self.db.execute("DELETE FROM commands WHERE updated_at<? AND update_id<? "
                            "AND execution NOT IN ('unknown','running')",
                            (now - 90 * 86400, acknowledged_offset))
        self.last_prune = now
