import pytest

from video_player_cli.cli.app import CliApp
from video_player_cli.cli.command import Command
from video_player_cli.cli.console_io import ConsoleIO
from video_player_cli.cli.exceptions import UsageError, ValueValidationError


class FakeIO(ConsoleIO):
    def __init__(self, inputs: list[object] | None = None) -> None:
        self._inputs = inputs or []
        self.outputs: list[str] = []
        self.errors: list[str] = []

    def read_line(self, prompt: str = "> ") -> str:
        if not self._inputs:
            raise EOFError
        item = self._inputs.pop(0)
        if isinstance(item, BaseException):
            raise item
        return str(item)

    def print_line(self, message: str) -> None:
        self.outputs.append(message)

    def print_error(self, message: str) -> None:
        self.errors.append(message)


class FailingParser:
    def parse(self, raw: str) -> Command:
        raise RuntimeError("boom")


def _app() -> tuple[CliApp, FakeIO]:
    io = FakeIO()
    return CliApp(io=io), io


def test_run_handles_keyboard_interrupt() -> None:
    io = FakeIO(inputs=[KeyboardInterrupt()])
    app = CliApp(io=io)

    app.run()

    assert io.outputs[0] == "Video Player CLI. Type 'help' for commands."
    assert io.outputs[-1] == "Goodbye"


def test_run_handles_unexpected_exception() -> None:
    io = FakeIO(inputs=["anything", EOFError()])
    app = CliApp(io=io, parser=FailingParser())

    app.run()

    assert any("Unhandled error: boom" in err for err in io.errors)
    assert io.outputs[-1] == "Goodbye"


def test_help_exit_status_and_formats_handlers() -> None:
    app, io = _app()

    assert app._handle_help(Command(name="help", args=[])) is True
    assert app._handle_status(Command(name="status", args=[])) is True
    assert app._handle_formats(Command(name="formats", args=["list"])) is True
    assert app._handle_exit(Command(name="exit", args=[])) is False

    assert any("Supported formats: avi, mkv, mp4" in line for line in io.outputs)
    assert any("Status: video=None, playback=stopped" in line for line in io.outputs)
    assert io.outputs[-1] == "Goodbye"


@pytest.mark.parametrize(
    ("name", "args", "usage"),
    [
        ("help", ["x"], "Usage: help"),
        ("exit", ["x"], "Usage: exit"),
        ("status", ["x"], "Usage: status"),
        ("play", ["x"], "Usage: play"),
        ("pause", ["x"], "Usage: pause"),
        ("stop", ["x"], "Usage: stop"),
        ("formats", [], "Usage: formats list"),
    ],
)
def test_simple_handlers_validate_usage(name: str, args: list[str], usage: str) -> None:
    app, _ = _app()
    handler = getattr(app, f"_handle_{name}")

    with pytest.raises(UsageError, match=usage):
        handler(Command(name=name, args=args))


def test_video_handler_branches_and_errors() -> None:
    app, io = _app()

    with pytest.raises(
        UsageError, match=r"Usage: video <add\|list\|remove\|select> \.\.\."
    ):
        app._handle_video(Command(name="video", args=[]))

    with pytest.raises(UsageError, match="Usage: video add <title> <format> <duration_seconds>"):
        app._handle_video(Command(name="video", args=["add", "only-title"]))

    with pytest.raises(ValueValidationError, match="duration_seconds must be an integer"):
        app._handle_video(Command(name="video", args=["add", "demo", "mp4", "NaN"]))

    with pytest.raises(ValueValidationError, match="duration_seconds must be > 0"):
        app._handle_video(Command(name="video", args=["add", "demo", "mp4", "0"]))

    assert app._handle_video(Command(name="video", args=["list"])) is True
    assert io.outputs[-1] == "Library is empty"

    assert app._handle_video(Command(name="video", args=["add", "demo", "MP4", "10"])) is True
    assert app._handle_video(Command(name="video", args=["list"])) is True
    assert any("1. demo (mp4, 10s)" in line for line in io.outputs)

    with pytest.raises(UsageError, match="Usage: video list"):
        app._handle_video(Command(name="video", args=["list", "extra"]))

    with pytest.raises(UsageError, match="Usage: video select <title>"):
        app._handle_video(Command(name="video", args=["select"]))
    assert app._handle_video(Command(name="video", args=["select", "demo"])) is True

    with pytest.raises(UsageError, match="Usage: video remove <title>"):
        app._handle_video(Command(name="video", args=["remove"]))
    assert app._handle_video(Command(name="video", args=["remove", "demo"])) is True

    with pytest.raises(
        UsageError, match=r"Usage: video <add\|list\|remove\|select> \.\.\."
    ):
        app._handle_video(Command(name="video", args=["unknown"]))


def test_playlist_handler_branches_and_errors() -> None:
    app, io = _app()
    app.service.add_video("demo", "mp4", 30)

    with pytest.raises(
        UsageError,
        match=r"Usage: playlist <create\|list\|add\|remove\|show\|select> \.\.\.",
    ):
        app._handle_playlist(Command(name="playlist", args=[]))

    with pytest.raises(UsageError, match="Usage: playlist create <name>"):
        app._handle_playlist(Command(name="playlist", args=["create"]))
    assert app._handle_playlist(Command(name="playlist", args=["create", "fav"])) is True

    assert app._handle_playlist(Command(name="playlist", args=["list"])) is True
    assert any("1. fav (0 videos)" in line for line in io.outputs)

    with pytest.raises(UsageError, match="Usage: playlist list"):
        app._handle_playlist(Command(name="playlist", args=["list", "extra"]))

    with pytest.raises(UsageError, match="Usage: playlist add <name> <video_title>"):
        app._handle_playlist(Command(name="playlist", args=["add", "fav"]))
    assert app._handle_playlist(Command(name="playlist", args=["add", "fav", "demo"])) is True

    with pytest.raises(UsageError, match="Usage: playlist show <name>"):
        app._handle_playlist(Command(name="playlist", args=["show"]))
    assert app._handle_playlist(Command(name="playlist", args=["show", "fav"])) is True
    assert any("1. demo (mp4, 30s)" in line for line in io.outputs)

    with pytest.raises(UsageError, match="Usage: playlist select <name> <video_title>"):
        app._handle_playlist(Command(name="playlist", args=["select", "fav"]))
    assert app._handle_playlist(Command(name="playlist", args=["select", "fav", "demo"])) is True

    with pytest.raises(UsageError, match="Usage: playlist remove <name> <video_title>"):
        app._handle_playlist(Command(name="playlist", args=["remove", "fav"]))
    assert app._handle_playlist(Command(name="playlist", args=["remove", "fav", "demo"])) is True

    assert app._handle_playlist(Command(name="playlist", args=["show", "fav"])) is True
    assert io.outputs[-1] == "Playlist 'fav' is empty"

    with pytest.raises(
        UsageError,
        match=r"Usage: playlist <create\|list\|add\|remove\|show\|select> \.\.\.",
    ):
        app._handle_playlist(Command(name="playlist", args=["unknown"]))


def test_volume_and_brightness_handlers() -> None:
    app, io = _app()

    with pytest.raises(UsageError, match="Usage: volume set <0-100>"):
        app._handle_volume(Command(name="volume", args=["wrong", "10"]))
    with pytest.raises(UsageError, match="Usage: brightness set <0-100>"):
        app._handle_brightness(Command(name="brightness", args=["wrong", "10"]))

    with pytest.raises(ValueValidationError, match="volume must be an integer"):
        app._handle_volume(Command(name="volume", args=["set", "x"]))
    with pytest.raises(ValueValidationError, match="brightness must be an integer"):
        app._handle_brightness(Command(name="brightness", args=["set", "x"]))

    assert app._handle_volume(Command(name="volume", args=["set", "77"])) is True
    assert app._handle_brightness(Command(name="brightness", args=["set", "66"])) is True

    assert io.outputs[-2] == "Volume set to 77"
    assert io.outputs[-1] == "Brightness set to 66"


def test_play_pause_stop_handlers() -> None:
    app, io = _app()
    app.service.add_video("demo", "mp4", 15)
    app.service.select_video("demo")

    assert app._handle_play(Command(name="play", args=[])) is True
    assert app._handle_pause(Command(name="pause", args=[])) is True
    assert app._handle_stop(Command(name="stop", args=[])) is True

    assert io.outputs[-3:] == ["Playback started", "Playback paused", "Playback stopped"]
