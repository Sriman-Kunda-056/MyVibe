"""Intent routing primitives for VibeOS."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional


@dataclass(frozen=True)
class VibeIntent:
    """Normalized action request produced from a user message."""

    name: str
    confidence: float
    source_text: str
    slots: Dict[str, str] = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        return self.name != "unknown" and self.confidence >= 0.5


class IntentRouter:
    """Small rule-based router before VibeOS grows an LLM planner."""

    def route(self, text: str) -> VibeIntent:
        normalized = " ".join(text.lower().strip().split())
        if not normalized:
            return self._unknown(text)

        if self._has_any(
            normalized,
            ("task", "tasks", "todo", "todos", "to-do", "to-dos"),
        ):
            return self._task_intent(text, normalized)

        if self._has_any(
            normalized,
            (
                "calendar",
                "calendars",
                "meeting",
                "meetings",
                "schedule",
                "event",
                "events",
            ),
        ):
            return self._calendar_intent(text, normalized)

        return self._unknown(text)

    def _calendar_intent(self, original: str, normalized: str) -> VibeIntent:
        if self._has_any(normalized, ("delete", "remove", "cancel")):
            return VibeIntent("calendar.delete_event", 0.75, original)

        if self._has_any(normalized, ("create", "add", "book", "schedule")):
            return VibeIntent("calendar.create_event", 0.8, original)

        if self._has_any(normalized, ("show", "list", "what", "next", "upcoming")):
            return VibeIntent("calendar.list_upcoming", 0.8, original)

        return VibeIntent("calendar.list_upcoming", 0.55, original)

    def _task_intent(self, original: str, normalized: str) -> VibeIntent:
        if self._has_any(normalized, ("delete", "remove")):
            slots = self._task_id_slots(normalized)
            return VibeIntent("tasks.delete", 0.75, original, slots)

        if self._has_any(normalized, ("create", "add", "new", "schedule")):
            slots = self._task_title_slots(original)
            return VibeIntent("tasks.create", 0.8, original, slots)

        if self._has_any(normalized, ("show", "list", "what")):
            status = "pending"
            if self._has_any(normalized, ("completed", "done")):
                status = "completed"
            elif self._has_any(normalized, ("all",)):
                status = "all"
            if self._has_any(normalized, ("pending",)):
                status = "pending"
            return VibeIntent("tasks.list", 0.8, original, {"status": status})

        if self._has_any(normalized, ("mark", "complete", "finish", "done")):
            slots = self._task_id_slots(normalized)
            return VibeIntent("tasks.complete", 0.8, original, slots)

        if self._has_any(normalized, ("next", "pending")):
            return VibeIntent("tasks.list", 0.8, original)

        return VibeIntent("tasks.list", 0.55, original)

    def _unknown(self, text: str) -> VibeIntent:
        return VibeIntent("unknown", 0.0, text)

    @staticmethod
    def _has_any(text: str, words: Iterable[str]) -> bool:
        return any(
            re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text)
            for word in words
        )

    @staticmethod
    def _task_id_slots(text: str) -> Dict[str, str]:
        match = re.search(
            r"(?<!\w)(?:task|tasks|todo|todos|to-do|to-dos)\s+(?:id\s+)?([a-z0-9][\w-]*)",
            text,
        )
        if not match:
            return {}
        return {"task_id": match.group(1)}

    @staticmethod
    def _task_title_slots(text: str) -> Dict[str, str]:
        normalized = " ".join(text.strip().split())
        for pattern in (
            r"(?i)\b(?:create|add|new)\s+(?:a\s+)?(?:task|todo|to-do)\s+(?:called|named|titled|for|to)\s+(.+)$",
            r"(?i)\b(?:create|add|new)\s+(?:a\s+)?(?:task|todo|to-do)\s+(.+)$",
        ):
            match = re.search(pattern, normalized)
            if match:
                title = match.group(1).strip(" .?!")
                if title:
                    return {"title": title}
        return {}


def route_intent(text: str, router: Optional[IntentRouter] = None) -> VibeIntent:
    active_router = router or IntentRouter()
    return active_router.route(text)
