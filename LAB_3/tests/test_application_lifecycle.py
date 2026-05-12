from __future__ import annotations

import pygame

import moorhuhn.main as moorhuhn_main
from moorhuhn.app.application import MoorhuhnApp


class _DummyAudio:
    def __init__(self) -> None:
        self.stop_calls = 0

    def stop_all(self) -> None:
        self.stop_calls += 1


class _DummyWorld:
    def __init__(self) -> None:
        self.stop_calls = 0

    def stop_round(self) -> None:
        self.stop_calls += 1


def test_app_shutdown_is_idempotent(monkeypatch) -> None:
    app = MoorhuhnApp.__new__(MoorhuhnApp)
    app._shutdown_complete = False
    app.running = True
    app.audio = _DummyAudio()
    app.world = _DummyWorld()

    lifecycle_calls: list[str] = []

    monkeypatch.setattr(pygame.event, "clear", lambda: lifecycle_calls.append("event_clear"))
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: True)
    monkeypatch.setattr(pygame.mixer, "quit", lambda: lifecycle_calls.append("mixer_quit"))
    monkeypatch.setattr(pygame.display, "get_init", lambda: True)
    monkeypatch.setattr(pygame.display, "quit", lambda: lifecycle_calls.append("display_quit"))
    monkeypatch.setattr(pygame, "quit", lambda: lifecycle_calls.append("pygame_quit"))

    app.shutdown()
    app.shutdown()

    assert app.running is False
    assert app.audio.stop_calls == 1
    assert app.world.stop_calls == 1
    assert lifecycle_calls.count("event_clear") == 1
    assert lifecycle_calls.count("mixer_quit") == 1
    assert lifecycle_calls.count("display_quit") == 1
    assert lifecycle_calls.count("pygame_quit") == 1


def test_main_shutdowns_pygame_when_app_creation_fails(monkeypatch, capsys) -> None:
    cleanup_calls: list[str] = []

    def _raise_on_create(*_args, **_kwargs):
        raise pygame.error("display init failed")

    monkeypatch.setattr(moorhuhn_main, "MoorhuhnApp", _raise_on_create)
    monkeypatch.setattr(moorhuhn_main, "_shutdown_pygame", lambda: cleanup_calls.append("shutdown"))

    assert moorhuhn_main.main() == 1
    assert cleanup_calls == ["shutdown"]
    assert "display init failed" in capsys.readouterr().out


def test_display_rect_preserves_aspect_ratio() -> None:
    app = MoorhuhnApp.__new__(MoorhuhnApp)
    app.window_surface = pygame.Surface((1600, 1200))
    app.surface = pygame.Surface((1280, 720))

    rect = app._display_rect()

    assert rect.size == (1600, 900)
    assert rect.topleft == (0, 150)


def test_window_to_virtual_accounts_for_letterboxing() -> None:
    app = MoorhuhnApp.__new__(MoorhuhnApp)
    app.window_surface = pygame.Surface((1600, 1200))
    app.surface = pygame.Surface((1280, 720))

    assert app._window_to_virtual((0, 0)) == (0, 0)
    assert app._window_to_virtual((800, 600)) == (640, 360)
