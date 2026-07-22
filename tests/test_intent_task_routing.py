"""Tests for routing task-related VibeOS intents."""

import unittest

from intent_router import route_intent


class IntentTaskRoutingTest(unittest.TestCase):
    def test_routes_task_actions_and_slots(self):
        cases = (
            ("show my pending tasks", "tasks.list", {}),
            ("add a task for the project review", "tasks.create", {"title": "the project review"}),
            ("create task called Ship adapters", "tasks.create", {"title": "Ship adapters"}),
            ("schedule a task for tomorrow", "tasks.create", {}),
            ("mark task 42 as done", "tasks.complete", {"task_id": "42"}),
            ("delete task 42", "tasks.delete", {"task_id": "42"}),
        )
        for text, name, slots in cases:
            with self.subTest(text=text):
                intent = route_intent(text)

                self.assertEqual(name, intent.name)
                for key, value in slots.items():
                    self.assertEqual(value, intent.slots[key])

    def test_routes_task_status_queries(self):
        cases = (
            ("show completed tasks", "completed"),
            ("show all pending tasks", "pending"),
        )
        for text, status in cases:
            with self.subTest(text=text):
                intent = route_intent(text)

                self.assertEqual("tasks.list", intent.name)
                self.assertEqual(status, intent.slots["status"])

    def test_completion_verbs_override_task_position_words(self):
        for text in ("complete my next task", "finish the pending task"):
            with self.subTest(text=text):
                self.assertEqual("tasks.complete", route_intent(text).name)

    def test_ignores_task_and_action_substrings(self):
        cases = (
            ("multitasking helps me focus", "unknown"),
            ("hide the taskbar", "unknown"),
            ("address the task backlog", "tasks.list"),
        )
        for text, name in cases:
            with self.subTest(text=text):
                self.assertEqual(name, route_intent(text).name)


if __name__ == "__main__":
    unittest.main()
