# Запуск, тестирование, покрытие и команды CLI

## 1. Запуск приложения

Из директории `LAB_1`:

```bash
PYTHONPATH=src python3 -m video_player_cli.main
```

## 2. Запуск тестов

Из директории `LAB_1`:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

Что покрывают тесты:

- `tests/unit/test_parser.py` - парсер команд (`CommandParser`);
- `tests/unit/test_player_service.py` - сервис + доменные сценарии;
- `tests/unit/test_supported_formats.py` - нормализация форматов;
- `tests/unit/test_settings.py` - валидация громкости/яркости;
- `tests/integration/test_cli_app.py` - сквозные CLI-сценарии.

Проверка покрытия программы:

```bash
PYTHONPATH=src .venv/bin/python -m pytest --cov=src/video_player_cli --cov-report=term
```



## 3. Проверка синтаксиса

```bash
python3 -m compileall src tests
```

## 4. Полный список команд

### Общие

- `help` - показать справку.
- `exit` - завершить приложение.
- `status` - текущее состояние (выбранное видео, playback, volume, brightness, размер библиотеки, число плейлистов).

### Управление воспроизведением

- `play` - начать воспроизведение выбранного видео.
- `pause` - поставить на паузу.
- `stop` - остановить воспроизведение.

### Форматы

- `formats list` - список поддерживаемых форматов.

### Видео

- `video add <title> <format> <duration_seconds>` - добавить видео.
- `video list` - список видео в библиотеке.
- `video select <title>` - выбрать текущее видео.
- `video remove <title>` - удалить видео.

Эффекты `video remove`:

- удаляет видео из библиотеки;
- удаляет это видео из всех плейлистов;
- если видео было текущим, сбрасывает выбор и останавливает воспроизведение.

### Плейлисты

- `playlist create <name>` - создать плейлист.
- `playlist list` - список плейлистов.
- `playlist add <name> <video_title>` - добавить видео в плейлист.
- `playlist remove <name> <video_title>` - удалить видео из плейлиста.
- `playlist show <name>` - показать содержимое плейлиста.
- `playlist select <name> <video_title>` - выбрать видео из плейлиста как текущее.

### Настройки

- `volume set <0-100>` - установить громкость.
- `brightness set <0-100>` - установить яркость.

## 5. Типовые ошибки и причины

- `Usage: ...` - неверное количество аргументов или неверный формат команды.
- `Unknown command. Type 'help'.` - неизвестная команда.
- `... must be an integer` - ожидалось целое число.
- `duration_seconds must be > 0` - длительность видео должна быть положительной.
- `Unsupported format: ...` - формат не поддерживается.
- `Video not found: ...` / `Playlist not found: ...` - объект не найден.
- `Volume must be in range 0..100` / `Brightness must be in range 0..100` - выход за границы значений.
