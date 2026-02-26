class CliError(Exception):
    """Базовая ошибка CLI."""


class CommandParseError(CliError):
    """Ошибка разбора команды пользователя."""
