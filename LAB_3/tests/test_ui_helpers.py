from __future__ import annotations

import pygame

from moorhuhn.config.game_config import load_game_config
from moorhuhn.ui.game_screens import NameEntryScreen, ResultScreen
from moorhuhn.ui.menu_screens import HighScoresScreen, MenuScreen
from moorhuhn.ui.screen_core import MenuBackdropScreen, ResultPayload
from moorhuhn.ui.screens import build_help_lines
from moorhuhn.ui.text import render_outlined_text
from moorhuhn.ui.theme import DEFAULT_THEME, draw_accent_button, draw_panel, draw_progress_bar
from moorhuhn.game.entities import RoundResult


def test_render_outlined_text_produces_larger_surface() -> None:
    font = pygame.font.Font(None, 32)
    plain = font.render("MOORHUHN", True, (255, 255, 255))
    outlined = render_outlined_text(font, "MOORHUHN", outline_width=1)

    assert outlined.get_width() > plain.get_width()
    assert outlined.get_height() > plain.get_height()


def test_theme_helpers_draw_visible_content() -> None:
    surface = pygame.Surface((240, 140), pygame.SRCALPHA)

    draw_panel(surface, pygame.Rect(10, 10, 120, 70), DEFAULT_THEME)
    draw_accent_button(surface, pygame.Rect(20, 20, 90, 36), DEFAULT_THEME, hovered=True)
    draw_progress_bar(surface, pygame.Rect(20, 90, 180, 20), 0.5, DEFAULT_THEME)

    assert surface.get_bounding_rect().width > 0


def test_help_lines_cover_all_major_mechanics(project_root) -> None:
    config = load_game_config(project_root / "config" / "game_config.json")
    text = "\n".join(build_help_lines(config))

    assert "Деревья прострелить нельзя" in text
    assert "Перезарядку можно запускать в любой момент" in text
    assert "Курица спавнится по всей ширине карты" in text
    assert "Слои фона двигаются с разной скоростью" in text


def test_menu_backdrop_draws_sign_by_default() -> None:
    calls: list[bool] = []

    class DummyScene:
        def draw(self, _surface: pygame.Surface, *, include_sign: bool = True) -> None:
            calls.append(include_sign)

    screen = MenuBackdropScreen.__new__(MenuBackdropScreen)
    screen.scene = DummyScene()
    screen.draw_menu_scene(pygame.Surface((16, 16)))

    assert calls == [True]


def test_menu_screen_keeps_existing_scene_state(monkeypatch) -> None:
    resets: list[bool] = []
    visibility: list[bool] = []

    class DummyScene:
        def on_enter(self, *, reset: bool = False) -> None:
            resets.append(reset)

    class DummyAudio:
        def play_menu_loop(self) -> None:
            pass

    app = type(
        "DummyApp",
        (),
        {
            "menu_scene": DummyScene(),
            "audio": DummyAudio(),
        },
    )()
    screen = MenuScreen(app)
    monkeypatch.setattr(pygame.mouse, "set_visible", visibility.append)

    screen.on_enter()

    assert visibility == [True]
    assert resets == [False]


def test_result_screen_replay_button_uses_mouse() -> None:
    actions: list[tuple[str, object | None]] = []

    class DummyScene:
        def on_enter(self, *, reset: bool = False) -> None:
            pass

    class DummyAudio:
        def play_menu_loop(self) -> None:
            pass

        def play_ui_hover(self) -> None:
            pass

        def play_ui_confirm(self) -> None:
            pass

    class DummyScreens:
        def switch(self, name: str, **payload: object) -> None:
            actions.append((name, payload.get("payload")))

    app = type(
        "DummyApp",
        (),
        {
            "menu_scene": DummyScene(),
            "audio": DummyAudio(),
            "screens": DummyScreens(),
            "surface": pygame.Surface((1280, 720)),
        },
    )()
    screen = ResultScreen(app)
    screen.handle_menu_scene_event = lambda event: False
    screen.on_enter(payload=ResultPayload(RoundResult(100, 5, 2, 7), False, False))

    replay_rect = screen._replay_button_rect(app.surface)
    screen.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": replay_rect.center},
        )
    )

    assert actions == [("game", None)]


def test_result_screen_save_button_opens_name_entry() -> None:
    actions: list[tuple[str, object | None]] = []

    class DummyScene:
        def on_enter(self, *, reset: bool = False) -> None:
            pass

    class DummyAudio:
        def play_menu_loop(self) -> None:
            pass

        def play_ui_hover(self) -> None:
            pass

        def play_ui_confirm(self) -> None:
            pass

    class DummyScreens:
        def switch(self, name: str, **payload: object) -> None:
            actions.append((name, payload.get("payload")))

    app = type(
        "DummyApp",
        (),
        {
            "menu_scene": DummyScene(),
            "audio": DummyAudio(),
            "screens": DummyScreens(),
            "surface": pygame.Surface((1280, 720)),
        },
    )()
    screen = ResultScreen(app)
    screen.handle_menu_scene_event = lambda event: False
    payload = ResultPayload(RoundResult(180, 9, 1, 10), True, False)
    screen.on_enter(payload=payload)

    save_rect = screen._save_button_rect(app.surface)
    screen.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": save_rect.center},
        )
    )

    assert actions == [("name_entry", payload)]


def test_result_screen_menu_button_resets_menu_scene() -> None:
    actions: list[tuple[str, dict[str, object]]] = []

    class DummyScene:
        def on_enter(self, *, reset: bool = False) -> None:
            pass

    class DummyAudio:
        def play_menu_loop(self) -> None:
            pass

        def play_ui_hover(self) -> None:
            pass

        def play_ui_confirm(self) -> None:
            pass

    class DummyScreens:
        def switch(self, name: str, **payload: object) -> None:
            actions.append((name, payload))

    app = type(
        "DummyApp",
        (),
        {
            "menu_scene": DummyScene(),
            "audio": DummyAudio(),
            "screens": DummyScreens(),
            "surface": pygame.Surface((1280, 720)),
        },
    )()
    screen = ResultScreen(app)
    screen.handle_menu_scene_event = lambda event: False
    screen.on_enter(payload=ResultPayload(RoundResult(100, 5, 2, 7), False, False))

    back_rect = screen._back_button_rect(app.surface)
    screen.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": back_rect.center},
        )
    )

    assert actions == [("menu", {"reset_scene": True})]


def test_result_screen_centers_panel_with_bottom_buttons() -> None:
    class DummyScene:
        def on_enter(self, *, reset: bool = False) -> None:
            pass

    class DummyAudio:
        def play_menu_loop(self) -> None:
            pass

        def play_ui_hover(self) -> None:
            pass

        def play_ui_confirm(self) -> None:
            pass

    app = type(
        "DummyApp",
        (),
        {
            "menu_scene": DummyScene(),
            "audio": DummyAudio(),
            "surface": pygame.Surface((1280, 720)),
        },
    )()
    screen = ResultScreen(app)
    screen.on_enter(payload=ResultPayload(RoundResult(100, 5, 2, 7), False, False))

    panel = screen._panel_rect(app.surface)
    buttons_bottom = screen._back_button_rect(app.surface).bottom
    group_center = (panel.top + buttons_bottom) / 2

    assert group_center == app.surface.get_height() / 2


def test_name_entry_back_button_returns_to_result() -> None:
    actions: list[tuple[str, object | None]] = []

    class DummyScene:
        def on_enter(self, *, reset: bool = False) -> None:
            pass

    class DummyAudio:
        def play_menu_loop(self) -> None:
            pass

        def play_ui_hover(self) -> None:
            pass

        def play_ui_confirm(self) -> None:
            pass

    class DummyScreens:
        def switch(self, name: str, **payload: object) -> None:
            actions.append((name, payload.get("payload")))

    app = type(
        "DummyApp",
        (),
        {
            "menu_scene": DummyScene(),
            "audio": DummyAudio(),
            "screens": DummyScreens(),
            "surface": pygame.Surface((1280, 720)),
        },
    )()
    screen = NameEntryScreen(app)
    screen.handle_menu_scene_event = lambda event: False
    payload = ResultPayload(RoundResult(150, 8, 2, 10), True, False)
    screen.on_enter(payload=payload)

    back_rect = screen._back_button_rect(app.surface)
    screen.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": back_rect.center},
        )
    )

    assert actions == [("result", payload)]


def test_name_entry_save_button_records_score_and_opens_scores() -> None:
    actions: list[str] = []
    saved_scores: list[tuple[str, int]] = []

    class DummyScene:
        def on_enter(self, *, reset: bool = False) -> None:
            pass

    class DummyAudio:
        def play_menu_loop(self) -> None:
            pass

        def play_ui_hover(self) -> None:
            pass

        def play_ui_confirm(self) -> None:
            pass

    class DummyScreens:
        def switch(self, name: str, **payload: object) -> None:
            actions.append(name)

    class DummyLeaderboard:
        def record_score(self, name: str, score: int) -> None:
            saved_scores.append((name, score))

    app = type(
        "DummyApp",
        (),
        {
            "menu_scene": DummyScene(),
            "audio": DummyAudio(),
            "screens": DummyScreens(),
            "leaderboard": DummyLeaderboard(),
            "surface": pygame.Surface((1280, 720)),
        },
    )()
    screen = NameEntryScreen(app)
    screen.handle_menu_scene_event = lambda event: False
    payload = ResultPayload(RoundResult(220, 10, 1, 11), True, False)
    screen.on_enter(payload=payload)

    save_rect = screen._save_button_rect(app.surface)
    screen.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": save_rect.center},
        )
    )

    assert saved_scores == [("PLAYER", 220)]
    assert actions == ["scores"]


def test_highscores_screen_can_reset_menu_scene_on_exit() -> None:
    actions: list[tuple[str, dict[str, object]]] = []

    class DummyScene:
        def on_enter(self, *, reset: bool = False) -> None:
            pass

    class DummyAudio:
        def play_menu_loop(self) -> None:
            pass

        def play_ui_confirm(self) -> None:
            pass

    class DummyLeaderboard:
        def load_entries(self) -> list[object]:
            return []

    class DummyScreens:
        def switch(self, name: str, **payload: object) -> None:
            actions.append((name, payload))

    app = type(
        "DummyApp",
        (),
        {
            "menu_scene": DummyScene(),
            "audio": DummyAudio(),
            "leaderboard": DummyLeaderboard(),
            "screens": DummyScreens(),
        },
    )()
    screen = HighScoresScreen(app)
    screen.handle_menu_scene_event = lambda event: False
    screen.on_enter(reset_menu_scene=True)
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))

    assert actions == [("menu", {"reset_scene": True})]
