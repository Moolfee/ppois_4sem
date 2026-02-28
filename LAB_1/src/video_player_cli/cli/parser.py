import shlex

from video_player_cli.cli.command import Command
from video_player_cli.cli.exceptions import CommandParseError


class CommandParser:
    def parse(self, raw: str) -> Command:
        line = raw.strip()
        if not line:
            raise CommandParseError.empty_command()

        try:
            parts = shlex.split(line)
        except ValueError as error:
            raise CommandParseError.from_parser_error(str(error)) from error

        if not parts:
            raise CommandParseError.empty_command()

        return Command(name=parts[0].lower(), args=parts[1:])
