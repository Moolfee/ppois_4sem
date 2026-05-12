from __future__ import annotations

import os
from pathlib import Path

import pygame

from ..config.game_config import load_game_config
from ..config.settings import UserSettings, UserSettingsStore
from ..game.world import GameWorld
from ..media.assets import AssetLibrary
from ..media.audio import AudioManager, prepare_audio
from ..storage.highscores import HighScoreTable
from ..ui.menu_scene import MenuScene
from ..ui.screens import (
    GameScreen,
    HelpScreen,
    HighScoresScreen,
    MenuScreen,
    NameEntryScreen,
    ResultScreen,
    ScreenManager,
    SettingsScreen,
)
from ..ui.text import render_outlined_text
from ..ui.theme import draw_progress_bar


class MoorhuhnApp:
    def __init__(self, project_root: Path) -> None:
        self._shutdown_complete = False
        self.project_root = project_root
        self.config = load_game_config(project_root / "config" / "game_config.json")
        self.settings_store = UserSettingsStore(project_root / "data" / "settings.json")
        self.settings = self.settings_store.load(self.config.audio)
        prepare_audio(self.config.audio)

        pygame.init()
        pygame.display.set_caption(self.config.window.title)
        self.clock = pygame.time.Clock()
        self.running = True
        self.base_size = (self.config.window.width, self.config.window.height)
        self.window_surface, applied_borderless = self._configure_display(
            self.settings.borderless_fullscreen,
            reset_display=False,
        )
        if applied_borderless != self.settings.borderless_fullscreen:
            self.settings = self.settings.updated(borderless_fullscreen=applied_borderless)
            self.settings_store.save(self.settings)
        self.surface = pygame.Surface(self.base_size).convert_alpha()
        self.loading_background = self._load_loading_background()
        self.game_logo = self._load_game_logo()
        self._bootstrap_font_title = self._load_font(40)
        self._bootstrap_font_body = self._load_font(22)
        self._draw_loading_screen("Подготовка запуска...", 0.06)

        self.fonts = self._with_loading("Загрузка шрифтов...", 0.16, self._build_fonts)
        self.audio = self._with_loading("Загрузка аудио...", 0.32, AudioManager, self.config.audio, project_root)
        self.audio.apply_settings(self.settings)
        self._draw_loading_screen("Загрузка ассетов...", 0.42)
        self.assets = self._with_loading("Загрузка ассетов...", 0.6, AssetLibrary, project_root, self.config)
        self.leaderboard = self._with_loading(
            "Подготовка рекордов...",
            0.72,
            HighScoreTable,
            self.config.leaderboard.file_path,
            self.config.leaderboard.max_entries,
        )
        self.leaderboard.ensure_storage()
        self.world = self._with_loading(
            "Сборка игрового мира...",
            0.84,
            GameWorld,
            self.config,
            self.audio,
            self.fonts,
            self.assets,
        )
        self.menu_scene = self._with_loading(
            "Подготовка меню...",
            0.9,
            MenuScene,
            self,
            self.world.parallax_background,
            self.world.backdrop,
        )

        self.screens = self._with_loading("Подготовка экранов...", 0.95, ScreenManager, self)
        self._register_screens()
        self._draw_loading_screen("Почти готово...", 0.98)
        self.screens.switch("menu")

    def _desktop_size(self) -> tuple[int, int]:
        desktop_sizes = pygame.display.get_desktop_sizes()
        if desktop_sizes:
            width, height = desktop_sizes[0]
            if width > 0 and height > 0:
                return width, height

        display_info = pygame.display.Info()
        width = display_info.current_w or self.base_size[0]
        height = display_info.current_h or self.base_size[1]
        return max(1, width), max(1, height)

    def _prepare_window_environment(self, borderless_fullscreen: bool) -> None:
        if borderless_fullscreen:
            os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"
            os.environ.pop("SDL_VIDEO_CENTERED", None)
            return

        os.environ.pop("SDL_VIDEO_WINDOW_POS", None)
        os.environ["SDL_VIDEO_CENTERED"] = "1"

    def _create_window_surface(
        self,
        size: tuple[int, int],
        flags: int,
        *,
        reset_display: bool,
    ) -> pygame.Surface:
        if reset_display and pygame.display.get_init():
            pygame.display.quit()
        if not pygame.display.get_init():
            pygame.display.init()
        pygame.display.set_caption(self.config.window.title)
        return pygame.display.set_mode(size, flags)

    def _configure_display(
        self,
        borderless_fullscreen: bool,
        *,
        reset_display: bool,
    ) -> tuple[pygame.Surface, bool]:
        self._prepare_window_environment(borderless_fullscreen)
        size = self._desktop_size() if borderless_fullscreen else self.base_size
        flags = pygame.NOFRAME if borderless_fullscreen else 0
        applied_borderless = borderless_fullscreen
        try:
            surface = self._create_window_surface(size, flags, reset_display=reset_display)
        except pygame.error:
            self._prepare_window_environment(False)
            surface = self._create_window_surface(
                self.base_size,
                0,
                reset_display=reset_display,
            )
            applied_borderless = False

        if applied_borderless:
            surface.fill((0, 0, 0))
            pygame.display.flip()
        return surface, applied_borderless

    def _load_font(self, size: int) -> pygame.font.Font:
        return pygame.font.Font(None, size)

    def _build_fonts(self) -> dict[str, pygame.font.Font]:
        return {
            "title": self._load_font(64),
            "heading": self._load_font(42),
            "body": self._load_font(32),
            "small": self._load_font(24),
        }

    def _register_screens(self) -> None:
        screen_specs = (
            ("menu", MenuScreen(self)),
            ("settings", SettingsScreen(self)),
            ("help", HelpScreen(self)),
            ("scores", HighScoresScreen(self)),
            ("game", GameScreen(self, self.world)),
            ("result", ResultScreen(self)),
            ("name_entry", NameEntryScreen(self)),
        )
        for name, screen in screen_specs:
            self.screens.register(name, screen)

    def _load_loading_background(self) -> pygame.Surface | None:
        image: pygame.Surface | None = None
        for file_name in ("loading_background.jpg", "loading_background.png"):
            image_path = self.project_root / "assets" / "background" / file_name
            if not image_path.exists():
                continue
            try:
                image = pygame.image.load(image_path.as_posix()).convert()
                break
            except pygame.error:
                continue
        if image is None:
            return None

        target_width, target_height = self.base_size
        image_width, image_height = image.get_size()
        if image_width <= 0 or image_height <= 0:
            return None

        scale = max(target_width / image_width, target_height / image_height)
        scaled_size = (
            max(1, int(round(image_width * scale))),
            max(1, int(round(image_height * scale))),
        )
        scaled = pygame.transform.smoothscale(image, scaled_size)
        fitted = pygame.Surface(self.base_size).convert()
        crop_rect = pygame.Rect(
            max(0, (scaled.get_width() - target_width) // 2),
            max(0, (scaled.get_height() - target_height) // 2),
            target_width,
            target_height,
        )
        fitted.blit(scaled, (0, 0), crop_rect)
        return fitted

    def _load_game_logo(self) -> pygame.Surface | None:
        image_path = self.project_root / "assets" / "ui" / "game_logo.png"
        if not image_path.exists():
            return None
        try:
            image = pygame.image.load(image_path.as_posix()).convert_alpha()
        except pygame.error:
            return None

        target_width = 480
        scale = target_width / max(1, image.get_width())
        target_height = max(1, int(round(image.get_height() * scale)))
        return pygame.transform.smoothscale(image, (target_width, target_height))

    def stop(self) -> None:
        self.running = False

    def update_settings(self, settings: UserSettings, *, save: bool = True) -> None:
        normalized = settings.normalized()
        fullscreen_changed = normalized.borderless_fullscreen != self.settings.borderless_fullscreen
        if fullscreen_changed:
            self.window_surface, applied_borderless = self._configure_display(
                normalized.borderless_fullscreen,
                reset_display=True,
            )
            if applied_borderless != normalized.borderless_fullscreen:
                normalized = normalized.updated(borderless_fullscreen=applied_borderless)
            self.surface = pygame.Surface(self.base_size).convert_alpha()
        self.settings = normalized
        self.audio.apply_settings(self.settings)
        if save:
            self.settings_store.save(self.settings)

    def _display_rect(self) -> pygame.Rect:
        window_width, window_height = self.window_surface.get_size()
        virtual_width, virtual_height = self.surface.get_size()
        if (window_width, window_height) == (virtual_width, virtual_height):
            return pygame.Rect(0, 0, window_width, window_height)

        scale = min(
            window_width / max(1, virtual_width),
            window_height / max(1, virtual_height),
        )
        scaled_width = max(1, int(round(virtual_width * scale)))
        scaled_height = max(1, int(round(virtual_height * scale)))
        return pygame.Rect(
            (window_width - scaled_width) // 2,
            (window_height - scaled_height) // 2,
            scaled_width,
            scaled_height,
        )

    def _window_to_virtual(self, position: tuple[int, int]) -> tuple[int, int]:
        display_rect = self._display_rect()
        virtual_width, virtual_height = self.surface.get_size()
        local_x = min(max(position[0] - display_rect.x, 0), max(0, display_rect.width - 1))
        local_y = min(max(position[1] - display_rect.y, 0), max(0, display_rect.height - 1))
        x_position = int(local_x * virtual_width / max(1, display_rect.width))
        y_position = int(local_y * virtual_height / max(1, display_rect.height))
        return (
            max(0, min(virtual_width - 1, x_position)),
            max(0, min(virtual_height - 1, y_position)),
        )

    def _scale_relative_motion(self, delta: tuple[int, int]) -> tuple[int, int]:
        display_rect = self._display_rect()
        virtual_width, virtual_height = self.surface.get_size()
        return (
            int(delta[0] * virtual_width / max(1, display_rect.width)),
            int(delta[1] * virtual_height / max(1, display_rect.height)),
        )

    def _translate_event(self, event: pygame.event.Event) -> pygame.event.Event:
        if event.type not in {pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP}:
            return event

        payload = event.dict.copy()
        if "pos" in payload:
            payload["pos"] = self._window_to_virtual(payload["pos"])
        if "rel" in payload:
            payload["rel"] = self._scale_relative_motion(payload["rel"])
        return pygame.event.Event(event.type, payload)

    def _present_frame(self) -> None:
        display_rect = self._display_rect()
        if display_rect.size == self.surface.get_size() and display_rect.topleft == (0, 0):
            self.window_surface.blit(self.surface, (0, 0))
            pygame.display.flip()
            return

        scaled = pygame.transform.smoothscale(self.surface, display_rect.size)
        self.window_surface.fill((0, 0, 0))
        self.window_surface.blit(scaled, display_rect.topleft)
        pygame.display.flip()

    def _draw_loading_screen(self, message: str, progress: float) -> None:
        pygame.event.pump()
        if self.loading_background is not None:
            self.surface.blit(self.loading_background, (0, 0))
        else:
            self.surface.fill((25, 34, 28))

            top_rect = pygame.Rect(0, 0, self.surface.get_width(), self.surface.get_height() // 2)
            pygame.draw.rect(self.surface, (38, 54, 44), top_rect)
            pygame.draw.circle(self.surface, (92, 128, 98), (self.surface.get_width() - 150, 120), 140)
            pygame.draw.ellipse(self.surface, (56, 84, 53), (-140, self.surface.get_height() - 180, 760, 280))
            pygame.draw.ellipse(self.surface, (63, 94, 58), (420, self.surface.get_height() - 194, 920, 300))

        if self.game_logo is not None:
            logo_rect = self.game_logo.get_rect(topleft=(0, 0))
            self.surface.blit(self.game_logo, logo_rect)

        interface_center_x = self.surface.get_width() // 2
        interface_title_y = self.surface.get_height() - 250
        interface_subtitle_y = self.surface.get_height() - 176
        interface_bar_y = self.surface.get_height() - 114
        interface_percent_y = self.surface.get_height() - 54

        title = render_outlined_text(self._bootstrap_font_title, "MOORHUHN", outline_width=1)
        subtitle = render_outlined_text(self._bootstrap_font_body, message, outline_width=1)
        if self.game_logo is None:
            self.surface.blit(title, title.get_rect(center=(interface_center_x, interface_title_y)))
        self.surface.blit(subtitle, subtitle.get_rect(center=(interface_center_x, interface_subtitle_y)))

        bar_rect = pygame.Rect(interface_center_x - 260, interface_bar_y, 520, 28)
        draw_progress_bar(self.surface, bar_rect, progress, self.config.ui)

        percent_text = render_outlined_text(
            self._bootstrap_font_body,
            f"{int(progress * 100):02d}%",
            outline_width=1,
        )
        self.surface.blit(percent_text, percent_text.get_rect(center=(interface_center_x, interface_percent_y)))
        self._present_frame()

    def _with_loading(self, message: str, progress: float, factory, *args):
        self._draw_loading_screen(message, progress)
        return factory(*args)

    def shutdown(self) -> None:
        if self._shutdown_complete:
            return

        self._shutdown_complete = True
        self.running = False

        try:
            pygame.event.clear()
        except pygame.error:
            pass

        audio = getattr(self, "audio", None)
        if audio is not None:
            try:
                audio.stop_all()
            except pygame.error:
                pass

        world = getattr(self, "world", None)
        if world is not None:
            world.stop_round()

        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.quit()
        except pygame.error:
            pass

        try:
            if pygame.display.get_init():
                pygame.display.quit()
        except pygame.error:
            pass

        pygame.quit()

    def run(self) -> int:
        try:
            while self.running:
                dt_ms = self.clock.tick(self.config.window.fps)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        break
                    translated_event = self._translate_event(event)
                    if self.screens.current is not None:
                        self.screens.current.handle_event(translated_event)

                if self.screens.current is not None:
                    self.screens.current.update(dt_ms)
                    self.screens.current.draw(self.surface)
                self.audio.update()

                self._present_frame()
            return 0
        finally:
            self.shutdown()
