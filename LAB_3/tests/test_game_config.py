from __future__ import annotations

import json

import pytest

from moorhuhn.config.game_config import ConfigError, load_game_config


def test_load_repo_game_config(project_root) -> None:
    config = load_game_config(project_root / "config" / "game_config.json")

    assert config.window.width == 1280
    assert config.effects.bullet_hole_lifetime_ms == (1000, 5000)
    assert config.effects.bullet_hole_scale_by_layer["sky"] == 0.5
    assert config.ui.accent_fill_color == (130, 18, 28)
    assert config.ui.pause_button_width == 420
    assert set(config.targets) == {"near", "mid", "far"}
    assert config.foreground_enemy is not None
    assert config.foreground_enemy.points == 75


def test_invalid_effect_mapping_raises_config_error(project_root, tmp_path) -> None:
    root = json.loads((project_root / "config" / "game_config.json").read_text(encoding="utf-8"))
    enemies = json.loads((project_root / "config" / "enemies.json").read_text(encoding="utf-8"))
    root["effects"]["bullet_hole_scale_by_layer"] = ["bad"]

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "game_config.json").write_text(json.dumps(root), encoding="utf-8")
    (config_dir / "enemies.json").write_text(json.dumps(enemies), encoding="utf-8")

    with pytest.raises(ConfigError):
        load_game_config(config_dir / "game_config.json")
