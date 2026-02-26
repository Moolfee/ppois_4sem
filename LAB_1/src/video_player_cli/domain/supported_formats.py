from dataclasses import dataclass, field


@dataclass(slots=True)
class SupportedFormats:
    formats: set[str] = field(default_factory=lambda: {"mp4", "avi", "mkv"})

    def is_supported(self, format_ext: str) -> bool:
        normalized = format_ext.lower().lstrip(".")
        return normalized in self.formats

    def list_formats(self) -> list[str]:
        return sorted(self.formats)
