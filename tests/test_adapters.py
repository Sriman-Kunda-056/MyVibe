"""Tests for VibeOS adapters."""

import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock

from Auth import GMAIL_SCOPES
from adapters import (
    GmailMessage,
    GoogleTasksAdapter,
    LocalFilesAdapter,
    LocalNotesAdapter,
    TaskItem,
    default_registry,
)


TEST_TMP_ROOT = Path(".test_tmp")


class AdapterParsingTest(unittest.TestCase):
    def test_gmail_scopes_match_supported_operations(self):
        self.assertEqual(
            [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
            ],
            GMAIL_SCOPES,
        )

    def test_gmail_message_from_google_payload(self):
        message = GmailMessage.from_google_message(
            {
                "id": "msg_1",
                "threadId": "thread_1",
                "snippet": "Short preview",
                "labelIds": ["INBOX"],
                "payload": {
                    "headers": [
                        {"name": "From", "value": "sam@example.com"},
                        {"name": "Subject", "value": "Launch notes"},
                    ]
                },
            }
        )

        self.assertEqual("msg_1", message.message_id)
        self.assertEqual("Launch notes", message.subject)
        self.assertEqual("sam@example.com", message.sender)

    def test_task_item_from_google_payload(self):
        task = TaskItem.from_google_task(
            {
                "id": "task_1",
                "title": "Ship adapter layer",
                "status": "needsAction",
                "notes": "Keep it small",
            }
        )

        self.assertEqual("task_1", task.task_id)
        self.assertEqual("Ship adapter layer", task.title)
        self.assertEqual("needsAction", task.status)

    def test_google_tasks_forwards_completed_visibility_flags(self):
        service = MagicMock()
        service.tasks.return_value.list.return_value.execute.return_value = {
            "items": []
        }
        adapter = GoogleTasksAdapter(service=service)

        adapter.list_tasks(
            show_completed=True,
            show_hidden=True,
            max_results=10,
        )

        service.tasks.return_value.list.assert_called_once_with(
            tasklist="@default",
            showCompleted=True,
            showHidden=True,
            maxResults=10,
        )

    def test_google_tasks_preserves_positional_max_results(self):
        service = MagicMock()
        service.tasks.return_value.list.return_value.execute.return_value = {
            "items": []
        }
        adapter = GoogleTasksAdapter(service=service)

        adapter.list_tasks(None, False, 10)

        service.tasks.return_value.list.assert_called_once_with(
            tasklist="@default",
            showCompleted=False,
            showHidden=False,
            maxResults=10,
        )


class LocalAdapterTest(unittest.TestCase):
    def setUp(self):
        TEST_TMP_ROOT.mkdir(exist_ok=True)
        self.root = TEST_TMP_ROOT / uuid.uuid4().hex

    def test_local_notes_create_find_and_append(self):
        adapter = LocalNotesAdapter(self.root / "notes")

        note = adapter.create_note("Daily Plan", "Build VibeOS adapters")
        updated = adapter.append_note(note.note_id, "Add tests")
        matches = adapter.find_notes("tests")

        self.assertEqual("daily-plan", note.note_id)
        self.assertIn("Add tests", updated.content)
        self.assertEqual([note.note_id], [match.note_id for match in matches])

    def test_local_notes_rejects_slug_collisions_without_overwriting(self):
        adapter = LocalNotesAdapter(self.root / "notes")
        note = adapter.create_note("Daily Plan", "Original content")

        with self.assertRaisesRegex(FileExistsError, "daily-plan"):
            adapter.create_note("Daily---Plan", "Replacement content")

        preserved = adapter.read_note(note.note_id)
        self.assertIn("Original content", preserved.content)
        self.assertNotIn("Replacement content", preserved.content)

    def test_local_files_stays_inside_root(self):
        adapter = LocalFilesAdapter(self.root / "workspace")

        written = adapter.write_text("plans/today.txt", "Build adapters")
        content = adapter.read_text("plans/today.txt")

        self.assertEqual(Path("plans/today.txt"), Path(written.relative_path))
        self.assertEqual("Build adapters", content)
        with self.assertRaises(ValueError):
            adapter.read_text("../outside.txt")


class RegistryTest(unittest.TestCase):
    def test_default_registry_exposes_all_adapters(self):
        names = default_registry().names()

        self.assertEqual(["calendar", "files", "gmail", "notes", "tasks"], names)

    def test_registry_can_create_task_adapter_without_google_imports(self):
        adapter = default_registry().create("tasks")

        self.assertIsInstance(adapter, GoogleTasksAdapter)


if __name__ == "__main__":
    unittest.main()
