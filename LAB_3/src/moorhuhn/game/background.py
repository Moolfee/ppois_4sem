from __future__ import annotations

import pygame

from ..config.game_config import GameConfig, LayerConfig
from ..media.assets import AssetLibrary

FALLBACK_LAYER_STYLES: dict[str, tuple[str, tuple[int, int, int]]] = {
    "sky": ("sky", (152, 208, 252)),
    "far_mountains": ("hills", (118, 168, 122)),
    "middle_hills_castle": ("hills", (83, 133, 83)),
    "foreground_landscape": ("fence", (134, 92, 58)),
    "front_trunks": ("trees", (134, 92, 58)),
}


def ease_out_cubic(progress: float) -> float:
    clamped = max(0.0, min(1.0, progress))
    return 1.0 - (1.0 - clamped) ** 3


class ParallaxLayer:
    def __init__(self, config: LayerConfig, asset_tile: pygame.Surface | None = None) -> None:
        self.config = config
        self.surface = asset_tile or self._build_tile()
        self.scroll_offset = 0.0
        self.cursor_offset = 0.0
        self.lowest_transparent_by_x = self._build_lowest_transparent_map()

    def _build_tile(self) -> pygame.Surface:
        tile = pygame.Surface((self.config.tile_width, self.config.height), pygame.SRCALPHA)
        layer_shape, accent_color = FALLBACK_LAYER_STYLES.get(
            self.config.name,
            ("hills", (96, 128, 96)),
        )

        if layer_shape == "sky":
            top = (152, 208, 252)
            bottom = (224, 233, 247)
            for y in range(tile.get_height()):
                blend = y / max(1, tile.get_height() - 1)
                row_color = (
                    int(top[0] + (bottom[0] - top[0]) * blend),
                    int(top[1] + (bottom[1] - top[1]) * blend),
                    int(top[2] + (bottom[2] - top[2]) * blend),
                )
                pygame.draw.line(tile, row_color, (0, y), (tile.get_width(), y))
            for index in range(7):
                cloud_x = 80 + index * 180
                cloud_y = 30 + (index % 2) * 24
                pygame.draw.ellipse(tile, (242, 246, 252), (cloud_x, cloud_y, 130, 42))
                pygame.draw.ellipse(tile, (232, 239, 248), (cloud_x + 36, cloud_y - 10, 84, 30))
        elif layer_shape == "hills":
            for index in range(4):
                radius = 120 + index * 24
                center_x = 120 + index * 170
                center_y = self.config.height - 18
                pygame.draw.circle(tile, accent_color, (center_x, center_y), radius)
                pygame.draw.circle(
                    tile,
                    tuple(max(0, channel - 20) for channel in accent_color),
                    (center_x + 55, center_y + 16),
                    max(20, radius - 20),
                )
        elif layer_shape == "trees":
            for index in range(7):
                trunk_x = 34 + index * 88
                pygame.draw.rect(tile, (85, 58, 33), (trunk_x, self.config.height - 70, 14, 70))
                pygame.draw.circle(tile, accent_color, (trunk_x + 7, self.config.height - 100), 38)
                pygame.draw.circle(tile, accent_color, (trunk_x - 14, self.config.height - 88), 24)
                pygame.draw.circle(tile, accent_color, (trunk_x + 26, self.config.height - 84), 22)
        elif layer_shape == "fence":
            pygame.draw.rect(tile, (83, 118, 46), (0, self.config.height - 56, tile.get_width(), 56))
            for index in range(11):
                board_x = 16 + index * 48
                pygame.draw.rect(
                    tile,
                    accent_color,
                    (board_x, self.config.height - 92, 20, 78),
                    border_radius=3,
                )
                pygame.draw.rect(tile, accent_color, (board_x - 6, self.config.height - 46, 32, 10))
            for index in range(48):
                blade_x = index * 12
                blade_height = 18 + (index % 3) * 9
                pygame.draw.polygon(
                    tile,
                    (44, 124, 39),
                    [
                        (blade_x, self.config.height - 14),
                        (blade_x + 6, self.config.height - 14 - blade_height),
                        (blade_x + 12, self.config.height - 14),
                    ],
                )

        return tile

    def _build_lowest_transparent_map(self) -> list[int | None]:
        width, height = self.surface.get_size()
        lowest_transparent_by_x: list[int | None] = [None] * width
        for x_position in range(width):
            for y_position in range(height - 1, -1, -1):
                if self.surface.get_at((x_position, y_position)).a == 0:
                    lowest_transparent_by_x[x_position] = y_position
                    break
        return lowest_transparent_by_x

    def update(
        self,
        dt_ms: int,
        world_shift_px: float,
        cursor_normalized: float,
        mouse_reaction_px: int,
        viewport_width: int,
    ) -> None:
        width = max(1, self.surface.get_width())
        smoothing = min(1.0, dt_ms / 180)
        target_cursor_offset = -cursor_normalized * mouse_reaction_px * self.config.cursor_factor

        if self.config.repeat_x:
            self.scroll_offset = (self.scroll_offset + world_shift_px * self.config.speed_factor) % width
            self.cursor_offset += (target_cursor_offset - self.cursor_offset) * smoothing
            return

        travel = max(0.0, width - viewport_width)
        self.scroll_offset += world_shift_px * self.config.speed_factor
        self.scroll_offset = max(-travel / 2, min(travel / 2, self.scroll_offset))
        target_cursor_offset = max(-travel / 2, min(travel / 2, target_cursor_offset))
        self.cursor_offset += (target_cursor_offset - self.cursor_offset) * smoothing

    def reset_view(self) -> None:
        self.scroll_offset = 0.0
        self.cursor_offset = 0.0

    def current_draw_x(self, viewport_width: int) -> float:
        width = max(1, self.surface.get_width())
        if not self.config.repeat_x:
            travel = max(0, width - viewport_width)
            base_x = -travel / 2
            position = base_x - self.scroll_offset + self.cursor_offset + self.config.horizontal_offset
            return max(-travel, min(0.0, position))
        offset = (self.scroll_offset + self.cursor_offset) % width
        return -offset + self.config.horizontal_offset

    def screen_to_local_x(self, screen_x: float, viewport_width: int) -> float | None:
        width = self.surface.get_width()
        if width <= 0:
            return None

        local_x = screen_x - self.current_draw_x(viewport_width)
        if self.config.repeat_x:
            return local_x % width
        return local_x if 0.0 <= local_x < width else None

    def local_to_screen_x(self, local_x: float, viewport_width: int) -> float | None:
        width = self.surface.get_width()
        if width <= 0:
            return None

        screen_x = self.current_draw_x(viewport_width) + local_x
        if not self.config.repeat_x or viewport_width <= 0:
            return screen_x

        width_float = float(width)
        target_center = viewport_width / 2
        while screen_x < -width_float:
            screen_x += width_float
        while screen_x > viewport_width + width_float:
            screen_x -= width_float
        if screen_x < 0:
            screen_x += width_float * round((target_center - screen_x) / width_float)
        elif screen_x > viewport_width:
            screen_x -= width_float * round((screen_x - target_center) / width_float)
        return screen_x

    def draw(self, surface: pygame.Surface) -> None:
        y_position = self.config.y + self.config.vertical_offset
        if not self.config.repeat_x:
            surface.blit(self.surface, (int(self.current_draw_x(surface.get_width())), y_position))
            return

        width = self.surface.get_width()
        x_position = int(self.current_draw_x(surface.get_width()))
        while x_position < surface.get_width():
            surface.blit(self.surface, (x_position, y_position))
            x_position += width

    def find_lowest_transparent_y_for_local_x(
        self,
        local_x: float,
        sample_half_width: int = 0,
    ) -> int | None:
        width = self.surface.get_width()
        if width <= 0 or not self.lowest_transparent_by_x:
            return None

        result: int | None = None
        local_center = int(round(local_x))
        for delta in range(-sample_half_width, sample_half_width + 1):
            sampled_x = local_center + delta
            if self.config.repeat_x:
                sampled_x %= width
            elif not (0 <= sampled_x < width):
                continue
            transparent_y = self.lowest_transparent_by_x[sampled_x]
            if transparent_y is None:
                continue
            absolute_y = self.config.y + self.config.vertical_offset + transparent_y
            if result is None or absolute_y > result:
                result = absolute_y
        return result

    def find_lowest_transparent_y(
        self,
        screen_x: int,
        viewport_width: int,
        sample_half_width: int = 0,
    ) -> int | None:
        local_x = self.screen_to_local_x(screen_x, viewport_width)
        if local_x is None:
            return None
        return self.find_lowest_transparent_y_for_local_x(local_x, sample_half_width)

    def is_opaque_at_screen_point(self, point: tuple[int, int], viewport_width: int) -> bool:
        local_x = self.screen_to_local_x(point[0], viewport_width)
        if local_x is None:
            return False

        sampled_x = int(round(local_x))
        if self.config.repeat_x:
            sampled_x %= self.surface.get_width()
        elif not (0 <= sampled_x < self.surface.get_width()):
            return False

        local_y = point[1] - (self.config.y + self.config.vertical_offset)
        if not (0 <= local_y < self.surface.get_height()):
            return False
        return self.surface.get_at((sampled_x, local_y)).a > 0


class ParallaxBackground:
    def __init__(self, config: GameConfig, assets: AssetLibrary) -> None:
        self.mouse_reaction_px = config.parallax_sheet.mouse_reaction_px if config.parallax_sheet else 0
        self.layers = [ParallaxLayer(layer, assets.get_background_tile(layer.name)) for layer in config.layers]
        self.layers_by_name = {layer.config.name: layer for layer in self.layers}

    def _find_layer(self, layer_name: str) -> ParallaxLayer | None:
        return self.layers_by_name.get(layer_name)

    def update(self, dt_ms: int, world_shift_px: float, cursor_x: int, viewport_width: int) -> None:
        if viewport_width <= 0:
            cursor_normalized = 0.0
        else:
            half_width = viewport_width / 2
            cursor_normalized = (cursor_x - half_width) / half_width
            cursor_normalized = max(-1.0, min(1.0, cursor_normalized))

        for layer in self.layers:
            layer.update(dt_ms, world_shift_px, cursor_normalized, self.mouse_reaction_px, viewport_width)

    def reset_view(self) -> None:
        for layer in self.layers:
            layer.reset_view()

    def draw_layers(
        self,
        surface: pygame.Surface,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> None:
        total = len(self.layers)
        start_index = max(0, min(total, start))
        end_index = total if end is None else max(start_index, min(total, end))
        for layer in self.layers[start_index:end_index]:
            layer.draw(surface)

    def draw_background_layers(self, surface: pygame.Surface, reserve_front_layers: int = 1) -> None:
        self.draw_layers(surface, end=max(0, len(self.layers) - max(0, reserve_front_layers)))

    def draw_foreground_layers(self, surface: pygame.Surface, count: int = 1) -> None:
        if not self.layers or count <= 0:
            return
        self.draw_layers(surface, start=max(0, len(self.layers) - count))

    def find_layer_lowest_transparent_y(
        self,
        layer_name: str,
        screen_x: int,
        viewport_width: int,
        sample_half_width: int = 0,
    ) -> int | None:
        layer = self._find_layer(layer_name)
        if layer is None:
            return None
        return layer.find_lowest_transparent_y(screen_x, viewport_width, sample_half_width)

    def find_layer_lowest_transparent_y_for_local_x(
        self,
        layer_name: str,
        local_x: float,
        sample_half_width: int = 0,
    ) -> int | None:
        layer = self._find_layer(layer_name)
        if layer is None:
            return None
        return layer.find_lowest_transparent_y_for_local_x(local_x, sample_half_width)

    def layer_screen_to_local_x(
        self,
        layer_name: str,
        screen_x: float,
        viewport_width: int,
    ) -> float | None:
        layer = self._find_layer(layer_name)
        if layer is None:
            return None
        return layer.screen_to_local_x(screen_x, viewport_width)

    def layer_local_to_screen_x(
        self,
        layer_name: str,
        local_x: float,
        viewport_width: int,
    ) -> float | None:
        layer = self._find_layer(layer_name)
        if layer is None:
            return None
        return layer.local_to_screen_x(local_x, viewport_width)

    def layer_is_opaque_at_screen_point(
        self,
        layer_name: str,
        point: tuple[int, int],
        viewport_width: int,
    ) -> bool:
        layer = self._find_layer(layer_name)
        if layer is None:
            return False
        return layer.is_opaque_at_screen_point(point, viewport_width)

    def topmost_layer_hit(
        self,
        point: tuple[int, int],
        viewport_width: int,
    ) -> tuple[str, float] | None:
        for layer in reversed(self.layers):
            if not layer.is_opaque_at_screen_point(point, viewport_width):
                continue
            local_x = layer.screen_to_local_x(point[0], viewport_width)
            if local_x is not None:
                return layer.config.name, local_x
        return None


def build_scene_backdrop(size: tuple[int, int], has_parallax_sheet: bool) -> pygame.Surface:
    width, height = size
    surface = pygame.Surface((width, height))
    top = (132, 209, 255)
    bottom = (255, 222, 163)
    for y in range(height):
        blend = y / height
        color = (
            int(top[0] + (bottom[0] - top[0]) * blend),
            int(top[1] + (bottom[1] - top[1]) * blend),
            int(top[2] + (bottom[2] - top[2]) * blend),
        )
        pygame.draw.line(surface, color, (0, y), (width, y))

    if has_parallax_sheet:
        return surface

    pygame.draw.circle(surface, (255, 237, 160), (width - 130, 110), 54)
    pygame.draw.rect(surface, (130, 183, 94), (0, 520, width, 200))
    pygame.draw.ellipse(surface, (172, 201, 111), (-40, 480, 520, 120))
    pygame.draw.ellipse(surface, (156, 190, 102), (360, 500, 620, 130))
    pygame.draw.ellipse(surface, (164, 199, 118), (820, 490, 520, 140))
    return surface
