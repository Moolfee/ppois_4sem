from dataclasses import dataclass

from video_player_cli.domain.exceptions import InvalidDurationError


@dataclass(slots=True)
class VideoFile:
    title: str
    format_ext: str
    duration_seconds: int

    def __post_init__(self) -> None:
        if self.duration_seconds <= 0:
            raise InvalidDurationError.for_value(self.duration_seconds)
