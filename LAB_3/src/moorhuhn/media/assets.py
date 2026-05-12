from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pygame

from ..config.game_config import GameConfig, LayerConfig


@dataclass(frozen=True, slots=True)
class TargetVisualSet:
    fly_frames: tuple[pygame.Surface, ...]
    fall_frames: tuple[pygame.Surface, ...]
    frame_duration_ms: int
    native_direction: str = "right"

    @property
    def has_any(self) -> bool:
        return bool(self.fly_frames or self.fall_frames)


@dataclass(frozen=True, slots=True)
class ForegroundEnemyVisualSet:
    appear_frames: tuple[pygame.Surface, ...]
    death_frames: tuple[pygame.Surface, ...]
    idle_start_frame: int
    native_direction: str = "left"

    @property
    def has_any(self) -> bool:
        return bool(self.appear_frames or self.death_frames)


class AssetLibrary:
    def __init__(self, project_root: Path, config: GameConfig) -> None:
        self.project_root = project_root
        self.root = project_root / "assets"
        self.background_tiles: dict[str, pygame.Surface] = {}
        self.target_visuals: dict[str, TargetVisualSet] = {}
        self.foreground_enemy_visuals: ForegroundEnemyVisualSet | None = None
        self.crosshair_frames: tuple[pygame.Surface, ...] = ()
        self.ammo_frames: tuple[pygame.Surface, ...] = ()
        self.bullet_hole_image: pygame.Surface | None = None

        self.manifest = self._load_asset_manifest(project_root)

        self._load_backgrounds(config)
        self._load_targets(config)
        self._load_special_targets(config)
        self._load_ui_assets()

    def _load_asset_manifest(self, project_root: Path) -> dict[str, Any]:
        manifest_path = project_root / "config" / "assets_manifest.json"
        if not manifest_path.exists():
            return {}
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _load_backgrounds(self, config: GameConfig) -> None:
        if config.parallax_sheet is not None and self._load_backgrounds_from_sheet(config):
            return

        for layer in config.layers:
            path = self.root / "background" / f"{layer.name}.png"
            image = self._load_optional_image(path)
            if image is None:
                continue
            self.background_tiles[layer.name] = pygame.transform.scale(
                image,
                (layer.tile_width, layer.height),
            )

    def _load_backgrounds_from_sheet(self, config: GameConfig) -> bool:
        sheet_config = config.parallax_sheet
        if sheet_config is None:
            return False

        sheet = self._load_raw_surface(sheet_config.file_path)
        if sheet is None:
            return False

        loaded_any = False
        for layer in config.layers:
            if layer.source_rect is None:
                continue

            self.background_tiles[layer.name] = self._build_background_layer_from_sheet(
                sheet,
                layer,
                config,
            )
            loaded_any = True

        return loaded_any

    def _build_background_layer_from_sheet(
        self,
        sheet: pygame.Surface,
        layer: LayerConfig,
        config: GameConfig,
    ) -> pygame.Surface:
        sheet_config = config.parallax_sheet
        if sheet_config is None or layer.source_rect is None:
            raise ValueError("sheet-backed background layer requires parallax sheet and source rectangle")

        layer_surface = self._extract_surface(sheet, pygame.Rect(layer.source_rect))
        layer_surface = self._apply_color_key(layer_surface, sheet_config.transparent_color)
        layer_surface = self._clear_border_connected_background(layer_surface, self._is_near_magenta)
        layer_surface = self._clear_pixels_by_predicate(layer_surface, self._is_near_magenta)
        layer_surface = self._clear_border_connected_background(layer_surface, self._is_near_white)
        if layer.name != "sky":
            layer_surface = self._clear_top_background_runs(
                layer_surface,
                sheet_config.clear_top_runs_min_width,
            )
        if layer.clear_top_rows > 0:
            layer_surface = self._clear_top_rows(layer_surface, layer.clear_top_rows)
        if layer.clear_rects:
            layer_surface = self._clear_rects(layer_surface, layer.clear_rects)
        layer_surface = self._trim_bottom_transparent_rows(layer_surface)
        layer_surface = self._bleed_top_transparent_rgb(layer_surface)
        layer_surface = self._scale_background_layer(layer_surface, layer, config)
        return self._strip_chroma_halo(layer_surface, self._is_chroma_halo)

    def _load_targets(self, config: GameConfig) -> None:
        if self._load_targets_from_manifest(config):
            return

        frame_durations = {
            "near": 85,
            "mid": 100,
            "far": 120,
        }
        for depth, target_config in config.targets.items():
            fly_frames = self._load_frames_from_strip(
                self.root / "targets" / f"chicken_{depth}_fly_sheet.png",
                frame_size=target_config.size,
            )
            fall_frames = self._load_frames_from_strip(
                self.root / "targets" / f"chicken_{depth}_fall_sheet.png",
                frame_size=target_config.size,
            )
            self.target_visuals[depth] = TargetVisualSet(
                fly_frames=fly_frames,
                fall_frames=fall_frames,
                frame_duration_ms=frame_durations.get(depth, 100),
            )

    def _load_special_targets(self, config: GameConfig) -> None:
        if config.foreground_enemy is None or not config.foreground_enemy.enabled:
            return

        special_targets = self.manifest.get("special_targets")
        if not isinstance(special_targets, dict):
            return

        foreground_enemy = special_targets.get("foreground_enemy")
        if not isinstance(foreground_enemy, dict):
            foreground_enemy = special_targets.get("foreground_huhn")
        if not isinstance(foreground_enemy, dict):
            return

        appear_manifest = foreground_enemy.get("appear")
        death_manifest = foreground_enemy.get("death")
        if not isinstance(appear_manifest, dict) or not isinstance(death_manifest, dict):
            return

        appear_frames = self._load_frames_from_strip_manifest(
            appear_manifest,
            scaled_size=config.foreground_enemy.size,
        )
        death_frames = self._load_frames_from_strip_manifest(
            death_manifest,
            scaled_size=config.foreground_enemy.size,
        )
        if not appear_frames and not death_frames:
            return

        self.foreground_enemy_visuals = ForegroundEnemyVisualSet(
            appear_frames=appear_frames,
            death_frames=death_frames,
            idle_start_frame=max(0, int(foreground_enemy.get("idle_start_frame", 0))),
            native_direction=str(foreground_enemy.get("native_direction", "left")).lower(),
        )

    def _load_targets_from_manifest(self, config: GameConfig) -> bool:
        targets_manifest = self.manifest.get("targets")
        if not isinstance(targets_manifest, dict):
            return False

        sheet_manifest = targets_manifest.get("sheet")
        depths_manifest = targets_manifest.get("depths")
        if not isinstance(sheet_manifest, dict) or not isinstance(depths_manifest, dict):
            return False

        path_value = sheet_manifest.get("file")
        if not isinstance(path_value, str):
            return False

        background_mode = str(sheet_manifest.get("background_mode", "white"))
        default_native_direction = str(sheet_manifest.get("native_direction", "right")).lower()
        sheet_path = self.root.parent / path_value
        loaded_any = False

        for depth, target_config in config.targets.items():
            depth_manifest = depths_manifest.get(depth)
            if not isinstance(depth_manifest, dict):
                continue

            fly_manifest = depth_manifest.get("fly")
            fall_manifest = depth_manifest.get("fall")
            if not isinstance(fly_manifest, dict) or not isinstance(fall_manifest, dict):
                continue

            fly_frames = self._load_frames_from_manifest_region(
                sheet_path,
                background_mode=background_mode,
                region_spec=fly_manifest,
                scaled_size=target_config.size,
            )
            fall_frames = self._load_frames_from_manifest_region(
                sheet_path,
                background_mode=background_mode,
                region_spec=fall_manifest,
                scaled_size=target_config.size,
            )

            if not fly_frames and not fall_frames:
                continue

            self.target_visuals[depth] = TargetVisualSet(
                fly_frames=fly_frames,
                fall_frames=fall_frames,
                frame_duration_ms=int(depth_manifest.get("frame_duration_ms", 100)),
                native_direction=str(depth_manifest.get("native_direction", default_native_direction)).lower(),
            )
            loaded_any = True

        return loaded_any

    def _load_ui_assets(self) -> None:
        ui_manifest = self.manifest.get("ui")
        if not isinstance(ui_manifest, dict):
            return

        crosshair_manifest = ui_manifest.get("crosshair")
        if isinstance(crosshair_manifest, dict):
            self.crosshair_frames = self._load_frames_from_strip_manifest(crosshair_manifest)

        ammo_manifest = ui_manifest.get("ammo")
        if isinstance(ammo_manifest, dict):
            self.ammo_frames = self._load_frames_from_strip_manifest(ammo_manifest)

        bullet_hole_manifest = ui_manifest.get("bullet_hole")
        if isinstance(bullet_hole_manifest, dict):
            self.bullet_hole_image = self._load_image_from_manifest(bullet_hole_manifest)

    def get_background_tile(self, name: str) -> pygame.Surface | None:
        return self.background_tiles.get(name)

    def get_target_frame(
        self,
        depth: str,
        state: str,
        age_ms: int,
        direction: str,
    ) -> tuple[pygame.Surface | None, bool]:
        visuals = self.target_visuals.get(depth)
        if visuals is None or not visuals.has_any:
            return None, False

        use_fall_frames = state == "falling" and bool(visuals.fall_frames)
        frames = visuals.fall_frames if use_fall_frames else visuals.fly_frames
        if not frames:
            frames = visuals.fall_frames
        if not frames:
            return None, False

        index = (age_ms // visuals.frame_duration_ms) % len(frames)
        frame = frames[index]
        if direction.lower() != visuals.native_direction:
            frame = pygame.transform.flip(frame, True, False)
        return frame, use_fall_frames

    def get_foreground_enemy_frame(
        self,
        state: str,
        age_ms: int,
        direction: str,
    ) -> pygame.Surface | None:
        visuals = self.foreground_enemy_visuals
        if visuals is None or not visuals.has_any:
            return None

        if state == "dying" and visuals.death_frames:
            index = min(len(visuals.death_frames) - 1, age_ms)
            frame = visuals.death_frames[index]
        else:
            frames = visuals.appear_frames
            if not frames:
                return None
            frame = frames[min(len(frames) - 1, age_ms)]

        if direction.lower() != visuals.native_direction:
            frame = pygame.transform.flip(frame, True, False)
        return frame

    def get_crosshair_frame(self, state: str) -> pygame.Surface | None:
        if not self.crosshair_frames:
            return None
        state_to_index = {
            "idle": 0,
            "shot": 1 if len(self.crosshair_frames) > 1 else 0,
            "reload": 2 if len(self.crosshair_frames) > 2 else 0,
        }
        return self.crosshair_frames[state_to_index.get(state, 0)]

    def get_ammo_idle_frame(self) -> pygame.Surface | None:
        if not self.ammo_frames:
            return None
        return self.ammo_frames[0]

    def get_ammo_animation_frame(self, progress: float) -> pygame.Surface | None:
        if not self.ammo_frames:
            return None
        clamped = max(0.0, min(1.0, progress))
        index = min(len(self.ammo_frames) - 1, int(clamped * (len(self.ammo_frames) - 1)))
        return self.ammo_frames[index]

    def _load_frames_from_strip_manifest(
        self,
        manifest: dict[str, Any],
        *,
        scaled_size: tuple[int, int] | None = None,
    ) -> tuple[pygame.Surface, ...]:
        path_value = manifest.get("file")
        if not isinstance(path_value, str):
            return ()

        frame_size = manifest.get("frame_size")
        if not (
            isinstance(frame_size, list)
            and len(frame_size) == 2
            and all(isinstance(item, int) and item > 0 for item in frame_size)
        ):
            return ()

        background_mode = str(manifest.get("background_mode", "alpha"))
        direction = str(manifest.get("direction", "horizontal"))
        frame_layout = str(manifest.get("frame_layout", "content")).lower()
        scale = float(manifest.get("scale", 1.0))
        target_size = scaled_size or (
            max(1, int(frame_size[0] * scale)),
            max(1, int(frame_size[1] * scale)),
        )

        return self._load_frames_from_strip(
            self.root.parent / path_value,
            frame_size=(frame_size[0], frame_size[1]),
            background_mode=background_mode,
            direction=direction,
            scaled_size=target_size,
            frame_layout=frame_layout,
        )

    def _load_image_from_manifest(self, manifest: dict[str, Any]) -> pygame.Surface | None:
        path_value = manifest.get("file")
        if not isinstance(path_value, str):
            return None

        background_mode = str(manifest.get("background_mode", "alpha"))
        scale = float(manifest.get("scale", 1.0))
        raw_surface = self._load_surface_for_mode(self.root.parent / path_value, background_mode)
        if raw_surface is None:
            return None

        surface = self._apply_background_mode(raw_surface, background_mode)
        surface = self._trim_surface(surface)
        if scale != 1.0:
            surface = pygame.transform.smoothscale(
                surface,
                (
                    max(1, int(surface.get_width() * scale)),
                    max(1, int(surface.get_height() * scale)),
                ),
            )
        return surface

    def _load_frames_from_manifest_region(
        self,
        sheet_path: Path,
        *,
        background_mode: str,
        region_spec: dict[str, Any],
        scaled_size: tuple[int, int],
    ) -> tuple[pygame.Surface, ...]:
        rect_value = region_spec.get("rect")
        frame_count = region_spec.get("frames")
        if not (
            isinstance(rect_value, list)
            and len(rect_value) == 4
            and all(isinstance(item, int) for item in rect_value)
            and isinstance(frame_count, int)
            and frame_count > 0
        ):
            return ()

        raw_sheet = self._load_surface_for_mode(sheet_path, background_mode)
        if raw_sheet is None:
            return ()

        region = self._extract_surface(raw_sheet, pygame.Rect(rect_value))
        frame_layout = str(region_spec.get("frame_layout", "content")).lower()
        frame_height = max(1, region.get_height() // frame_count)
        frames: list[pygame.Surface] = []
        for index in range(frame_count):
            slot_rect = pygame.Rect(0, index * frame_height, region.get_width(), frame_height)
            slot = self._extract_surface(region, slot_rect)
            frame = self._prepare_frame(slot, background_mode, frame_layout)
            frames.append(frame)
        return self._scale_frames(frames, scaled_size, frame_layout)

    def _load_frames_from_strip(
        self,
        path: Path,
        *,
        frame_size: tuple[int, int],
        background_mode: str = "alpha",
        direction: str = "horizontal",
        scaled_size: tuple[int, int] | None = None,
        frame_layout: str = "content",
    ) -> tuple[pygame.Surface, ...]:
        image = self._load_surface_for_mode(path, background_mode)
        if image is None:
            return ()

        frame_width, frame_height = frame_size
        if frame_width <= 0 or frame_height <= 0:
            return ()

        if direction == "vertical":
            frame_count = image.get_height() // frame_height
            rects = [
                pygame.Rect(0, index * frame_height, frame_width, frame_height)
                for index in range(frame_count)
            ]
        else:
            frame_count = image.get_width() // frame_width
            rects = [
                pygame.Rect(index * frame_width, 0, frame_width, frame_height)
                for index in range(frame_count)
            ]

        frames: list[pygame.Surface] = []
        for rect in rects:
            slot = self._extract_surface(image, rect)
            frame = self._prepare_frame(slot, background_mode, frame_layout)
            frames.append(frame)

        normalized_target = scaled_size or frame_size
        return self._scale_frames(frames, normalized_target, frame_layout)

    def _prepare_frame(
        self,
        slot: pygame.Surface,
        background_mode: str,
        frame_layout: str,
    ) -> pygame.Surface:
        frame = self._apply_background_mode(slot, background_mode)
        if frame_layout == "cell":
            return frame
        return self._trim_surface(frame)

    def _scale_frames(
        self,
        frames: list[pygame.Surface],
        target_size: tuple[int, int],
        frame_layout: str,
    ) -> tuple[pygame.Surface, ...]:
        if not frames:
            return ()

        if frame_layout == "cell":
            return tuple(pygame.transform.smoothscale(frame, target_size) for frame in frames)

        max_width = max(1, max(frame.get_width() for frame in frames))
        max_height = max(1, max(frame.get_height() for frame in frames))
        normalized: list[pygame.Surface] = []
        for frame in frames:
            canvas = pygame.Surface((max_width, max_height), pygame.SRCALPHA)
            frame_rect = frame.get_rect(center=(max_width // 2, max_height // 2))
            canvas.blit(frame, frame_rect)
            normalized.append(pygame.transform.smoothscale(canvas, target_size))
        return tuple(normalized)

    def _load_optional_image(self, path: Path) -> pygame.Surface | None:
        if not path.exists():
            return None
        try:
            return pygame.image.load(path.as_posix()).convert_alpha()
        except pygame.error:
            return None

    def _load_raw_surface(self, path: Path) -> pygame.Surface | None:
        if not path.exists():
            return None
        try:
            return pygame.image.load(path.as_posix()).convert()
        except pygame.error:
            return None

    def _load_surface_for_mode(self, path: Path, mode: str) -> pygame.Surface | None:
        return self._load_optional_image(path) if mode.lower() == "alpha" else self._load_raw_surface(path)

    def _extract_surface(self, surface: pygame.Surface, rect: pygame.Rect) -> pygame.Surface:
        clipped = rect.clip(surface.get_rect())
        target = pygame.Surface(clipped.size, pygame.SRCALPHA)
        target.blit(surface, (0, 0), clipped)
        return target

    def _apply_background_mode(
        self,
        surface: pygame.Surface,
        mode: str,
    ) -> pygame.Surface:
        normalized = mode.lower()
        if normalized == "magenta":
            return self._apply_color_key(surface, (255, 0, 255))
        if normalized in {"white_magenta", "magenta_white"}:
            result = self._apply_color_key(surface, (255, 0, 255))
            return self._clear_border_connected_background(result, self._is_near_white)
        if normalized == "white":
            result = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            result.blit(surface, (0, 0))
            return self._clear_border_connected_background(result, self._is_near_white)
        result = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        result.blit(surface, (0, 0))
        return result

    def _apply_color_key(
        self,
        surface: pygame.Surface,
        key_color: tuple[int, int, int],
    ) -> pygame.Surface:
        keyed = surface.copy()
        keyed.set_colorkey(key_color)
        result = pygame.Surface(keyed.get_size(), pygame.SRCALPHA)
        result.blit(keyed, (0, 0))
        return result

    def _scale_background_layer(
        self,
        surface: pygame.Surface,
        layer: LayerConfig,
        config: GameConfig,
    ) -> pygame.Surface:
        if layer.fit_mode == "screen_height":
            target_height = max(1, int(round(config.window.height * layer.scale_multiplier)))
            scale = target_height / max(1, surface.get_height())
            target_width = max(config.window.width, int(surface.get_width() * scale))
            return pygame.transform.scale(surface, (target_width, target_height))

        target_width = max(1, int(round(layer.tile_width * layer.scale_multiplier)))
        target_height = max(1, int(round(layer.height * layer.scale_multiplier)))
        return pygame.transform.scale(surface, (target_width, target_height))

    def _trim_surface(self, surface: pygame.Surface) -> pygame.Surface:
        rect = surface.get_bounding_rect()
        if rect.width <= 0 or rect.height <= 0:
            return surface
        trimmed = pygame.Surface(rect.size, pygame.SRCALPHA)
        trimmed.blit(surface, (0, 0), rect)
        return trimmed

    def _trim_bottom_transparent_rows(self, surface: pygame.Surface) -> pygame.Surface:
        width, height = surface.get_size()
        if width <= 0 or height <= 0:
            return surface

        bottom = height - 1
        while bottom >= 0:
            if any(surface.get_at((x_position, bottom)).a > 0 for x_position in range(width)):
                break
            bottom -= 1

        if bottom < 0 or bottom == height - 1:
            return surface

        rect = pygame.Rect(0, 0, width, bottom + 1)
        trimmed = pygame.Surface(rect.size, pygame.SRCALPHA)
        trimmed.blit(surface, (0, 0), rect)
        return trimmed

    def _clear_border_connected_background(
        self,
        surface: pygame.Surface,
        predicate: Any,
    ) -> pygame.Surface:
        width, height = surface.get_size()
        result = surface.copy()
        visited = [[False] * width for _ in range(height)]
        queue: deque[tuple[int, int]] = deque()

        for x_position in range(width):
            queue.append((x_position, 0))
            queue.append((x_position, height - 1))
        for y_position in range(height):
            queue.append((0, y_position))
            queue.append((width - 1, y_position))

        while queue:
            x_position, y_position = queue.popleft()
            if not (0 <= x_position < width and 0 <= y_position < height):
                continue
            if visited[y_position][x_position]:
                continue
            visited[y_position][x_position] = True

            pixel = result.get_at((x_position, y_position))
            if pixel.a == 0 or not predicate(pixel):
                continue

            result.set_at((x_position, y_position), pygame.Color(0, 0, 0, 0))
            for next_x, next_y in (
                (x_position + 1, y_position),
                (x_position - 1, y_position),
                (x_position, y_position + 1),
                (x_position, y_position - 1),
            ):
                if 0 <= next_x < width and 0 <= next_y < height and not visited[next_y][next_x]:
                    queue.append((next_x, next_y))

        return result

    def _clear_pixels_by_predicate(
        self,
        surface: pygame.Surface,
        predicate: Any,
    ) -> pygame.Surface:
        width, height = surface.get_size()
        result = surface.copy()
        for y_position in range(height):
            for x_position in range(width):
                pixel = result.get_at((x_position, y_position))
                if pixel.a == 0:
                    continue
                if predicate(pixel):
                    result.set_at((x_position, y_position), pygame.Color(0, 0, 0, 0))
        return result

    def _clear_top_background_runs(
        self,
        surface: pygame.Surface,
        min_width: int,
    ) -> pygame.Surface:
        width, height = surface.get_size()
        if width <= 0 or height <= 0:
            return surface

        result = surface.copy()
        qualifying_colors: list[tuple[int, int, int]] = []
        seed_positions: list[tuple[int, int]] = []

        run_start = 0
        run_color = result.get_at((0, 0))
        for x_position in range(1, width + 1):
            next_color = result.get_at((x_position, 0)) if x_position < width else None
            same_color = (
                next_color is not None
                and next_color.a > 0
                and run_color.a > 0
                and next_color[:3] == run_color[:3]
            )
            if same_color:
                continue

            run_width = x_position - run_start
            if run_color.a > 0 and run_width >= min_width:
                qualifying_colors.append(run_color[:3])
                seed_positions.extend((seed_x, 0) for seed_x in range(run_start, x_position))

            if x_position < width:
                run_start = x_position
                run_color = next_color

        if not seed_positions:
            return result

        visited = [[False] * width for _ in range(height)]
        queue: deque[tuple[int, int]] = deque(seed_positions)

        def matches_background(pixel: pygame.Color) -> bool:
            if pixel.a == 0:
                return False
            return any(self._color_distance(pixel[:3], color) <= 18 for color in qualifying_colors)

        while queue:
            x_position, y_position = queue.popleft()
            if not (0 <= x_position < width and 0 <= y_position < height):
                continue
            if visited[y_position][x_position]:
                continue
            visited[y_position][x_position] = True

            pixel = result.get_at((x_position, y_position))
            if not matches_background(pixel):
                continue

            result.set_at((x_position, y_position), pygame.Color(0, 0, 0, 0))
            for next_x, next_y in (
                (x_position + 1, y_position),
                (x_position - 1, y_position),
                (x_position, y_position + 1),
                (x_position, y_position - 1),
            ):
                if 0 <= next_x < width and 0 <= next_y < height and not visited[next_y][next_x]:
                    queue.append((next_x, next_y))

        return result

    def _clear_top_rows(self, surface: pygame.Surface, row_count: int) -> pygame.Surface:
        if row_count <= 0:
            return surface
        result = surface.copy()
        clear_height = min(row_count, result.get_height())
        result.fill((0, 0, 0, 0), pygame.Rect(0, 0, result.get_width(), clear_height))
        return result

    def _clear_rects(
        self,
        surface: pygame.Surface,
        rects: tuple[tuple[int, int, int, int], ...],
    ) -> pygame.Surface:
        result = surface.copy()
        for rect_values in rects:
            result.fill((0, 0, 0, 0), pygame.Rect(rect_values))
        return result

    def _bleed_top_transparent_rgb(self, surface: pygame.Surface) -> pygame.Surface:
        width, height = surface.get_size()
        if width <= 0 or height <= 0:
            return surface

        result = surface.copy()
        for x_position in range(width):
            first_opaque_y: int | None = None
            first_opaque_color: pygame.Color | None = None
            for y_position in range(height):
                pixel = result.get_at((x_position, y_position))
                if pixel.a > 0:
                    first_opaque_y = y_position
                    first_opaque_color = pixel
                    break

            if first_opaque_y is None or first_opaque_y <= 0 or first_opaque_color is None:
                continue

            bleed_color = pygame.Color(
                first_opaque_color.r,
                first_opaque_color.g,
                first_opaque_color.b,
                0,
            )
            for y_position in range(first_opaque_y):
                pixel = result.get_at((x_position, y_position))
                if pixel.a != 0:
                    break
                result.set_at((x_position, y_position), bleed_color)

        return result

    def _strip_chroma_halo(
        self,
        surface: pygame.Surface,
        predicate: Any,
    ) -> pygame.Surface:
        width, height = surface.get_size()
        if width <= 0 or height <= 0:
            return surface

        result = surface.copy()
        for _ in range(4):
            source = result.copy()
            changed = False
            for y_position in range(height):
                for x_position in range(width):
                    pixel = source.get_at((x_position, y_position))
                    if pixel.a == 0 or not predicate(pixel):
                        continue

                    touches_transparent = False
                    for offset_x, offset_y in (
                        (-1, 0),
                        (1, 0),
                        (0, -1),
                        (0, 1),
                        (-1, -1),
                        (1, -1),
                        (-1, 1),
                        (1, 1),
                    ):
                        neighbor_x = x_position + offset_x
                        neighbor_y = y_position + offset_y
                        if not (0 <= neighbor_x < width and 0 <= neighbor_y < height):
                            touches_transparent = True
                            break
                        if source.get_at((neighbor_x, neighbor_y)).a == 0:
                            touches_transparent = True
                            break

                    if not touches_transparent:
                        continue

                    neighbor_rgb: list[tuple[int, int, int]] = []
                    for offset_x, offset_y in (
                        (-1, 0),
                        (1, 0),
                        (0, -1),
                        (0, 1),
                        (-1, -1),
                        (1, -1),
                        (-1, 1),
                        (1, 1),
                    ):
                        neighbor_x = x_position + offset_x
                        neighbor_y = y_position + offset_y
                        if not (0 <= neighbor_x < width and 0 <= neighbor_y < height):
                            continue
                        neighbor = source.get_at((neighbor_x, neighbor_y))
                        if neighbor.a > 0 and not predicate(neighbor):
                            neighbor_rgb.append((neighbor.r, neighbor.g, neighbor.b))

                    if neighbor_rgb:
                        red = sum(item[0] for item in neighbor_rgb) // len(neighbor_rgb)
                        green = sum(item[1] for item in neighbor_rgb) // len(neighbor_rgb)
                        blue = sum(item[2] for item in neighbor_rgb) // len(neighbor_rgb)
                        result.set_at((x_position, y_position), pygame.Color(red, green, blue, pixel.a))
                    else:
                        result.set_at((x_position, y_position), pygame.Color(0, 0, 0, 0))
                    changed = True

            if not changed:
                break

        return result

    def _is_near_white(self, pixel: pygame.Color) -> bool:
        return pixel.r >= 245 and pixel.g >= 245 and pixel.b >= 245

    def _is_near_magenta(self, pixel: pygame.Color) -> bool:
        return (
            pixel.r >= 140
            and pixel.b >= 110
            and pixel.g <= 185
            and (pixel.r - pixel.g) >= 35
            and (pixel.b - pixel.g) >= 10
            and (pixel.r + pixel.b - (2 * pixel.g)) >= 80
        )

    def _is_chroma_halo(self, pixel: pygame.Color) -> bool:
        return (
            pixel.r >= 70
            and pixel.b >= 80
            and pixel.g <= 150
            and (pixel.r - pixel.g) >= 10
            and (pixel.b - pixel.g) >= 20
            and (pixel.r + pixel.b - (2 * pixel.g)) >= 70
        )

    def _color_distance(
        self,
        left: tuple[int, int, int],
        right: tuple[int, int, int],
    ) -> int:
        return abs(left[0] - right[0]) + abs(left[1] - right[1]) + abs(left[2] - right[2])
