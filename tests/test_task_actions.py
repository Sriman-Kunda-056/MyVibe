"""Tests for the VibeOS intent-to-task flow."""

import unittest

from adapters import TaskItem
from intent_router import VibeIntent, route_intent
from task_actions import TaskActionRunner


class FakeTasksAdapter:
    def __init__(self):
        self.list_calls = []
        self.created = []
        self.completed = []
        self.deleted = []

    def list_tasks(self, **kwargs):
        self.list_calls.append(kwargs)
        return [
            TaskItem(
                task_id="task_1",
                title="Review adapter design",
                status="needsAction",
                due="2026-07-14T00:00:00Z",
            ),
            TaskItem(
                task_id="task_2",
                title="Archive launch notes",
                status="completed",
            ),
        ]

    def create_task(self, **kwargs):
        self.created.append(kwargs)
        return TaskItem(
            task_id="task_created",
            title=kwargs["title"],
            status="needsAction",
            due=kwargs.get("due"),
            notes=kwargs.get("notes"),
        )

    def complete_task(self, task_id, tasklist_id=None):
        self.completed.append((task_id, tasklist_id))
        return TaskItem(
            task_id=task_id,
            title="Review adapter design",
            status="completed",
        )

    def delete_task(self, task_id, tasklist_id=None):
        self.deleted.append((task_id, tasklist_id))


class TaskActionFlowTest(unittest.TestCase):
    def test_list_completed_tasks_uses_routed_slots(self):
        adapter = FakeTasksAdapter()
        intent = route_intent("show completed tasks")

        result = TaskActionRunner(adapter).run(intent)

        self.assertTrue(result.ok)
        self.assertEqual(
            [
                {
                    "tasklist_id": None,
                    "show_completed": True,
                    "show_hidden": True,
                }
            ],
            adapter.list_calls,
        )
        self.assertEqual(
            ["task_2"],
            [task["task_id"] for task in result.payload["tasks"]],
        )

    def test_list_pending_tasks_excludes_completed_results(self):
        adapter = FakeTasksAdapter()
        intent = route_intent("show pending tasks")

        result = TaskActionRunner(adapter).run(intent)

        self.assertTrue(result.ok)
        self.assertEqual(
            [
                {
                    "tasklist_id": None,
                    "show_completed": False,
                    "show_hidden": False,
                }
            ],
            adapter.list_calls,
        )
        self.assertEqual(
            ["task_1"],
            [task["task_id"] for task in result.payload["tasks"]],
        )

    def test_create_task_validates_title_before_adapter_call(self):
        adapter = FakeTasksAdapter()

        result = TaskActionRunner(adapter).run(
            VibeIntent("tasks.create", 0.9, "add a task")
        )

        self.assertFalse(result.ok)
        self.assertIn("title", result.message)
        self.assertEqual([], adapter.created)

    def test_create_task_uses_adapter(self):
        adapter = FakeTasksAdapter()

        result = TaskActionRunner(adapter).run(
            VibeIntent(
                "tasks.create",
                0.9,
                "add a review task",
                {
                    "title": "Review adapter design",
                    "notes": "Focus on validation",
                    "due": "2026-07-14T00:00:00Z",
                    "tasklist_id": "work",
                },
            )
        )

        self.assertTrue(result.ok)
        self.assertEqual("Review adapter design", adapter.created[0]["title"])
        self.assertEqual("work", adapter.created[0]["tasklist_id"])
        self.assertEqual("task_created", result.payload["task"]["task_id"])

    def test_complete_task_validates_id_before_adapter_call(self):
        adapter = FakeTasksAdapter()

        result = TaskActionRunner(adapter).run(
            VibeIntent("tasks.complete", 0.9, "complete the task")
        )

        self.assertFalse(result.ok)
        self.assertIn("task_id", result.message)
        self.assertEqual([], adapter.completed)

    def test_complete_task_uses_adapter(self):
        adapter = FakeTasksAdapter()

        result = TaskActionRunner(adapter).run(
            VibeIntent(
                "tasks.complete",
                0.9,
                "complete the task",
                {"task_id": "task_1", "tasklist_id": "work"},
            )
        )

        self.assertTrue(result.ok)
        self.assertEqual([("task_1", "work")], adapter.completed)
        self.assertEqual("completed", result.payload["task"]["status"])

    def test_delete_task_validates_id_before_adapter_call(self):
        adapter = FakeTasksAdapter()

        result = TaskActionRunner(adapter).run(
            VibeIntent("tasks.delete", 0.9, "delete the task")
        )

        self.assertFalse(result.ok)
        self.assertIn("task_id", result.message)
        self.assertEqual([], adapter.deleted)

    def test_delete_task_rejects_low_confidence_intent(self):
        adapter = FakeTasksAdapter()

        result = TaskActionRunner(adapter).run(
            VibeIntent(
                "tasks.delete",
                0.0,
                "maybe delete the task",
                {"task_id": "task_1"},
            )
        )

        self.assertFalse(result.ok)
        self.assertIn("not actionable", result.message)
        self.assertEqual([], adapter.deleted)

    def test_delete_task_uses_adapter(self):
        adapter = FakeTasksAdapter()

        result = TaskActionRunner(adapter).run(
            VibeIntent(
                "tasks.delete",
                0.9,
                "delete the task",
                {"task_id": "task_1"},
            )
        )

        self.assertTrue(result.ok)
        self.assertEqual([("task_1", None)], adapter.deleted)
        self.assertEqual("task_1", result.payload["task_id"])


if __name__ == "__main__":
    unittest.main()
