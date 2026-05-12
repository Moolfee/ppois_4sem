from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(RuntimeError):
    """Raised when the external configuration file is invalid."""


@dataclass(frozen=True, slots=True)
class WindowConfig:
    title: str
    width: int
    height: int
    fps: int


@dataclass(frozen=True, slots=True)
class GameplayConfig:
    round_time_seconds: int
    base_scroll_speed: int
    playfield_width_factor: float
    camera_pan_margin_px: int
    camera_pan_speed_px_per_sec: int
    crosshair_radius: int
    shot_flash_ms: int
    hit_effect_ms: int


@dataclass(frozen=True, slots=True)
class EffectConfig:
    shot_flash_color: tuple[int, int, int]
    shot_flash_base_radius: int
    shot_flash_max_radius: int
    hit_popup_color: tuple[int, int, int]
    hit_popup_base_radius: int
    hit_popup_max_radius: int
    bullet_hole_lifetime_ms: tuple[int, int]
    bullet_hole_scale_by_layer: dict[str, float]
    spent_ammo_velocity: tuple[int, int]
    spent_ammo_lifetime_ms: int
    spent_ammo_rotation_deg: float
    spent_ammo_angular_velocity_deg: float


@dataclass(frozen=True, slots=True)
class WeaponConfig:
    magazine_size: int
    reload_time_ms: int
    shot_cooldown_ms: int


@dataclass(frozen=True, slots=True)
class AudioConfig:
    enabled: bool
    master_volume: float
    music_volume: float
    gameplay_sfx_volume: float
    weapon_sfx_volume: float
    ui_sfx_volume: float


@dataclass(frozen=True, slots=True)
class UiConfig:
    accent_fill_color: tuple[int, int, int]
    accent_border_color: tuple[int, int, int]
    accent_hover_fill_color: tuple[int, int, int]
    accent_hover_border_color: tuple[int, int, int]
    accent_base_alpha: int
    accent_hover_alpha: int
    button_border_radius: int
    button_small_border_radius: int
    panel_fill_color: tuple[int, int, int]
    panel_fill_alpha: int
    panel_border_color: tuple[int, int, int]
    panel_border_radius: int
    loading_overlay_color: tuple[int, int, int]
    loading_overlay_alpha: int
    loading_bar_background_color: tuple[int, int, int]
    loading_bar_background_alpha: int
    loading_bar_fill_color: tuple[int, int, int]
    loading_bar_fill_alpha: int
    loading_bar_border_color: tuple[int, int, int]
    loading_bar_border_radius: int
    pause_overlay_color: tuple[int, int, int]
    pause_overlay_alpha: int
    crosshair_fallback_color: tuple[int, int, int]
    hud_left_margin_px: int
    hud_top_margin_px: int
    hud_line_gap_px: int
    hud_timer_right_margin_px: int
    hud_timer_top_margin_px: int
    ammo_right_margin_px: int
    ammo_bottom_margin_px: int
    ammo_spacing_factor: float
    reload_label_gap_px: int
    pause_button_width: int
    pause_button_height: int
    pause_button_gap_px: int
    menu_chicken_scale: float
    menu_chicken_center_x: int
    menu_chicken_bottom_offset_px: int
    menu_chicken_down_delay_ms: int
    menu_chicken_return_duration_ms: int


@dataclass(frozen=True, slots=True)
class LeaderboardConfig:
    file_path: Path
    max_entries: int


@dataclass(frozen=True, slots=True)
class ParallaxSheetConfig:
    file_path: Path
    transparent_color: tuple[int, int, int]
    mouse_reaction_px: int
    clear_top_runs_min_width: int


@dataclass(frozen=True, slots=True)
class LayerConfig:
    name: str
    speed_factor: float
    y: int
    tile_width: int
    height: int
    scale_multiplier: float
    source_rect: tuple[int, int, int, int] | None
    vertical_offset: int
    horizontal_offset: int
    cursor_factor: float
    repeat_x: bool
    fit_mode: str
    clear_top_rows: int
    clear_rects: tuple[tuple[int, int, int, int], ...]


@dataclass(frozen=True, slots=True)
class TargetConfig:
    size: tuple[int, int]
    speed: tuple[int, int]
    points: int
    spawn_interval_ms: tuple[int, int]
    directions: tuple[str, ...]
    y_range: tuple[int, int]


@dataclass(frozen=True, slots=True)
class ForegroundEnemyConfig:
    enabled: bool
    size: tuple[int, int]
    points: int
    spawn_interval_ms: tuple[int, int]
    visible_time_ms: tuple[int, int]
    appear_frame_duration_ms: int
    death_frame_duration_ms: int
    death_sink_px: int
    x_margin: int
    spawn_bottom_offset_px: int


@dataclass(frozen=True, slots=True)
class GameConfig:
    base_dir: Path
    window: WindowConfig
    gameplay: GameplayConfig
    effects: EffectConfig
    weapon: WeaponConfig
    audio: AudioConfig
    ui: UiConfig
    leaderboard: LeaderboardConfig
    parallax_sheet: ParallaxSheetConfig | None
    layers: tuple[LayerConfig, ...]
    targets: dict[str, TargetConfig]
    foreground_enemy: ForegroundEnemyConfig | None


def _require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{path} must be an object")
    return value


def _require_str(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{path} must be a non-empty string")
    return value


def _require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{path} must be a boolean")
    return value


def _require_int(value: Any, path: str) -> int:
    if not isinstance(value, int):
        raise ConfigError(f"{path} must be an integer")
    return value


def _require_float(value: Any, path: str) -> float:
    if not isinstance(value, (int, float)):
        raise ConfigError(f"{path} must be a number")
    return float(value)


def _require_int_pair(value: Any, path: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2 or not all(isinstance(item, int) for item in value):
        raise ConfigError(f"{path} must be an array of two integers")
    return value[0], value[1]


def _require_color(value: Any, path: str) -> tuple[int, int, int]:
    if not isinstance(value, list) or len(value) != 3 or not all(isinstance(item, int) for item in value):
        raise ConfigError(f"{path} must be an array of three integers")
    if not all(0 <= item <= 255 for item in value):
        raise ConfigError(f"{path} must contain values in range 0..255")
    return value[0], value[1], value[2]


def _require_int_quad(value: Any, path: str) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4 or not all(isinstance(item, int) for item in value):
        raise ConfigError(f"{path} must be an array of four integers")
    return value[0], value[1], value[2], value[3]


def _require_str_list(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{path} must be a non-empty array of strings")
    return tuple(value)


def _require_float_mapping(value: Any, path: str) -> dict[str, float]:
    mapping = _require_mapping(value, path)
    return {str(key): _require_float(item, f"{path}.{key}") for key, item in mapping.items()}


def _require_int_quad_list(value: Any, path: str) -> tuple[tuple[int, int, int, int], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ConfigError(f"{path} must be an array of rectangles")
    return tuple(_require_int_quad(item, f"{path}[{index}]") for index, item in enumerate(value))


def _load_json_mapping(path: Path, path_name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read {path_name} file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path_name} file {path}: {exc}") from exc
    return _require_mapping(payload, path_name)


def load_game_config(config_path: str | Path) -> GameConfig:
    path = Path(config_path).resolve()

    root = _load_json_mapping(path, "root")
    base_dir = path.parent.parent

    window_raw = _require_mapping(root.get("window"), "window")
    gameplay_raw = _require_mapping(root.get("gameplay"), "gameplay")
    effects_raw = _require_mapping(root.get("effects"), "effects")
    weapon_raw = _require_mapping(root.get("weapon"), "weapon")
    audio_raw = _require_mapping(root.get("audio"), "audio")
    ui_raw = _require_mapping(root.get("ui"), "ui")
    leaderboard_raw = _require_mapping(root.get("leaderboard"), "leaderboard")
    enemy_config_raw = _require_mapping(root.get("enemy_config"), "enemy_config")
    parallax_sheet_raw = root.get("parallax_sheet")

    layers_raw = root.get("layers")
    if not isinstance(layers_raw, list) or not layers_raw:
        raise ConfigError("layers must be a non-empty array")

    enemy_config_path = (base_dir / _require_str(enemy_config_raw.get("file"), "enemy_config.file")).resolve()
    enemy_root = _load_json_mapping(enemy_config_path, "enemy_config")
    foreground_enemy_raw = enemy_root.get("foreground_enemy")
    targets_raw = _require_mapping(enemy_root.get("targets"), "enemy_config.targets")

    parallax_sheet: ParallaxSheetConfig | None = None
    if parallax_sheet_raw is not None:
        sheet = _require_mapping(parallax_sheet_raw, "parallax_sheet")
        parallax_sheet = ParallaxSheetConfig(
            file_path=(base_dir / _require_str(sheet.get("file"), "parallax_sheet.file")).resolve(),
            transparent_color=_require_color(
                sheet.get("transparent_color"),
                "parallax_sheet.transparent_color",
            ),
            mouse_reaction_px=_require_int(
                sheet.get("mouse_reaction_px"),
                "parallax_sheet.mouse_reaction_px",
            ),
            clear_top_runs_min_width=_require_int(
                sheet.get("clear_top_runs_min_width", 120),
                "parallax_sheet.clear_top_runs_min_width",
            ),
        )

    layers: list[LayerConfig] = []
    for index, item in enumerate(layers_raw):
        layer = _require_mapping(item, f"layers[{index}]")
        source_rect_raw = layer.get("source_rect")
        layers.append(
            LayerConfig(
                name=_require_str(layer.get("name"), f"layers[{index}].name"),
                speed_factor=_require_float(layer.get("speed_factor"), f"layers[{index}].speed_factor"),
                y=_require_int(layer.get("y"), f"layers[{index}].y"),
                tile_width=_require_int(layer.get("tile_width"), f"layers[{index}].tile_width"),
                height=_require_int(layer.get("height"), f"layers[{index}].height"),
                scale_multiplier=_require_float(layer.get("scale_multiplier", 1.0), f"layers[{index}].scale_multiplier"),
                source_rect=None
                if source_rect_raw is None
                else _require_int_quad(source_rect_raw, f"layers[{index}].source_rect"),
                vertical_offset=_require_int(layer.get("vertical_offset", 0), f"layers[{index}].vertical_offset"),
                horizontal_offset=_require_int(layer.get("horizontal_offset", 0), f"layers[{index}].horizontal_offset"),
                cursor_factor=_require_float(layer.get("cursor_factor", 0.0), f"layers[{index}].cursor_factor"),
                repeat_x=_require_bool(layer.get("repeat_x", True), f"layers[{index}].repeat_x"),
                fit_mode=_require_str(layer.get("fit_mode", "fixed"), f"layers[{index}].fit_mode"),
                clear_top_rows=_require_int(layer.get("clear_top_rows", 0), f"layers[{index}].clear_top_rows"),
                clear_rects=_require_int_quad_list(layer.get("clear_rects"), f"layers[{index}].clear_rects"),
            )
        )

    targets: dict[str, TargetConfig] = {}
    for name, item in targets_raw.items():
        target = _require_mapping(item, f"targets.{name}")
        targets[name] = TargetConfig(
            size=_require_int_pair(target.get("size"), f"targets.{name}.size"),
            speed=_require_int_pair(target.get("speed"), f"targets.{name}.speed"),
            points=_require_int(target.get("points"), f"targets.{name}.points"),
            spawn_interval_ms=_require_int_pair(
                target.get("spawn_interval_ms"), f"targets.{name}.spawn_interval_ms"
            ),
            directions=_require_str_list(target.get("directions"), f"targets.{name}.directions"),
            y_range=_require_int_pair(target.get("y_range"), f"targets.{name}.y_range"),
        )

    foreground_enemy: ForegroundEnemyConfig | None = None
    if foreground_enemy_raw is not None:
        enemy = _require_mapping(foreground_enemy_raw, "foreground_enemy")
        enemy_size = _require_int_pair(enemy.get("size"), "foreground_enemy.size")
        foreground_enemy = ForegroundEnemyConfig(
            enabled=_require_bool(enemy.get("enabled"), "foreground_enemy.enabled"),
            size=enemy_size,
            points=_require_int(enemy.get("points"), "foreground_enemy.points"),
            spawn_interval_ms=_require_int_pair(
                enemy.get("spawn_interval_ms"),
                "foreground_enemy.spawn_interval_ms",
            ),
            visible_time_ms=_require_int_pair(
                enemy.get("visible_time_ms"),
                "foreground_enemy.visible_time_ms",
            ),
            appear_frame_duration_ms=_require_int(
                enemy.get("appear_frame_duration_ms"),
                "foreground_enemy.appear_frame_duration_ms",
            ),
            death_frame_duration_ms=_require_int(
                enemy.get("death_frame_duration_ms"),
                "foreground_enemy.death_frame_duration_ms",
            ),
            death_sink_px=_require_int(
                enemy.get("death_sink_px", max(28, enemy_size[1] // 2)),
                "foreground_enemy.death_sink_px",
            ),
            x_margin=_require_int(enemy.get("x_margin"), "foreground_enemy.x_margin"),
            spawn_bottom_offset_px=_require_int(
                enemy.get("spawn_bottom_offset_px", max(8, enemy_size[1] // 12)),
                "foreground_enemy.spawn_bottom_offset_px",
            ),
        )

    return GameConfig(
        base_dir=base_dir,
        window=WindowConfig(
            title=_require_str(window_raw.get("title"), "window.title"),
            width=_require_int(window_raw.get("width"), "window.width"),
            height=_require_int(window_raw.get("height"), "window.height"),
            fps=_require_int(window_raw.get("fps"), "window.fps"),
        ),
        gameplay=GameplayConfig(
            round_time_seconds=_require_int(
                gameplay_raw.get("round_time_seconds"), "gameplay.round_time_seconds"
            ),
            base_scroll_speed=_require_int(
                gameplay_raw.get("base_scroll_speed"), "gameplay.base_scroll_speed"
            ),
            playfield_width_factor=_require_float(
                gameplay_raw.get("playfield_width_factor", 1.75),
                "gameplay.playfield_width_factor",
            ),
            camera_pan_margin_px=_require_int(
                gameplay_raw.get("camera_pan_margin_px", 220),
                "gameplay.camera_pan_margin_px",
            ),
            camera_pan_speed_px_per_sec=_require_int(
                gameplay_raw.get("camera_pan_speed_px_per_sec", 900),
                "gameplay.camera_pan_speed_px_per_sec",
            ),
            crosshair_radius=_require_int(
                gameplay_raw.get("crosshair_radius"), "gameplay.crosshair_radius"
            ),
            shot_flash_ms=_require_int(gameplay_raw.get("shot_flash_ms"), "gameplay.shot_flash_ms"),
            hit_effect_ms=_require_int(gameplay_raw.get("hit_effect_ms"), "gameplay.hit_effect_ms"),
        ),
        effects=EffectConfig(
            shot_flash_color=_require_color(
                effects_raw.get("shot_flash_color"),
                "effects.shot_flash_color",
            ),
            shot_flash_base_radius=_require_int(
                effects_raw.get("shot_flash_base_radius"),
                "effects.shot_flash_base_radius",
            ),
            shot_flash_max_radius=_require_int(
                effects_raw.get("shot_flash_max_radius"),
                "effects.shot_flash_max_radius",
            ),
            hit_popup_color=_require_color(
                effects_raw.get("hit_popup_color"),
                "effects.hit_popup_color",
            ),
            hit_popup_base_radius=_require_int(
                effects_raw.get("hit_popup_base_radius"),
                "effects.hit_popup_base_radius",
            ),
            hit_popup_max_radius=_require_int(
                effects_raw.get("hit_popup_max_radius"),
                "effects.hit_popup_max_radius",
            ),
            bullet_hole_lifetime_ms=_require_int_pair(
                effects_raw.get("bullet_hole_lifetime_ms"),
                "effects.bullet_hole_lifetime_ms",
            ),
            bullet_hole_scale_by_layer=_require_float_mapping(
                effects_raw.get("bullet_hole_scale_by_layer"),
                "effects.bullet_hole_scale_by_layer",
            ),
            spent_ammo_velocity=_require_int_pair(
                effects_raw.get("spent_ammo_velocity"),
                "effects.spent_ammo_velocity",
            ),
            spent_ammo_lifetime_ms=_require_int(
                effects_raw.get("spent_ammo_lifetime_ms"),
                "effects.spent_ammo_lifetime_ms",
            ),
            spent_ammo_rotation_deg=_require_float(
                effects_raw.get("spent_ammo_rotation_deg"),
                "effects.spent_ammo_rotation_deg",
            ),
            spent_ammo_angular_velocity_deg=_require_float(
                effects_raw.get("spent_ammo_angular_velocity_deg"),
                "effects.spent_ammo_angular_velocity_deg",
            ),
        ),
        weapon=WeaponConfig(
            magazine_size=_require_int(weapon_raw.get("magazine_size"), "weapon.magazine_size"),
            reload_time_ms=_require_int(weapon_raw.get("reload_time_ms"), "weapon.reload_time_ms"),
            shot_cooldown_ms=_require_int(
                weapon_raw.get("shot_cooldown_ms"), "weapon.shot_cooldown_ms"
            ),
        ),
        audio=AudioConfig(
            enabled=_require_bool(audio_raw.get("enabled"), "audio.enabled"),
            master_volume=_require_float(audio_raw.get("master_volume"), "audio.master_volume"),
            music_volume=_require_float(audio_raw.get("music_volume"), "audio.music_volume"),
            gameplay_sfx_volume=_require_float(
                audio_raw.get("gameplay_sfx_volume", 1.0),
                "audio.gameplay_sfx_volume",
            ),
            weapon_sfx_volume=_require_float(
                audio_raw.get("weapon_sfx_volume", 1.0),
                "audio.weapon_sfx_volume",
            ),
            ui_sfx_volume=_require_float(
                audio_raw.get("ui_sfx_volume", 1.0),
                "audio.ui_sfx_volume",
            ),
        ),
        ui=UiConfig(
            accent_fill_color=_require_color(
                ui_raw.get("accent_fill_color"),
                "ui.accent_fill_color",
            ),
            accent_border_color=_require_color(
                ui_raw.get("accent_border_color"),
                "ui.accent_border_color",
            ),
            accent_hover_fill_color=_require_color(
                ui_raw.get("accent_hover_fill_color"),
                "ui.accent_hover_fill_color",
            ),
            accent_hover_border_color=_require_color(
                ui_raw.get("accent_hover_border_color"),
                "ui.accent_hover_border_color",
            ),
            accent_base_alpha=_require_int(ui_raw.get("accent_base_alpha"), "ui.accent_base_alpha"),
            accent_hover_alpha=_require_int(ui_raw.get("accent_hover_alpha"), "ui.accent_hover_alpha"),
            button_border_radius=_require_int(
                ui_raw.get("button_border_radius"),
                "ui.button_border_radius",
            ),
            button_small_border_radius=_require_int(
                ui_raw.get("button_small_border_radius"),
                "ui.button_small_border_radius",
            ),
            panel_fill_color=_require_color(ui_raw.get("panel_fill_color"), "ui.panel_fill_color"),
            panel_fill_alpha=_require_int(ui_raw.get("panel_fill_alpha"), "ui.panel_fill_alpha"),
            panel_border_color=_require_color(ui_raw.get("panel_border_color"), "ui.panel_border_color"),
            panel_border_radius=_require_int(
                ui_raw.get("panel_border_radius"),
                "ui.panel_border_radius",
            ),
            loading_overlay_color=_require_color(
                ui_raw.get("loading_overlay_color"),
                "ui.loading_overlay_color",
            ),
            loading_overlay_alpha=_require_int(
                ui_raw.get("loading_overlay_alpha"),
                "ui.loading_overlay_alpha",
            ),
            loading_bar_background_color=_require_color(
                ui_raw.get("loading_bar_background_color"),
                "ui.loading_bar_background_color",
            ),
            loading_bar_background_alpha=_require_int(
                ui_raw.get("loading_bar_background_alpha"),
                "ui.loading_bar_background_alpha",
            ),
            loading_bar_fill_color=_require_color(
                ui_raw.get("loading_bar_fill_color"),
                "ui.loading_bar_fill_color",
            ),
            loading_bar_fill_alpha=_require_int(
                ui_raw.get("loading_bar_fill_alpha"),
                "ui.loading_bar_fill_alpha",
            ),
            loading_bar_border_color=_require_color(
                ui_raw.get("loading_bar_border_color"),
                "ui.loading_bar_border_color",
            ),
            loading_bar_border_radius=_require_int(
                ui_raw.get("loading_bar_border_radius"),
                "ui.loading_bar_border_radius",
            ),
            pause_overlay_color=_require_color(
                ui_raw.get("pause_overlay_color"),
                "ui.pause_overlay_color",
            ),
            pause_overlay_alpha=_require_int(
                ui_raw.get("pause_overlay_alpha"),
                "ui.pause_overlay_alpha",
            ),
            crosshair_fallback_color=_require_color(
                ui_raw.get("crosshair_fallback_color"),
                "ui.crosshair_fallback_color",
            ),
            hud_left_margin_px=_require_int(ui_raw.get("hud_left_margin_px"), "ui.hud_left_margin_px"),
            hud_top_margin_px=_require_int(ui_raw.get("hud_top_margin_px"), "ui.hud_top_margin_px"),
            hud_line_gap_px=_require_int(ui_raw.get("hud_line_gap_px"), "ui.hud_line_gap_px"),
            hud_timer_right_margin_px=_require_int(
                ui_raw.get("hud_timer_right_margin_px"),
                "ui.hud_timer_right_margin_px",
            ),
            hud_timer_top_margin_px=_require_int(
                ui_raw.get("hud_timer_top_margin_px"),
                "ui.hud_timer_top_margin_px",
            ),
            ammo_right_margin_px=_require_int(
                ui_raw.get("ammo_right_margin_px"),
                "ui.ammo_right_margin_px",
            ),
            ammo_bottom_margin_px=_require_int(
                ui_raw.get("ammo_bottom_margin_px"),
                "ui.ammo_bottom_margin_px",
            ),
            ammo_spacing_factor=_require_float(
                ui_raw.get("ammo_spacing_factor"),
                "ui.ammo_spacing_factor",
            ),
            reload_label_gap_px=_require_int(
                ui_raw.get("reload_label_gap_px"),
                "ui.reload_label_gap_px",
            ),
            pause_button_width=_require_int(
                ui_raw.get("pause_button_width"),
                "ui.pause_button_width",
            ),
            pause_button_height=_require_int(
                ui_raw.get("pause_button_height"),
                "ui.pause_button_height",
            ),
            pause_button_gap_px=_require_int(
                ui_raw.get("pause_button_gap_px"),
                "ui.pause_button_gap_px",
            ),
            menu_chicken_scale=_require_float(
                ui_raw.get("menu_chicken_scale"),
                "ui.menu_chicken_scale",
            ),
            menu_chicken_center_x=_require_int(
                ui_raw.get("menu_chicken_center_x"),
                "ui.menu_chicken_center_x",
            ),
            menu_chicken_bottom_offset_px=_require_int(
                ui_raw.get("menu_chicken_bottom_offset_px"),
                "ui.menu_chicken_bottom_offset_px",
            ),
            menu_chicken_down_delay_ms=_require_int(
                ui_raw.get("menu_chicken_down_delay_ms"),
                "ui.menu_chicken_down_delay_ms",
            ),
            menu_chicken_return_duration_ms=_require_int(
                ui_raw.get("menu_chicken_return_duration_ms"),
                "ui.menu_chicken_return_duration_ms",
            ),
        ),
        leaderboard=LeaderboardConfig(
            file_path=(base_dir / _require_str(leaderboard_raw.get("file"), "leaderboard.file")).resolve(),
            max_entries=_require_int(leaderboard_raw.get("max_entries"), "leaderboard.max_entries"),
        ),
        parallax_sheet=parallax_sheet,
        layers=tuple(layers),
        targets=targets,
        foreground_enemy=foreground_enemy,
    )
