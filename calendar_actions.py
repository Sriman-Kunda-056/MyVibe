"""Calendar action runner for VibeOS intents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from adapters import CalendarEvent, GoogleCalendarAdapter
from intent_router import VibeIntent


@dataclass(frozen=True)
class CalendarActionResult:
    """Result returned after trying to execute a calendar intent."""

    ok: bool
    message: str
    payload: Dict[str, Any] = field(default_factory=dict)


class CalendarActionRunner:
    """Executes normalized calendar intents against the calendar adapter."""

    def __init__(self, adapter: Optional[GoogleCalendarAdapter] = None) -> None:
        self.adapter = adapter or GoogleCalendarAdapter()

    def run(self, intent: VibeIntent) -> CalendarActionResult:
        if not intent.is_actionable:
            return CalendarActionResult(False, "Calendar intent is not actionable.")

        if intent.name == "calendar.list_upcoming":
            return self._list_upcoming()

        if intent.name == "calendar.create_event":
            return self._create_event(intent.slots)

        if intent.name == "calendar.delete_event":
            return self._delete_event(intent.slots)

        return CalendarActionResult(False, f"Unsupported calendar intent: {intent.name}")

    def _list_upcoming(self) -> CalendarActionResult:
        events = self.adapter.list_upcoming_events()
        return CalendarActionResult(
            True,
            f"Found {len(events)} upcoming calendar events.",
            {"events": [_event_payload(event) for event in events]},
        )

    def _create_event(self, slots: Dict[str, str]) -> CalendarActionResult:
        missing = [key for key in ("summary", "start", "end") if not slots.get(key)]
        if missing:
            return CalendarActionResult(
                False,
                "Missing required event fields: " + ", ".join(missing),
            )

        event = self.adapter.create_event(
            summary=slots["summary"],
            start=slots["start"],
            end=slots["end"],
            description=slots.get("description"),
            time_zone=slots.get("time_zone"),
        )
        return CalendarActionResult(
            True,
            f"Created calendar event: {event.summary}",
            {"event": _event_payload(event)},
        )

    def _delete_event(self, slots: Dict[str, str]) -> CalendarActionResult:
        event_id = slots.get("event_id")
        if not event_id:
            return CalendarActionResult(False, "Missing required event_id field.")

        self.adapter.delete_event(event_id)
        return CalendarActionResult(
            True,
            f"Deleted calendar event: {event_id}",
            {"event_id": event_id},
        )


def _event_payload(event: CalendarEvent) -> Dict[str, Optional[str]]:
    return {
        "event_id": event.event_id,
        "summary": event.summary,
        "start": event.start,
        "end": event.end,
        "link": event.link,
    }
