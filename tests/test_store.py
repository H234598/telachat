from __future__ import annotations

import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from telachat.store import ChatStore, messages_for_api, normalize_tag, title_from_prompt


class StoreTests(unittest.TestCase):
    def test_session_message_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                session = store.create_session(
                    title="Test",
                    profile="tki",
                    model="Qwen/Qwen2.5-1.5B-Instruct",
                    system_prompt="System",
                )
                self.assertEqual(session.model, "Qwen/Qwen2.5-1.5B-Instruct")
                store.add_message(session.id, "user", "Hallo")
                store.add_message(session.id, "assistant", "Hi")
                messages = store.messages(session.id)
                self.assertEqual([m.role for m in messages], ["user", "assistant"])
                deleted = store.delete_last_assistant_message(session.id)
                self.assertIsNotNone(deleted)
                assert deleted is not None
                self.assertEqual(deleted.content, "Hi")
                self.assertEqual([m.role for m in store.messages(session.id)], ["user"])
                self.assertIsNone(store.delete_last_assistant_message(session.id))
                store.add_message(session.id, "assistant", "Hi")
                store.add_message(session.id, "system", "Systemnotiz")
                messages = store.messages(session.id)
                self.assertEqual([m.role for m in messages], ["user", "assistant", "system"])
                api_messages = messages_for_api("System", messages)
                self.assertEqual(api_messages[0]["role"], "system")
                self.assertEqual(api_messages[-1]["content"], "Hi")
                exported = store.export_markdown(session.id)
                self.assertIn("# Telachat Session", exported)
                self.assertIn("- Model: Qwen/Qwen2.5-1.5B-Instruct", exported)
                self.assertIn("Hallo", exported)
                self.assertIn("## System", exported)
                self.assertIn("Systemnotiz", exported)
            finally:
                store.close()

    def test_session_foreign_keys_prevent_orphaned_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                session = store.create_session(
                    title="FK",
                    profile="tki",
                    system_prompt="System",
                )
                store.add_message(session.id, "user", "Hallo")

                with self.assertRaises(sqlite3.IntegrityError):
                    store.add_message("missing-session", "user", "Verwaist")

                store.delete_session(session.id)
                self.assertEqual(store.messages(session.id), [])
            finally:
                store.close()

    def test_title_from_prompt(self) -> None:
        self.assertEqual(title_from_prompt("  hallo   welt "), "hallo welt")
        self.assertEqual(title_from_prompt(""), "Neue Unterhaltung")
        self.assertLessEqual(len(title_from_prompt("x" * 200)), 64)

    def test_edit_last_user_message_removes_later_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                session = store.create_session(
                    title="Edit",
                    profile="tki",
                    model="Qwen/Qwen2.5-1.5B-Instruct",
                    system_prompt="System",
                )
                store.add_message(session.id, "user", "Erste Frage")
                store.add_message(session.id, "assistant", "Erste Antwort")
                store.add_message(session.id, "user", "Zweite Frage")
                store.add_message(session.id, "assistant", "Zweite Antwort")

                edited = store.edit_last_user_message(session.id, "  Zweite Frage verbessert  ")

                self.assertEqual(edited.content, "Zweite Frage verbessert")
                self.assertEqual(
                    [(message.role, message.content) for message in store.messages(session.id)],
                    [
                        ("user", "Erste Frage"),
                        ("assistant", "Erste Antwort"),
                        ("user", "Zweite Frage verbessert"),
                    ],
                )
                with self.assertRaisesRegex(ValueError, "Nachricht fehlt"):
                    store.edit_last_user_message(session.id, "  ")
            finally:
                store.close()

    def test_edit_last_user_message_requires_user_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                session = store.create_session(
                    title="Leer",
                    profile="tki",
                    system_prompt="System",
                )
                with self.assertRaisesRegex(ValueError, "Keine Nutzernachricht"):
                    store.edit_last_user_message(session.id, "Hallo")
                with self.assertRaises(KeyError):
                    store.edit_last_user_message("fehlt", "Hallo")
            finally:
                store.close()

    def test_edit_last_user_message_does_not_touch_other_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                first = store.create_session(
                    title="First",
                    profile="tki",
                    system_prompt="System",
                )
                second = store.create_session(
                    title="Second",
                    profile="tki",
                    system_prompt="System",
                )
                store.add_message(first.id, "user", "Alt")
                store.add_message(first.id, "assistant", "Antwort")
                store.add_message(second.id, "user", "Andere Frage")
                store.add_message(second.id, "assistant", "Andere Antwort")

                store.edit_last_user_message(first.id, "Neu")

                self.assertEqual(
                    [(message.role, message.content) for message in store.messages(first.id)],
                    [("user", "Neu")],
                )
                self.assertEqual(
                    [(message.role, message.content) for message in store.messages(second.id)],
                    [("user", "Andere Frage"), ("assistant", "Andere Antwort")],
                )
            finally:
                store.close()

    def test_fork_session_copies_metadata_and_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                folder = store.create_folder("Projekt", system_prompt="Ordner")
                session = store.create_session(
                    title="Original",
                    profile="openai",
                    model="gpt-5.5",
                    system_prompt="System",
                    folder_id=folder.id,
                )
                store.add_message(session.id, "user", "Frage")
                store.add_message(session.id, "assistant", "Antwort")
                store.set_session_pinned(session.id, True)
                store.set_session_tags(session.id, ["Projekt", "#Review Notes"])
                store.set_session_archived(session.id, True)

                fork = store.fork_session(session.id, "  Variante A  ")

                self.assertNotEqual(fork.id, session.id)
                self.assertEqual(fork.title, "Variante A")
                self.assertEqual(fork.profile, "openai")
                self.assertEqual(fork.model, "gpt-5.5")
                self.assertEqual(fork.system_prompt, "System")
                self.assertEqual(fork.folder_id, folder.id)
                self.assertFalse(fork.pinned)
                self.assertFalse(fork.archived)
                self.assertEqual(fork.tags, ("projekt", "review-notes"))
                self.assertEqual(
                    [(message.role, message.content) for message in store.messages(fork.id)],
                    [("user", "Frage"), ("assistant", "Antwort")],
                )
                store.edit_last_user_message(fork.id, "Andere Frage")
                self.assertEqual(
                    [(message.role, message.content) for message in store.messages(session.id)],
                    [("user", "Frage"), ("assistant", "Antwort")],
                )
            finally:
                store.close()

    def test_session_archive_filter_export_and_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                active = store.create_session(
                    title="Active",
                    profile="openai",
                    model="gpt-5.5",
                    system_prompt="System",
                )
                archived = store.create_session(
                    title="Archived",
                    profile="tki",
                    system_prompt="System",
                )
                store.add_message(active.id, "user", "Aktivnotiz")
                store.add_message(archived.id, "user", "Archivnotiz")
                archived = store.set_session_archived(archived.id, True)

                self.assertTrue(archived.archived)
                self.assertEqual([session.id for session in store.list_sessions(10)], [active.id])
                self.assertEqual(
                    [session.id for session in store.list_sessions(10, archive="archived")],
                    [archived.id],
                )
                self.assertEqual(
                    [session.title for session in store.list_sessions(10, archive="all", sort="title_asc")],
                    ["Active", "Archived"],
                )
                self.assertEqual(store.list_sessions(10, query="Archivnotiz"), [])
                self.assertEqual(
                    [session.id for session in store.list_sessions(10, query="Archivnotiz", archive="all")],
                    [archived.id],
                )
                self.assertIn("- Archived: yes", store.export_markdown(archived.id))

                restored = store.set_session_archived(archived.id, False)
                self.assertFalse(restored.archived)
                self.assertEqual(
                    [session.title for session in store.list_sessions(10, sort="title_asc")],
                    ["Active", "Archived"],
                )
                with self.assertRaisesRegex(ValueError, "Archivfilter"):
                    store.list_sessions(10, archive="kaputt")
            finally:
                store.close()

    def test_session_tags_filter_search_export_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                alpha = store.create_session(
                    title="Alpha",
                    profile="openai",
                    model="gpt-5.5",
                    system_prompt="System",
                )
                beta = store.create_session(
                    title="Beta",
                    profile="tki",
                    system_prompt="System",
                )

                self.assertEqual(normalize_tag(" #Needs Review "), "needs-review")
                tags = store.set_session_tags(alpha.id, ["#Needs Review", "Plan", "plan"])
                self.assertEqual(tags, ["needs-review", "plan"])
                self.assertEqual(store.get_session(alpha.id).tags, ("needs-review", "plan"))
                self.assertEqual(store.add_session_tags(beta.id, ["Plan"]), ["plan"])
                self.assertEqual(store.remove_session_tags(alpha.id, ["needs review"]), ["plan"])

                self.assertEqual(
                    [session.title for session in store.list_sessions(tag="plan", sort="title_asc")],
                    ["Alpha", "Beta"],
                )
                self.assertEqual(
                    [session.id for session in store.list_sessions(query="#plan", sort="title_asc")],
                    [alpha.id, beta.id],
                )
                self.assertEqual(store.list_tags(), [("plan", 2)])
                exported = store.export_markdown(alpha.id)
                self.assertIn("- Tags: #plan", exported)

                store.delete_session(alpha.id)
                self.assertEqual(store.list_tags(), [("plan", 1)])
            finally:
                store.close()

    def test_folders_sorting_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                work = store.create_folder(" Arbeit ")
                again = store.create_folder("arbeit")
                self.assertEqual(work.id, again.id)

                alpha = store.create_session(
                    title="Alpha",
                    profile="openai",
                    model="gpt-5.5",
                    system_prompt="System",
                    folder_id=work.id,
                )
                beta = store.create_session(
                    title="Beta",
                    profile="huggingface",
                    model="Qwen/Qwen2.5-1.5B-Instruct",
                    system_prompt="System",
                )
                store.add_message(alpha.id, "user", "Projektplan")
                store.add_message(beta.id, "user", "Notiz")

                self.assertEqual(
                    [session.id for session in store.list_sessions(folder_id=work.id)],
                    [alpha.id],
                )
                self.assertEqual(
                    [session.id for session in store.list_sessions(folder_id="__none__")],
                    [beta.id],
                )
                self.assertEqual(
                    [session.title for session in store.list_sessions(sort="title_asc")],
                    ["Alpha", "Beta"],
                )
                pinned = store.set_session_pinned(beta.id, True)
                self.assertTrue(pinned.pinned)
                self.assertEqual(
                    [session.title for session in store.list_sessions(sort="title_asc")],
                    ["Beta", "Alpha"],
                )
                unpinned = store.set_session_pinned(beta.id, False)
                self.assertFalse(unpinned.pinned)
                self.assertEqual(
                    [session.title for session in store.list_sessions(sort="title_asc")],
                    ["Alpha", "Beta"],
                )
                self.assertEqual(
                    [session.id for session in store.list_sessions(query="projekt")],
                    [alpha.id],
                )
                self.assertEqual(
                    [session.id for session in store.list_sessions(query="gpt-5.5")],
                    [alpha.id],
                )

                updated_backend = store.update_session_backend(beta.id, "openai", "gpt-5.5")
                self.assertEqual(updated_backend.profile, "openai")
                self.assertEqual(updated_backend.model, "gpt-5.5")

                moved = store.move_session(beta.id, work.id)
                self.assertEqual(moved.folder_id, work.id)
                self.assertEqual(len(store.list_sessions(folder_id=work.id)), 2)

                renamed = store.update_session_title(alpha.id, "Alpha neu")
                self.assertEqual(renamed.title, "Alpha neu")
                renamed_folder = store.update_folder_name(work.id, "Projekte")
                self.assertEqual(renamed_folder.name, "Projekte")
                folder_prompt = store.update_folder_system_prompt(work.id, "Antworte projektbezogen.")
                self.assertEqual(folder_prompt.system_prompt, "Antworte projektbezogen.")
                loaded_folder = store.get_folder(work.id)
                self.assertIsNotNone(loaded_folder)
                assert loaded_folder is not None
                self.assertEqual(loaded_folder.system_prompt, "Antworte projektbezogen.")
                backend_folder = store.update_folder_backend(work.id, "openai", "gpt-test")
                self.assertEqual(backend_folder.default_profile, "openai")
                self.assertEqual(backend_folder.default_model, "gpt-test")
                loaded_folder = store.get_folder(work.id)
                self.assertIsNotNone(loaded_folder)
                assert loaded_folder is not None
                self.assertEqual(loaded_folder.default_profile, "openai")
                self.assertEqual(loaded_folder.default_model, "gpt-test")
                store.delete_folder(work.id)
                self.assertEqual(store.list_folders(), [])
                self.assertEqual(len(store.list_sessions(folder_id="__none__")), 2)
                store.delete_session(alpha.id)
                self.assertIsNone(store.get_session(alpha.id))
            finally:
                store.close()

    def test_stats_returns_zero_counts_for_empty_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                stats = store.stats()

                self.assertEqual(stats.sessions_total, 0)
                self.assertEqual(stats.sessions_active, 0)
                self.assertEqual(stats.sessions_archived, 0)
                self.assertEqual(stats.sessions_pinned, 0)
                self.assertEqual(stats.sessions_unfiled, 0)
                self.assertEqual(stats.folders_total, 0)
                self.assertEqual(stats.folders_with_system_prompt, 0)
                self.assertEqual(stats.tags_total, 0)
                self.assertEqual(stats.tag_links_total, 0)
                self.assertEqual(stats.tagged_sessions, 0)
                self.assertEqual(stats.messages_total, 0)
                self.assertEqual(stats.message_roles, ())
                self.assertEqual(stats.session_profiles, ())
                self.assertEqual(stats.session_models, ())
                self.assertEqual(stats.usage_records, 0)
                self.assertEqual(stats.usage_total_tokens, 0)
            finally:
                store.close()

    def test_stats_counts_local_history_without_message_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            try:
                folder = store.create_folder("Arbeit", system_prompt="Nur Fakten.")
                active = store.create_session(
                    title="Aktiv",
                    profile="openai",
                    model="gpt-5.5",
                    system_prompt="System",
                    folder_id=folder.id,
                )
                unfiled = store.create_session(
                    title="Ohne Ordner",
                    profile="tki",
                    model="Qwen/Qwen2.5-1.5B-Instruct",
                    system_prompt="System",
                )
                archived = store.create_session(
                    title="Archiv",
                    profile="tki",
                    system_prompt="System",
                )
                store.add_message(active.id, "user", "Geheimer Inhalt")
                assistant = store.add_message(
                    active.id,
                    "assistant",
                    "Antwort",
                    metadata={
                        "usage": {
                            "input_tokens": 21,
                            "output_tokens": 8,
                            "total_tokens": 29,
                            "cached_input_tokens": 3,
                            "reasoning_tokens": 2,
                        }
                    },
                )
                store.add_message(unfiled.id, "system", "Systemnotiz")
                store.add_message(archived.id, "user", "Archivnotiz")
                store.set_session_pinned(active.id, True)
                store.set_session_archived(archived.id, True)
                store.set_session_tags(active.id, ["Projekt", "Review"])
                store.set_session_tags(unfiled.id, ["Projekt"])

                stats = store.stats()
                messages = store.messages(active.id)

                self.assertEqual(
                    assistant.metadata["usage"],
                    {
                        "input_tokens": 21,
                        "output_tokens": 8,
                        "total_tokens": 29,
                        "cached_input_tokens": 3,
                        "reasoning_tokens": 2,
                    },
                )
                self.assertEqual(messages[-1].metadata, assistant.metadata)
                self.assertEqual(stats.sessions_total, 3)
                self.assertEqual(stats.sessions_active, 2)
                self.assertEqual(stats.sessions_archived, 1)
                self.assertEqual(stats.sessions_pinned, 1)
                self.assertEqual(stats.sessions_unfiled, 2)
                self.assertEqual(stats.folders_total, 1)
                self.assertEqual(stats.folders_with_system_prompt, 1)
                self.assertEqual(stats.tags_total, 2)
                self.assertEqual(stats.tag_links_total, 3)
                self.assertEqual(stats.tagged_sessions, 2)
                self.assertEqual(stats.messages_total, 4)
                self.assertEqual(dict(stats.message_roles), {"assistant": 1, "system": 1, "user": 2})
                self.assertEqual(dict(stats.session_profiles), {"openai": 1, "tki": 2})
                self.assertEqual(
                    dict(stats.session_models),
                    {"": 1, "Qwen/Qwen2.5-1.5B-Instruct": 1, "gpt-5.5": 1},
                )
                self.assertEqual(stats.usage_records, 1)
                self.assertEqual(stats.usage_input_tokens, 21)
                self.assertEqual(stats.usage_output_tokens, 8)
                self.assertEqual(stats.usage_total_tokens, 29)
                self.assertEqual(stats.usage_cached_input_tokens, 3)
                self.assertEqual(stats.usage_reasoning_tokens, 2)
                self.assertNotIn("Geheimer Inhalt", repr(stats))
            finally:
                store.close()

    def test_import_history_database_adds_copies_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = ChatStore(Path(tmp) / "source.sqlite3")
            target = ChatStore(Path(tmp) / "target.sqlite3")
            try:
                source_folder = source.create_folder(
                    "Arbeit",
                    system_prompt="Quellprojekt",
                )
                source_session = source.create_session(
                    title="Import",
                    profile="openai",
                    model="gpt-5.5",
                    system_prompt="System",
                    folder_id=source_folder.id,
                )
                source.add_message(source_session.id, "user", "Frage")
                source.add_message(source_session.id, "assistant", "Antwort")
                source.set_session_tags(source_session.id, ["Import", "Projekt"])
                source.set_session_archived(source_session.id, True)
                existing_folder = target.create_folder(
                    "arbeit",
                    system_prompt="Zielprojekt",
                )
                existing_session = target.create_session(
                    title="Bleibt",
                    profile="tki",
                    model="Qwen/Qwen2.5-1.5B-Instruct",
                    system_prompt="System",
                    folder_id=existing_folder.id,
                )
                target.add_message(existing_session.id, "user", "Vorhanden")

                dry_run = target.import_history_database(source.path, dry_run=True)
                self.assertTrue(dry_run.dry_run)
                self.assertEqual(dry_run.folders, 0)
                self.assertEqual(dry_run.sessions, 1)
                self.assertEqual(dry_run.messages, 2)

                summary = target.import_history_database(source.path)
                self.assertEqual(summary.folders, 0)
                self.assertEqual(summary.sessions, 1)
                self.assertEqual(summary.messages, 2)

                sessions = target.list_sessions(limit=10, folder_id="__all__", archive="all")
                self.assertEqual(len(sessions), 2)
                imported = [session for session in sessions if session.title == "Import"]
                self.assertEqual(len(imported), 1)
                self.assertNotEqual(imported[0].id, source_session.id)
                self.assertEqual(imported[0].folder_id, existing_folder.id)
                self.assertTrue(imported[0].archived)
                self.assertEqual(imported[0].tags, ("import", "projekt"))
                self.assertEqual(
                    [message.content for message in target.messages(imported[0].id)],
                    ["Frage", "Antwort"],
                )
                self.assertEqual(len(target.list_folders()), 1)
            finally:
                source.close()
                target.close()

    def test_store_can_be_used_from_worker_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ChatStore(Path(tmp) / "history.sqlite3")
            errors: list[BaseException] = []
            try:
                session = store.create_session(
                    title="Thread", profile="tki", system_prompt="System"
                )

                def worker() -> None:
                    try:
                        store.add_message(session.id, "user", "Hallo aus dem Thread")
                        store.messages(session.id)
                    except BaseException as exc:
                        errors.append(exc)

                thread = threading.Thread(target=worker)
                thread.start()
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertEqual(len(store.messages(session.id)), 1)
            finally:
                store.close()

    def test_legacy_database_adds_pinned_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.sqlite3"
            db = sqlite3.connect(path)
            try:
                db.execute(
                    """
                    CREATE TABLE sessions (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        profile TEXT NOT NULL,
                        system_prompt TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL,
                        folder_id TEXT
                    )
                    """
                )
                db.execute(
                    """
                    INSERT INTO sessions(id, title, profile, system_prompt, created_at, updated_at, folder_id)
                    VALUES ('legacy', 'Legacy', 'tki', 'System', 1, 1, NULL)
                    """
                )
                db.commit()
            finally:
                db.close()

            store = ChatStore(path)
            try:
                session = store.get_session("legacy")
                self.assertIsNotNone(session)
                assert session is not None
                self.assertFalse(session.pinned)
                self.assertFalse(session.archived)
                self.assertEqual(session.model, "")
                pinned = store.set_session_pinned(session.id, True)
                self.assertTrue(pinned.pinned)
                archived = store.set_session_archived(session.id, True)
                self.assertTrue(archived.archived)
            finally:
                store.close()

    def test_legacy_database_adds_model_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.sqlite3"
            db = sqlite3.connect(path)
            try:
                db.execute(
                    """
                    CREATE TABLE sessions (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        profile TEXT NOT NULL,
                        system_prompt TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL,
                        folder_id TEXT,
                        pinned INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                db.execute(
                    """
                    INSERT INTO sessions(id, title, profile, system_prompt, created_at, updated_at, folder_id, pinned)
                    VALUES ('legacy-model', 'Legacy Model', 'openai', 'System', 1, 1, NULL, 0)
                    """
                )
                db.commit()
            finally:
                db.close()

            store = ChatStore(path)
            try:
                session = store.get_session("legacy-model")
                self.assertIsNotNone(session)
                assert session is not None
                self.assertEqual(session.model, "")
                updated = store.update_session_backend(session.id, "openai", "gpt-5.5")
                self.assertEqual(updated.model, "gpt-5.5")
            finally:
                store.close()

    def test_legacy_database_adds_folder_system_prompt_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.sqlite3"
            db = sqlite3.connect(path)
            try:
                db.execute(
                    """
                    CREATE TABLE folders (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    )
                    """
                )
                db.execute(
                    """
                    INSERT INTO folders(id, name, created_at, updated_at)
                    VALUES ('folder1', 'Projekt', 1, 1)
                    """
                )
                db.commit()
            finally:
                db.close()

            store = ChatStore(path)
            try:
                folder = store.get_folder("folder1")
                self.assertIsNotNone(folder)
                assert folder is not None
                self.assertEqual(folder.system_prompt, "")
                self.assertEqual(folder.default_profile, "")
                self.assertEqual(folder.default_model, "")
                updated = store.update_folder_system_prompt(folder.id, "Nur Fakten.")
                self.assertEqual(updated.system_prompt, "Nur Fakten.")
                backend = store.update_folder_backend(folder.id, "tki", "qwen")
                self.assertEqual(backend.default_profile, "tki")
                self.assertEqual(backend.default_model, "qwen")
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
