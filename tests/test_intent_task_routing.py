"""Tests for routing task-related VibeOS intents."""

import unittest

from intent_router import route_intent


class IntentTaskRoutingTest(unittest.TestCase):
    def test_routes_task_list_request(self):
        intent = route_intent("show my pending tasks")

        self.assertEqual("tasks.list", intent.name)
        self.assertTrue(intent.is_actionable)

    def test_routes_task_create_request(self):
        intent = route_intent("add a task for the project review")

        self.assertEqual("tasks.create", intent.name)

    def test_routes_scheduled_task_before_calendar_keywords(self):
        intent = route_intent("schedule a task for tomorrow")

        self.assertEqual("tasks.create", intent.name)

    def test_routes_task_completion_request(self):
        intent = route_intent("mark task 42 as done")

        self.assertEqual("tasks.complete", intent.name)
        self.assertEqual("42", intent.slots["task_id"])

    def test_completion_verbs_override_task_position_words(self):
        next_task = route_intent("complete my next task")
        pending_task = route_intent("finish the pending task")

        self.assertEqual("tasks.complete", next_task.name)
        self.assertEqual("tasks.complete", pending_task.name)

    def test_routes_completed_task_query_as_list(self):
        intent = route_intent("show completed tasks")

        self.assertEqual("tasks.list", intent.name)
        self.assertEqual("completed", intent.slots["status"])

    def test_pending_tasks_override_all_tasks(self):
        intent = route_intent("show all pending tasks")

        self.assertEqual("pending", intent.slots["status"])

    def test_routes_task_delete_request(self):
        intent = route_intent("delete task 42")

        self.assertEqual("tasks.delete", intent.name)
        self.assertEqual("42", intent.slots["task_id"])

    def test_ignores_task_substrings(self):
        multitasking = route_intent("multitasking helps me focus")
        taskbar = route_intent("hide the taskbar")

        self.assertEqual("unknown", multitasking.name)
        self.assertEqual("unknown", taskbar.name)

    def test_ignores_action_substrings(self):
        intent = route_intent("address the task backlog")

        self.assertEqual("tasks.list", intent.name)


if __name__ == "__main__":
    unittest.main()
