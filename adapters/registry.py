"""Adapter registry for VibeOS."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from .gmail import GmailAdapter
from .google_calendar import GoogleCalendarAdapter
from .google_tasks import GoogleTasksAdapter
from .local_calendar import LocalCalendarAdapter
from .local_files import LocalFilesAdapter
from .local_notes import LocalNotesAdapter
from .local_tasks import LocalTasksAdapter


AdapterFactory = Callable[[], Any]


class AdapterRegistry:
    """Maps adapter names to factories."""

    def __init__(self) -> None:
        self._factories: Dict[str, AdapterFactory] = {}

    def register(self, name: str, factory: AdapterFactory) -> None:
        self._factories[name] = factory

    def names(self) -> List[str]:
        return sorted(self._factories)

    def create(self, name: str) -> Any:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            raise KeyError(f"Unknown adapter: {name}") from exc
        return factory()


def default_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    for name, factory in (
        ("calendar", GoogleCalendarAdapter),
        ("files", LocalFilesAdapter),
        ("gmail", GmailAdapter),
        ("local_calendar", LocalCalendarAdapter),
        ("local_tasks", LocalTasksAdapter),
        ("notes", LocalNotesAdapter),
        ("tasks", GoogleTasksAdapter),
    ):
        registry.register(name, factory)
    return registry
