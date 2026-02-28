import pytest

from video_player_cli.application.services import PlayerService
from video_player_cli.domain.exceptions import (
    DuplicateVideoError,
    InvalidDurationError,
    PlaybackError,
    PlaylistNotFoundError,
    UnsupportedFormatError,
    VideoNotFoundError,
)


def test_add_and_select_video() -> None:
    service = PlayerService()

    service.add_video("demo", "mp4", 42)
    service.select_video("demo")

    status = service.status()
    assert status["current_video"] == "demo"
    assert status["library_size"] == 1


def test_add_video_with_unsupported_format() -> None:
    service = PlayerService()

    with pytest.raises(UnsupportedFormatError):
        service.add_video("demo", "mov", 42)


def test_play_requires_selected_video() -> None:
    service = PlayerService()

    with pytest.raises(PlaybackError):
        service.play()


def test_playlist_flow() -> None:
    service = PlayerService()
    service.add_video("demo", "mp4", 42)
    service.create_playlist("fav")
    service.add_to_playlist("fav", "demo")

    playlist = service.show_playlist("fav")
    assert len(playlist.videos) == 1
    assert playlist.videos[0].title == "demo"


def test_missing_playlist() -> None:
    service = PlayerService()

    with pytest.raises(PlaylistNotFoundError):
        service.show_playlist("missing")


def test_supported_formats_available() -> None:
    service = PlayerService()

    assert service.list_supported_formats() == ["avi", "mkv", "mp4"]


def test_remove_video_updates_library() -> None:
    service = PlayerService()
    service.add_video("demo", "mp4", 42)

    service.remove_video("demo")

    assert service.status()["library_size"] == 0


def test_add_video_with_non_positive_duration() -> None:
    service = PlayerService()

    with pytest.raises(InvalidDurationError):
        service.add_video("demo", "mp4", 0)


def test_add_duplicate_video_raises_error() -> None:
    service = PlayerService()
    service.add_video("demo", "mp4", 42)

    with pytest.raises(DuplicateVideoError):
        service.add_video("demo", "mp4", 60)


def test_remove_missing_video_raises_error() -> None:
    service = PlayerService()

    with pytest.raises(VideoNotFoundError):
        service.remove_video("missing")


def test_remove_missing_video_from_playlist_raises_error() -> None:
    service = PlayerService()
    service.add_video("demo", "mp4", 42)
    service.create_playlist("fav")

    with pytest.raises(VideoNotFoundError):
        service.remove_from_playlist("fav", "missing")


def test_select_missing_video_from_playlist_raises_error() -> None:
    service = PlayerService()
    service.add_video("demo", "mp4", 42)
    service.create_playlist("fav")

    with pytest.raises(VideoNotFoundError):
        service.select_from_playlist("fav", "missing")


def test_remove_from_missing_playlist_raises_error() -> None:
    service = PlayerService()

    with pytest.raises(PlaylistNotFoundError):
        service.remove_from_playlist("missing", "demo")


def test_select_from_missing_playlist_raises_error() -> None:
    service = PlayerService()

    with pytest.raises(PlaylistNotFoundError):
        service.select_from_playlist("missing", "demo")
