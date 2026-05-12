from __future__ import annotations

import pygame
import pygame.freetype

TEXT_FILL = (255, 255, 255)
TEXT_OUTLINE = (0, 0, 0)


def _render_text_surface(font: object, text: str, color: tuple[int, int, int]) -> pygame.Surface:
    if isinstance(font, pygame.freetype.Font):
        surface, _ = font.render(text, fgcolor=color, bgcolor=None)
        return surface
    if isinstance(font, pygame.font.Font):
        return font.render(text, True, color)
    raise TypeError(f"Unsupported font type: {type(font)!r}")


def render_outlined_text(
    font: object,
    text: str,
    *,
    outline_width: int = 1,
) -> pygame.Surface:
    base = _render_text_surface(font, text, TEXT_FILL)
    if outline_width <= 0:
        return base

    outline = _render_text_surface(font, text, TEXT_OUTLINE)
    result = pygame.Surface(
        (base.get_width() + outline_width * 2, base.get_height() + outline_width * 2),
        pygame.SRCALPHA,
    )

    for offset_x in range(-outline_width, outline_width + 1):
        for offset_y in range(-outline_width, outline_width + 1):
            if offset_x == 0 and offset_y == 0:
                continue
            if offset_x * offset_x + offset_y * offset_y > outline_width * outline_width + 1:
                continue
            result.blit(outline, (offset_x + outline_width, offset_y + outline_width))

    result.blit(base, (outline_width, outline_width))
    return result
