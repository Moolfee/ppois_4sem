from __future__ import annotations

import pygame

from moorhuhn.config.game_config import load_game_config
from moorhuhn.game.entities import RoundResult, rounded_accuracy_percent
import moorhuhn.game.world as world_module
from moorhuhn.game.world import GameWorld


class DummyAudio:
    def play_shot(self) -> None:
        pass

    def play_reload(self) -> None:
        pass

    def play_hit(self) -> None:
        pass

    def play_miss(self) -> None:
        pass


class DummyAssets:
    def __init__(self) -> None:
        self.bullet_hole_image = pygame.Surface((18, 18), pygame.SRCALPHA)
        self.bullet_hole_image.fill((255, 255, 255, 255))
        self.foreground_enemy_visuals = None

    def get_background_tile(self, _name: str):
        return None

    def get_crosshair_frame(self, _state: str):
        return None

    def get_ammo_idle_frame(self):
        surface = pygame.Surface((18, 42), pygame.SRCALPHA)
        surface.fill((200, 0, 0, 255))
        return surface

    def get_ammo_animation_frame(self, _progress: float):
        return None

    def get_target_frame(self, _depth: str, _state: str, _elapsed_ms: int, _direction: str):
        return None, False

    def get_foreground_enemy_frame(self, _state: str, _frame_index: int, _direction: str):
        return None


def _build_world(project_root) -> GameWorld:
    config = load_game_config(project_root / "config" / "game_config.json")
    fonts = {
        "title": pygame.font.Font(None, 64),
        "heading": pygame.font.Font(None, 42),
        "body": pygame.font.Font(None, 32),
        "small": pygame.font.Font(None, 24),
    }
    return GameWorld(config, DummyAudio(), fonts, DummyAssets())


def test_foreground_enemy_spawn_uses_full_playfield(project_root) -> None:
    world = _build_world(project_root)
    world_x, bottom_y, direction = world._build_foreground_enemy_spawn()
    enemy_config = world.config.foreground_enemy

    assert enemy_config is not None
    assert enemy_config.x_margin <= world_x <= world.playfield_width - enemy_config.x_margin
    assert bottom_y == world.bounds.height + enemy_config.spawn_bottom_offset_px
    assert direction in {"left", "right"}


def test_reload_slots_fill_right_to_left(project_root) -> None:
    world = _build_world(project_root)
    world.ammo = 3
    world.start_reload()

    assert world.reloading is True
    assert world.reload_start_ammo == 3
    assert [world._reload_slot_index_for_added_shell(index) for index in range(4)] == [3, 2, 1, 0]


def test_impact_decal_attaches_to_parallax_layer(project_root) -> None:
    world = _build_world(project_root)
    decal = world._build_impact_decal((50, 50))

    assert decal.layer_name == "sky"
    assert decal.world_x is None
    assert world.config.effects.bullet_hole_lifetime_ms[0] <= decal.lifetime_ms <= world.config.effects.bullet_hole_lifetime_ms[1]


def test_pause_button_rects_use_ui_config(project_root) -> None:
    world = _build_world(project_root)
    rects = world.pause_button_rects()

    assert rects["resume"].size == (
        world.config.ui.pause_button_width,
        world.config.ui.pause_button_height,
    )
    assert rects["menu"].y == (
        rects["resume"].y
        + world.config.ui.pause_button_height
        + world.config.ui.pause_button_gap_px
    )


def test_accuracy_rounds_to_whole_percent_without_padding() -> None:
    assert rounded_accuracy_percent(0, 0) == 0
    assert rounded_accuracy_percent(1, 100) == 1
    assert rounded_accuracy_percent(1, 3) == 33
    assert RoundResult(0, 1, 99, 100).rounded_accuracy == 1


def test_hud_draws_stats_as_separate_lines(monkeypatch, project_root) -> None:
    world = _build_world(project_root)
    world.score = 120
    world.hits = 7
    world.misses = 2
    world.shots = 10
    captured_texts: list[str] = []

    def _capture_text(_font, text: str, **_kwargs):
        captured_texts.append(text)
        return pygame.Surface((8, 8), pygame.SRCALPHA)

    monkeypatch.setattr(world_module, "render_outlined_text", _capture_text)

    world._draw_hud(pygame.Surface((world.bounds.width, world.bounds.height), pygame.SRCALPHA))

    assert captured_texts[:4] == [
        "Очки: 120",
        "Попадания: 7",
        "Промахи: 2",
        "Точность: 70%",
    ]
