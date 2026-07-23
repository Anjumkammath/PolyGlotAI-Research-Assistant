from pathlib import Path
from datetime import UTC, datetime
import json
import sqlite3
from time import time


class MemoryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    language TEXT,
                    document_id TEXT,
                    metadata_json TEXT,
                    created_at REAL NOT NULL
                )
                """
            )
            self._ensure_column(connection, "document_id", "TEXT")
            self._ensure_column(connection, "metadata_json", "TEXT")
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_session_created
                ON conversation_messages (session_id, created_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_created
                ON conversation_messages (created_at)
                """
            )

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        column_name: str,
        column_type: str,
    ) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(conversation_messages)")
        }
        if column_name not in columns:
            connection.execute(
                f"ALTER TABLE conversation_messages ADD COLUMN {column_name} {column_type}"
            )

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        language: str | None = None,
        document_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversation_messages
                    (session_id, role, content, language, document_id, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    role,
                    content,
                    language,
                    document_id,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    time(),
                ),
            )

    def recent_messages(self, session_id: str, limit: int = 8) -> list[dict[str, str]]:
        messages = self.session_messages(session_id=session_id, limit=limit, newest_first=True)
        messages.reverse()
        return [
            {
                "role": message["role"],
                "content": message["content"],
                "language": message["language"] or "",
                "document_id": message["document_id"] or "",
            }
            for message in messages
        ]

    def session_messages(
        self,
        session_id: str,
        limit: int = 50,
        newest_first: bool = False,
    ) -> list[dict]:
        order = "DESC" if newest_first else "ASC"
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, session_id, role, content, language, document_id,
                       metadata_json, created_at
                FROM conversation_messages
                WHERE session_id = ?
                ORDER BY created_at {order}, id {order}
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

        return [self._row_to_message(row) for row in rows]

    def list_sessions(self, limit: int = 25) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT session_id,
                       COUNT(*) AS message_count,
                       MIN(created_at) AS first_message_at,
                       MAX(created_at) AS last_message_at
                FROM conversation_messages
                GROUP BY session_id
                ORDER BY last_message_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            {
                "session_id": str(row["session_id"]),
                "message_count": int(row["message_count"]),
                "first_message_at": self._format_timestamp(float(row["first_message_at"])),
                "last_message_at": self._format_timestamp(float(row["last_message_at"])),
                "preferred_language": self._latest_value(str(row["session_id"]), "language"),
                "last_document_id": self._latest_value(str(row["session_id"]), "document_id"),
            }
            for row in rows
        ]

    def delete_session(self, session_id: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversation_messages WHERE session_id = ?",
                (session_id,),
            )
            return int(cursor.rowcount)

    def clear_all(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM conversation_messages")
            return int(cursor.rowcount)

    def _latest_value(self, session_id: str, column_name: str) -> str | None:
        if column_name not in {"language", "document_id"}:
            return None
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT {column_name}
                FROM conversation_messages
                WHERE session_id = ? AND {column_name} IS NOT NULL AND {column_name} != ''
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return str(row[column_name])

    def _row_to_message(self, row: sqlite3.Row) -> dict:
        metadata = {}
        if row["metadata_json"]:
            try:
                metadata = json.loads(row["metadata_json"])
            except json.JSONDecodeError:
                metadata = {}
        return {
            "id": int(row["id"]),
            "session_id": str(row["session_id"]),
            "role": str(row["role"]),
            "content": str(row["content"]),
            "language": row["language"],
            "document_id": row["document_id"],
            "created_at": self._format_timestamp(float(row["created_at"])),
            "metadata": metadata,
        }

    @staticmethod
    def _format_timestamp(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()
