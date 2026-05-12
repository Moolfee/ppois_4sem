from __future__ import annotations

import pygame

from ..config.game_config import GameConfig
from .text import render_outlined_text


def build_help_lines(config: GameConfig) -> list[str]:
    round_seconds = config.gameplay.round_time_seconds
    magazine_size = config.weapon.magazine_size
    reload_seconds = config.weapon.reload_time_ms / 1000
    cooldown_seconds = config.weapon.shot_cooldown_ms / 1000
    far_points = config.targets["far"].points
    mid_points = config.targets["mid"].points
    near_points = config.targets["near"].points
    foreground_enemy = config.foreground_enemy
    playfield_factor = config.gameplay.playfield_width_factor
    bullet_hole_min, bullet_hole_max = config.effects.bullet_hole_lifetime_ms

    return [
        "Правила и цель:",
        f"Раунд длится {round_seconds} секунд. За это время нужно набрать максимум очков.",
        "Побеждает не выживание, а точный и быстрый набор очков по движущимся целям.",
        "Промахи очки не отнимают, но ухудшают итоговую точность раунда.",
        "",
        "Обычные цели:",
        f"Ближний план: {near_points} очков, крупнее, летит ниже и заметнее.",
        f"Средний план: {mid_points} очков, средний размер и скорость.",
        f"Дальний план: {far_points} очков, мельче, сложнее, но выгоднее по очкам.",
        "Птицы летят в обе стороны, а попадание засчитывается только по живой цели.",
        "",
        "Особая курица:",
        (
            f"Редкая вылазящая курица приносит {foreground_enemy.points} очков."
            if foreground_enemy is not None
            else "Редкая вылазящая курица может появляться отдельно от обычных целей."
        ),
        (
            "Она появляется снизу и держится на экране от "
            f"{foreground_enemy.visible_time_ms[0] / 1000:.1f} до {foreground_enemy.visible_time_ms[1] / 1000:.1f} сек."
            if foreground_enemy is not None
            else "Она появляется снизу и вскоре исчезает, если не попасть."
        ),
        "Курица спавнится по всей ширине карты, поэтому иногда камеру нужно дотянуть до неё.",
        "",
        "Оружие и перезарядка:",
        f"В магазине {magazine_size} патронов.",
        f"Задержка между выстрелами около {cooldown_seconds:.2f} сек.",
        f"Ручная перезарядка занимает около {reload_seconds:.2f} сек.",
        "Перезарядку можно запускать в любой момент, магазин дозаряжается до полного.",
        "Новые патроны во время перезарядки возвращаются справа налево.",
        "",
        "Камера и фон:",
        f"Игровое поле шире экрана примерно в {playfield_factor:.2f} раза.",
        "Если увести прицел к левому или правому краю, камера начнёт панорамировать сцену.",
        "Слои фона двигаются с разной скоростью: дальние слабее, ближние сильнее.",
        "",
        "Попадания и окружение:",
        "Деревья прострелить нельзя: выстрел по стволу считается промахом.",
        "Дырки от промахов остаются на том слое, в который попал выстрел.",
        f"Следы живут случайное время от {bullet_hole_min / 1000:.0f} до {bullet_hole_max / 1000:.0f} сек.",
        "На дальних слоях дырки меньше, на ближних больше.",
        "",
        "Управление:",
        "ЛКМ - выстрел",
        "R или ПКМ - ручная перезарядка",
        "Esc - пауза",
        "В паузе используются экранные кнопки, а не горячие клавиши.",
        "",
        "Экраны после раунда:",
        "После завершения раунда показываются очки, попадания, промахи и точность.",
        "Если результат проходит в таблицу, можно ввести имя и сохранить рекорд.",
        "",
        "Esc / Enter / Backspace - назад из справки",
    ]


def wrap_outlined_text(font: object, text: str, max_width: int) -> list[pygame.Surface]:
    if not text:
        return [render_outlined_text(font, "", outline_width=1)]

    words = text.split()
    lines: list[str] = []
    current_line = words[0]

    for word in words[1:]:
        candidate = f"{current_line} {word}"
        if render_outlined_text(font, candidate, outline_width=1).get_width() <= max_width:
            current_line = candidate
            continue
        lines.append(current_line)
        current_line = word

    lines.append(current_line)
    return [render_outlined_text(font, line, outline_width=1) for line in lines]
