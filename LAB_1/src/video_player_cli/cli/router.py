from collections.abc import Callable

from video_player_cli.cli.command import Command

CommandHandler = Callable[[Command], bool]


class CommandRouter:
    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, command_name: str, handler: CommandHandler) -> None:
        self._handlers[command_name] = handler

    def dispatch(self, command: Command) -> bool:
        handler = self._handlers.get(command.name)
        if handler is None:
            raise KeyError(f"Unknown command: {command.name}")
        return handler(command)
