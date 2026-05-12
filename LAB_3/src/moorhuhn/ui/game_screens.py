from __future__ import annotations

import pygame

from ..game.entities import RoundResult
from ..game.world import GameWorld
from .screen_core import BaseScreen, MenuBackdropScreen, ResultPayload
from .text import render_outlined_text
from .theme import draw_accent_button, draw_panel


class GameScreen(BaseScreen):
    def __init__(self, app, world: GameWorld) -> None:
        super().__init__(app)
        self.world = world
        self.transitioned = False

    def on_enter(self, **_: object) -> None:
        pygame.mouse.set_visible(False)
        self.app.audio.play_game_loop()
        self.transitioned = False
        self.world.start_round()

    def on_leave(self) -> None:
        self.world.stop_round()
        pygame.mouse.set_visible(True)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.audio.play_ui_confirm()
                self.world.toggle_pause()
                pygame.mouse.set_visible(self.world.paused)
                return
            if self.world.paused:
                return
        if self.world.paused and event.type == pygame.MOUSEMOTION:
            self.world.set_pause_hover(event.pos)
            return
        if self.world.paused and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = self.world.get_pause_action(event.pos)
            if action == "resume":
                self.app.audio.play_ui_confirm()
                self.world.toggle_pause()
                pygame.mouse.set_visible(False)
                return
            if action == "menu":
                self.app.audio.play_ui_confirm()
                self.app.screens.switch("menu", reset_scene=True)
                return
        self.world.handle_event(event)

    def update(self, dt_ms: int) -> None:
        self.world.update(dt_ms)
        if self.world.finished and self.world.result and not self.transitioned:
            qualified, new_champion = self.app.leaderboard.score_status(self.world.result.score)
            self.transitioned = True
            self.app.screens.switch(
                "result",
                payload=ResultPayload(
                    result=self.world.result,
                    qualified=qualified,
                    new_champion=new_champion,
                ),
            )

    def draw(self, surface: pygame.Surface) -> None:
        self.world.draw(surface)


class ResultScreen(MenuBackdropScreen):
    _panel_side_margin = 210
    _panel_vertical_margin = 100
    _action_gap = 18
    _action_height = 56

    def __init__(self, app) -> None:
        super().__init__(app)
        self.payload = ResultPayload(RoundResult(0, 0, 0, 0), False, False)
        self.hovered_action: str | None = None

    def on_enter(self, payload: ResultPayload, **_: object) -> None:
        super().on_enter()
        self.payload = payload
        self.hovered_action = None

    def _panel_rect(self, surface: pygame.Surface) -> pygame.Rect:
        width = surface.get_width() - self._panel_side_margin * 2
        height = surface.get_height() - self._panel_vertical_margin * 2
        total_height = height + self._action_gap + self._action_height
        top = max(24, (surface.get_height() - total_height) // 2)
        return pygame.Rect(self._panel_side_margin, top, width, height)

    def _back_button_rect(self, surface: pygame.Surface) -> pygame.Rect:
        panel = self._panel_rect(surface)
        return pygame.Rect(panel.x, panel.bottom + self._action_gap, 220, self._action_height)

    def _replay_button_rect(self, surface: pygame.Surface) -> pygame.Rect:
        panel = self._panel_rect(surface)
        return pygame.Rect(panel.right - 220, panel.bottom + self._action_gap, 220, self._action_height)

    def _save_button_rect(self, surface: pygame.Surface) -> pygame.Rect:
        panel = self._panel_rect(surface)
        return pygame.Rect(panel.centerx - 190, panel.bottom - 106, 380, 56)

    def _action_rects(self) -> dict[str, pygame.Rect]:
        rects = {
            "menu": self._back_button_rect(self.app.surface),
            "game": self._replay_button_rect(self.app.surface),
        }
        if self.payload.qualified:
            rects["save"] = self._save_button_rect(self.app.surface)
        return rects

    def _action_at(self, position: tuple[int, int]) -> str | None:
        for action, rect in self._action_rects().items():
            if rect.collidepoint(position):
                return action
        return None

    def _set_hovered_action(self, action: str | None) -> None:
        if action == self.hovered_action:
            return
        self.hovered_action = action
        if action is not None:
            self.app.audio.play_ui_hover()

    def _activate_action(self, action: str) -> None:
        self.app.audio.play_ui_confirm()
        if action == "game":
            self.app.screens.switch("game")
        elif action == "menu":
            self.app.screens.switch("menu", reset_scene=True)
        elif action == "save" and self.payload.qualified:
            self.app.screens.switch("name_entry", payload=self.payload)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.handle_menu_scene_event(event):
            return
        if event.type == pygame.MOUSEMOTION:
            self._set_hovered_action(self._action_at(event.pos))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = self._action_at(event.pos)
            if action is not None:
                self._activate_action(action)

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_menu_scene(surface)
        panel = self._panel_rect(surface)
        draw_panel(surface, panel, self.app.config.ui)

        title = render_outlined_text(self.app.fonts["title"], "Результаты раунда", outline_width=1)
        surface.blit(title, title.get_rect(center=(surface.get_width() // 2, panel.y + 54)))

        result = self.payload.result
        lines = [
            f"Очки: {result.score}",
            f"Попадания: {result.hits}",
            f"Промахи: {result.misses}",
            f"Точность: {result.rounded_accuracy}%",
        ]
        y_position = panel.y + 130
        for line in lines:
            text = render_outlined_text(self.app.fonts["heading"], line)
            surface.blit(text, text.get_rect(center=(surface.get_width() // 2, y_position)))
            y_position += 54

        if self.payload.new_champion:
            message = "Поздравление: это новый рекорд таблицы."
        elif self.payload.qualified:
            message = "Результат попадает в таблицу рекордов."
        else:
            message = "Результат не вошёл в таблицу рекордов."
        message_text = render_outlined_text(self.app.fonts["body"], message)
        surface.blit(message_text, message_text.get_rect(center=(surface.get_width() // 2, y_position + 8)))

        if self.payload.qualified:
            save_rect = self._save_button_rect(surface)
            draw_accent_button(
                surface,
                save_rect,
                self.app.config.ui,
                hovered=self.hovered_action == "save",
                border_radius=self.app.config.ui.button_small_border_radius + 2,
            )
            save_text = render_outlined_text(self.app.fonts["body"], "Сохранить рекорд")
            surface.blit(save_text, save_text.get_rect(center=save_rect.center))

        actions = (
            ("menu", self._back_button_rect(surface), "Назад"),
            ("game", self._replay_button_rect(surface), "Заново"),
        )
        for action, rect, label in actions:
            draw_accent_button(
                surface,
                rect,
                self.app.config.ui,
                hovered=self.hovered_action == action,
                border_radius=self.app.config.ui.button_small_border_radius + 2,
            )
            text = render_outlined_text(self.app.fonts["body"], label)
            surface.blit(text, text.get_rect(center=rect.center))


class NameEntryScreen(MenuBackdropScreen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.payload = ResultPayload(RoundResult(0, 0, 0, 0), False, False)
        self.name = ""
        self.hovered_action: str | None = None

    def on_enter(self, payload: ResultPayload, **_: object) -> None:
        super().on_enter()
        self.payload = payload
        self.name = ""
        self.hovered_action = None

    def _panel_rect(self, surface: pygame.Surface) -> pygame.Rect:
        return pygame.Rect(250, 160, surface.get_width() - 500, surface.get_height() - 320)

    def _input_rect(self, surface: pygame.Surface) -> pygame.Rect:
        panel = self._panel_rect(surface)
        return pygame.Rect(panel.x + 120, panel.y + 190, panel.width - 240, 72)

    def _back_button_rect(self, surface: pygame.Surface) -> pygame.Rect:
        panel = self._panel_rect(surface)
        return pygame.Rect(panel.x, panel.bottom + 18, 220, 56)

    def _save_button_rect(self, surface: pygame.Surface) -> pygame.Rect:
        panel = self._panel_rect(surface)
        return pygame.Rect(panel.right - 220, panel.bottom + 18, 220, 56)

    def _action_at(self, position: tuple[int, int]) -> str | None:
        action_rects = {
            "back": self._back_button_rect(self.app.surface),
            "save": self._save_button_rect(self.app.surface),
        }
        for action, rect in action_rects.items():
            if rect.collidepoint(position):
                return action
        return None

    def _set_hovered_action(self, action: str | None) -> None:
        if action == self.hovered_action:
            return
        self.hovered_action = action
        if action is not None:
            self.app.audio.play_ui_hover()

    def _saved_name(self) -> str:
        return self.name.strip().upper() or "PLAYER"

    def _save_score(self) -> None:
        self.app.leaderboard.record_score(self._saved_name(), self.payload.result.score)

    def _activate_action(self, action: str) -> None:
        self.app.audio.play_ui_confirm()
        if action == "back":
            self.app.screens.switch("result", payload=self.payload)
        elif action == "save":
            self._save_score()
            self.app.screens.switch("scores", reset_menu_scene=True)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.handle_menu_scene_event(event):
            return
        if event.type == pygame.MOUSEMOTION:
            self._set_hovered_action(self._action_at(event.pos))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = self._action_at(event.pos)
            if action is not None:
                self._activate_action(action)
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self._activate_action("back")
            return
        if event.key == pygame.K_BACKSPACE:
            self.name = self.name[:-1]
            return
        if event.key == pygame.K_RETURN:
            self._activate_action("save")
            return
        if event.unicode and len(self.name) < 12 and (
            event.unicode.isalnum() or event.unicode in {"_", "-"}
        ):
            self.name += event.unicode.upper()

    def draw(self, surface: pygame.Surface) -> None:
        self.draw_menu_scene(surface)
        panel = self._panel_rect(surface)
        draw_panel(surface, panel, self.app.config.ui)

        title = render_outlined_text(self.app.fonts["title"], "Введите имя", outline_width=1)
        surface.blit(title, title.get_rect(center=(surface.get_width() // 2, panel.y + 60)))

        score_text = render_outlined_text(self.app.fonts["heading"], f"Очки: {self.payload.result.score}")
        surface.blit(score_text, score_text.get_rect(center=(surface.get_width() // 2, panel.y + 130)))

        input_rect = self._input_rect(surface)
        draw_accent_button(
            surface,
            input_rect,
            self.app.config.ui,
            hovered=bool(self.name),
            border_radius=self.app.config.ui.button_small_border_radius + 2,
        )
        caption = render_outlined_text(self.app.fonts["body"], self.name or "PLAYER")
        surface.blit(caption, caption.get_rect(center=input_rect.center))

        hint = render_outlined_text(self.app.fonts["body"], "Допустимо до 12 символов: буквы, цифры, _, -")
        surface.blit(hint, hint.get_rect(center=(surface.get_width() // 2, input_rect.bottom + 52)))

        actions = (
            ("back", self._back_button_rect(surface), "Назад"),
            ("save", self._save_button_rect(surface), "Сохранить"),
        )
        for action, rect, label in actions:
            draw_accent_button(
                surface,
                rect,
                self.app.config.ui,
                hovered=self.hovered_action == action,
                border_radius=self.app.config.ui.button_small_border_radius + 2,
            )
            text = render_outlined_text(self.app.fonts["body"], label)
            surface.blit(text, text.get_rect(center=rect.center))
