"""Local JSON-backed tasks adapter for VibeOS."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Union

from .google_tasks import TaskItem, TaskList
from .local_json_store import LocalJsonStore


class LocalTasksAdapter:
    """Stores task items in a local JSON file for offline development."""

    def __init__(
        self,
        root_dir: str = "tasks",
        tasklist_id: str = "@default",
        tasklist_title: str = "Local Tasks",
    ) -> None:
        self.tasklist_id = tasklist_id
        self.store = LocalJsonStore(
            root_dir,
            "tasks.json",
            {
                "tasklists": [
                    {"id": tasklist_id, "title": tasklist_title},
                ],
                "tasks": [],
            },
        )

    def list_tasklists(self) -> List[TaskList]:
        data = self._load()
        return [TaskList.from_google_tasklist(tasklist) for tasklist in data["tasklists"]]

    def list_tasks(
        self,
        tasklist_id: Optional[str] = None,
        show_completed: bool = False,
        max_results: int = 20,
        show_hidden: bool = False,
    ) -> List[TaskItem]:
        active_tasklist_id = tasklist_id or self.tasklist_id
        tasks = [
            task
            for task in self._load()["tasks"]
            if task.get("tasklist_id") == active_tasklist_id
        ]
        if not show_completed:
            tasks = [task for task in tasks if task.get("status") != "completed"]
        if not show_hidden:
            tasks = [task for task in tasks if not task.get("hidden", False)]
        return [TaskItem.from_google_task(task) for task in tasks[:max_results]]

    def create_task(
        self,
        title: str,
        notes: Optional[str] = None,
        due: Optional[Union[datetime, date, str]] = None,
        tasklist_id: Optional[str] = None,
    ) -> TaskItem:
        title = title.strip()
        if not title:
            raise ValueError("Task title must not be empty.")

        data = self._load()
        task = {
            "id": f"local-{uuid.uuid4().hex}",
            "tasklist_id": tasklist_id or self.tasklist_id,
            "title": title,
            "status": "needsAction",
        }
        if notes:
            task["notes"] = notes
        if due:
            task["due"] = _as_task_due(due)

        data["tasks"].append(task)
        self._save(data)
        return TaskItem.from_google_task(task)

    def complete_task(
        self,
        task_id: str,
        tasklist_id: Optional[str] = None,
    ) -> TaskItem:
        data, task = self._find_task(task_id, tasklist_id)
        task["status"] = "completed"
        self._save(data)
        return TaskItem.from_google_task(task)

    def delete_task(self, task_id: str, tasklist_id: Optional[str] = None) -> None:
        data, task = self._find_task(task_id, tasklist_id)
        data["tasks"].remove(task)
        self._save(data)

    def _find_task(
        self,
        task_id: str,
        tasklist_id: Optional[str] = None,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        active_tasklist_id = tasklist_id or self.tasklist_id
        data = self._load()
        for task in data["tasks"]:
            if task.get("id") == task_id and task.get("tasklist_id") == active_tasklist_id:
                return data, task
        raise KeyError(f"Unknown task: {task_id}")

    def _load(self) -> Dict[str, Any]:
        return self.store.load()

    def _save(self, data: Dict[str, Any]) -> None:
        self.store.save(data)


def _as_task_due(value: Union[datetime, date, str]) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return datetime(
            value.year,
            value.month,
            value.day,
            tzinfo=timezone.utc,
        ).isoformat().replace("+00:00", "Z")
    return value
