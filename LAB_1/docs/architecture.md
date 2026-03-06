# Архитектура и модель классов

## 1. Общая архитектура

Проект построен в 3 слоя:

- `domain` - бизнес-модель, инварианты и правила.
- `application` - сервисный слой (use-case API), через который работает интерфейс.
- `cli` - парсинг команд, роутинг, взаимодействие с пользователем.

Направление зависимостей:

- `cli` -> `application` -> `domain`

`domain` не зависит от верхних слоев.

## 2. Domain-слой: классы, поля, ответственность

### `VideoFile` (`domain/video_file.py`)

Поля:

- `title: str`
- `format_ext: str`
- `duration_seconds: int`

Ответственность:

- хранит данные о видео;
- валидирует длительность в `__post_init__` (`duration_seconds > 0`), иначе `InvalidDurationError`.

Взаимодействия:

- создается в `PlayerService.add_video()`;
- хранится в `VideoPlayer.library` и `Playlist.videos`.

### `SupportedFormats` (`domain/supported_formats.py`)

Поля:

- `formats: set[str]` (по умолчанию `{"mp4", "avi", "mkv"}`)

Методы:

- `is_supported(format_ext)` - проверка с нормализацией (`lower()`, удаление точки).
- `list_formats()` - отсортированный список форматов.

Взаимодействия:

- используется `VideoPlayer.add_video()` для проверки формата;
- используется `VideoPlayer.list_supported_formats()`.

### `PlaybackStatus`, `PlaybackControl` (`domain/playback.py`)

- `PlaybackStatus`: `STOPPED`, `PLAYING`, `PAUSED`.
- `PlaybackControl.status` хранит текущее состояние.

Методы:

- `play()` -> `PLAYING`
- `pause()` -> `PAUSED` только если было `PLAYING`
- `stop()` -> `STOPPED`

Взаимодействия:

- управляется из `VideoPlayer.play/pause/stop`.

### `SoundSettings`, `DisplaySettings` (`domain/settings.py`)

Поля:

- `SoundSettings.volume: int = 50`
- `DisplaySettings.brightness: int = 50`

Методы:

- `set_volume(value)` - допустим `0..100`, иначе `InvalidVolumeError`.
- `set_brightness(value)` - допустим `0..100`, иначе `InvalidBrightnessError`.

Взаимодействия:

- вызываются из `VideoPlayer.set_volume/set_brightness`.

### `Playlist` (`domain/playlist.py`)

Поля:

- `name: str`
- `videos: list[VideoFile]`

Методы:

- `add_video(video)`
- `remove_video(title) -> bool`

Взаимодействия:

- создается и управляется только через `VideoPlayer`.

### `VideoPlayer` (`domain/player.py`) - корневой агрегат

Поля состояния:

- `library: list[VideoFile]`
- `playlists: list[Playlist]`
- `current_video: VideoFile | None`
- `sound: SoundSettings`
- `display: DisplaySettings`
- `formats: SupportedFormats`
- `playback: PlaybackControl`

Основные операции:

- библиотека: `add_video`, `list_videos`, `remove_video`, `select_video`
- воспроизведение: `play`, `pause`, `stop`
- настройки: `set_volume`, `set_brightness`
- плейлисты: `create_playlist`, `list_playlists`, `get_playlist`, `add_video_to_playlist`, `remove_video_from_playlist`, `select_video_from_playlist`
- состояние/справка: `status`, `list_supported_formats`

Ключевые правила в `VideoPlayer`:

- запрет дубликатов названий видео (`DuplicateVideoError`);
- запрет неподдерживаемого формата (`UnsupportedFormatError`);
- `play()` невозможен без `current_video` (`PlaybackError`);
- при удалении видео из библиотеки оно удаляется из всех плейлистов;
- если удаленное видео было текущим, `current_video = None`, состояние -> `stopped`.

### Исключения домена (`domain/exceptions.py`)

Используются типизированные ошибки:

- `UnsupportedFormatError`
- `VideoNotFoundError`
- `DuplicateVideoError`
- `PlaylistNotFoundError`
- `PlaylistAlreadyExistsError`
- `InvalidVolumeError`
- `InvalidBrightnessError`
- `InvalidDurationError`
- `PlaybackError`

Все наследуются от `DomainError`.

## 3. Application-слой

### `PlayerService` (`application/services.py`)

Поля:

- `player: VideoPlayer`

Роль:

- предоставляет стабильный API для CLI;
- создает доменные объекты (`VideoFile`) из пользовательского ввода;
- делегирует бизнес-операции в `VideoPlayer`.

Важная деталь:

- в `add_video` формат нормализуется в нижний регистр (`format_ext.lower()`).

## 4. CLI-слой

### `Command` (`cli/command.py`)

- DTO команды: `name: str`, `args: list[str]`.

### `CommandParser` (`cli/parser.py`)

- парсит строку в `Command` через `shlex.split`;
- поддерживает кавычки (`"my demo"`);
- пустой ввод/ошибка синтаксиса -> `CommandParseError`.

### `CommandRouter` (`cli/router.py`)

- реестр обработчиков `dict[str, CommandHandler]`;
- `dispatch(command)` вызывает обработчик по имени;
- неизвестная команда -> `UnknownCommandError`.

### `ConsoleIO` (`cli/console_io.py`)

- абстракция ввода/вывода: `read_line`, `print_line`, `print_error`.

### `HelpProvider` (`cli/help_provider.py`)

- возвращает текст справки и список поддерживаемых форматов.

### `CliApp` (`cli/app.py`)

Роль:

- главный цикл приложения (`run`);
- регистрация команд и обработчиков;
- валидация аргументов;
- вызов `PlayerService`;
- перехват ошибок (`CliError`, `DomainError`, `CommandParseError`) без аварийного завершения.

Связи:

- `CliApp` использует `ConsoleIO`, `CommandParser`, `CommandRouter`, `PlayerService`.
- Обработчики в `CliApp` вызывают методы `PlayerService`, а тот - `VideoPlayer`.

## 5. Поток выполнения команды

1. Пользователь вводит строку в CLI.
2. `CommandParser` преобразует строку в `Command`.
3. `CommandRouter` находит обработчик.
4. Обработчик `CliApp` валидирует аргументы и вызывает `PlayerService`.
5. `PlayerService` выполняет операцию через `VideoPlayer`.
6. Результат или ошибка выводится через `ConsoleIO`.
