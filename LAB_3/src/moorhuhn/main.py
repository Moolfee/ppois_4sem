from __future__ import annotations

from pathlib import Path

import pygame

from .app.application import MoorhuhnApp
from .config.game_config import ConfigError


def _shutdown_pygame() -> None:
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


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    app: MoorhuhnApp | None = None

    try:
        app = MoorhuhnApp(project_root)
        return app.run()
    except (ConfigError, OSError, pygame.error) as exc:
        print(f"Failed to start LAB_3 Moorhuhn: {exc}")
        return 1
    finally:
        if app is not None:
            app.shutdown()
        else:
            _shutdown_pygame()
