"""Stateful memory management: Per-session key-value memory and checkpointer."""

import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


class SessionMemoryStore:
    """Thread-safe SQLite-backed key-value store for cross-run session facts."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize session memory store with SQLite database path."""
        self._lock = threading.Lock()
        if db_path and db_path != ":memory:" and not str(db_path).startswith(":memory:"):
            path = Path(db_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(path)
        else:
            self.db_path = ":memory:"

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        """Create session facts table if not exists."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session_facts (
                    session_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, key)
                )
                """
            )
            self._conn.commit()

    def read(self, session_id: str, key: str) -> Optional[str]:
        """Read a stored fact for the given session and key."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT value FROM session_facts WHERE session_id = ? AND key = ?",
                (session_id, key),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def write(self, session_id: str, key: str, value: str) -> None:
        """Store or update a fact for the given session and key."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO session_facts (session_id, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id, key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (session_id, key, str(value), now),
            )
            self._conn.commit()
            logger.debug("Wrote session memory: [%s] %s = %s", session_id, key, value)

    def list_facts(self, session_id: str) -> Dict[str, str]:
        """Return all stored key-value facts for a session."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT key, value FROM session_facts WHERE session_id = ?",
                (session_id,),
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

    def clear(self, session_id: str) -> None:
        """Remove all facts associated with a session."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "DELETE FROM session_facts WHERE session_id = ?",
                (session_id,),
            )
            self._conn.commit()

    def close(self) -> None:
        """Close SQLite connection."""
        with self._lock:
            self._conn.close()


def create_sqlite_checkpointer(db_path: Optional[str] = None) -> Any:
    """Create and return a LangGraph checkpointer instance.

    Uses MemorySaver / async-compatible checkpoint storage for workflow state execution.
    """
    return MemorySaver()
