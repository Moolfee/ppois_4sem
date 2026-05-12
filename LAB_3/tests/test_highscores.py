from __future__ import annotations

import json

from moorhuhn.storage.highscores import HighScoreTable


def test_record_score_sorts_truncates_and_normalizes_name(tmp_path) -> None:
    table = HighScoreTable(tmp_path / "highscores.json", max_entries=3)
    table.ensure_storage()

    table.record_score("alice", 10)
    table.record_score("bob", 40)
    table.record_score(" charlie-long-name ", 25)
    entries = table.record_score("zed", 55)

    assert [entry.score for entry in entries] == [55, 40, 25]
    assert entries[0].name == "ZED"
    assert entries[-1].name == "CHARLIE-LONG"


def test_load_entries_ignores_invalid_payloads(tmp_path) -> None:
    table = HighScoreTable(tmp_path / "highscores.json", max_entries=5)
    table.file_path.parent.mkdir(parents=True, exist_ok=True)
    table.file_path.write_text(
        json.dumps(
            [
                {"name": "OK", "score": 30, "created_at": "2026-04-19 20:00"},
                {"name": "BROKEN", "score": "bad", "created_at": "2026-04-19 20:00"},
            ]
        ),
        encoding="utf-8",
    )

    entries = table.load_entries()

    assert len(entries) == 1
    assert entries[0].name == "OK"
    assert entries[0].score == 30
