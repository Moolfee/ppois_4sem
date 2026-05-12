from __future__ import annotations

import math
import random

import pygame

from ..config.game_config import GameConfig
from ..media.assets import AssetLibrary
from ..media.audio import AudioManager
from ..ui.text import render_outlined_text
from ..ui.theme import draw_accent_button
from .background import ParallaxBackground, build_scene_backdrop
from .entities import (
    DEPTH_ORDER,
    DEPTH_PRIORITY,
    Effect,
    ForegroundEnemy,
    ImpactDecal,
    RoundResult,
    SpentAmmoAnimation,
    Target,
    rounded_accuracy_percent,
)
from .events import (
    EVENT_TO_DEPTH,
    FOREGROUND_ENEMY_EVENT,
    RELOAD_COMPLETE_EVENT,
    SPAWN_EVENTS,
)


class GameWorld:
    def __init__(
        self,
        config: GameConfig,
        audio: AudioManager,
        fonts: dict[str, pygame.font.Font],
        assets: AssetLibrary,
    ) -> None:
        self.config = config
        self.audio = audio
        self.fonts = fonts
        self.assets = assets
        self.random = random.Random()
        self.bounds = pygame.Rect(0, 0, config.window.width, config.window.height)
        self.playfield_width = max(
            self.bounds.width,
            int(round(self.bounds.width * config.gameplay.playfield_width_factor)),
        )
        self.max_camera_x = max(0.0, float(self.playfield_width - self.bounds.width))
        self.camera_x = self.max_camera_x / 2
        self.parallax_background = ParallaxBackground(config, assets)
        self.backdrop = self._build_backdrop()
        self.targets: list[Target] = []
        self.foreground_enemy: ForegroundEnemy | None = None
        self.effects: list[Effect] = []
        self.decals: list[ImpactDecal] = []
        self.spent_ammo_animations: list[SpentAmmoAnimation] = []
        self.result: RoundResult | None = None
        self.pause_hover_action: str | None = None
        self._reset_round_state()

    def _build_backdrop(self) -> pygame.Surface:
        return build_scene_backdrop(
            (self.bounds.width, self.bounds.height),
            has_parallax_sheet=self.config.parallax_sheet is not None,
        )

    def _reset_round_state(self) -> None:
        self.targets.clear()
        self.foreground_enemy = None
        self.effects.clear()
        self.decals.clear()
        self.spent_ammo_animations.clear()
        self.crosshair = (self.bounds.width // 2, self.bounds.height // 2)
        self.paused = False
        self.round_closing = False
        self.finished = False
        self.result = None
        self.reloading = False
        self.reload_started_at = 0
        self.reload_remaining_ms = self.config.weapon.reload_time_ms
        self.reload_progress_ms = 0
        self.reload_start_ammo = self.config.weapon.magazine_size
        self.score = 0
        self.hits = 0
        self.misses = 0
        self.shots = 0
        self.ammo = self.config.weapon.magazine_size
        self.remaining_ms = self.config.gameplay.round_time_seconds * 1000
        self.last_shot_at = -self.config.weapon.shot_cooldown_ms
        self.pause_hover_action = None
        self.camera_x = self.max_camera_x / 2

    def start_round(self) -> None:
        self._reset_round_state()
        self.parallax_background.reset_view()
        self._cancel_timers()
        self._schedule_all_spawns()

    def stop_round(self) -> None:
        self._cancel_timers()
        self.reloading = False
        self.reload_progress_ms = 0
        self.reload_start_ammo = self.config.weapon.magazine_size
        self.paused = False
        self.round_closing = False
        self.pause_hover_action = None

    def _schedule_all_spawns(self) -> None:
        for depth in DEPTH_ORDER:
            self._schedule_spawn(depth)
        self._schedule_foreground_enemy_spawn()

    def _schedule_spawn(self, depth: str) -> None:
        interval = self.random.randint(*self.config.targets[depth].spawn_interval_ms)
        pygame.time.set_timer(SPAWN_EVENTS[depth], interval, loops=1)

    def _schedule_foreground_enemy_spawn(self) -> None:
        enemy_config = self.config.foreground_enemy
        if enemy_config is None or not enemy_config.enabled:
            return
        interval = self.random.randint(*enemy_config.spawn_interval_ms)
        pygame.time.set_timer(FOREGROUND_ENEMY_EVENT, interval, loops=1)

    def _build_impact_decal(self, position: tuple[int, int]) -> ImpactDecal:
        lifetime_ms = self.random.randint(*self.config.effects.bullet_hole_lifetime_ms)
        layer_hit = self.parallax_background.topmost_layer_hit(position, self.bounds.width)
        if layer_hit is not None:
            layer_name, layer_local_x = layer_hit
            return ImpactDecal(
                screen_y=position[1],
                lifetime_ms=lifetime_ms,
                layer_name=layer_name,
                layer_local_x=layer_local_x,
            )
        return ImpactDecal(
            screen_y=position[1],
            lifetime_ms=lifetime_ms,
            world_x=self.camera_x + position[0],
        )

    def _build_foreground_enemy_spawn(self) -> tuple[float, int, str]:
        enemy_config = self.config.foreground_enemy
        if enemy_config is None:
            return float(self.camera_x + self.bounds.centerx), self.bounds.height, "right"

        bottom_spawn_y = self.bounds.height + enemy_config.spawn_bottom_offset_px
        left_world_x = float(enemy_config.x_margin)
        right_world_x = float(self.playfield_width - enemy_config.x_margin)
        world_x = float(self.random.randint(int(left_world_x), int(right_world_x)))
        direction = self.random.choice(("left", "right"))
        return world_x, bottom_spawn_y, direction

    def _cancel_timers(self) -> None:
        for event_type in SPAWN_EVENTS.values():
            pygame.time.set_timer(event_type, 0)
        pygame.time.set_timer(RELOAD_COMPLETE_EVENT, 0)
        pygame.time.set_timer(FOREGROUND_ENEMY_EVENT, 0)

    def _camera_pan_margin(self) -> int:
        return max(1, min(self.bounds.width // 2 - 1, self.config.gameplay.camera_pan_margin_px))

    def _update_camera(self, dt_ms: int) -> float:
        if self.max_camera_x <= 0:
            return 0.0

        margin = self._camera_pan_margin()
        left_zone_end = margin
        right_zone_start = self.bounds.width - margin
        velocity_px_per_sec = 0.0

        if self.crosshair[0] < left_zone_end:
            intensity = (left_zone_end - self.crosshair[0]) / max(1, left_zone_end)
            velocity_px_per_sec = -self.config.gameplay.camera_pan_speed_px_per_sec * intensity
        elif self.crosshair[0] > right_zone_start:
            intensity = (self.crosshair[0] - right_zone_start) / max(1, margin)
            velocity_px_per_sec = self.config.gameplay.camera_pan_speed_px_per_sec * intensity

        previous_camera_x = self.camera_x
        self.camera_x = max(
            0.0,
            min(self.max_camera_x, self.camera_x + velocity_px_per_sec * (dt_ms / 1000)),
        )
        return self.camera_x - previous_camera_x

    def toggle_pause(self) -> None:
        if self.finished or self.round_closing:
            return
        if self.paused:
            self.paused = False
            self.pause_hover_action = None
            self._schedule_all_spawns()
            if self.reloading:
                self.reload_started_at = pygame.time.get_ticks()
                pygame.time.set_timer(RELOAD_COMPLETE_EVENT, self.reload_remaining_ms, loops=1)
            return

        self.paused = True
        self.pause_hover_action = None
        self._cancel_timers()
        if self.reloading:
            elapsed = pygame.time.get_ticks() - self.reload_started_at
            self.reload_progress_ms = min(
                self.config.weapon.reload_time_ms,
                self.reload_progress_ms + max(0, elapsed),
            )
            self.reload_remaining_ms = max(1, self.config.weapon.reload_time_ms - self.reload_progress_ms)

    @staticmethod
    def _advance_timed_objects(items, dt_ms: int):
        for item in items:
            item.update(dt_ms)
        return [item for item in items if not item.done]

    def _spawn_target(self, depth: str) -> None:
        self.targets.append(
            Target(
                depth,
                self.config.targets[depth],
                self.bounds,
                self.playfield_width,
                self.camera_x,
                self.random,
                self.assets,
            )
        )

    def _spawn_foreground_enemy(self) -> None:
        if (
            self.config.foreground_enemy is None
            or not self.config.foreground_enemy.enabled
            or self.assets.foreground_enemy_visuals is None
        ):
            return
        world_x, bottom_y, direction = self._build_foreground_enemy_spawn()
        self.foreground_enemy = ForegroundEnemy(
            self.config.foreground_enemy,
            self.bounds,
            self.random,
            self.assets,
            world_x=world_x,
            bottom_y=bottom_y,
            direction=direction,
        )

    def _finish_reload(self) -> None:
        self.reloading = False
        self.reload_remaining_ms = self.config.weapon.reload_time_ms
        self.reload_progress_ms = 0
        self.ammo = self.config.weapon.magazine_size
        self.reload_start_ammo = self.config.weapon.magazine_size

    def _sorted_targets(self, *, reverse: bool) -> list[Target]:
        return sorted(self.targets, key=lambda item: DEPTH_PRIORITY[item.depth], reverse=reverse)

    def _spawn_shot_effect(self, position: tuple[int, int]) -> None:
        self.effects.append(
            Effect(
                position=position,
                color=self.config.effects.shot_flash_color,
                base_radius=self.config.effects.shot_flash_base_radius,
                max_radius=self.config.effects.shot_flash_max_radius,
                lifetime_ms=self.config.gameplay.shot_flash_ms,
            )
        )

    def _record_hit(self, position: tuple[int, int], points: int) -> None:
        self.score += points
        self.hits += 1
        self.audio.play_hit()
        self.effects.append(
            Effect(
                position=position,
                color=self.config.effects.hit_popup_color,
                base_radius=self.config.effects.hit_popup_base_radius,
                max_radius=self.config.effects.hit_popup_max_radius,
                lifetime_ms=self.config.gameplay.hit_effect_ms,
                label=f"+{points}",
                show_marker=False,
            )
        )

    def _record_miss(self, position: tuple[int, int]) -> None:
        self.decals.append(self._build_impact_decal(position))
        self.misses += 1
        self.audio.play_miss()

    def _try_hit_foreground_enemy(self, position: tuple[int, int]) -> bool:
        enemy = self.foreground_enemy
        if enemy is None or not enemy.contains_point(position, self.camera_x) or not enemy.hit():
            return False
        self._record_hit(position, enemy.points)
        return True

    def _try_hit_target(self, position: tuple[int, int]) -> bool:
        for target in self._sorted_targets(reverse=True):
            if not target.contains_point(position, self.camera_x) or not target.hit():
                continue
            self._record_hit(position, target.points)
            return True
        return False

    def _update_foreground_enemy(self, dt_ms: int) -> None:
        if self.foreground_enemy is None:
            return
        self.foreground_enemy.update(dt_ms)
        if self.foreground_enemy.dead:
            self.foreground_enemy = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.crosshair = event.pos

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.toggle_pause()
            return
        if self.finished or self.paused or self.round_closing:
            return

        if event.type in EVENT_TO_DEPTH:
            depth = EVENT_TO_DEPTH[event.type]
            self._spawn_target(depth)
            self._schedule_spawn(depth)
            return
        if event.type == FOREGROUND_ENEMY_EVENT:
            self._spawn_foreground_enemy()
            self._schedule_foreground_enemy_spawn()
            return
        if event.type == RELOAD_COMPLETE_EVENT:
            self._finish_reload()
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.fire(event.pos)
            elif event.button == 3:
                self.start_reload()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self.start_reload()

    def fire(self, position: tuple[int, int]) -> None:
        now = pygame.time.get_ticks()
        if self.reloading:
            return
        if now - self.last_shot_at < self.config.weapon.shot_cooldown_ms:
            return
        if self.ammo <= 0:
            self.start_reload()
            return

        self.last_shot_at = now
        self.ammo -= 1
        self.shots += 1
        self._spawn_spent_ammo()
        self._spawn_shot_effect(position)
        self.audio.play_shot()

        if self.parallax_background.layer_is_opaque_at_screen_point("front_trunks", position, self.bounds.width):
            self._record_miss(position)
            return
        if self._try_hit_foreground_enemy(position):
            return
        if self._try_hit_target(position):
            return
        self._record_miss(position)

    def start_reload(self) -> None:
        if self.round_closing or self.reloading or self.ammo == self.config.weapon.magazine_size:
            return
        self.reloading = True
        self.reload_start_ammo = self.ammo
        self.reload_started_at = pygame.time.get_ticks()
        self.reload_remaining_ms = self.config.weapon.reload_time_ms
        self.reload_progress_ms = 0
        pygame.time.set_timer(RELOAD_COMPLETE_EVENT, self.config.weapon.reload_time_ms, loops=1)
        self.audio.play_reload()

    def update(self, dt_ms: int) -> None:
        if self.finished:
            return

        self.effects = self._advance_timed_objects(self.effects, dt_ms)
        self.decals = self._advance_timed_objects(self.decals, dt_ms)
        self.spent_ammo_animations = self._advance_timed_objects(self.spent_ammo_animations, dt_ms)

        if self.paused:
            return
        if self.round_closing:
            self._update_foreground_enemy(dt_ms)
            if self.foreground_enemy is None:
                self.finish_round()
            return

        self.remaining_ms -= dt_ms
        if self.remaining_ms <= 0:
            self._begin_round_finish()
            if self.finished or self.round_closing:
                if self.round_closing:
                    self._update_foreground_enemy(dt_ms)
                    if self.foreground_enemy is None:
                        self.finish_round()
                return

        camera_shift_px = self._update_camera(dt_ms)
        world_shift_px = self.config.gameplay.base_scroll_speed * dt_ms / 1000 + camera_shift_px
        self.parallax_background.update(dt_ms, world_shift_px, self.bounds.width // 2, self.bounds.width)

        dt_seconds = dt_ms / 1000
        for target in self.targets:
            target.update(dt_seconds)
        self.targets = [target for target in self.targets if not target.dead]
        self._update_foreground_enemy(dt_ms)

    def finish_round(self) -> None:
        self.finished = True
        self.round_closing = False
        self._cancel_timers()
        self.result = RoundResult(
            score=self.score,
            hits=self.hits,
            misses=self.misses,
            shots=self.shots,
        )

    def _begin_round_finish(self) -> None:
        if self.finished or self.round_closing:
            return

        self.remaining_ms = 0
        self.round_closing = True
        self.reloading = False
        self.reload_progress_ms = 0
        self.reload_remaining_ms = self.config.weapon.reload_time_ms
        self._cancel_timers()
        if self.foreground_enemy is not None and self.foreground_enemy.start_hiding():
            return
        self.finish_round()

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.backdrop, (0, 0))
        self.parallax_background.draw_background_layers(surface, reserve_front_layers=1)

        for target in self._sorted_targets(reverse=False):
            target.draw(surface, self.camera_x)
        if self.foreground_enemy is not None:
            self.foreground_enemy.draw(surface, self.camera_x)

        self.parallax_background.draw_foreground_layers(surface, count=1)
        for decal in self.decals:
            decal.draw(
                surface,
                self.assets.bullet_hole_image,
                self.camera_x,
                self.parallax_background,
                self.config.effects.bullet_hole_scale_by_layer,
            )
        for animation in self.spent_ammo_animations:
            animation.draw(surface, self.assets)
        for effect in self.effects:
            effect.draw(surface, self.fonts["small"])

        self._draw_hud(surface)
        self._draw_crosshair(surface)
        if self.paused:
            self._draw_pause_overlay(surface)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        time_left = max(0, math.ceil(self.remaining_ms / 1000))
        accuracy = rounded_accuracy_percent(self.hits, self.shots)

        hud_lines = [
            f"Очки: {self.score}",
            f"Попадания: {self.hits}",
            f"Промахи: {self.misses}",
            f"Точность: {accuracy}%",
        ]
        y_position = self.config.ui.hud_top_margin_px
        for line in hud_lines:
            text = render_outlined_text(self.fonts["body"], line)
            surface.blit(text, (self.config.ui.hud_left_margin_px, y_position))
            y_position += self.config.ui.hud_line_gap_px

        timer = render_outlined_text(self.fonts["title"], f"{time_left:02d}", outline_width=1)
        timer_rect = timer.get_rect(
            center=(
                surface.get_width() - self.config.ui.hud_timer_right_margin_px,
                self.config.ui.hud_timer_top_margin_px,
            )
        )
        surface.blit(timer, timer_rect)

        self._draw_loaded_ammo(surface)
        if self.reloading:
            self._draw_reload_ammo(surface)

    def _draw_crosshair(self, surface: pygame.Surface) -> None:
        now = pygame.time.get_ticks()
        state = "reload" if self.reloading or self.ammo <= 0 else "idle"
        if self.last_shot_at >= 0 and now - self.last_shot_at <= 130:
            state = "shot"

        sprite = self.assets.get_crosshair_frame(state)
        if sprite is not None:
            surface.blit(sprite, sprite.get_rect(center=self.crosshair))
            return

        radius = self.config.gameplay.crosshair_radius
        x_position, y_position = self.crosshair
        color = self.config.ui.crosshair_fallback_color
        pygame.draw.circle(surface, color, self.crosshair, radius, width=2)
        pygame.draw.line(
            surface,
            color,
            (x_position - radius - 8, y_position),
            (x_position + radius + 8, y_position),
            2,
        )
        pygame.draw.line(
            surface,
            color,
            (x_position, y_position - radius - 8),
            (x_position, y_position + radius + 8),
            2,
        )

    def _spawn_spent_ammo(self) -> None:
        ammo_frame = self.assets.get_ammo_idle_frame()
        if ammo_frame is None:
            return
        start_x, start_y = self._ammo_slot_center(ammo_frame, self._spent_ammo_slot_index())
        self.spent_ammo_animations.append(
            SpentAmmoAnimation(
                position=pygame.Vector2(start_x, start_y),
                velocity=pygame.Vector2(*self.config.effects.spent_ammo_velocity),
                lifetime_ms=self.config.effects.spent_ammo_lifetime_ms,
                rotation=self.config.effects.spent_ammo_rotation_deg,
                angular_velocity=self.config.effects.spent_ammo_angular_velocity_deg,
            )
        )

    def _draw_loaded_ammo(self, surface: pygame.Surface) -> None:
        ammo_frame = self.assets.get_ammo_idle_frame()
        displayed_ammo = self._displayed_ammo_count()
        if ammo_frame is None:
            ammo_text = render_outlined_text(
                self.fonts["small"],
                f"Патроны: {displayed_ammo}/{self.config.weapon.magazine_size}",
            )
            rect = ammo_text.get_rect(
                bottomright=(
                    surface.get_width() - self.config.ui.ammo_right_margin_px,
                    surface.get_height() - self.config.ui.ammo_bottom_margin_px,
                )
            )
            surface.blit(ammo_text, rect)
            return

        start_slot = self.config.weapon.magazine_size - displayed_ammo
        for slot_index in range(start_slot, self.config.weapon.magazine_size):
            x_position, base_y = self._ammo_slot_center(ammo_frame, slot_index)
            surface.blit(ammo_frame, ammo_frame.get_rect(center=(x_position, base_y)))

    def _draw_reload_ammo(self, surface: pygame.Surface) -> None:
        ammo_frame = self.assets.get_ammo_idle_frame()
        if ammo_frame is None or not self.reloading:
            return

        visible_shells = self._reload_shells_visible()
        _, base_y = self._ammo_slot_center(ammo_frame, 0)
        label = render_outlined_text(self.fonts["small"], "Перезарядка")
        label_rect = label.get_rect(
            bottomright=(
                surface.get_width() - self.config.ui.ammo_right_margin_px,
                base_y - ammo_frame.get_height() // 2 - self.config.ui.reload_label_gap_px,
            )
        )
        surface.blit(label, label_rect)
        for added_index in range(visible_shells):
            slot_index = self._reload_slot_index_for_added_shell(added_index)
            x_position, _ = self._ammo_slot_center(ammo_frame, slot_index)
            pop_scale = self._reload_shell_pop_scale(added_index)
            sprite = ammo_frame if pop_scale == 1.0 else pygame.transform.rotozoom(ammo_frame, 0.0, pop_scale)
            surface.blit(sprite, sprite.get_rect(center=(x_position, base_y)))

    def _ammo_slot_center(self, ammo_frame: pygame.Surface, slot_index: int) -> tuple[int, int]:
        spacing = max(20, int(ammo_frame.get_width() * self.config.ui.ammo_spacing_factor))
        base_y = self.bounds.height - ammo_frame.get_height() // 2 - self.config.ui.ammo_bottom_margin_px
        group_width = max(0, (self.config.weapon.magazine_size - 1) * spacing)
        leftmost_x = self.bounds.width - self.config.ui.ammo_right_margin_px - group_width
        return leftmost_x + slot_index * spacing, base_y

    def _reload_shells_visible(self) -> int:
        if not self.reloading:
            return 0
        missing_shells = max(0, self.config.weapon.magazine_size - self.reload_start_ammo)
        if missing_shells <= 0:
            return 0
        elapsed = self._current_reload_elapsed_ms()
        total = max(1, self.config.weapon.reload_time_ms)
        visible = 0
        for index in range(missing_shells):
            if elapsed >= total * (index + 1) / (missing_shells + 1):
                visible += 1
        return min(missing_shells, visible)

    def _reload_shell_pop_scale(self, added_shell_index: int) -> float:
        missing_shells = max(0, self.config.weapon.magazine_size - self.reload_start_ammo)
        if missing_shells <= 0:
            return 1.0
        elapsed = self._current_reload_elapsed_ms()
        total = max(1, self.config.weapon.reload_time_ms)
        threshold = total * (added_shell_index + 1) / (missing_shells + 1)
        if elapsed <= threshold:
            return 1.0
        progress = min(1.0, (elapsed - threshold) / 140)
        return 0.82 + progress * 0.18

    def _displayed_ammo_count(self) -> int:
        if not self.reloading:
            return self.ammo
        return min(
            self.config.weapon.magazine_size,
            self.reload_start_ammo + self._reload_shells_visible(),
        )

    def _current_reload_elapsed_ms(self) -> int:
        if not self.reloading:
            return 0
        if self.paused:
            return self.reload_progress_ms
        elapsed = max(0, pygame.time.get_ticks() - self.reload_started_at)
        return min(self.config.weapon.reload_time_ms, self.reload_progress_ms + elapsed)

    def _reload_slot_index_for_added_shell(self, added_shell_index: int) -> int:
        total_slots = self.config.weapon.magazine_size
        return max(0, min(total_slots - 1, total_slots - self.reload_start_ammo - added_shell_index - 1))

    def _spent_ammo_slot_index(self) -> int:
        spent_count = self.config.weapon.magazine_size - self.ammo
        return max(0, min(self.config.weapon.magazine_size - 1, spent_count - 1))

    def _pause_menu_top_y(self) -> int:
        title_height = self.fonts["title"].get_height()
        button_stack_height = self.config.ui.pause_button_height * 2 + self.config.ui.pause_button_gap_px
        total_height = title_height + 28 + button_stack_height
        return max(24, (self.bounds.height - total_height) // 2 - 42)

    def pause_button_rects(self) -> dict[str, pygame.Rect]:
        center_x = self.bounds.width // 2
        top_y = self._pause_menu_top_y() + self.fonts["title"].get_height() + 28
        return {
            "resume": pygame.Rect(
                center_x - self.config.ui.pause_button_width // 2,
                top_y,
                self.config.ui.pause_button_width,
                self.config.ui.pause_button_height,
            ),
            "menu": pygame.Rect(
                center_x - self.config.ui.pause_button_width // 2,
                top_y + self.config.ui.pause_button_height + self.config.ui.pause_button_gap_px,
                self.config.ui.pause_button_width,
                self.config.ui.pause_button_height,
            ),
        }

    def set_pause_hover(self, position: tuple[int, int]) -> None:
        self.pause_hover_action = None
        for action, rect in self.pause_button_rects().items():
            if rect.collidepoint(position):
                self.pause_hover_action = action
                return

    def get_pause_action(self, position: tuple[int, int]) -> str | None:
        for action, rect in self.pause_button_rects().items():
            if rect.collidepoint(position):
                return action
        return None

    def _draw_pause_overlay(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((*self.config.ui.pause_overlay_color, self.config.ui.pause_overlay_alpha))
        surface.blit(overlay, (0, 0))

        title = render_outlined_text(self.fonts["title"], "ПАУЗА", outline_width=1)
        title_center_y = self._pause_menu_top_y() + title.get_height() // 2
        surface.blit(title, title.get_rect(center=(surface.get_width() // 2, title_center_y)))

        labels = {
            "resume": "Вернуться в игру",
            "menu": "В меню",
        }
        for action, rect in self.pause_button_rects().items():
            draw_accent_button(surface, rect, self.config.ui, hovered=self.pause_hover_action == action)
            text = render_outlined_text(self.fonts["heading"], labels[action])
            surface.blit(text, text.get_rect(center=rect.center))


__all__ = ["GameWorld", "RoundResult"]
