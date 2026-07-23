"""Local JSON-backed calendar adapter for VibeOS."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Union

from .google_calendar import CalendarEvent
from .local_json_store import LocalJsonStore


class LocalCalendarAdapter:
    """Stores calendar events in a local JSON file for offline development."""

    def __init__(self, root_dir: str = "calendar") -> None:
        self.store = LocalJsonStore(root_dir, "events.json", {"events": []})

    def list_upcoming_events(
        self,
        max_results: int = 10,
        time_min: Optional[datetime] = None,
    ) -> List[CalendarEvent]:
        cutoff = _as_datetime(time_min or datetime.now(timezone.utc))
        events = [
            event
            for event in self.store.load()["events"]
            if _event_start_datetime(event) >= cutoff
        ]
        events.sort(key=_event_start_datetime)
        return [CalendarEvent.from_google_event(event) for event in events[:max_results]]

    def create_event(
        self,
        summary: str,
        start: Union[datetime, date, str],
        end: Union[datetime, date, str],
        description: Optional[str] = None,
        time_zone: Optional[str] = None,
    ) -> CalendarEvent:
        summary = summary.strip()
        if not summary:
            raise ValueError("Calendar event summary must not be empty.")

        data = self.store.load()
        event = {
            "id": f"local-{uuid.uuid4().hex}",
            "summary": summary,
            "start": _event_time(start, time_zone),
            "end": _event_time(end, time_zone),
        }
        if description:
            event["description"] = description
        event["htmlLink"] = f"local://calendar/{event['id']}"

        data["events"].append(event)
        self.store.save(data)
        return CalendarEvent.from_google_event(event)

    def delete_event(self, event_id: str) -> None:
        data = self.store.load()
        for event in data["events"]:
            if event.get("id") == event_id:
                data["events"].remove(event)
                self.store.save(data)
                return
        raise KeyError(f"Unknown calendar event: {event_id}")


def _event_time(
    value: Union[datetime, date, str],
    time_zone: Optional[str],
) -> Dict[str, str]:
    if isinstance(value, datetime):
        result = {"dateTime": _as_rfc3339(value)}
    elif isinstance(value, date):
        result = {"date": value.isoformat()}
    else:
        result = {"dateTime": value}

    if time_zone and "dateTime" in result:
        result["timeZone"] = time_zone
    return result


def _event_start_datetime(event: Dict[str, Any]) -> datetime:
    start = event.get("start", {})
    value = start.get("dateTime") or start.get("date") or "1970-01-01T00:00:00Z"
    return _as_datetime(value)


def _as_datetime(value: Union[datetime, str]) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    normalized = value.replace("Z", "+00:00")
    if "T" not in normalized:
        normalized = f"{normalized}T00:00:00+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_rfc3339(value: datetime) -> str:
    return _as_datetime(value).isoformat().replace("+00:00", "Z")
