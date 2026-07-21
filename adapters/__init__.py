"""External service adapters for VibeOS."""

from .gmail import GmailAdapter, GmailMessage
from .google_calendar import CalendarEvent, GoogleCalendarAdapter
from .google_tasks import GoogleTasksAdapter, TaskItem, TaskList
from .local_calendar import LocalCalendarAdapter
from .local_files import FileEntry, LocalFilesAdapter
from .local_notes import LocalNotesAdapter, Note
from .local_tasks import LocalTasksAdapter
from .registry import AdapterRegistry, default_registry

__all__ = [
    "AdapterRegistry",
    "CalendarEvent",
    "FileEntry",
    "GmailAdapter",
    "GmailMessage",
    "GoogleCalendarAdapter",
    "GoogleTasksAdapter",
    "LocalCalendarAdapter",
    "LocalFilesAdapter",
    "LocalNotesAdapter",
    "LocalTasksAdapter",
    "Note",
    "TaskItem",
    "TaskList",
    "default_registry",
]
