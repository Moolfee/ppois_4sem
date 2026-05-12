from __future__ import annotations

import pygame

SPAWN_EVENTS = {
    "near": pygame.USEREVENT + 1,
    "mid": pygame.USEREVENT + 2,
    "far": pygame.USEREVENT + 3,
}
EVENT_TO_DEPTH = {event_type: depth for depth, event_type in SPAWN_EVENTS.items()}
RELOAD_COMPLETE_EVENT = pygame.USEREVENT + 4
FOREGROUND_ENEMY_EVENT = pygame.USEREVENT + 5
