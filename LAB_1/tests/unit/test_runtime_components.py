from video_player_cli import main as main_module
from video_player_cli.cli.console_io import ConsoleIO
from video_player_cli.domain.playback import PlaybackControl, PlaybackStatus
from video_player_cli.domain.playlist import Playlist
from video_player_cli.domain.video_file import VideoFile


def test_console_io_methods(monkeypatch, capsys) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "help")
    io = ConsoleIO()

    assert io.read_line() == "help"

    io.print_line("ok")
    io.print_error("bad")

    captured = capsys.readouterr()
    assert "ok" in captured.out
    assert "[ERROR] bad" in captured.out


def test_main_creates_and_runs_cli_app(monkeypatch) -> None:
    state = {"created": False, "ran": False}

    class FakeCliApp:
        def __init__(self) -> None:
            state["created"] = True

        def run(self) -> None:
            state["ran"] = True

    monkeypatch.setattr(main_module, "CliApp", FakeCliApp)

    main_module.main()

    assert state == {"created": True, "ran": True}


def test_playback_pause_only_changes_state_when_playing() -> None:
    playback = PlaybackControl()

    playback.pause()
    assert playback.status == PlaybackStatus.STOPPED

    playback.play()
    playback.pause()
    assert playback.status == PlaybackStatus.PAUSED


def test_playlist_remove_video_found_and_not_found() -> None:
    video = VideoFile(title="demo", format_ext="mp4", duration_seconds=10)
    playlist = Playlist(name="fav", videos=[video])

    assert playlist.remove_video("demo") is True
    assert playlist.remove_video("missing") is False
