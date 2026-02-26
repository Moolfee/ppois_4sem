from dataclasses import dataclass


@dataclass(slots=True)
class VideoFile:
    title: str
    format_ext: str
    duration_seconds: int
