"""Intent routing primitives for VibeOS."""

from __future__ import annotations

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

        if self._has_any(normalized, ("calendar", "meeting", "schedule", "event")):
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

    def _unknown(self, text: str) -> VibeIntent:
        return VibeIntent("unknown", 0.0, text)

    @staticmethod
    def _has_any(text: str, words: Iterable[str]) -> bool:
        return any(word in text for word in words)


def route_intent(text: str, router: Optional[IntentRouter] = None) -> VibeIntent:
    active_router = router or IntentRouter()
    return active_router.route(text)
