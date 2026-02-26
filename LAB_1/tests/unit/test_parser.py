import pytest

from video_player_cli.cli.exceptions import CommandParseError
from video_player_cli.cli.parser import CommandParser


def test_parse_simple_command() -> None:
    parser = CommandParser()
    command = parser.parse("help")

    assert command.name == "help"
    assert command.args == []


def test_parse_command_with_args() -> None:
    parser = CommandParser()
    command = parser.parse("video select demo")

    assert command.name == "video"
    assert command.args == ["select", "demo"]


def test_parse_command_with_quotes() -> None:
    parser = CommandParser()
    command = parser.parse('video add "my demo" mp4 100')

    assert command.name == "video"
    assert command.args == ["add", "my demo", "mp4", "100"]


def test_parse_empty_command() -> None:
    parser = CommandParser()

    with pytest.raises(CommandParseError):
        parser.parse("   ")
