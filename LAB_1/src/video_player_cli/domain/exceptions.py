class DomainError(Exception):
    """Базовая ошибка доменной логики."""


class UnsupportedFormatError(DomainError):
    """Формат файла не поддерживается."""


class VideoNotFoundError(DomainError):
    """Видеофайл не найден."""


class DuplicateVideoError(DomainError):
    """Видеофайл с таким названием уже существует."""


class PlaylistNotFoundError(DomainError):
    """Плейлист не найден."""


class PlaylistAlreadyExistsError(DomainError):
    """Плейлист с таким названием уже существует."""


class InvalidVolumeError(DomainError):
    """Некорректное значение громкости."""


class InvalidBrightnessError(DomainError):
    """Некорректное значение яркости."""


class PlaybackError(DomainError):
    """Некорректная операция воспроизведения."""
