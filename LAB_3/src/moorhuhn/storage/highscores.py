from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ScoreEntry:
    name: str
    score: int
    created_at: str

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> "ScoreEntry | None":
        name = payload.get("name")
        score = payload.get("score")
        created_at = payload.get("created_at")
        if not isinstance(name, str) or not isinstance(score, int) or not isinstance(created_at, str):
            return None
        return cls(name=name[:12], score=score, created_at=created_at)

    def to_mapping(self) -> dict[str, object]:
        return {
            "name": self.name,
            "score": self.score,
            "created_at": self.created_at,
        }


class HighScoreTable:
    def __init__(self, file_path: Path, max_entries: int) -> None:
        self.file_path = file_path
        self.max_entries = max_entries

    def ensure_storage(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write_entries([])

    def load_entries(self) -> list[ScoreEntry]:
        self.ensure_storage()
        try:
            payload = json.loads(self.file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        if not isinstance(payload, list):
            return []

        entries = [entry for item in payload if isinstance(item, dict) if (entry := ScoreEntry.from_mapping(item))]
        return sorted(entries, key=lambda item: item.score, reverse=True)[: self.max_entries]

    def qualifies(self, score: int) -> bool:
        qualifies, _ = self.score_status(score)
        return qualifies

    def is_new_champion(self, score: int) -> bool:
        _, new_champion = self.score_status(score)
        return new_champion

    def score_status(self, score: int) -> tuple[bool, bool]:
        entries = self.load_entries()
        qualifies = len(entries) < self.max_entries or score > entries[-1].score
        new_champion = not entries or score > entries[0].score
        return qualifies, new_champion

    def record_score(self, name: str, score: int) -> list[ScoreEntry]:
        cleaned_name = (name.strip().upper() or "PLAYER")[:12]
        entries = self.load_entries()
        entries.append(
            ScoreEntry(
                name=cleaned_name,
                score=score,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
        )
        entries = sorted(entries, key=lambda item: item.score, reverse=True)[: self.max_entries]
        self._write_entries(entries)
        return entries

    def _write_entries(self, entries: list[ScoreEntry]) -> None:
        payload = [entry.to_mapping() for entry in entries]
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
