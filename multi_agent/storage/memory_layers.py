from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class MemoryManager:
    """Filesystem-backed memory layer manager.

    Layout:
    - local short-term memory: <root>/local_short_term/<agent>/<run_id>/
    - shared working memory:   <root>/shared_working/<run_id>/
    - long-term memory:        <root>/long_term/
    - artifact store:          <root>/artifacts/<run_id>/
    """

    root: Path = Path("runtime_state")

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def local_short_term(self, agent_name: str, run_id: str) -> Path:
        path = self.root / "local_short_term" / agent_name / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def shared_working(self, run_id: str) -> Path:
        path = self.root / "shared_working" / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def long_term(self, namespace: Optional[str] = None) -> Path:
        path = self.root / "long_term"
        if namespace:
            path = path / namespace
        path.mkdir(parents=True, exist_ok=True)
        return path

    def artifact_store(self, run_id: str) -> Path:
        path = self.root / "artifacts" / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path
