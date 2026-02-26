from dataclasses import dataclass

from video_player_cli.domain.exceptions import InvalidBrightnessError, InvalidVolumeError


@dataclass(slots=True)
class SoundSettings:
    volume: int = 50

    def set_volume(self, value: int) -> None:
        if not 0 <= value <= 100:
            raise InvalidVolumeError("Volume must be in range 0..100")
        self.volume = value


@dataclass(slots=True)
class DisplaySettings:
    brightness: int = 50

    def set_brightness(self, value: int) -> None:
        if not 0 <= value <= 100:
            raise InvalidBrightnessError("Brightness must be in range 0..100")
        self.brightness = value
