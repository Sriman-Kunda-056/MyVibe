"""Google Tasks adapter for VibeOS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Union


@dataclass(frozen=True)
class TaskItem:
    """Normalized Google Tasks item."""

    task_id: str
    title: str
    status: str
    due: Optional[str] = None
    notes: Optional[str] = None
    link: Optional[str] = None

    @classmethod
    def from_google_task(cls, task: Dict[str, Any]) -> "TaskItem":
        return cls(
            task_id=task.get("id", ""),
            title=task.get("title", "(no title)"),
            status=task.get("status", ""),
            due=task.get("due"),
            notes=task.get("notes"),
            link=task.get("selfLink"),
        )


@dataclass(frozen=True)
class TaskList:
    """Normalized Google Tasks list."""

    tasklist_id: str
    title: str

    @classmethod
    def from_google_tasklist(cls, tasklist: Dict[str, Any]) -> "TaskList":
        return cls(
            tasklist_id=tasklist.get("id", ""),
            title=tasklist.get("title", "(no title)"),
        )


class GoogleTasksAdapter:
    """Thin adapter around Google Tasks."""

    def __init__(self, tasklist_id: str = "@default", service: Any = None) -> None:
        self.tasklist_id = tasklist_id
        self._service = service

    @property
    def service(self) -> Any:
        if self._service is None:
            from googleapiclient.discovery import build

            from Auth import get_tasks_credentials

            self._service = build("tasks", "v1", credentials=get_tasks_credentials())
        return self._service

    def list_tasklists(self) -> List[TaskList]:
        response = self.service.tasklists().list().execute()
        return [
            TaskList.from_google_tasklist(tasklist)
            for tasklist in response.get("items", [])
        ]

    def list_tasks(
        self,
        tasklist_id: Optional[str] = None,
        show_completed: bool = False,
        max_results: int = 20,
    ) -> List[TaskItem]:
        response = (
            self.service.tasks()
            .list(
                tasklist=tasklist_id or self.tasklist_id,
                showCompleted=show_completed,
                maxResults=max_results,
            )
            .execute()
        )
        return [TaskItem.from_google_task(task) for task in response.get("items", [])]

    def create_task(
        self,
        title: str,
        notes: Optional[str] = None,
        due: Optional[Union[datetime, date, str]] = None,
        tasklist_id: Optional[str] = None,
    ) -> TaskItem:
        body: Dict[str, Any] = {"title": title}
        if notes:
            body["notes"] = notes
        if due:
            body["due"] = _as_task_due(due)

        task = (
            self.service.tasks()
            .insert(tasklist=tasklist_id or self.tasklist_id, body=body)
            .execute()
        )
        return TaskItem.from_google_task(task)

    def complete_task(
        self,
        task_id: str,
        tasklist_id: Optional[str] = None,
    ) -> TaskItem:
        task = (
            self.service.tasks()
            .patch(
                tasklist=tasklist_id or self.tasklist_id,
                task=task_id,
                body={"status": "completed"},
            )
            .execute()
        )
        return TaskItem.from_google_task(task)

    def delete_task(self, task_id: str, tasklist_id: Optional[str] = None) -> None:
        self.service.tasks().delete(
            tasklist=tasklist_id or self.tasklist_id,
            task=task_id,
        ).execute()


def _as_task_due(value: Union[datetime, date, str]) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc).isoformat().replace(
            "+00:00",
            "Z",
        )
    return value
