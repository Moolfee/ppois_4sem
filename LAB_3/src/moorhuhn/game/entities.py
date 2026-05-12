from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from ..config.game_config import ForegroundEnemyConfig, TargetConfig
from ..media.assets import AssetLibrary
from ..ui.text import render_outlined_text
from .background import ease_out_cubic

if TYPE_CHECKING:
    from .background import ParallaxBackground

DEPTH_ORDER = ("far", "mid", "near")
DEPTH_PRIORITY = {depth: index for index, depth in enumerate(DEPTH_ORDER)}

FALLBACK_TARGET_COLORS: dict[str, dict[str, tuple[int, int, int]]] = {
    "near": {
        "body": (151, 95, 45),
        "wing": (211, 157, 73),
    },
    "mid": {
        "body": (94, 81, 58),
        "wing": (179, 170, 118),
    },
    "far": {
        "body": (70, 70, 70),
        "wing": (164, 164, 164),
    },
}


def rounded_accuracy_percent(hits: int, shots: int) -> int:
    if shots <= 0:
        return 0
    return int((hits * 100) / shots + 0.5)


@dataclass(slots=True)
class RoundResult:
    score: int
    hits: int
    misses: int
    shots: int

    @property
    def accuracy(self) -> float:
        return 0.0 if self.shots == 0 else (self.hits / self.shots) * 100.0

    @property
    def rounded_accuracy(self) -> int:
        return rounded_accuracy_percent(self.hits, self.shots)


@dataclass(slots=True)
class Effect:
    position: tuple[int, int]
    color: tuple[int, int, int]
    base_radius: float
    max_radius: float
    lifetime_ms: int
    label: str = ""
    show_marker: bool = True
    age_ms: int = 0

    def update(self, dt_ms: int) -> None:
        self.age_ms += dt_ms

    @property
    def done(self) -> bool:
        return self.age_ms >= self.lifetime_ms

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        progress = min(1.0, self.age_ms / self.lifetime_ms)
        radius = int(self.base_radius + (self.max_radius - self.base_radius) * progress)
        if self.show_marker:
            alpha = max(0, 255 - int(255 * progress))
            overlay = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
            center = overlay.get_width() // 2, overlay.get_height() // 2
            pygame.draw.circle(overlay, (*self.color, alpha), center, radius, width=3)
            pygame.draw.line(
                overlay,
                (*self.color, alpha),
                (center[0] - radius - 4, center[1]),
                (center[0] + radius + 4, center[1]),
                2,
            )
            pygame.draw.line(
                overlay,
                (*self.color, alpha),
                (center[0], center[1] - radius - 4),
                (center[0], center[1] + radius + 4),
                2,
            )
            surface.blit(overlay, overlay.get_rect(center=self.position))

        if self.label:
            text = render_outlined_text(font, self.label, outline_width=1)
            text_rect = text.get_rect(center=(self.position[0], self.position[1] - radius - 16))
            surface.blit(text, text_rect)


@dataclass(slots=True)
class ImpactDecal:
    screen_y: int
    lifetime_ms: int
    world_x: float | None = None
    layer_name: str | None = None
    layer_local_x: float | None = None
    age_ms: int = 0

    def update(self, dt_ms: int) -> None:
        self.age_ms += dt_ms

    @property
    def done(self) -> bool:
        return self.age_ms >= self.lifetime_ms

    def draw(
        self,
        surface: pygame.Surface,
        image: pygame.Surface | None,
        camera_x: float,
        parallax_background: "ParallaxBackground",
        scale_by_layer: dict[str, float],
    ) -> None:
        if image is None:
            return

        screen_x: int | None = None
        if self.layer_name is not None and self.layer_local_x is not None:
            layer_screen_x = parallax_background.layer_local_to_screen_x(
                self.layer_name,
                self.layer_local_x,
                surface.get_width(),
            )
            if layer_screen_x is not None:
                screen_x = int(round(layer_screen_x))
        elif self.world_x is not None:
            screen_x = int(round(self.world_x - camera_x))
        if screen_x is None:
            return

        alpha = max(0, 255 - int(255 * (self.age_ms / max(1, self.lifetime_ms))))
        sprite = image.copy()
        scale = scale_by_layer.get(self.layer_name or "", 1.0)
        if scale != 1.0:
            sprite = pygame.transform.smoothscale(
                sprite,
                (
                    max(1, int(round(sprite.get_width() * scale))),
                    max(1, int(round(sprite.get_height() * scale))),
                ),
            )
        sprite.set_alpha(alpha)
        surface.blit(sprite, sprite.get_rect(center=(screen_x, self.screen_y)))


@dataclass(slots=True)
class SpentAmmoAnimation:
    position: pygame.Vector2
    velocity: pygame.Vector2
    lifetime_ms: int
    rotation: float = 0.0
    angular_velocity: float = 580.0
    age_ms: int = 0

    def update(self, dt_ms: int) -> None:
        dt_seconds = dt_ms / 1000
        self.age_ms += dt_ms
        self.position += self.velocity * dt_seconds
        self.velocity.y += 720.0 * dt_seconds
        self.rotation += self.angular_velocity * dt_seconds

    @property
    def done(self) -> bool:
        return self.age_ms >= self.lifetime_ms

    def draw(self, surface: pygame.Surface, assets: AssetLibrary) -> None:
        frame = assets.get_ammo_animation_frame(self.age_ms / max(1, self.lifetime_ms))
        if frame is None:
            return
        sprite = pygame.transform.rotozoom(frame, -self.rotation, 1.0)
        surface.blit(sprite, sprite.get_rect(center=(round(self.position.x), round(self.position.y))))


class Target:
    def __init__(
        self,
        depth: str,
        config: TargetConfig,
        bounds: pygame.Rect,
        playfield_width: int,
        camera_x: float,
        rng: random.Random,
        assets: AssetLibrary,
    ) -> None:
        self.depth = depth
        self.config = config
        self.assets = assets
        self.width, self.height = config.size
        self.points = config.points
        self.direction = rng.choice(config.directions)
        self.speed = rng.uniform(config.speed[0], config.speed[1])
        self.base_y = float(rng.randint(config.y_range[0], config.y_range[1]))
        self.playfield_width = playfield_width
        self.position = pygame.Vector2(
            camera_x - self.width if self.direction == "right" else camera_x + bounds.width + self.width,
            self.base_y,
        )
        self.velocity = pygame.Vector2(self.speed if self.direction == "right" else -self.speed, 0.0)
        self.gravity = 610.0
        self.dead = False
        self.state = "flying"
        self.rotation = 0.0
        self.age = 0.0
        self.bob_phase = rng.random() * math.tau
        self.wing_phase = rng.random() * math.tau
        self.bounds = bounds

    @property
    def world_center(self) -> tuple[float, float]:
        return self.position.x + self.width / 2, self.position.y + self.height / 2

    def hitbox(self, camera_x: float) -> pygame.Rect:
        screen_x = self.position.x - camera_x
        return pygame.Rect(
            int(screen_x + self.width * 0.15),
            int(self.position.y + self.height * 0.18),
            int(self.width * 0.7),
            int(self.height * 0.58),
        )

    def contains_point(self, point: tuple[int, int], camera_x: float) -> bool:
        return self.hitbox(camera_x).collidepoint(point)

    def hit(self) -> bool:
        if self.state != "flying":
            return False
        self.state = "falling"
        self.velocity.x *= 0.45
        self.velocity.y = 40.0
        return True

    def update(self, dt_seconds: float) -> None:
        self.age += dt_seconds
        self.wing_phase += dt_seconds * 10.5

        if self.state == "flying":
            self.position.x += self.velocity.x * dt_seconds
            self.position.y = self.base_y + math.sin(self.bob_phase + self.age * 3.0) * 9.0
            if self.position.x > self.playfield_width + self.width * 1.5:
                self.dead = True
            if self.position.x < -self.width * 1.5:
                self.dead = True
            return

        self.velocity.y += self.gravity * dt_seconds
        self.position += self.velocity * dt_seconds
        self.rotation = min(90.0, self.rotation + 220.0 * dt_seconds)
        if self.position.y > self.bounds.height + self.height:
            self.dead = True

    def draw(self, surface: pygame.Surface, camera_x: float) -> None:
        sprite_frame, uses_fall_frames = self.assets.get_target_frame(
            self.depth,
            self.state,
            int(self.age * 1000),
            self.direction,
        )
        if sprite_frame is not None:
            sprite = sprite_frame
            if self.state == "falling" and not uses_fall_frames:
                sprite = pygame.transform.rotate(
                    sprite,
                    -self.rotation if self.direction == "right" else self.rotation,
                )
            screen_center_x = int(self.position.x - camera_x + self.width / 2)
            rect = sprite.get_rect(center=(screen_center_x, int(self.position.y + self.height / 2)))
            surface.blit(sprite, rect)
            return

        color_style = FALLBACK_TARGET_COLORS.get(self.depth, FALLBACK_TARGET_COLORS["mid"])
        sprite = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        flap = math.sin(self.wing_phase) * self.height * 0.22 if self.state == "flying" else -self.height * 0.04

        wing_back = [
            (self.width * 0.28, self.height * 0.44),
            (self.width * 0.06, self.height * 0.18 - flap),
            (self.width * 0.2, self.height * 0.7),
        ]
        wing_front = [
            (self.width * 0.52, self.height * 0.38),
            (self.width * 0.78, self.height * 0.16 + flap * 0.6),
            (self.width * 0.7, self.height * 0.68),
        ]
        pygame.draw.polygon(sprite, color_style["wing"], wing_back)
        pygame.draw.polygon(sprite, color_style["wing"], wing_front)
        pygame.draw.ellipse(
            sprite,
            color_style["body"],
            (self.width * 0.16, self.height * 0.32, self.width * 0.58, self.height * 0.34),
        )
        pygame.draw.circle(
            sprite,
            color_style["body"],
            (int(self.width * 0.74), int(self.height * 0.36)),
            max(6, int(self.height * 0.12)),
        )
        pygame.draw.polygon(
            sprite,
            (230, 176, 42),
            [
                (self.width * 0.84, self.height * 0.38),
                (self.width * 0.98, self.height * 0.34),
                (self.width * 0.84, self.height * 0.3),
            ],
        )
        pygame.draw.circle(sprite, (15, 15, 15), (int(self.width * 0.78), int(self.height * 0.34)), 2)
        pygame.draw.polygon(
            sprite,
            color_style["wing"],
            [
                (self.width * 0.14, self.height * 0.46),
                (0, self.height * 0.38),
                (self.width * 0.1, self.height * 0.56),
            ],
        )

        if self.direction == "left":
            sprite = pygame.transform.flip(sprite, True, False)
        if self.state == "falling":
            sprite = pygame.transform.rotate(
                sprite,
                -self.rotation if self.direction == "right" else self.rotation,
            )
        surface.blit(
            sprite,
            sprite.get_rect(
                center=(int(self.position.x - camera_x + self.width / 2), int(self.position.y + self.height / 2))
            ),
        )


class ForegroundEnemy:
    def __init__(
        self,
        config: ForegroundEnemyConfig,
        bounds: pygame.Rect,
        rng: random.Random,
        assets: AssetLibrary,
        *,
        world_x: float | None = None,
        bottom_y: int | None = None,
        direction: str | None = None,
    ) -> None:
        self.config = config
        self.assets = assets
        self.bounds = bounds
        self.rng = rng
        self.width, self.height = config.size
        self.points = config.points
        self.direction = direction or rng.choice(("left", "right"))
        self.world_x = (
            world_x
            if world_x is not None
            else float(rng.randint(config.x_margin, bounds.width - config.x_margin))
        )
        self.anchor_bottom_y = (
            bottom_y
            if bottom_y is not None
            else bounds.height + config.spawn_bottom_offset_px
        )
        self.bottom_y = self.anchor_bottom_y
        self.state = "appearing"
        self.state_age_ms = 0
        self.hiding_start_frame = 0
        self.visible_time_limit_ms = rng.randint(*config.visible_time_ms)
        self.dead = False

    @property
    def hitbox(self) -> pygame.Rect:
        rect = self.current_rect(0.0)
        return pygame.Rect(
            rect.x + int(rect.width * 0.18),
            rect.y + int(rect.height * 0.1),
            int(rect.width * 0.64),
            int(rect.height * 0.72),
        )

    def current_rect(self, camera_x: float) -> pygame.Rect:
        frame = self._current_frame()
        screen_center_x = int(round(self.world_x - camera_x))
        if frame is None:
            return pygame.Rect(
                screen_center_x - self.width // 2,
                self.bottom_y - self.height,
                self.width,
                self.height,
            )
        return frame.get_rect(midbottom=(screen_center_x, self.bottom_y))

    def contains_point(self, point: tuple[int, int], camera_x: float) -> bool:
        rect = self.current_rect(camera_x)
        hitbox = pygame.Rect(
            rect.x + int(rect.width * 0.18),
            rect.y + int(rect.height * 0.1),
            int(rect.width * 0.64),
            int(rect.height * 0.72),
        )
        return hitbox.collidepoint(point)

    def hit(self) -> bool:
        if self.state in {"dying", "hiding"}:
            return False
        self.state = "dying"
        self.state_age_ms = 0
        return True

    def start_hiding(self) -> bool:
        if self.state in {"dying", "hiding"}:
            return False

        visuals = self.assets.foreground_enemy_visuals
        if visuals is None or not visuals.appear_frames:
            self.dead = True
            return False

        hide_frame_count = max(1, visuals.idle_start_frame)
        if self.state == "appearing":
            self.hiding_start_frame = min(
                hide_frame_count - 1,
                self.state_age_ms // max(1, self.config.appear_frame_duration_ms),
            )
        else:
            self.hiding_start_frame = hide_frame_count - 1

        self.state = "hiding"
        self.state_age_ms = 0
        self.bottom_y = self.anchor_bottom_y
        return True

    def update(self, dt_ms: int) -> None:
        self.state_age_ms += dt_ms

        visuals = self.assets.foreground_enemy_visuals
        if visuals is None:
            self.dead = True
            return

        if self.state == "appearing":
            self.bottom_y = self.anchor_bottom_y
            appear_frames = max(1, visuals.idle_start_frame)
            if self.state_age_ms >= appear_frames * self.config.appear_frame_duration_ms:
                self.state = "idle"
                self.state_age_ms = 0
            return

        if self.state == "idle":
            self.bottom_y = self.anchor_bottom_y
            if self.state_age_ms >= self.visible_time_limit_ms:
                self.start_hiding()
            return

        if self.state == "hiding":
            self.bottom_y = self.anchor_bottom_y
            hide_duration_ms = max(1, (self.hiding_start_frame + 1) * self.config.appear_frame_duration_ms)
            if self.state_age_ms >= hide_duration_ms:
                self.dead = True
            return

        death_frame_count = max(1, len(visuals.death_frames))
        death_duration_ms = max(1, death_frame_count * self.config.death_frame_duration_ms)
        progress = min(1.0, self.state_age_ms / death_duration_ms)
        self.bottom_y = self.anchor_bottom_y + int(self.config.death_sink_px * ease_out_cubic(progress))
        if self.state_age_ms >= death_duration_ms:
            self.dead = True

    def draw(self, surface: pygame.Surface, camera_x: float) -> None:
        frame = self._current_frame()
        if frame is None:
            return
        rect = frame.get_rect(midbottom=(int(round(self.world_x - camera_x)), self.bottom_y))
        surface.blit(frame, rect)

    def _current_frame(self) -> pygame.Surface | None:
        visuals = self.assets.foreground_enemy_visuals
        if visuals is None:
            return None

        if self.state == "dying":
            if not visuals.death_frames:
                if not visuals.appear_frames:
                    return None
                return self.assets.get_foreground_enemy_frame(
                    "appearing",
                    len(visuals.appear_frames) - 1,
                    self.direction,
                )
            frame_index = min(
                len(visuals.death_frames) - 1,
                self.state_age_ms // max(1, self.config.death_frame_duration_ms),
            )
            return self.assets.get_foreground_enemy_frame("dying", frame_index, self.direction)

        if self.state == "appearing":
            frame_index = min(
                max(0, visuals.idle_start_frame - 1),
                self.state_age_ms // max(1, self.config.appear_frame_duration_ms),
            )
            return self.assets.get_foreground_enemy_frame("appearing", frame_index, self.direction)

        if self.state == "hiding":
            step = min(
                self.hiding_start_frame,
                self.state_age_ms // max(1, self.config.appear_frame_duration_ms),
            )
            frame_index = max(0, self.hiding_start_frame - step)
            return self.assets.get_foreground_enemy_frame("appearing", frame_index, self.direction)

        idle_frames = visuals.appear_frames[visuals.idle_start_frame:] or visuals.appear_frames[-1:]
        if not idle_frames:
            return None
        idle_index = (self.state_age_ms // max(1, self.config.appear_frame_duration_ms)) % len(idle_frames)
        return self.assets.get_foreground_enemy_frame(
            "appearing",
            visuals.idle_start_frame + idle_index,
            self.direction,
        )
