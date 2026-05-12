from __future__ import annotations

import pygame

from .help import build_help_lines, wrap_outlined_text
from .screen_core import MenuBackdropScreen, SETTING_OPTIONS, SettingOption
from .text import render_outlined_text
from .theme import draw_accent_button, draw_panel


class MenuScreen(MenuBackdropScreen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.items = [
            ("Начать игру", "game"),
            ("Настройки", "settings"),
            ("Таблица рекордов", "scores"),
            ("Справка", "help"),
            ("Выход", "quit"),
        ]
        self.selected = 0

    def on_enter(self, *, reset_scene: bool = False, **_: object) -> None:
        super().on_enter(reset_scene=reset_scene)

    def _rect_for(self, index: int) -> pygame.Rect:
        width = self.app.surface.get_width()
        return pygame.Rect(width // 2 - 210, 260 + index * 74, 420, 56)

    def _set_selected(self, index: int, *, play_sound: bool = False) -> None:
        index %= len(self.items)
        if index == self.selected:
            return
        self.selected = index
        if play_sound:
            self.app.audio.play_ui_hover()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.handle_menu_scene_event(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._set_selected(self.selected - 1, play_sound=True)
            elif event.key == pygame.K_DOWN:
                self._set_selected(self.selected + 1, play_sound=True)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate(self.selected)
        elif event.type == pygame.MOUSEMOTION:
            for index in range(len(self.items)):
                if self._rect_for(index).collidepoint(event.pos):
                    self._set_selected(index, play_sound=True)
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index in range(len(self.items)):
                if self._rect_for(index).collidepoint(event.pos):
                    self._activate(index)
                    break

    def _activate(self, index: int) -> None:
        action = self.items[index][1]
        self.app.audio.play_ui_confirm()
        if action == "quit":
            self.app.stop()
        else:
            self.app.screens.switch(action)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_menu_scene(surface)
        if self.app.game_logo is not None:
            logo_rect = self.app.game_logo.get_rect(center=(surface.get_width() // 2, 104))
            surface.blit(self.app.game_logo, logo_rect)
        else:
            title = render_outlined_text(self.app.fonts["title"], "Moorhuhn", outline_width=1)
            surface.blit(title, title.get_rect(center=(surface.get_width() // 2, 120)))

        for index, (label, _) in enumerate(self.items):
            rect = self._rect_for(index)
            draw_accent_button(surface, rect, self.app.config.ui, hovered=index == self.selected)
            text = render_outlined_text(self.app.fonts["heading"], label)
            surface.blit(text, text.get_rect(center=rect.center))


class SettingsScreen(MenuBackdropScreen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.selected = 0
        self.options = SETTING_OPTIONS

    @property
    def selected_option(self) -> SettingOption:
        return self.options[self.selected]

    def _option_rect(self, index: int) -> pygame.Rect:
        width = self.app.surface.get_width()
        return pygame.Rect(width // 2 - 330, 212 + index * 72, 660, 56)

    def _minus_rect(self, index: int) -> pygame.Rect:
        row = self._option_rect(index)
        return pygame.Rect(row.right - 170, row.y + 6, 42, row.height - 12)

    def _plus_rect(self, index: int) -> pygame.Rect:
        row = self._option_rect(index)
        return pygame.Rect(row.right - 46, row.y + 6, 42, row.height - 12)

    def _toggle_rect(self, index: int) -> pygame.Rect:
        row = self._option_rect(index)
        return pygame.Rect(row.right - 170, row.y + 6, 166, row.height - 12)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.handle_menu_scene_event(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
                self.app.audio.play_ui_hover()
                return
            if event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
                self.app.audio.play_ui_hover()
                return
            if event.key == pygame.K_LEFT:
                self._adjust_selected(-0.05)
                return
            if event.key == pygame.K_RIGHT:
                self._adjust_selected(0.05)
                return
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._toggle_selected()
                return
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.app.audio.play_ui_confirm()
                self.app.screens.switch("menu")
                return

        if event.type == pygame.MOUSEMOTION:
            for index in range(len(self.options)):
                if self._option_rect(index).collidepoint(event.pos):
                    if self.selected != index:
                        self.selected = index
                        self.app.audio.play_ui_hover()
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, option in enumerate(self.options):
                if not self._option_rect(index).collidepoint(event.pos):
                    continue
                self.selected = index
                if option.is_toggle:
                    if self._toggle_rect(index).collidepoint(event.pos):
                        self._toggle_selected()
                    else:
                        self.app.audio.play_ui_hover()
                    return
                if self._minus_rect(index).collidepoint(event.pos):
                    self._adjust_selected(-0.05)
                    return
                if self._plus_rect(index).collidepoint(event.pos):
                    self._adjust_selected(0.05)
                    return
                self.app.audio.play_ui_hover()
                return

    def _adjust_selected(self, delta: float) -> None:
        option = self.selected_option
        if option.is_toggle:
            self._toggle_selected()
            return
        settings = self.app.settings
        current_value = getattr(settings, option.key)
        new_value = max(0.0, min(1.0, current_value + delta))
        if abs(new_value - current_value) < 1e-9:
            return
        self.app.audio.play_ui_confirm()
        self.app.update_settings(settings.updated(**{option.key: new_value}))

    def _toggle_selected(self) -> None:
        option = self.selected_option
        if not option.is_toggle:
            return
        settings = self.app.settings
        self.app.audio.play_ui_confirm()
        self.app.update_settings(
            settings.updated(borderless_fullscreen=not settings.borderless_fullscreen)
        )

    def _value_label(self, key: str) -> str:
        value = getattr(self.app.settings, key)
        if isinstance(value, bool):
            return "ВКЛ" if value else "ВЫКЛ"
        return f"{int(round(value * 100)):3d}%"

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_menu_scene(surface)
        title = render_outlined_text(self.app.fonts["title"], "Настройки", outline_width=1)
        subtitle = render_outlined_text(self.app.fonts["body"], "Громкость и режим окна")
        surface.blit(title, title.get_rect(center=(surface.get_width() // 2, 112)))
        surface.blit(subtitle, subtitle.get_rect(center=(surface.get_width() // 2, 160)))

        for index, option in enumerate(self.options):
            row = self._option_rect(index)
            selected = index == self.selected
            draw_accent_button(surface, row, self.app.config.ui, hovered=selected)

            label = render_outlined_text(self.app.fonts["body"], option.label)
            surface.blit(label, (row.x + 18, row.y + 10))

            if option.is_toggle:
                toggle_rect = self._toggle_rect(index)
                draw_accent_button(
                    surface,
                    toggle_rect,
                    self.app.config.ui,
                    hovered=selected or getattr(self.app.settings, option.key),
                    border_radius=self.app.config.ui.button_small_border_radius,
                )
                toggle_text = render_outlined_text(self.app.fonts["small"], self._value_label(option.key))
                surface.blit(toggle_text, toggle_text.get_rect(center=toggle_rect.center))
                continue

            minus_rect = self._minus_rect(index)
            plus_rect = self._plus_rect(index)
            value_rect = pygame.Rect(
                minus_rect.right + 8,
                row.y + 6,
                plus_rect.x - minus_rect.right - 16,
                row.height - 12,
            )
            for rect, caption in ((minus_rect, "-"), (plus_rect, "+")):
                draw_accent_button(
                    surface,
                    rect,
                    self.app.config.ui,
                    hovered=selected,
                    border_radius=self.app.config.ui.button_small_border_radius,
                )
                button_text = render_outlined_text(self.app.fonts["heading"], caption)
                surface.blit(button_text, button_text.get_rect(center=rect.center))

            draw_accent_button(
                surface,
                value_rect,
                self.app.config.ui,
                hovered=selected,
                border_radius=self.app.config.ui.button_small_border_radius,
            )
            value_text = render_outlined_text(self.app.fonts["small"], self._value_label(option.key))
            surface.blit(value_text, value_text.get_rect(center=value_rect.center))


class HelpScreen(MenuBackdropScreen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.scroll_offset = 0
        self.max_scroll_offset = 0
        self.cached_content_size = (0, 0)
        self.cached_content_surface: pygame.Surface | None = None

    def on_enter(self, **_: object) -> None:
        super().on_enter()
        self.scroll_offset = 0
        self.max_scroll_offset = 0
        self.cached_content_size = (0, 0)
        self.cached_content_surface = None

    def _panel_rect(self, surface: pygame.Surface) -> pygame.Rect:
        return pygame.Rect(120, 70, surface.get_width() - 240, surface.get_height() - 140)

    def _content_rect(self, surface: pygame.Surface) -> pygame.Rect:
        panel = self._panel_rect(surface)
        return pygame.Rect(panel.x + 28, panel.y + 100, panel.width - 56, panel.height - 132)

    def _scroll(self, delta: int) -> None:
        self.scroll_offset = max(0, min(self.max_scroll_offset, self.scroll_offset + delta))

    def _build_content_cache(self, content_rect: pygame.Rect) -> None:
        if self.cached_content_surface is not None and self.cached_content_size == content_rect.size:
            return

        rendered_lines: list[tuple[pygame.Surface, int]] = []
        total_height = 0
        max_width = content_rect.width - 12
        for line in build_help_lines(self.app.config):
            font = self.app.fonts["heading"] if line.endswith(":") else self.app.fonts["body"]
            line_gap = 38 if line.endswith(":") else 28
            for item in wrap_outlined_text(font, line, max_width):
                rendered_lines.append((item, line_gap))
                total_height += item.get_height() + line_gap - 6

        cache_height = max(content_rect.height, total_height)
        cache = pygame.Surface((content_rect.width, cache_height), pygame.SRCALPHA)
        y_position = 0
        for item, line_gap in rendered_lines:
            cache.blit(item, (0, y_position))
            y_position += item.get_height() + line_gap - 6

        self.cached_content_size = content_rect.size
        self.cached_content_surface = cache
        self.max_scroll_offset = max(0, cache.get_height() - content_rect.height)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.handle_menu_scene_event(event):
            return
        if event.type == pygame.MOUSEWHEEL:
            self._scroll(-event.y * 48)
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_BACKSPACE):
                self.app.audio.play_ui_confirm()
                self.app.screens.switch("menu")
                return
            if event.key == pygame.K_UP:
                self._scroll(-36)
                return
            if event.key == pygame.K_DOWN:
                self._scroll(36)
                return
            if event.key == pygame.K_PAGEUP:
                self._scroll(-220)
                return
            if event.key == pygame.K_PAGEDOWN:
                self._scroll(220)
                return
            if event.key == pygame.K_HOME:
                self.scroll_offset = 0
                return
            if event.key == pygame.K_END:
                self.scroll_offset = self.max_scroll_offset
                return

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_menu_scene(surface)
        panel = self._panel_rect(surface)
        draw_panel(surface, panel, self.app.config.ui)

        title = render_outlined_text(self.app.fonts["title"], "Справка", outline_width=1)
        surface.blit(title, (panel.x + 28, panel.y + 20))
        content_rect = self._content_rect(surface)
        self._build_content_cache(content_rect)
        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll_offset))
        if self.cached_content_surface is None:
            return
        visible_area = pygame.Rect(0, self.scroll_offset, content_rect.width, content_rect.height)
        surface.blit(self.cached_content_surface, content_rect.topleft, area=visible_area)


class HighScoresScreen(MenuBackdropScreen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.entries = []
        self.reset_menu_scene_on_exit = False

    def on_enter(self, *, reset_menu_scene: bool = False, **_: object) -> None:
        super().on_enter()
        self.entries = self.app.leaderboard.load_entries()
        self.reset_menu_scene_on_exit = reset_menu_scene

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.handle_menu_scene_event(event):
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_BACKSPACE):
            self.app.audio.play_ui_confirm()
            self.app.screens.switch("menu", reset_scene=self.reset_menu_scene_on_exit)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_menu_scene(surface)
        panel = pygame.Rect(180, 60, surface.get_width() - 360, surface.get_height() - 120)
        draw_panel(surface, panel, self.app.config.ui)

        title = render_outlined_text(self.app.fonts["title"], "Таблица рекордов", outline_width=1)
        surface.blit(title, title.get_rect(center=(surface.get_width() // 2, panel.y + 46)))

        headers = ["Место", "Игрок", "Очки", "Дата"]
        x_positions = [panel.x + 40, panel.x + 170, panel.x + 430, panel.x + 580]
        for header, x_position in zip(headers, x_positions, strict=True):
            text = render_outlined_text(self.app.fonts["heading"], header)
            surface.blit(text, (x_position, panel.y + 102))

        y_position = panel.y + 150
        for index, entry in enumerate(self.entries, start=1):
            values = [str(index), entry.name, str(entry.score), entry.created_at]
            for value, x_position in zip(values, x_positions, strict=True):
                text = render_outlined_text(self.app.fonts["body"], value)
                surface.blit(text, (x_position, y_position))
            y_position += 42

        footer = render_outlined_text(self.app.fonts["body"], "Enter / Esc - назад в меню")
        surface.blit(footer, (panel.x + 40, panel.bottom - 50))
