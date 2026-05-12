from __future__ import annotations

import builtins
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pygame
import pygame.freetype
import pytest

import main as root_launcher
import moorhuhn.main as moorhuhn_main
from moorhuhn.media.assets import AssetLibrary
from moorhuhn.config.game_config import (
    AudioConfig,
    ConfigError,
    _load_json_mapping,
    _require_bool,
    _require_color,
    _require_float,
    _require_int,
    _require_int_pair,
    _require_int_quad,
    _require_int_quad_list,
    _require_mapping,
    _require_str,
    _require_str_list,
    load_game_config,
)
from moorhuhn.config.settings import UserSettings, UserSettingsStore
from moorhuhn.storage.highscores import HighScoreTable, ScoreEntry
from moorhuhn.ui.help import wrap_outlined_text
from moorhuhn.ui.screen_core import BaseScreen, MenuBackdropScreen, ScreenManager
from moorhuhn.ui.text import _render_text_surface, render_outlined_text


def test_root_launcher_delegates_to_package_main(monkeypatch) -> None:
    monkeypatch.setattr(moorhuhn_main, "main", lambda: 17)

    assert root_launcher.main() == 17


def test_root_launcher_reports_missing_pygame(monkeypatch, capsys) -> None:
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "moorhuhn.main":
            exc = ModuleNotFoundError("No module named 'pygame'")
            exc.name = "pygame"
            raise exc
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert root_launcher.main() == 1
    assert "pygame is not installed" in capsys.readouterr().out


def test_root_launcher_runs_main_block(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(moorhuhn_main, "main", lambda: calls.append("main") or 0)

    runpy.run_module("main", run_name="__main__")

    assert calls == ["main"]


def test_package_dunder_main_runs_main(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(moorhuhn_main, "main", lambda: calls.append("main") or 0)

    runpy.run_module("moorhuhn.__main__", run_name="__main__")

    assert calls == ["main"]


def test_shutdown_pygame_quits_mixer_display_and_pygame(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(pygame.mixer, "get_init", lambda: True)
    monkeypatch.setattr(pygame.mixer, "quit", lambda: calls.append("mixer"))
    monkeypatch.setattr(pygame.display, "get_init", lambda: True)
    monkeypatch.setattr(pygame.display, "quit", lambda: calls.append("display"))
    monkeypatch.setattr(pygame, "quit", lambda: calls.append("pygame"))

    moorhuhn_main._shutdown_pygame()

    assert calls == ["mixer", "display", "pygame"]


def test_shutdown_pygame_ignores_pygame_errors(monkeypatch) -> None:
    calls: list[str] = []

    def broken_mixer_quit() -> None:
        raise pygame.error("mixer quit failed")

    def broken_display_quit() -> None:
        raise pygame.error("display quit failed")

    monkeypatch.setattr(pygame.mixer, "get_init", lambda: True)
    monkeypatch.setattr(pygame.mixer, "quit", broken_mixer_quit)
    monkeypatch.setattr(pygame.display, "get_init", lambda: True)
    monkeypatch.setattr(pygame.display, "quit", broken_display_quit)
    monkeypatch.setattr(pygame, "quit", lambda: calls.append("pygame"))

    moorhuhn_main._shutdown_pygame()

    assert calls == ["pygame"]


def test_package_main_runs_app_and_shuts_it_down(monkeypatch) -> None:
    created_apps: list[object] = []

    class DummyApp:
        def __init__(self, project_root: Path) -> None:
            self.project_root = project_root
            self.calls: list[str] = []

        def run(self) -> int:
            self.calls.append("run")
            return 23

        def shutdown(self) -> None:
            self.calls.append("shutdown")

    def build_app(project_root: Path) -> DummyApp:
        app = DummyApp(project_root)
        created_apps.append(app)
        return app

    monkeypatch.setattr(moorhuhn_main, "MoorhuhnApp", build_app)

    assert moorhuhn_main.main() == 23
    assert len(created_apps) == 1
    assert created_apps[0].calls == ["run", "shutdown"]


@pytest.mark.parametrize(
    ("factory", "value", "path", "message"),
    [
        (_require_mapping, [], "node", "node must be an object"),
        (_require_str, "", "node", "node must be a non-empty string"),
        (_require_bool, "yes", "flag", "flag must be a boolean"),
        (_require_int, 1.5, "count", "count must be an integer"),
        (_require_float, "bad", "ratio", "ratio must be a number"),
        (_require_int_pair, [1, "x"], "pair", "pair must be an array of two integers"),
        (_require_int_quad, [1, 2, 3], "quad", "quad must be an array of four integers"),
        (_require_str_list, [], "names", "names must be a non-empty array of strings"),
    ],
)
def test_game_config_helper_validation_errors(factory, value, path, message) -> None:
    with pytest.raises(ConfigError, match=message):
        factory(value, path)


def test_game_config_color_validation_errors() -> None:
    with pytest.raises(ConfigError, match="color must be an array of three integers"):
        _require_color([0, 1], "color")

    with pytest.raises(ConfigError, match="color must contain values in range 0..255"):
        _require_color([0, 300, 1], "color")


def test_game_config_int_quad_list_handles_none_valid_and_invalid() -> None:
    assert _require_int_quad_list(None, "rects") == ()
    assert _require_int_quad_list([[1, 2, 3, 4]], "rects") == ((1, 2, 3, 4),)

    with pytest.raises(ConfigError, match="rects must be an array of rectangles"):
        _require_int_quad_list("bad", "rects")


def test_load_json_mapping_reports_file_and_json_errors(tmp_path) -> None:
    missing_path = tmp_path / "missing.json"
    with pytest.raises(ConfigError, match="cannot read root file"):
        _load_json_mapping(missing_path, "root")

    broken_path = tmp_path / "broken.json"
    broken_path.write_text("{bad json", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid JSON in root file"):
        _load_json_mapping(broken_path, "root")


def test_load_game_config_requires_non_empty_layers(project_root, tmp_path) -> None:
    root = json.loads((project_root / "config" / "game_config.json").read_text(encoding="utf-8"))
    enemies = json.loads((project_root / "config" / "enemies.json").read_text(encoding="utf-8"))
    root["layers"] = []

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "game_config.json").write_text(json.dumps(root), encoding="utf-8")
    (config_dir / "enemies.json").write_text(json.dumps(enemies), encoding="utf-8")

    with pytest.raises(ConfigError, match="layers must be a non-empty array"):
        load_game_config(config_dir / "game_config.json")


def test_user_settings_updated_and_from_mapping_normalize_values() -> None:
    defaults = UserSettings(0.7, 0.5, 0.6, 0.4, 0.3, False)

    updated = defaults.updated(master_volume=2.0, music_volume=-1.0, borderless_fullscreen=1)
    from_mapping = UserSettings.from_mapping(
        {
            "master_volume": "bad",
            "music_volume": "0.25",
            "gameplay_sfx_volume": None,
            "weapon_sfx_volume": "0.8",
            "ui_sfx_volume": "2.0",
            "borderless_fullscreen": 1,
        },
        defaults,
    )

    assert updated.master_volume == 1.0
    assert updated.music_volume == 0.0
    assert updated.borderless_fullscreen is True
    assert from_mapping.master_volume == defaults.master_volume
    assert from_mapping.music_volume == 0.25
    assert from_mapping.gameplay_sfx_volume == defaults.gameplay_sfx_volume
    assert from_mapping.weapon_sfx_volume == 0.8
    assert from_mapping.ui_sfx_volume == 1.0
    assert from_mapping.borderless_fullscreen is True


def test_settings_store_load_falls_back_for_invalid_payload_and_save_normalizes(tmp_path) -> None:
    audio = AudioConfig(
        enabled=True,
        master_volume=0.7,
        music_volume=0.35,
        gameplay_sfx_volume=0.8,
        weapon_sfx_volume=0.85,
        ui_sfx_volume=0.6,
    )
    store = UserSettingsStore(tmp_path / "settings.json")

    store.path.write_text("[]", encoding="utf-8")
    assert store.load(audio) == store.build_defaults(audio)

    store.path.write_text("{broken", encoding="utf-8")
    assert store.load(audio) == store.build_defaults(audio)

    store.save(UserSettings(2.0, -1.0, 0.3, 0.4, 5.0, 1))
    saved_payload = json.loads(store.path.read_text(encoding="utf-8"))

    assert saved_payload == {
        "master_volume": 1.0,
        "music_volume": 0.0,
        "gameplay_sfx_volume": 0.3,
        "weapon_sfx_volume": 0.4,
        "ui_sfx_volume": 1.0,
        "borderless_fullscreen": True,
    }


def test_score_entry_mapping_and_highscore_table_edge_cases(tmp_path) -> None:
    table = HighScoreTable(tmp_path / "scores.json", max_entries=2)

    assert ScoreEntry.from_mapping({"name": "AAA", "score": "5", "created_at": "2026"}) is None

    entry = ScoreEntry.from_mapping({"name": "LONG-NAME-12345", "score": 5, "created_at": "2026"})
    assert entry is not None
    assert entry.name == "LONG-NAME-12"
    assert entry.to_mapping() == {"name": "LONG-NAME-12", "score": 5, "created_at": "2026"}

    table.ensure_storage()
    assert json.loads(table.file_path.read_text(encoding="utf-8")) == []

    table.file_path.write_text("{}", encoding="utf-8")
    assert table.load_entries() == []

    table.file_path.write_text("{bad", encoding="utf-8")
    assert table.load_entries() == []

    table.record_score("alpha", 10)
    table.record_score("beta", 30)

    assert table.qualifies(40) is True
    assert table.qualifies(5) is False
    assert table.is_new_champion(31) is True
    assert table.is_new_champion(25) is False


def test_wrap_outlined_text_handles_empty_wrapped_and_single_line() -> None:
    font = pygame.font.Font(None, 28)

    empty_lines = wrap_outlined_text(font, "", 200)
    wrapped_lines = wrap_outlined_text(font, "one two three four", 35)
    single_line = wrap_outlined_text(font, "short text", 500)

    assert len(empty_lines) == 1
    assert len(wrapped_lines) > 1
    assert len(single_line) == 1


def test_text_helpers_cover_freetype_type_error_and_zero_outline() -> None:
    font = pygame.font.Font(None, 28)
    freetype_font = pygame.freetype.Font(None, 28)

    plain = render_outlined_text(font, "text", outline_width=0)
    assert plain.get_width() > 0
    assert _render_text_surface(freetype_font, "text", (255, 255, 255)).get_width() > 0

    with pytest.raises(TypeError, match="Unsupported font type"):
        _render_text_surface(object(), "text", (255, 255, 255))


def test_screen_core_base_backdrop_and_manager_behaviour(monkeypatch) -> None:
    events: list[tuple[str, object]] = []
    visible_calls: list[bool] = []

    class DummyChicken:
        def __init__(self, should_hit: bool) -> None:
            self.should_hit = should_hit

        def handle_click(self, position: tuple[int, int]) -> bool:
            events.append(("click", position))
            return self.should_hit

    class DummyScene:
        def __init__(self, should_hit: bool) -> None:
            self.chicken = DummyChicken(should_hit)

        def on_enter(self, *, reset: bool = False) -> None:
            events.append(("enter", reset))

        def update(self, dt_ms: int) -> None:
            events.append(("update", dt_ms))

        def draw(self, _surface: pygame.Surface, *, include_sign: bool = True) -> None:
            events.append(("draw", include_sign))

        def handle_mouse_motion(self, position: tuple[int, int]) -> None:
            events.append(("move", position))

    class DummyAudio:
        def play_menu_loop(self) -> None:
            events.append(("menu_loop", None))

        def play_hit(self) -> None:
            events.append(("hit", None))

    app = type(
        "DummyApp",
        (),
        {
            "menu_scene": DummyScene(True),
            "audio": DummyAudio(),
        },
    )()
    screen = MenuBackdropScreen(app)
    monkeypatch.setattr(pygame.mouse, "set_visible", visible_calls.append)

    screen.on_enter(reset_scene=True)
    screen.update(30)
    screen.draw_menu_scene(pygame.Surface((16, 16)), include_sign=False)
    assert screen.handle_menu_scene_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (1, 2)})) is False
    assert screen.handle_menu_scene_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (3, 4)})
    ) is True

    assert visible_calls == [True]
    assert events[:6] == [
        ("menu_loop", None),
        ("enter", True),
        ("update", 30),
        ("draw", False),
        ("move", (1, 2)),
        ("click", (3, 4)),
    ]
    assert ("hit", None) in events

    assert BaseScreen(app).on_enter() is None
    assert BaseScreen(app).on_leave() is None
    assert BaseScreen(app).handle_event(pygame.event.Event(pygame.USEREVENT, {})) is None
    assert BaseScreen(app).update(1) is None
    with pytest.raises(NotImplementedError):
        BaseScreen(app).draw(pygame.Surface((8, 8)))

    manager = ScreenManager(app)

    class DummyScreen(BaseScreen):
        def __init__(self, app, name: str) -> None:
            super().__init__(app)
            self.name = name

        def on_enter(self, **payload: object) -> None:
            events.append((f"{self.name}_enter", payload))

        def on_leave(self) -> None:
            events.append((f"{self.name}_leave", None))

        def draw(self, surface: pygame.Surface) -> None:
            surface.fill((0, 0, 0))

    first = DummyScreen(app, "first")
    second = DummyScreen(app, "second")
    manager.register("first", first)
    manager.register("second", second)
    manager.switch("first", token=1)
    manager.switch("second", token=2)

    assert manager.current is second
    assert ("first_enter", {"token": 1}) in events
    assert ("first_leave", None) in events
    assert ("second_enter", {"token": 2}) in events


def test_asset_library_accepts_foreground_enemy_and_legacy_foreground_huhn_keys(monkeypatch) -> None:
    captured: list[tuple[int, str]] = []

    def fake_load_frames(self, manifest, *, scaled_size=None):
        captured.append((manifest["frame_size"][0], manifest["file"]))
        return (pygame.Surface((4, 4), pygame.SRCALPHA),)

    monkeypatch.setattr(AssetLibrary, "_load_frames_from_strip_manifest", fake_load_frames)

    def build_assets(manifest: dict[str, object]) -> AssetLibrary:
        library = AssetLibrary.__new__(AssetLibrary)
        library.manifest = manifest
        library.foreground_enemy_visuals = None
        library.project_root = Path(".")
        library.root = Path("assets")
        config = SimpleNamespace(foreground_enemy=SimpleNamespace(enabled=True, size=(182, 182)))
        library._load_special_targets(config)
        return library

    current = build_assets(
        {
            "special_targets": {
                "foreground_enemy": {
                    "idle_start_frame": 5,
                    "native_direction": "left",
                    "appear": {"file": "appear.png", "frame_size": [10, 10]},
                    "death": {"file": "death.png", "frame_size": [10, 10]},
                }
            }
        }
    )
    legacy = build_assets(
        {
            "special_targets": {
                "foreground_huhn": {
                    "idle_start_frame": 3,
                    "native_direction": "right",
                    "appear": {"file": "legacy_appear.png", "frame_size": [8, 8]},
                    "death": {"file": "legacy_death.png", "frame_size": [8, 8]},
                }
            }
        }
    )

    assert current.foreground_enemy_visuals is not None
    assert current.foreground_enemy_visuals.idle_start_frame == 5
    assert current.foreground_enemy_visuals.native_direction == "left"
    assert legacy.foreground_enemy_visuals is not None
    assert legacy.foreground_enemy_visuals.idle_start_frame == 3
    assert legacy.foreground_enemy_visuals.native_direction == "right"
    assert captured == [
        (10, "appear.png"),
        (10, "death.png"),
        (8, "legacy_appear.png"),
        (8, "legacy_death.png"),
    ]
