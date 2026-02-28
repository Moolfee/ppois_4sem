class CliError(Exception):
    """Базовая ошибка CLI."""

    default_message = "CLI error"

    def __init__(self, message: str | None = None, **context: str | int) -> None:
        self.message = message or self.default_message
        self.context = context
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class CommandParseError(CliError):
    """Ошибка разбора команды пользователя."""

    default_message = "Parse error"

    @classmethod
    def empty_command(cls) -> "CommandParseError":
        return cls("Empty command")

    @classmethod
    def from_parser_error(cls, details: str) -> "CommandParseError":
        return cls(f"{cls.default_message}: {details}", details=details)


class UnknownCommandError(CliError):
    """Команда не распознана роутером."""

    default_message = "Unknown command. Type 'help'."

    @classmethod
    def for_command(cls, name: str) -> "UnknownCommandError":
        return cls(cls.default_message, command=name)


class UsageError(CliError):
    """Неверное использование команды."""

    @classmethod
    def for_usage(cls, usage: str) -> "UsageError":
        return cls(f"Usage: {usage}", usage=usage)


class ValueValidationError(CliError):
    """Ошибка валидации пользовательского значения."""

    @classmethod
    def integer_required(cls, field_name: str) -> "ValueValidationError":
        return cls(f"{field_name} must be an integer", field=field_name)

    @classmethod
    def must_be_positive(cls, field_name: str) -> "ValueValidationError":
        return cls(f"{field_name} must be > 0", field=field_name)
