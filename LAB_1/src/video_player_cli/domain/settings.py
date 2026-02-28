from dataclasses import dataclass

from video_player_cli.domain.exceptions import InvalidBrightnessError, InvalidVolumeError


@dataclass(slots=True)
class SoundSettings:
    volume: int = 50

    def set_volume(self, value: int) -> None:
        if not 0 <= value <= 100:
            raise InvalidVolumeError.for_value(value)
        self.volume = value


@dataclass(slots=True)
class DisplaySettings:
    brightness: int = 50

    def set_brightness(self, value: int) -> None:
        if not 0 <= value <= 100:
            raise InvalidBrightnessError.for_value(value)
        self.brightness = value
