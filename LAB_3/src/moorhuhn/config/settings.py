from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from .game_config import AudioConfig


@dataclass(slots=True)
class UserSettings:
    master_volume: float
    music_volume: float
    gameplay_sfx_volume: float
    weapon_sfx_volume: float
    ui_sfx_volume: float
    borderless_fullscreen: bool

    def normalized(self) -> "UserSettings":
        return UserSettings(
            master_volume=_clamp_unit(self.master_volume),
            music_volume=_clamp_unit(self.music_volume),
            gameplay_sfx_volume=_clamp_unit(self.gameplay_sfx_volume),
            weapon_sfx_volume=_clamp_unit(self.weapon_sfx_volume),
            ui_sfx_volume=_clamp_unit(self.ui_sfx_volume),
            borderless_fullscreen=bool(self.borderless_fullscreen),
        )

    def updated(self, **changes: Any) -> "UserSettings":
        return replace(self, **changes).normalized()

    @classmethod
    def from_mapping(cls, payload: dict[str, Any], defaults: "UserSettings") -> "UserSettings":
        return cls(
            master_volume=_coerce_float(payload.get("master_volume"), defaults.master_volume),
            music_volume=_coerce_float(payload.get("music_volume"), defaults.music_volume),
            gameplay_sfx_volume=_coerce_float(
                payload.get("gameplay_sfx_volume"),
                defaults.gameplay_sfx_volume,
            ),
            weapon_sfx_volume=_coerce_float(
                payload.get("weapon_sfx_volume"),
                defaults.weapon_sfx_volume,
            ),
            ui_sfx_volume=_coerce_float(payload.get("ui_sfx_volume"), defaults.ui_sfx_volume),
            borderless_fullscreen=bool(
                payload.get("borderless_fullscreen", defaults.borderless_fullscreen)
            ),
        ).normalized()


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class UserSettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def build_defaults(self, audio: AudioConfig) -> UserSettings:
        return UserSettings(
            master_volume=audio.master_volume,
            music_volume=audio.music_volume,
            gameplay_sfx_volume=audio.gameplay_sfx_volume,
            weapon_sfx_volume=audio.weapon_sfx_volume,
            ui_sfx_volume=audio.ui_sfx_volume,
            borderless_fullscreen=False,
        ).normalized()

    def load(self, audio: AudioConfig) -> UserSettings:
        defaults = self.build_defaults(audio)
        if not self.path.exists():
            return defaults

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return defaults

        if not isinstance(payload, dict):
            return defaults

        return UserSettings.from_mapping(payload, defaults)

    def save(self, settings: UserSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(settings.normalized()), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
