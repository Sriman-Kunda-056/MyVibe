"""Tests for the VibeOS intent-to-calendar flow."""

import unittest

from adapters import CalendarEvent
from calendar_actions import CalendarActionRunner
from intent_router import VibeIntent, route_intent


class FakeCalendarAdapter:
    def __init__(self):
        self.created = []
        self.deleted = []

    def list_upcoming_events(self):
        return [
            CalendarEvent(
                event_id="evt_1",
                summary="Focus block",
                start="2026-07-10T09:00:00Z",
                end="2026-07-10T10:00:00Z",
                link="https://calendar.example/events/evt_1",
            )
        ]

    def create_event(self, **kwargs):
        self.created.append(kwargs)
        return CalendarEvent(
            event_id="evt_created",
            summary=kwargs["summary"],
            start=kwargs["start"],
            end=kwargs["end"],
        )

    def delete_event(self, event_id):
        self.deleted.append(event_id)


class IntentCalendarFlowTest(unittest.TestCase):
    def test_routes_and_lists_calendar_events(self):
        intent = route_intent("show my next calendar events")
        result = CalendarActionRunner(FakeCalendarAdapter()).run(intent)

        self.assertEqual("calendar.list_upcoming", intent.name)
        self.assertTrue(intent.is_actionable)
        self.assertTrue(result.ok)
        self.assertEqual("evt_1", result.payload["events"][0]["event_id"])

    def test_create_event_validates_required_slots(self):
        result = CalendarActionRunner(FakeCalendarAdapter()).run(
            VibeIntent("calendar.create_event", 0.9, "book focus time")
        )

        self.assertFalse(result.ok)
        self.assertIn("summary", result.message)
        self.assertIn("start", result.message)
        self.assertIn("end", result.message)

    def test_delete_event_flow_and_confidence_guard(self):
        adapter = FakeCalendarAdapter()
        intent = route_intent("delete event evt_1")

        result = CalendarActionRunner(adapter).run(intent)
        blocked = CalendarActionRunner(adapter).run(
            VibeIntent(
                "calendar.delete_event",
                0.0,
                "maybe delete my event",
                {"event_id": "evt_2"},
            )
        )

        self.assertTrue(result.ok)
        self.assertEqual("evt_1", intent.slots["event_id"])
        self.assertEqual(["evt_1"], adapter.deleted)
        self.assertFalse(blocked.ok)
        self.assertIn("not actionable", blocked.message)
        self.assertEqual(["evt_1"], adapter.deleted)


if __name__ == "__main__":
    unittest.main()
