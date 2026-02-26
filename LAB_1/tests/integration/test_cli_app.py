from video_player_cli.cli.app import CliApp
from video_player_cli.cli.console_io import ConsoleIO


class FakeConsoleIO(ConsoleIO):
    def __init__(self, inputs: list[str]) -> None:
        self._inputs = inputs
        self.outputs: list[str] = []
        self.errors: list[str] = []

    def read_line(self, prompt: str = "> ") -> str:
        if not self._inputs:
            return "exit"
        return self._inputs.pop(0)

    def print_line(self, message: str) -> None:
        self.outputs.append(message)

    def print_error(self, message: str) -> None:
        self.errors.append(message)


def test_cli_happy_path() -> None:
    io = FakeConsoleIO(
        [
            "formats list",
            'video add "demo video" mp4 120',
            'video select "demo video"',
            "play",
            'video remove "demo video"',
            "status",
            "exit",
        ]
    )
    app = CliApp(io=io)

    app.run()

    assert any("Video added: demo video" in line for line in io.outputs)
    assert any("Selected video: demo video" in line for line in io.outputs)
    assert any("Playback started" in line for line in io.outputs)
    assert any("Video removed: demo video" in line for line in io.outputs)
    assert any("Supported formats: avi, mkv, mp4" in line for line in io.outputs)
    assert any("playback=stopped" in line for line in io.outputs)
    assert not io.errors


def test_cli_reports_validation_error() -> None:
    io = FakeConsoleIO(["volume set abc", "exit"])
    app = CliApp(io=io)

    app.run()

    assert any("must be an integer" in error for error in io.errors)


def test_help_contains_supported_formats() -> None:
    io = FakeConsoleIO(["help", "exit"])
    app = CliApp(io=io)

    app.run()

    assert any("Supported formats: avi, mkv, mp4" in line for line in io.outputs)
