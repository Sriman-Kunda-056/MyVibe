"""Local file adapter for VibeOS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class FileEntry:
    """A file visible through the local file adapter."""

    relative_path: str
    size: int
    is_dir: bool


class LocalFilesAdapter:
    """Restricts file operations to a configured root directory."""

    def __init__(self, root_dir: str = "workspace") -> None:
        self.root = Path(root_dir)

    def list_entries(self, relative_dir: str = ".") -> List[FileEntry]:
        directory = self._resolve(relative_dir)
        if not directory.exists():
            return []
        return [
            FileEntry(
                relative_path=self._relative_path(path),
                size=0 if path.is_dir() else path.stat().st_size,
                is_dir=path.is_dir(),
            )
            for path in sorted(directory.iterdir())
        ]

    def read_text(self, relative_path: str) -> str:
        return self._resolve(relative_path).read_text(encoding="utf-8")

    def write_text(self, relative_path: str, content: str) -> FileEntry:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return FileEntry(self._relative_path(path), path.stat().st_size, False)

    def _relative_path(self, path: Path) -> str:
        return path.relative_to(self.root.resolve()).as_posix()

    def _resolve(self, relative_path: str) -> Path:
        if not str(relative_path).strip():
            raise ValueError("Path must not be empty.")

        requested = Path(relative_path)
        if requested.is_absolute():
            raise ValueError(f"Path must be relative: {relative_path}")

        self.root.mkdir(parents=True, exist_ok=True)
        root = self.root.resolve()
        path = (root / requested).resolve()
        if root != path and root not in path.parents:
            raise ValueError(f"Path escapes adapter root: {relative_path}")
        return path
