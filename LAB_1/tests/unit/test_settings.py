import pytest

from video_player_cli.domain.exceptions import InvalidVolumeError
from video_player_cli.domain.settings import SoundSettings


def test_set_volume_success() -> None:
    settings = SoundSettings()
    settings.set_volume(75)

    assert settings.volume == 75


def test_set_volume_out_of_range() -> None:
    settings = SoundSettings()

    with pytest.raises(InvalidVolumeError):
        settings.set_volume(101)
