import pytest

from video_player_cli.domain.exceptions import InvalidBrightnessError, InvalidVolumeError
from video_player_cli.domain.settings import DisplaySettings, SoundSettings


def test_set_volume_success() -> None:
    settings = SoundSettings()
    settings.set_volume(75)

    assert settings.volume == 75


def test_set_volume_out_of_range() -> None:
    settings = SoundSettings()

    with pytest.raises(InvalidVolumeError):
        settings.set_volume(101)


def test_set_brightness_success() -> None:
    settings = DisplaySettings()
    settings.set_brightness(25)

    assert settings.brightness == 25


def test_set_brightness_out_of_range() -> None:
    settings = DisplaySettings()

    with pytest.raises(InvalidBrightnessError):
        settings.set_brightness(-1)
