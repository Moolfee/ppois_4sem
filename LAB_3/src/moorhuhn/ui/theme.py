from __future__ import annotations

import pygame

from ..config.game_config import UiConfig

DEFAULT_THEME = UiConfig(
    accent_fill_color=(130, 18, 28),
    accent_border_color=(198, 56, 52),
    accent_hover_fill_color=(201, 92, 24),
    accent_hover_border_color=(245, 163, 64),
    accent_base_alpha=192,
    accent_hover_alpha=238,
    button_border_radius=14,
    button_small_border_radius=8,
    panel_fill_color=(92, 11, 21),
    panel_fill_alpha=184,
    panel_border_color=(181, 52, 48),
    panel_border_radius=18,
    loading_overlay_color=(0, 0, 0),
    loading_overlay_alpha=0,
    loading_bar_background_color=(78, 8, 16),
    loading_bar_background_alpha=190,
    loading_bar_fill_color=(182, 70, 26),
    loading_bar_fill_alpha=240,
    loading_bar_border_color=(229, 140, 58),
    loading_bar_border_radius=14,
    pause_overlay_color=(20, 4, 10),
    pause_overlay_alpha=142,
    crosshair_fallback_color=(238, 63, 48),
    hud_left_margin_px=34,
    hud_top_margin_px=30,
    hud_line_gap_px=30,
    hud_timer_right_margin_px=134,
    hud_timer_top_margin_px=58,
    ammo_right_margin_px=34,
    ammo_bottom_margin_px=34,
    ammo_spacing_factor=0.7,
    reload_label_gap_px=12,
    pause_button_width=420,
    pause_button_height=58,
    pause_button_gap_px=20,
    menu_chicken_scale=1.35,
    menu_chicken_center_x=230,
    menu_chicken_bottom_offset_px=42,
    menu_chicken_down_delay_ms=650,
    menu_chicken_return_duration_ms=230,
)


def _pick_theme(theme: UiConfig | None) -> UiConfig:
    return theme or DEFAULT_THEME


def draw_accent_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    theme: UiConfig | None = None,
    *,
    hovered: bool = False,
    border_radius: int | None = None,
    alpha: int | None = None,
) -> None:
    palette = _pick_theme(theme)
    fill_alpha = alpha if alpha is not None else (
        palette.accent_hover_alpha if hovered else palette.accent_base_alpha
    )
    fill_color = palette.accent_hover_fill_color if hovered else palette.accent_fill_color
    border_color = palette.accent_hover_border_color if hovered else palette.accent_border_color
    corner_radius = palette.button_border_radius if border_radius is None else border_radius
    fill = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(
        fill,
        (*fill_color, fill_alpha),
        fill.get_rect(),
        border_radius=corner_radius,
    )
    surface.blit(fill, rect)
    pygame.draw.rect(
        surface,
        border_color,
        rect,
        width=2,
        border_radius=corner_radius,
    )


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    theme: UiConfig | None = None,
) -> None:
    palette = _pick_theme(theme)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((*palette.panel_fill_color, palette.panel_fill_alpha))
    surface.blit(panel, rect)
    pygame.draw.rect(
        surface,
        palette.panel_border_color,
        rect,
        width=2,
        border_radius=palette.panel_border_radius,
    )


def draw_progress_bar(
    surface: pygame.Surface,
    rect: pygame.Rect,
    progress: float,
    theme: UiConfig | None = None,
) -> None:
    palette = _pick_theme(theme)
    fill_back = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(
        fill_back,
        (*palette.loading_bar_background_color, palette.loading_bar_background_alpha),
        fill_back.get_rect(),
        border_radius=palette.loading_bar_border_radius,
    )
    surface.blit(fill_back, rect)
    pygame.draw.rect(
        surface,
        palette.loading_bar_border_color,
        rect,
        width=2,
        border_radius=palette.loading_bar_border_radius,
    )

    inner_width = max(0, rect.width - 6)
    fill_width = max(0, min(inner_width, int(inner_width * max(0.0, min(1.0, progress)))))
    if fill_width <= 0:
        return

    fill_rect = pygame.Rect(rect.x + 3, rect.y + 3, fill_width, rect.height - 6)
    fill_surface = pygame.Surface(fill_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(
        fill_surface,
        (*palette.loading_bar_fill_color, palette.loading_bar_fill_alpha),
        fill_surface.get_rect(),
        border_radius=max(1, palette.loading_bar_border_radius - 3),
    )
    surface.blit(fill_surface, fill_rect)
