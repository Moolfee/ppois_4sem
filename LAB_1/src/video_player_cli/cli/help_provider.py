class HelpProvider:
    @staticmethod
    def text(supported_formats: list[str] | None = None) -> str:
        formats_line = ""
        if supported_formats is not None:
            formats_line = f"Supported formats: {', '.join(supported_formats)}\n\n"

        return (
            "Commands:\n"
            "  help\n"
            "  exit\n"
            "  status\n"
            "  play\n"
            "  pause\n"
            "  stop\n"
            "  formats list\n"
            "  video add <title> <format> <duration_seconds>\n"
            "  video list\n"
            "  video remove <title>\n"
            "  video select <title>\n"
            "  playlist create <name>\n"
            "  playlist list\n"
            "  playlist add <name> <video_title>\n"
            "  playlist remove <name> <video_title>\n"
            "  playlist show <name>\n"
            "  playlist select <name> <video_title>\n"
            "  volume set <0-100>\n"
            "  brightness set <0-100>\n"
            "\n"
            f"{formats_line}"
            "Tips:\n"
            "  Use quotes for values with spaces, example:\n"
            "  video add \"My Demo\" mp4 120"
        )
