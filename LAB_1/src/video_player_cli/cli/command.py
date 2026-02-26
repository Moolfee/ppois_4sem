from dataclasses import dataclass


@dataclass(slots=True)
class Command:
    name: str
    args: list[str]
