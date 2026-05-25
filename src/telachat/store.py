from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .paths import db_path


@dataclass(frozen=True)
class Session:
    id: str
    title: str
    profile: str
    system_prompt: str
    created_at: int
    updated_at: int
    folder_id: str | None = None
    pinned: bool = False
    model: str = ""


@dataclass(frozen=True)
class Folder:
    id: str
    name: str
    created_at: int
    updated_at: int
    system_prompt: str = ""


@dataclass(frozen=True)
class Message:
    id: int
    session_id: str
    role: str
    content: str
    created_at: int


@dataclass(frozen=True)
class HistoryImportSummary:
    folders: int
    sessions: int
    messages: int
    dry_run: bool = False


class ChatStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        with self._lock:
            self.db.close()

    def _new_unique_id(self, table: str) -> str:
        if table not in {"folders", "sessions"}:
            raise ValueError(f"Ungueltige Tabelle: {table}")
        while True:
            candidate = uuid.uuid4().hex[:12]
            row = self.db.execute(f"SELECT 1 FROM {table} WHERE id = ?", (candidate,)).fetchone()
            if row is None:
                return candidate

    def _init_schema(self) -> None:
        with self._lock:
            self.db.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    model TEXT NOT NULL DEFAULT '',
                    system_prompt TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    folder_id TEXT REFERENCES folders(id) ON DELETE SET NULL,
                    pinned INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS folders (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    system_prompt TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session_created
                    ON messages(session_id, created_at, id);
                """
            )
            self._migrate_schema()
            self.db.commit()

    def _migrate_schema(self) -> None:
        with self._lock:
            columns = {
                row["name"]
                for row in self.db.execute("PRAGMA table_info(sessions)").fetchall()
            }
            if "folder_id" not in columns:
                self.db.execute("ALTER TABLE sessions ADD COLUMN folder_id TEXT")
            if "pinned" not in columns:
                self.db.execute("ALTER TABLE sessions ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
            if "model" not in columns:
                self.db.execute("ALTER TABLE sessions ADD COLUMN model TEXT NOT NULL DEFAULT ''")
            folder_columns = {
                row["name"]
                for row in self.db.execute("PRAGMA table_info(folders)").fetchall()
            }
            if "system_prompt" not in folder_columns:
                self.db.execute(
                    "ALTER TABLE folders ADD COLUMN system_prompt TEXT NOT NULL DEFAULT ''"
                )

    def create_session(
        self,
        *,
        title: str,
        profile: str,
        system_prompt: str,
        model: str | None = None,
        folder_id: str | None = None,
    ) -> Session:
        with self._lock:
            now = int(time.time())
            session_id = uuid.uuid4().hex[:12]
            self.db.execute(
                """
                INSERT INTO sessions(id, title, profile, model, system_prompt, created_at, updated_at, folder_id, pinned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (session_id, title, profile, model or "", system_prompt, now, now, folder_id),
            )
            self.db.commit()
            return Session(
                session_id,
                title,
                profile,
                system_prompt,
                now,
                now,
                folder_id,
                False,
                model or "",
            )

    def get_session(self, session_id_or_prefix: str) -> Session | None:
        with self._lock:
            rows = self.db.execute(
                """
                SELECT * FROM sessions
                WHERE id = ? OR id LIKE ?
                ORDER BY updated_at DESC
                LIMIT 2
                """,
                (session_id_or_prefix, f"{session_id_or_prefix}%"),
            ).fetchall()
            if len(rows) != 1:
                return None
            return _session_from_row(rows[0])

    def list_sessions(
        self,
        limit: int = 20,
        *,
        folder_id: str | None = None,
        sort: str = "updated_desc",
        query: str | None = None,
    ) -> list[Session]:
        with self._lock:
            order = {
                "updated_desc": "updated_at DESC, created_at DESC",
                "updated_asc": "updated_at ASC, created_at ASC",
                "title_asc": "lower(title) ASC, updated_at DESC",
                "title_desc": "lower(title) DESC, updated_at DESC",
                "profile_asc": "lower(profile) ASC, updated_at DESC",
            }.get(sort, "updated_at DESC, created_at DESC")

            clauses: list[str] = []
            params: list[object] = []
            if folder_id == "__all__":
                pass
            elif folder_id == "__none__":
                clauses.append("folder_id IS NULL")
            elif folder_id:
                clauses.append("folder_id = ?")
                params.append(folder_id)

            clean_query = " ".join((query or "").strip().split())
            if clean_query:
                like = f"%{clean_query}%"
                clauses.append(
                    """
                    (
                        sessions.title LIKE ?
                        OR sessions.profile LIKE ?
                        OR sessions.model LIKE ?
                        OR EXISTS (
                            SELECT 1 FROM messages
                            WHERE messages.session_id = sessions.id
                            AND messages.content LIKE ?
                        )
                    )
                    """
                )
                params.extend([like, like, like, like])

            where = "WHERE " + " AND ".join(clauses) if clauses else ""
            params.append(limit)
            rows = self.db.execute(
                f"SELECT * FROM sessions {where} ORDER BY pinned DESC, {order} LIMIT ?",
                tuple(params),
            ).fetchall()
            return [_session_from_row(row) for row in rows]

    def list_folders(self) -> list[Folder]:
        with self._lock:
            rows = self.db.execute(
                "SELECT * FROM folders ORDER BY lower(name) ASC"
            ).fetchall()
            return [_folder_from_row(row) for row in rows]

    def get_folder(self, folder_id_or_prefix: str) -> Folder | None:
        with self._lock:
            rows = self.db.execute(
                """
                SELECT * FROM folders
                WHERE id = ? OR id LIKE ?
                ORDER BY updated_at DESC
                LIMIT 2
                """,
                (folder_id_or_prefix, f"{folder_id_or_prefix}%"),
            ).fetchall()
            if len(rows) != 1:
                return None
            return _folder_from_row(rows[0])

    def create_folder(self, name: str, *, system_prompt: str = "") -> Folder:
        with self._lock:
            clean = " ".join(name.strip().split())
            if not clean:
                raise ValueError("Ordnername fehlt.")
            existing = self.db.execute(
                "SELECT * FROM folders WHERE lower(name) = lower(?)",
                (clean,),
            ).fetchone()
            if existing:
                return _folder_from_row(existing)
            now = int(time.time())
            folder_id = uuid.uuid4().hex[:12]
            self.db.execute(
                """
                INSERT INTO folders(id, name, created_at, updated_at, system_prompt)
                VALUES (?, ?, ?, ?, ?)
                """,
                (folder_id, clean, now, now, system_prompt.strip()),
            )
            self.db.commit()
            return Folder(folder_id, clean, now, now, system_prompt.strip())

    def move_session(self, session_id: str, folder_id: str | None) -> Session:
        with self._lock:
            now = int(time.time())
            self.db.execute(
                "UPDATE sessions SET folder_id = ?, updated_at = ? WHERE id = ?",
                (folder_id, now, session_id),
            )
            self.db.commit()
            session = self.get_session(session_id)
            if session is None:
                raise KeyError(session_id)
            return session

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            cur = self.db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            self.db.commit()
            if cur.rowcount != 1:
                raise KeyError(session_id)

    def update_folder_name(self, folder_id: str, name: str) -> Folder:
        with self._lock:
            clean = " ".join(name.strip().split())
            if not clean:
                raise ValueError("Ordnername fehlt.")
            now = int(time.time())
            self.db.execute(
                "UPDATE folders SET name = ?, updated_at = ? WHERE id = ?",
                (clean, now, folder_id),
            )
            self.db.commit()
            folder = self.db.execute(
                "SELECT * FROM folders WHERE id = ?",
                (folder_id,),
            ).fetchone()
            if folder is None:
                raise KeyError(folder_id)
            return _folder_from_row(folder)

    def update_folder_system_prompt(self, folder_id: str, system_prompt: str) -> Folder:
        with self._lock:
            now = int(time.time())
            self.db.execute(
                "UPDATE folders SET system_prompt = ?, updated_at = ? WHERE id = ?",
                (system_prompt.strip(), now, folder_id),
            )
            self.db.commit()
            folder = self.get_folder(folder_id)
            if folder is None:
                raise KeyError(folder_id)
            return folder

    def delete_folder(self, folder_id: str) -> None:
        with self._lock:
            cur = self.db.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            self.db.commit()
            if cur.rowcount != 1:
                raise KeyError(folder_id)

    def delete_empty_sessions(self) -> int:
        with self._lock:
            cur = self.db.execute(
                """
                DELETE FROM sessions
                WHERE id NOT IN (SELECT DISTINCT session_id FROM messages)
                """
            )
            self.db.commit()
            return int(cur.rowcount)

    def update_session_title(self, session_id: str, title: str) -> Session:
        with self._lock:
            now = int(time.time())
            self.db.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id),
            )
            self.db.commit()
            session = self.get_session(session_id)
            if session is None:
                raise KeyError(session_id)
            return session

    def update_session_backend(self, session_id: str, profile: str, model: str) -> Session:
        with self._lock:
            now = int(time.time())
            self.db.execute(
                "UPDATE sessions SET profile = ?, model = ?, updated_at = ? WHERE id = ?",
                (profile, model, now, session_id),
            )
            self.db.commit()
            session = self.get_session(session_id)
            if session is None:
                raise KeyError(session_id)
            return session

    def set_session_pinned(self, session_id: str, pinned: bool) -> Session:
        with self._lock:
            self.db.execute(
                "UPDATE sessions SET pinned = ? WHERE id = ?",
                (1 if pinned else 0, session_id),
            )
            self.db.commit()
            session = self.get_session(session_id)
            if session is None:
                raise KeyError(session_id)
            return session

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        metadata: dict[str, object] | None = None,
    ) -> Message:
        with self._lock:
            now = int(time.time())
            cur = self.db.execute(
                """
                INSERT INTO messages(session_id, role, content, created_at, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, role, content, now, json.dumps(metadata or {}, sort_keys=True)),
            )
            self.db.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
            self.db.commit()
            return Message(int(cur.lastrowid), session_id, role, content, now)

    def messages(self, session_id: str, *, limit: int | None = None) -> list[Message]:
        with self._lock:
            params: tuple[object, ...]
            if limit is None:
                sql = (
                    "SELECT * FROM messages WHERE session_id = ? "
                    "ORDER BY created_at ASC, id ASC"
                )
                params = (session_id,)
            else:
                sql = """
                    SELECT * FROM (
                        SELECT * FROM messages WHERE session_id = ?
                        ORDER BY created_at DESC, id DESC LIMIT ?
                    ) ORDER BY created_at ASC, id ASC
                """
                params = (session_id, limit)
            rows = self.db.execute(sql, params).fetchall()
            return [_message_from_row(row) for row in rows]

    def delete_last_assistant_message(self, session_id: str) -> Message | None:
        with self._lock:
            row = self.db.execute(
                """
                SELECT * FROM messages
                WHERE session_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            if row is None or row["role"] != "assistant":
                return None
            message = _message_from_row(row)
            now = int(time.time())
            self.db.execute("DELETE FROM messages WHERE id = ?", (message.id,))
            self.db.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
            self.db.commit()
            return message

    def import_history_database(
        self,
        source_path: Path,
        *,
        dry_run: bool = False,
    ) -> HistoryImportSummary:
        source = sqlite3.connect(source_path)
        source.row_factory = sqlite3.Row
        try:
            if not _table_exists(source, "sessions") or not _table_exists(source, "messages"):
                raise ValueError("Backup enthaelt keine Telachat-Historie.")
            source_folders = (
                source.execute("SELECT * FROM folders ORDER BY created_at ASC, id ASC").fetchall()
                if _table_exists(source, "folders")
                else []
            )
            source_sessions = source.execute(
                "SELECT * FROM sessions ORDER BY created_at ASC, id ASC"
            ).fetchall()
            source_messages = source.execute(
                "SELECT * FROM messages ORDER BY created_at ASC, id ASC"
            ).fetchall()
        finally:
            source.close()

        with self._lock:
            existing_folder_rows = self.db.execute("SELECT id, name FROM folders").fetchall()
            folder_map = {
                row["id"]: existing["id"]
                for row in source_folders
                for existing in existing_folder_rows
                if existing["name"].casefold() == _row_value(row, "name", "").casefold()
            }
            folders_to_add = [
                row
                for row in source_folders
                if row["id"] not in folder_map and _row_value(row, "name", "").strip()
            ]
            session_ids = {row["id"] for row in source_sessions}
            message_count = sum(1 for row in source_messages if row["session_id"] in session_ids)
            if dry_run:
                return HistoryImportSummary(
                    folders=len(folders_to_add),
                    sessions=len(source_sessions),
                    messages=message_count,
                    dry_run=True,
                )

            now = int(time.time())
            folders_added = 0
            sessions_added = 0
            messages_added = 0
            for row in folders_to_add:
                folder_id = self._new_unique_id("folders")
                folder_map[row["id"]] = folder_id
                self.db.execute(
                    """
                    INSERT INTO folders(id, name, created_at, updated_at, system_prompt)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        folder_id,
                        _row_value(row, "name", "").strip(),
                        int(_row_value(row, "created_at", now)),
                        int(_row_value(row, "updated_at", now)),
                        _row_value(row, "system_prompt", ""),
                    ),
                )
                folders_added += 1

            session_map: dict[str, str] = {}
            for row in source_sessions:
                session_id = self._new_unique_id("sessions")
                source_folder_id = _row_value(row, "folder_id", None)
                target_folder_id = folder_map.get(source_folder_id) if source_folder_id else None
                session_map[row["id"]] = session_id
                self.db.execute(
                    """
                    INSERT INTO sessions(
                        id, title, profile, model, system_prompt,
                        created_at, updated_at, folder_id, pinned
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        _row_value(row, "title", "Importierte Unterhaltung"),
                        _row_value(row, "profile", ""),
                        _row_value(row, "model", ""),
                        _row_value(row, "system_prompt", ""),
                        int(_row_value(row, "created_at", now)),
                        int(_row_value(row, "updated_at", now)),
                        target_folder_id,
                        int(_row_value(row, "pinned", 0) or 0),
                    ),
                )
                sessions_added += 1

            for row in source_messages:
                target_session_id = session_map.get(row["session_id"])
                if not target_session_id:
                    continue
                self.db.execute(
                    """
                    INSERT INTO messages(session_id, role, content, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        target_session_id,
                        _row_value(row, "role", "user"),
                        _row_value(row, "content", ""),
                        int(_row_value(row, "created_at", now)),
                        _row_value(row, "metadata", "{}"),
                    ),
                )
                messages_added += 1

            self.db.commit()
            return HistoryImportSummary(folders_added, sessions_added, messages_added)

    def export_markdown(self, session_id: str) -> str:
        with self._lock:
            session = self.get_session(session_id)
            if session is None:
                raise KeyError(session_id)
            lines = [
                f"# Telachat Session {session.id}",
                "",
                f"- Title: {session.title}",
                f"- Profile: {session.profile}",
                f"- Model: {session.model or '-'}",
                "",
            ]
            for message in self.messages(session.id):
                heading = "User" if message.role == "user" else "Assistant"
                lines.extend([f"## {heading}", "", message.content.strip(), ""])
            return "\n".join(lines).rstrip() + "\n"


def messages_for_api(
    system_prompt: str,
    messages: list[Message],
) -> list[dict[str, str]]:
    api_messages = [{"role": "system", "content": system_prompt}]
    for message in messages:
        if message.role in {"user", "assistant"} and message.content:
            api_messages.append({"role": message.role, "content": message.content})
    return api_messages


def title_from_prompt(prompt: str) -> str:
    clean = " ".join(prompt.strip().split())
    if not clean:
        return "Neue Unterhaltung"
    return clean[:64]


def _table_exists(db: sqlite3.Connection, table: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _row_value(row: sqlite3.Row, key: str, default: object) -> object:
    return row[key] if key in row.keys() else default


def _session_from_row(row: sqlite3.Row) -> Session:
    return Session(
        id=row["id"],
        title=row["title"],
        profile=row["profile"],
        system_prompt=row["system_prompt"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        folder_id=row["folder_id"] if "folder_id" in row.keys() else None,
        pinned=bool(row["pinned"]) if "pinned" in row.keys() else False,
        model=row["model"] if "model" in row.keys() else "",
    )


def _folder_from_row(row: sqlite3.Row) -> Folder:
    return Folder(
        id=row["id"],
        name=row["name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        system_prompt=row["system_prompt"] if "system_prompt" in row.keys() else "",
    )


def _message_from_row(row: sqlite3.Row) -> Message:
    return Message(
        id=row["id"],
        session_id=row["session_id"],
        role=row["role"],
        content=row["content"],
        created_at=row["created_at"],
    )
