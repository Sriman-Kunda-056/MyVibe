"""Google Tasks action runner for VibeOS intents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from adapters import GoogleTasksAdapter, TaskItem
from intent_router import VibeIntent


@dataclass(frozen=True)
class TaskActionResult:
    """Result returned after trying to execute a task intent."""

    ok: bool
    message: str
    payload: Dict[str, Any] = field(default_factory=dict)


class TaskActionRunner:
    """Executes normalized task intents against the Google Tasks adapter."""

    def __init__(self, adapter: Optional[GoogleTasksAdapter] = None) -> None:
        self.adapter = adapter or GoogleTasksAdapter()

    def run(self, intent: VibeIntent) -> TaskActionResult:
        if not intent.is_actionable:
            return TaskActionResult(False, "Task intent is not actionable.")

        if intent.name == "tasks.list":
            return self._list_tasks(intent.slots)

        if intent.name == "tasks.create":
            return self._create_task(intent.slots)

        if intent.name == "tasks.complete":
            return self._complete_task(intent.slots)

        if intent.name == "tasks.delete":
            return self._delete_task(intent.slots)

        return TaskActionResult(False, f"Unsupported task intent: {intent.name}")

    def _list_tasks(self, slots: Dict[str, str]) -> TaskActionResult:
        status = slots.get("status", "pending")
        if status not in {"all", "completed", "pending"}:
            return TaskActionResult(False, f"Unsupported task status: {status}")

        include_completed = status in {"all", "completed"}
        tasks = self.adapter.list_tasks(
            tasklist_id=slots.get("tasklist_id"),
            show_completed=include_completed,
            show_hidden=include_completed,
        )
        if status == "completed":
            tasks = [task for task in tasks if task.status == "completed"]
        elif status == "pending":
            tasks = [task for task in tasks if task.status != "completed"]

        return TaskActionResult(
            True,
            f"Found {len(tasks)} tasks.",
            {"tasks": [_task_payload(task) for task in tasks]},
        )

    def _create_task(self, slots: Dict[str, str]) -> TaskActionResult:
        title = slots.get("title", "").strip()
        if not title:
            return TaskActionResult(False, "Missing required task title.")

        task = self.adapter.create_task(
            title=title,
            notes=slots.get("notes"),
            due=slots.get("due"),
            tasklist_id=slots.get("tasklist_id"),
        )
        return TaskActionResult(
            True,
            f"Created task: {task.title}",
            {"task": _task_payload(task)},
        )

    def _complete_task(self, slots: Dict[str, str]) -> TaskActionResult:
        task_id = slots.get("task_id", "").strip()
        if not task_id:
            return TaskActionResult(False, "Missing required task_id field.")

        task = self.adapter.complete_task(
            task_id=task_id,
            tasklist_id=slots.get("tasklist_id"),
        )
        return TaskActionResult(
            True,
            f"Completed task: {task.title}",
            {"task": _task_payload(task)},
        )

    def _delete_task(self, slots: Dict[str, str]) -> TaskActionResult:
        task_id = slots.get("task_id", "").strip()
        if not task_id:
            return TaskActionResult(False, "Missing required task_id field.")

        self.adapter.delete_task(
            task_id=task_id,
            tasklist_id=slots.get("tasklist_id"),
        )
        return TaskActionResult(
            True,
            f"Deleted task: {task_id}",
            {"task_id": task_id},
        )


def _task_payload(task: TaskItem) -> Dict[str, Optional[str]]:
    return {
        "task_id": task.task_id,
        "title": task.title,
        "status": task.status,
        "due": task.due,
        "notes": task.notes,
        "link": task.link,
    }
