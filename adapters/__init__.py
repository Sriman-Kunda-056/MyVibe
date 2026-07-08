"""External service adapters for VibeOS."""

from .google_calendar import CalendarEvent, GoogleCalendarAdapter

__all__ = ["CalendarEvent", "GoogleCalendarAdapter"]
