"""Google Calendar adapter for VibeOS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Union

from googleapiclient.discovery import build

from Auth import get_calendar_credentials


@dataclass(frozen=True)
class CalendarEvent:
    """Normalized calendar event returned by the adapter."""

    event_id: str
    summary: str
    start: str
    end: str
    link: Optional[str] = None

    @classmethod
    def from_google_event(cls, event: Dict[str, Any]) -> "CalendarEvent":
        start = event.get("start", {})
        end = event.get("end", {})
        return cls(
            event_id=event.get("id", ""),
            summary=event.get("summary", "(no title)"),
            start=start.get("dateTime") or start.get("date", ""),
            end=end.get("dateTime") or end.get("date", ""),
            link=event.get("htmlLink"),
        )


class GoogleCalendarAdapter:
    """Thin adapter around Google Calendar events used by VibeOS."""

    def __init__(self, calendar_id: str = "primary", service: Any = None) -> None:
        self.calendar_id = calendar_id
        self._service = service

    @property
    def service(self) -> Any:
        if self._service is None:
            credentials = get_calendar_credentials()
            self._service = build("calendar", "v3", credentials=credentials)
        return self._service

    def list_upcoming_events(
        self,
        max_results: int = 10,
        time_min: Optional[datetime] = None,
    ) -> List[CalendarEvent]:
        response = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=_as_rfc3339(time_min or datetime.now(timezone.utc)),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return [
            CalendarEvent.from_google_event(event)
            for event in response.get("items", [])
        ]

    def create_event(
        self,
        summary: str,
        start: Union[datetime, date, str],
        end: Union[datetime, date, str],
        description: Optional[str] = None,
        time_zone: Optional[str] = None,
    ) -> CalendarEvent:
        body: Dict[str, Any] = {
            "summary": summary,
            "start": _event_time(start, time_zone),
            "end": _event_time(end, time_zone),
        }
        if description:
            body["description"] = description

        event = (
            self.service.events()
            .insert(calendarId=self.calendar_id, body=body)
            .execute()
        )
        return CalendarEvent.from_google_event(event)

    def delete_event(self, event_id: str) -> None:
        self.service.events().delete(
            calendarId=self.calendar_id,
            eventId=event_id,
        ).execute()


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


def _as_rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
