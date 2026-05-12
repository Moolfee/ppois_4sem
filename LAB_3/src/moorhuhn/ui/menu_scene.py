from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from ..game.background import ParallaxBackground, build_scene_backdrop, ease_out_cubic

if TYPE_CHECKING:
    from ..app.application import MoorhuhnApp


class MenuChicken:
    def __init__(self, app: "MoorhuhnApp") -> None:
        self.app = app
        enemy_config = app.config.foreground_enemy
        ui = app.config.ui
        base_width, base_height = enemy_config.size if enemy_config is not None else (182, 182)
        self.scale = ui.menu_chicken_scale
        self.width = int(base_width * self.scale)
        self.height = int(base_height * self.scale)
        self.appear_frame_duration_ms = (
            enemy_config.appear_frame_duration_ms if enemy_config is not None else 75
        )
        self.death_frame_duration_ms = (
            enemy_config.death_frame_duration_ms if enemy_config is not None else 95
        )
        self.death_sink_px = int(
            (enemy_config.death_sink_px if enemy_config is not None else 84) * self.scale
        )
        self.down_delay_ms = ui.menu_chicken_down_delay_ms
        self.return_duration_ms = ui.menu_chicken_return_duration_ms
        self.recover_sink_px = max(20, self.height // 9)
        self.direction = "right"
        self.center_x = ui.menu_chicken_center_x
        self.cover_layer_name = "foreground_landscape"
        self.cover_local_x: float | None = None
        self.cover_bottom_offset: int | None = None
        self.anchor_bottom_y = app.surface.get_height() - ui.menu_chicken_bottom_offset_px
        self.bottom_y = self.anchor_bottom_y
        self.state = "idle"
        self.state_age_ms = 0

    @property
    def current_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.center_x - self.width // 2,
            self.bottom_y - self.height,
            self.width,
            self.height,
        )

    def reset(self) -> None:
        self.state = "idle"
        self.state_age_ms = 0
        self.bottom_y = self.anchor_bottom_y

    def contains_point(self, point: tuple[int, int]) -> bool:
        return self.current_rect.collidepoint(point)

    def handle_click(self, point: tuple[int, int]) -> bool:
        if self.state != "idle" or not self.contains_point(point):
            return False
        self.state = "dying"
        self.state_age_ms = 0
        return True

    def update(self, dt_ms: int) -> None:
        self.state_age_ms += dt_ms
        visuals = self.app.assets.foreground_enemy_visuals

        if self.state == "dying":
            death_frames = len(visuals.death_frames) if visuals is not None and visuals.death_frames else 6
            death_duration_ms = max(1, death_frames * self.death_frame_duration_ms)
            progress = min(1.0, self.state_age_ms / death_duration_ms)
            self.bottom_y = self.anchor_bottom_y + int(self.death_sink_px * ease_out_cubic(progress))
            if self.state_age_ms >= death_duration_ms:
                self.state = "down"
                self.state_age_ms = 0
                self.bottom_y = self.anchor_bottom_y + self.death_sink_px
            return

        if self.state == "down":
            self.bottom_y = self.anchor_bottom_y + self.death_sink_px
            if self.state_age_ms >= self.down_delay_ms:
                self.state = "returning"
                self.state_age_ms = 0
            return

        if self.state == "returning":
            progress = min(1.0, self.state_age_ms / max(1, self.return_duration_ms))
            self.bottom_y = self.anchor_bottom_y + self.recover_sink_px + int(
                (self.death_sink_px - self.recover_sink_px) * (1.0 - ease_out_cubic(progress))
            )
            if self.state_age_ms >= self.return_duration_ms:
                self.state = "recovering"
                self.state_age_ms = 0
                self.bottom_y = self.anchor_bottom_y + self.recover_sink_px
            return

        if self.state == "recovering":
            recovery_frames = (
                max(1, visuals.idle_start_frame + 1)
                if visuals is not None and visuals.appear_frames
                else 6
            )
            recovery_duration_ms = max(1, recovery_frames * self.appear_frame_duration_ms)
            progress = min(1.0, self.state_age_ms / recovery_duration_ms)
            self.bottom_y = self.anchor_bottom_y + int(
                self.recover_sink_px * (1.0 - ease_out_cubic(progress))
            )
            if self.state_age_ms >= recovery_frames * self.appear_frame_duration_ms:
                self.state = "idle"
                self.state_age_ms = 0
                self.bottom_y = self.anchor_bottom_y
            return

        self.bottom_y = self.anchor_bottom_y

    def sync_to_cover(self, parallax_background: ParallaxBackground) -> None:
        if self.cover_local_x is None:
            self.cover_local_x = parallax_background.layer_screen_to_local_x(
                self.cover_layer_name,
                self.center_x,
                self.app.surface.get_width(),
            )
        if self.cover_local_x is not None:
            screen_x = parallax_background.layer_local_to_screen_x(
                self.cover_layer_name,
                self.cover_local_x,
                self.app.surface.get_width(),
            )
            if screen_x is not None:
                self.center_x = round(screen_x)

        cover_edge_y = (
            None
            if self.cover_local_x is None
            else parallax_background.find_layer_lowest_transparent_y_for_local_x(
                self.cover_layer_name,
                self.cover_local_x,
                sample_half_width=max(2, self.width // 18),
            )
        )
        if cover_edge_y is None:
            self.anchor_bottom_y = self.app.surface.get_height() - self.app.config.ui.menu_chicken_bottom_offset_px
            if self.state in {"idle", "recovering"}:
                self.bottom_y = self.anchor_bottom_y
            return

        if self.cover_bottom_offset is None:
            self.cover_bottom_offset = max(12, self.height // 14)
        self.anchor_bottom_y = cover_edge_y + self.cover_bottom_offset
        if self.state in {"idle", "recovering"}:
            self.bottom_y = self.anchor_bottom_y

    def draw(self, surface: pygame.Surface) -> None:
        frame = self._current_frame()
        if frame is not None:
            if frame.get_size() != (self.width, self.height):
                frame = pygame.transform.smoothscale(frame, (self.width, self.height))
            surface.blit(frame, frame.get_rect(midbottom=(self.center_x, self.bottom_y)))
            return

        sprite = self._build_vector_fallback()
        surface.blit(sprite, sprite.get_rect(midbottom=(self.center_x, self.bottom_y)))

    def _current_frame(self) -> pygame.Surface | None:
        visuals = self.app.assets.foreground_enemy_visuals
        if visuals is None or not visuals.has_any:
            return None

        if self.state == "dying":
            if not visuals.death_frames:
                if not visuals.appear_frames:
                    return None
                return self.app.assets.get_foreground_enemy_frame(
                    "appearing",
                    len(visuals.appear_frames) - 1,
                    self.direction,
                )
            frame_index = min(
                len(visuals.death_frames) - 1,
                self.state_age_ms // max(1, self.death_frame_duration_ms),
            )
            return self.app.assets.get_foreground_enemy_frame("dying", frame_index, self.direction)

        if self.state in {"down", "returning"}:
            if not visuals.death_frames:
                if not visuals.appear_frames:
                    return None
                return self.app.assets.get_foreground_enemy_frame(
                    "appearing",
                    len(visuals.appear_frames) - 1,
                    self.direction,
                )
            return self.app.assets.get_foreground_enemy_frame(
                "dying",
                len(visuals.death_frames) - 1,
                self.direction,
            )

        if self.state == "recovering":
            frame_index = min(
                visuals.idle_start_frame,
                self.state_age_ms // max(1, self.appear_frame_duration_ms),
            )
            return self.app.assets.get_foreground_enemy_frame("appearing", frame_index, self.direction)

        idle_frames = visuals.appear_frames[visuals.idle_start_frame:] or visuals.appear_frames[-1:]
        if not idle_frames:
            return None
        idle_index = (self.state_age_ms // max(1, self.appear_frame_duration_ms)) % len(idle_frames)
        return self.app.assets.get_foreground_enemy_frame(
            "appearing",
            visuals.idle_start_frame + idle_index,
            self.direction,
        )

    def _build_vector_fallback(self) -> pygame.Surface:
        sprite = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        body_rect = pygame.Rect(
            int(self.width * 0.22),
            int(self.height * 0.36),
            int(self.width * 0.5),
            int(self.height * 0.3),
        )
        head_center = (int(self.width * 0.73), int(self.height * 0.38))
        tail = [
            (self.width * 0.14, self.height * 0.46),
            (self.width * 0.02, self.height * 0.36),
            (self.width * 0.1, self.height * 0.56),
        ]
        wing_rect = pygame.Rect(
            int(self.width * 0.34),
            int(self.height * 0.4),
            int(self.width * 0.26),
            int(self.height * 0.16),
        )

        eye_shift = math.sin(pygame.time.get_ticks() / 320) * 4 if self.state == "idle" else 0
        pygame.draw.ellipse(sprite, (168, 104, 56), body_rect)
        pygame.draw.ellipse(sprite, (126, 76, 38), wing_rect)
        pygame.draw.circle(sprite, (168, 104, 56), head_center, max(12, int(self.width * 0.1)))
        pygame.draw.polygon(sprite, (120, 72, 36), tail)
        pygame.draw.polygon(
            sprite,
            (227, 171, 62),
            [
                (self.width * 0.81, self.height * 0.39),
                (self.width * 0.95, self.height * 0.36),
                (self.width * 0.81, self.height * 0.33),
            ],
        )
        pygame.draw.circle(
            sprite,
            (16, 16, 16),
            (int(self.width * 0.74 + eye_shift), int(self.height * 0.36)),
            3,
        )
        pygame.draw.line(
            sprite,
            (214, 146, 50),
            (int(self.width * 0.48), int(self.height * 0.66)),
            (int(self.width * 0.46), int(self.height * 0.88)),
            3,
        )
        pygame.draw.line(
            sprite,
            (214, 146, 50),
            (int(self.width * 0.58), int(self.height * 0.66)),
            (int(self.width * 0.56), int(self.height * 0.88)),
            3,
        )

        if self.state in {"dying", "down"}:
            return pygame.transform.rotozoom(sprite, 84, 1.0)
        if self.state == "recovering":
            progress = min(1.0, self.state_age_ms / max(1, self.appear_frame_duration_ms * 4))
            return pygame.transform.rotozoom(sprite, 84 * (1.0 - progress), 1.0)
        return sprite


class MenuSign:
    def __init__(self, app: "MoorhuhnApp") -> None:
        self.app = app
        self.sprite = self._build_sprite()
        self.center_x = 146
        self.cover_layer_name = "foreground_landscape"
        self.cover_local_x: float | None = None
        self.cover_bottom_offset = 16
        self.anchor_bottom_y = app.surface.get_height() - 12

    def _build_sprite(self) -> pygame.Surface | None:
        source = self.app.assets.get_background_tile("front_trunks")
        if source is None:
            return None

        width, height = source.get_size()
        segments: list[tuple[int, int]] = []
        in_run = False
        start = 0
        for x_position in range(width):
            has_alpha = any(source.get_at((x_position, y_position)).a > 0 for y_position in range(height))
            if has_alpha and not in_run:
                start = x_position
                in_run = True
            elif not has_alpha and in_run:
                segments.append((start, x_position - 1))
                in_run = False
        if in_run:
            segments.append((start, width - 1))
        if not segments:
            return None

        x_start, x_end = min(segments, key=lambda item: item[0])
        y_values = [
            y_position
            for x_position in range(x_start, x_end + 1)
            for y_position in range(height)
            if source.get_at((x_position, y_position)).a > 0
        ]
        if not y_values:
            return None

        rect = pygame.Rect(x_start, min(y_values), x_end - x_start + 1, max(y_values) - min(y_values) + 1)
        sign = pygame.Surface(rect.size, pygame.SRCALPHA)
        sign.blit(source, (0, 0), rect)

        target_height = min(420, int(sign.get_height() * 0.94))
        target_width = max(1, int(sign.get_width() * (target_height / max(1, sign.get_height()))))
        return pygame.transform.smoothscale(sign, (target_width, target_height))

    def sync_to_cover(self, parallax_background: ParallaxBackground) -> None:
        if self.sprite is None:
            return

        if self.cover_local_x is None:
            self.cover_local_x = parallax_background.layer_screen_to_local_x(
                self.cover_layer_name,
                self.center_x,
                self.app.surface.get_width(),
            )
        if self.cover_local_x is not None:
            screen_x = parallax_background.layer_local_to_screen_x(
                self.cover_layer_name,
                self.cover_local_x,
                self.app.surface.get_width(),
            )
            if screen_x is not None:
                self.center_x = round(screen_x)

        cover_edge_y = (
            None
            if self.cover_local_x is None
            else parallax_background.find_layer_lowest_transparent_y_for_local_x(
                self.cover_layer_name,
                self.cover_local_x,
                sample_half_width=max(3, self.sprite.get_width() // 22),
            )
        )
        if cover_edge_y is None:
            self.anchor_bottom_y = self.app.surface.get_height() - 12
            return

        self.anchor_bottom_y = cover_edge_y + self.cover_bottom_offset

    def draw(self, surface: pygame.Surface) -> None:
        if self.sprite is None:
            return
        surface.blit(self.sprite, self.sprite.get_rect(midbottom=(self.center_x, self.anchor_bottom_y)))


class MenuScene:
    def __init__(
        self,
        app: "MoorhuhnApp",
        parallax_background: ParallaxBackground | None = None,
        backdrop: pygame.Surface | None = None,
    ) -> None:
        self.app = app
        self.cursor_x = app.surface.get_width() // 2
        self.parallax_background = parallax_background or ParallaxBackground(app.config, app.assets)
        self.backdrop = backdrop or build_scene_backdrop(
            app.surface.get_size(),
            has_parallax_sheet=app.config.parallax_sheet is not None,
        )
        self.sign = MenuSign(app)
        self.chicken = MenuChicken(app)
        self.initialized = False

    def on_enter(self, *, reset: bool = False) -> None:
        if reset or not self.initialized:
            self.cursor_x = self.app.surface.get_width() // 2
            self.parallax_background.reset_view()
            self.sign.sync_to_cover(self.parallax_background)
            self.chicken.reset()
            self.chicken.sync_to_cover(self.parallax_background)
            self.initialized = True
            return
        self.sign.sync_to_cover(self.parallax_background)
        self.chicken.sync_to_cover(self.parallax_background)

    def handle_mouse_motion(self, position: tuple[int, int]) -> None:
        self.cursor_x = position[0]

    def update(self, dt_ms: int) -> None:
        self.parallax_background.update(dt_ms, 0.0, self.cursor_x, self.app.surface.get_width())
        self.sign.sync_to_cover(self.parallax_background)
        self.chicken.sync_to_cover(self.parallax_background)
        self.chicken.update(dt_ms)

    def draw(self, surface: pygame.Surface, *, include_sign: bool = True) -> None:
        surface.blit(self.backdrop, (0, 0))
        self.parallax_background.draw_background_layers(surface, reserve_front_layers=2)
        if include_sign:
            self.sign.draw(surface)
        self.chicken.draw(surface)
        self.parallax_background.draw_foreground_layers(surface, count=2)
