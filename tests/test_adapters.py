"""Tests for VibeOS adapters."""

import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from Auth import GMAIL_SCOPES
from adapters import (
    GmailAdapter,
    GmailMessage,
    GoogleTasksAdapter,
    LocalCalendarAdapter,
    LocalFilesAdapter,
    LocalNotesAdapter,
    LocalTasksAdapter,
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

    def test_gmail_list_query_arguments(self):
        for query, expected in (
            (None, {"userId": "me", "maxResults": 10}),
            (
                "from:sam@example.com",
                {"userId": "me", "maxResults": 5, "q": "from:sam@example.com"},
            ),
        ):
            with self.subTest(query=query):
                service = MagicMock()
                service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
                    "messages": []
                }
                adapter = GmailAdapter(service=service)

                adapter.list_recent_messages(max_results=expected["maxResults"], query=query)

                service.users.return_value.messages.return_value.list.assert_called_once_with(
                    **expected
                )

    def test_gmail_send_rejects_blank_recipient(self):
        service = MagicMock()
        adapter = GmailAdapter(service=service)

        with self.assertRaisesRegex(ValueError, "recipient"):
            adapter.send_email("   ", "Launch notes", "Body")

        service.users.assert_not_called()

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

    def test_google_tasks_list_arguments(self):
        cases = (
            (
                {"show_completed": True, "show_hidden": True, "max_results": 10},
                {
                    "tasklist": "@default",
                    "showCompleted": True,
                    "showHidden": True,
                    "maxResults": 10,
                },
            ),
            (
                {"tasklist_id": None, "show_completed": False, "max_results": 10},
                {
                    "tasklist": "@default",
                    "showCompleted": False,
                    "showHidden": False,
                    "maxResults": 10,
                },
            ),
        )
        for kwargs, expected in cases:
            with self.subTest(kwargs=kwargs):
                service = MagicMock()
                service.tasks.return_value.list.return_value.execute.return_value = {
                    "items": []
                }
                adapter = GoogleTasksAdapter(service=service)

                adapter.list_tasks(**kwargs)

                service.tasks.return_value.list.assert_called_once_with(**expected)


class LocalAdapterTest(unittest.TestCase):
    def setUp(self):
        TEST_TMP_ROOT.mkdir(exist_ok=True)
        self.root = TEST_TMP_ROOT / uuid.uuid4().hex

    def test_local_notes_flow_and_validation(self):
        adapter = LocalNotesAdapter(self.root / "notes")

        note = adapter.create_note("Daily Plan", "Build VibeOS adapters")
        updated = adapter.append_note(note.note_id, "Add tests")
        matches = adapter.find_notes("tests")

        self.assertEqual("daily-plan", note.note_id)
        self.assertIn("Add tests", updated.content)
        self.assertEqual([note.note_id], [match.note_id for match in matches])
        with self.assertRaisesRegex(ValueError, "query"):
            adapter.find_notes("   ")
        with self.assertRaises(FileNotFoundError):
            adapter.append_note("missing-note", "Do not create this file")
        self.assertFalse((self.root / "notes" / "missing-note.md").exists())

    def test_local_notes_rejects_invalid_creates(self):
        adapter = LocalNotesAdapter(self.root / "notes")

        with self.assertRaisesRegex(ValueError, "title"):
            adapter.create_note("   ", "No title")
        self.assertFalse((self.root / "notes").exists())

        note = adapter.create_note("Daily Plan", "Original content")
        with self.assertRaisesRegex(FileExistsError, "daily-plan"):
            adapter.create_note("Daily---Plan", "Replacement content")
        preserved = adapter.read_note(note.note_id)
        self.assertIn("Original content", preserved.content)
        self.assertNotIn("Replacement content", preserved.content)

    def test_local_calendar_flow_and_validation(self):
        adapter = LocalCalendarAdapter(self.root / "calendar")

        adapter.create_event(
            "Yesterday sync",
            "2026-07-20T09:00:00Z",
            "2026-07-20T09:30:00Z",
        )
        focus = adapter.create_event(
            "Focus block",
            "2026-07-21T09:00:00Z",
            "2026-07-21T10:00:00Z",
            description="Adapter work",
        )
        reloaded = LocalCalendarAdapter(self.root / "calendar")

        upcoming = reloaded.list_upcoming_events(
            time_min=datetime(2026, 7, 21, tzinfo=timezone.utc),
        )

        self.assertTrue(focus.event_id.startswith("local-"))
        self.assertEqual([focus.event_id], [event.event_id for event in upcoming])
        self.assertEqual("Focus block", upcoming[0].summary)
        self.assertEqual("local://calendar/" + focus.event_id, upcoming[0].link)

        reloaded.delete_event(focus.event_id)
        self.assertEqual(
            [],
            reloaded.list_upcoming_events(
                time_min=datetime(2026, 7, 21, tzinfo=timezone.utc),
            ),
        )
        with self.assertRaisesRegex(ValueError, "summary"):
            adapter.create_event("   ", "2026-07-21T09:00:00Z", "2026-07-21T10:00:00Z")

    def test_local_tasks_flow_and_validation(self):
        adapter = LocalTasksAdapter(self.root / "tasks")

        task = adapter.create_task(
            "Review adapter design",
            notes="Focus on local parity",
            due="2026-07-21T00:00:00Z",
        )
        pending_tasks = adapter.list_tasks()
        completed = adapter.complete_task(task.task_id)
        reloaded = LocalTasksAdapter(self.root / "tasks")

        self.assertTrue(task.task_id.startswith("local-"))
        self.assertEqual([task.task_id], [item.task_id for item in pending_tasks])
        self.assertEqual("completed", completed.status)
        self.assertEqual([], adapter.list_tasks())
        self.assertEqual(
            [task.task_id],
            [item.task_id for item in reloaded.list_tasks(show_completed=True)],
        )

        adapter.delete_task(task.task_id)
        self.assertEqual([], adapter.list_tasks(show_completed=True))
        with self.assertRaisesRegex(ValueError, "title"):
            adapter.create_task("   ")

    def test_local_files_flow_and_validation(self):
        adapter = LocalFilesAdapter(self.root / "workspace")

        written = adapter.write_text("plans/today.txt", "Build adapters")
        entries = adapter.list_entries("plans")
        content = adapter.read_text("plans/today.txt")

        self.assertEqual("plans/today.txt", written.relative_path)
        self.assertEqual(["plans/today.txt"], [entry.relative_path for entry in entries])
        self.assertEqual("Build adapters", content)
        with self.assertRaisesRegex(ValueError, "empty"):
            adapter.write_text("   ", "No path")
        with self.assertRaisesRegex(ValueError, "relative"):
            adapter.write_text(str((self.root / "workspace" / "inside.txt").resolve()), "Nope")
        with self.assertRaises(ValueError):
            adapter.read_text("../outside.txt")


class RegistryTest(unittest.TestCase):
    def test_default_registry_exposes_and_creates_key_adapters(self):
        registry = default_registry()

        self.assertEqual(
            ["calendar", "files", "gmail", "local_calendar", "local_tasks", "notes", "tasks"],
            registry.names(),
        )
        self.assertIsInstance(registry.create("tasks"), GoogleTasksAdapter)
        self.assertIsInstance(registry.create("local_calendar"), LocalCalendarAdapter)
        self.assertIsInstance(registry.create("local_tasks"), LocalTasksAdapter)


if __name__ == "__main__":
    unittest.main()
