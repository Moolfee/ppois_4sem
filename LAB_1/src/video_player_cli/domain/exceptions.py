class DomainError(Exception):
    """Базовая ошибка доменной логики."""

    default_message = "Domain error"

    def __init__(self, message: str | None = None, **context: str | int) -> None:
        self.message = message or self.default_message
        self.context = context
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class UnsupportedFormatError(DomainError):
    """Формат файла не поддерживается."""

    default_message = "Unsupported format"

    @classmethod
    def for_format(cls, format_ext: str) -> "UnsupportedFormatError":
        return cls(f"{cls.default_message}: {format_ext}", format_ext=format_ext)


class VideoNotFoundError(DomainError):
    """Видеофайл не найден."""

    default_message = "Video not found"

    @classmethod
    def for_title(cls, title: str) -> "VideoNotFoundError":
        return cls(f"{cls.default_message}: {title}", title=title)

    @classmethod
    def for_playlist_video(
        cls, playlist_name: str, video_title: str
    ) -> "VideoNotFoundError":
        return cls(
            f"{cls.default_message} in playlist '{playlist_name}': {video_title}",
            playlist=playlist_name,
            title=video_title,
        )


class DuplicateVideoError(DomainError):
    """Видеофайл с таким названием уже существует."""

    default_message = "Video already exists"

    @classmethod
    def for_title(cls, title: str) -> "DuplicateVideoError":
        return cls(f"{cls.default_message}: {title}", title=title)


class PlaylistNotFoundError(DomainError):
    """Плейлист не найден."""

    default_message = "Playlist not found"

    @classmethod
    def for_name(cls, name: str) -> "PlaylistNotFoundError":
        return cls(f"{cls.default_message}: {name}", playlist=name)


class PlaylistAlreadyExistsError(DomainError):
    """Плейлист с таким названием уже существует."""

    default_message = "Playlist already exists"

    @classmethod
    def for_name(cls, name: str) -> "PlaylistAlreadyExistsError":
        return cls(f"{cls.default_message}: {name}", playlist=name)


class InvalidVolumeError(DomainError):
    """Некорректное значение громкости."""

    default_message = "Volume must be in range 0..100"

    @classmethod
    def for_value(cls, value: int) -> "InvalidVolumeError":
        return cls(cls.default_message, value=value)


class InvalidBrightnessError(DomainError):
    """Некорректное значение яркости."""

    default_message = "Brightness must be in range 0..100"

    @classmethod
    def for_value(cls, value: int) -> "InvalidBrightnessError":
        return cls(cls.default_message, value=value)


class InvalidDurationError(DomainError):
    """Некорректная длительность видео."""

    default_message = "duration_seconds must be > 0"

    @classmethod
    def for_value(cls, value: int) -> "InvalidDurationError":
        return cls(cls.default_message, value=value)


class PlaybackError(DomainError):
    """Некорректная операция воспроизведения."""

    default_message = "Playback operation is invalid"

    @classmethod
    def no_selected_video(cls) -> "PlaybackError":
        return cls("Cannot play without selected video")
