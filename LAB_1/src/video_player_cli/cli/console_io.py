class ConsoleIO:
    def read_line(self, prompt: str = "> ") -> str:
        return input(prompt)

    def print_line(self, message: str) -> None:
        print(message)

    def print_error(self, message: str) -> None:
        print(f"[ERROR] {message}")
