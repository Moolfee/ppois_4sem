from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from ..game.entities import RoundResult

if TYPE_CHECKING:
    from ..app.application import MoorhuhnApp


@dataclass(slots=True)
class ResultPayload:
    result: RoundResult
    qualified: bool
    new_champion: bool


@dataclass(frozen=True, slots=True)
class SettingOption:
    key: str
    label: str
    is_toggle: bool = False


SETTING_OPTIONS = (
    SettingOption("master_volume", "Общая громкость"),
    SettingOption("music_volume", "Музыка"),
    SettingOption("gameplay_sfx_volume", "Эффекты игры"),
    SettingOption("weapon_sfx_volume", "Эффекты оружия"),
    SettingOption("ui_sfx_volume", "Звуки интерфейса"),
    SettingOption("borderless_fullscreen", "Безрамочный полный экран", is_toggle=True),
)


class BaseScreen:
    def __init__(self, app: "MoorhuhnApp") -> None:
        self.app = app

    def on_enter(self, **_: object) -> None:
        pass

    def on_leave(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt_ms: int) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        raise NotImplementedError


class MenuBackdropScreen(BaseScreen):
    def __init__(self, app: "MoorhuhnApp") -> None:
        super().__init__(app)
        self.scene = app.menu_scene

    def on_enter(self, *, reset_scene: bool = False, **_: object) -> None:
        pygame.mouse.set_visible(True)
        self.app.audio.play_menu_loop()
        self.scene.on_enter(reset=reset_scene)

    def update(self, dt_ms: int) -> None:
        self.scene.update(dt_ms)

    def draw_menu_scene(self, surface: pygame.Surface, *, include_sign: bool = True) -> None:
        self.scene.draw(surface, include_sign=include_sign)

    def handle_menu_scene_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.scene.handle_mouse_motion(event.pos)
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.scene.chicken.handle_click(event.pos):
                self.app.audio.play_hit()
                return True
        return False


class ScreenManager:
    def __init__(self, app: "MoorhuhnApp") -> None:
        self.app = app
        self.screens: dict[str, BaseScreen] = {}
        self.current: BaseScreen | None = None

    def register(self, name: str, screen: BaseScreen) -> None:
        self.screens[name] = screen

    def switch(self, name: str, **payload: object) -> None:
        if self.current is not None:
            self.current.on_leave()
        self.current = self.screens[name]
        self.current.on_enter(**payload)
