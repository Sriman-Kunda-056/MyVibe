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
    def test_list_tasks_filters_by_status(self):
        cases = (
            ("show completed tasks", True, True, ["task_2"]),
            ("show pending tasks", False, False, ["task_1"]),
        )
        for text, show_completed, show_hidden, task_ids in cases:
            with self.subTest(text=text):
                adapter = FakeTasksAdapter()
                intent = route_intent(text)

                result = TaskActionRunner(adapter).run(intent)

                self.assertTrue(result.ok)
                self.assertEqual(
                    [
                        {
                            "tasklist_id": None,
                            "show_completed": show_completed,
                            "show_hidden": show_hidden,
                        }
                    ],
                    adapter.list_calls,
                )
                self.assertEqual(task_ids, [task["task_id"] for task in result.payload["tasks"]])

    def test_task_mutations_validate_required_slots(self):
        cases = (
            ("tasks.create", "add a task", "title", "created"),
            ("tasks.complete", "complete the task", "task_id", "completed"),
            ("tasks.delete", "delete the task", "task_id", "deleted"),
        )
        for name, source_text, missing_field, collection in cases:
            with self.subTest(name=name):
                adapter = FakeTasksAdapter()

                result = TaskActionRunner(adapter).run(VibeIntent(name, 0.9, source_text))

                self.assertFalse(result.ok)
                self.assertIn(missing_field, result.message)
                self.assertEqual([], getattr(adapter, collection))

    def test_task_mutations_use_adapter(self):
        adapter = FakeTasksAdapter()
        runner = TaskActionRunner(adapter)

        created = runner.run(
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
        completed = runner.run(
            VibeIntent(
                "tasks.complete",
                0.9,
                "complete the task",
                {"task_id": "task_1", "tasklist_id": "work"},
            )
        )
        deleted = runner.run(
            VibeIntent("tasks.delete", 0.9, "delete the task", {"task_id": "task_1"})
        )

        self.assertTrue(created.ok)
        self.assertEqual("Review adapter design", adapter.created[0]["title"])
        self.assertEqual("work", adapter.created[0]["tasklist_id"])
        self.assertEqual("task_created", created.payload["task"]["task_id"])
        self.assertTrue(completed.ok)
        self.assertEqual([("task_1", "work")], adapter.completed)
        self.assertEqual("completed", completed.payload["task"]["status"])
        self.assertTrue(deleted.ok)
        self.assertEqual([("task_1", None)], adapter.deleted)
        self.assertEqual("task_1", deleted.payload["task_id"])

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


if __name__ == "__main__":
    unittest.main()