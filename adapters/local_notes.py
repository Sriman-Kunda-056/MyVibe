"""Local markdown notes adapter for VibeOS."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class Note:
    """A local markdown note."""

    note_id: str
    title: str
    path: str
    content: str
    updated_at: str


class LocalNotesAdapter:
    """Stores simple markdown notes under a local directory."""

    def __init__(self, root_dir: str = "notes") -> None:
        self.root = Path(root_dir)

    def list_notes(self) -> List[Note]:
        if not self.root.exists():
            return []
        return [self.read_note(path.stem) for path in sorted(self.root.glob("*.md"))]

    def create_note(self, title: str, content: str = "") -> Note:
        self.root.mkdir(parents=True, exist_ok=True)
        note_id = _slugify(title)
        path = self._path_for(note_id)
        body = _note_body(title, content)
        try:
            with path.open("x", encoding="utf-8") as note_file:
                note_file.write(body)
        except FileExistsError as exc:
            raise FileExistsError(f"Note already exists: {note_id}") from exc
        return self.read_note(note_id)

    def read_note(self, note_id: str) -> Note:
        path = self._path_for(note_id)
        content = path.read_text(encoding="utf-8")
        title = _title_from_content(content) or note_id.replace("-", " ").title()
        updated_at = datetime.fromtimestamp(
            path.stat().st_mtime,
            tz=timezone.utc,
        ).isoformat()
        return Note(note_id, title, str(path), content, updated_at)

    def append_note(self, note_id: str, content: str) -> Note:
        path = self._path_for(note_id)
        with path.open("r+", encoding="utf-8") as note_file:
            note_file.seek(0, 2)
            note_file.write("\n")
            note_file.write(content)
            note_file.write("\n")
        return self.read_note(note_id)

    def find_notes(self, query: str) -> List[Note]:
        normalized = query.lower()
        return [
            note
            for note in self.list_notes()
            if normalized in note.title.lower() or normalized in note.content.lower()
        ]

    def _path_for(self, note_id: str) -> Path:
        safe_id = _slugify(note_id)
        return self.root / f"{safe_id}.md"


def _note_body(title: str, content: str) -> str:
    parts = [f"# {title.strip()}", ""]
    if content:
        parts.append(content.rstrip())
        parts.append("")
    return "\n".join(parts)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def _title_from_content(content: str) -> Optional[str]:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None
