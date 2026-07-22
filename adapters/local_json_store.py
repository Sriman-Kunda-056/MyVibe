"""Shared JSON persistence helper for local VibeOS adapters."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict


class LocalJsonStore:
    """Loads and saves a small JSON document under an adapter-owned root."""

    def __init__(self, root_dir: str, filename: str, default_data: Dict[str, Any]) -> None:
        self.root = Path(root_dir)
        self.path = self.root / filename
        self.default_data = default_data

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return copy.deepcopy(self.default_data)
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: Dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )