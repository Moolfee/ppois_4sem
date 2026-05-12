from __future__ import annotations

from moorhuhn.config.game_config import AudioConfig
from moorhuhn.config.settings import UserSettings, UserSettingsStore


def test_user_settings_normalized_clamps_values() -> None:
    settings = UserSettings(
        master_volume=1.4,
        music_volume=-0.5,
        gameplay_sfx_volume=0.6,
        weapon_sfx_volume=5.0,
        ui_sfx_volume=0.2,
        borderless_fullscreen=1,
    ).normalized()

    assert settings.master_volume == 1.0
    assert settings.music_volume == 0.0
    assert settings.weapon_sfx_volume == 1.0
    assert settings.borderless_fullscreen is True


def test_user_settings_store_roundtrip(tmp_path) -> None:
    store = UserSettingsStore(tmp_path / "settings.json")
    defaults = AudioConfig(
        enabled=True,
        master_volume=0.7,
        music_volume=0.35,
        gameplay_sfx_volume=0.8,
        weapon_sfx_volume=0.85,
        ui_sfx_volume=0.6,
    )

    loaded_defaults = store.load(defaults)
    assert loaded_defaults.master_volume == defaults.master_volume
    assert loaded_defaults.borderless_fullscreen is False

    updated = UserSettings(
        master_volume=0.25,
        music_volume=0.5,
        gameplay_sfx_volume=0.75,
        weapon_sfx_volume=0.9,
        ui_sfx_volume=0.1,
        borderless_fullscreen=False,
    )
    store.save(updated)
    loaded = store.load(defaults)

    assert loaded == updated
