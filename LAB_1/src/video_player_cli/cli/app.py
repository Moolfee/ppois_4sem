from video_player_cli.application.services import PlayerService
from video_player_cli.cli.command import Command
from video_player_cli.cli.console_io import ConsoleIO
from video_player_cli.cli.exceptions import CliError, CommandParseError
from video_player_cli.cli.help_provider import HelpProvider
from video_player_cli.cli.parser import CommandParser
from video_player_cli.cli.router import CommandRouter
from video_player_cli.domain.exceptions import DomainError


class CliApp:
    def __init__(
        self,
        io: ConsoleIO | None = None,
        parser: CommandParser | None = None,
        router: CommandRouter | None = None,
        service: PlayerService | None = None,
    ) -> None:
        self.io = io or ConsoleIO()
        self.parser = parser or CommandParser()
        self.router = router or CommandRouter()
        self.service = service or PlayerService()
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.router.register("help", self._handle_help)
        self.router.register("exit", self._handle_exit)
        self.router.register("status", self._handle_status)
        self.router.register("play", self._handle_play)
        self.router.register("pause", self._handle_pause)
        self.router.register("stop", self._handle_stop)
        self.router.register("formats", self._handle_formats)
        self.router.register("video", self._handle_video)
        self.router.register("playlist", self._handle_playlist)
        self.router.register("volume", self._handle_volume)
        self.router.register("brightness", self._handle_brightness)

    def run(self) -> None:
        self.io.print_line("Video Player CLI. Type 'help' for commands.")
        is_running = True
        while is_running:
            try:
                raw = self.io.read_line()
                command = self.parser.parse(raw)
                is_running = self.router.dispatch(command)
            except (EOFError, KeyboardInterrupt):
                self.io.print_line("Goodbye")
                is_running = False
            except (CommandParseError, CliError, DomainError) as error:
                self.io.print_error(str(error))
            except KeyError:
                self.io.print_error("Unknown command. Type 'help'.")
            except Exception as error:  # noqa: BLE001
                self.io.print_error(f"Unhandled error: {error}")

    def _handle_help(self, command: Command) -> bool:
        self._ensure_arg_count(command, 0, "help")
        self.io.print_line(
            HelpProvider.text(supported_formats=self.service.list_supported_formats())
        )
        return True

    def _handle_exit(self, command: Command) -> bool:
        self._ensure_arg_count(command, 0, "exit")
        self.io.print_line("Goodbye")
        return False

    def _handle_status(self, command: Command) -> bool:
        self._ensure_arg_count(command, 0, "status")
        state = self.service.status()
        self.io.print_line(
            "Status: "
            f"video={state['current_video']}, "
            f"playback={state['playback']}, "
            f"volume={state['volume']}, "
            f"brightness={state['brightness']}, "
            f"library={state['library_size']}, "
            f"playlists={state['playlists_size']}"
        )
        return True

    def _handle_play(self, command: Command) -> bool:
        self._ensure_arg_count(command, 0, "play")
        self.service.play()
        self.io.print_line("Playback started")
        return True

    def _handle_pause(self, command: Command) -> bool:
        self._ensure_arg_count(command, 0, "pause")
        self.service.pause()
        self.io.print_line("Playback paused")
        return True

    def _handle_stop(self, command: Command) -> bool:
        self._ensure_arg_count(command, 0, "stop")
        self.service.stop()
        self.io.print_line("Playback stopped")
        return True

    def _handle_formats(self, command: Command) -> bool:
        if len(command.args) != 1 or command.args[0].lower() != "list":
            raise CliError("Usage: formats list")
        formats = ", ".join(self.service.list_supported_formats())
        self.io.print_line(f"Supported formats: {formats}")
        return True

    def _handle_video(self, command: Command) -> bool:
        if not command.args:
            raise CliError("Usage: video <add|list|remove|select> ...")

        action = command.args[0].lower()
        args = command.args[1:]

        if action == "add":
            if len(args) != 3:
                raise CliError("Usage: video add <title> <format> <duration_seconds>")
            title, format_ext, duration_raw = args
            duration = self._parse_int(duration_raw, "duration_seconds")
            if duration <= 0:
                raise CliError("duration_seconds must be > 0")
            self.service.add_video(title, format_ext, duration)
            self.io.print_line(f"Video added: {title}")
            return True

        if action == "list":
            self._ensure_exact_arg_len(args, 0, "video list")
            videos = self.service.list_videos()
            if not videos:
                self.io.print_line("Library is empty")
                return True
            for index, video in enumerate(videos, start=1):
                self.io.print_line(
                    f"{index}. {video.title} ({video.format_ext}, {video.duration_seconds}s)"
                )
            return True

        if action == "select":
            if len(args) != 1:
                raise CliError("Usage: video select <title>")
            title = args[0]
            self.service.select_video(title)
            self.io.print_line(f"Selected video: {title}")
            return True

        if action == "remove":
            if len(args) != 1:
                raise CliError("Usage: video remove <title>")
            title = args[0]
            self.service.remove_video(title)
            self.io.print_line(f"Video removed: {title}")
            return True

        raise CliError("Usage: video <add|list|remove|select> ...")

    def _handle_playlist(self, command: Command) -> bool:
        if not command.args:
            raise CliError("Usage: playlist <create|list|add|remove|show|select> ...")

        action = command.args[0].lower()
        args = command.args[1:]

        if action == "create":
            if len(args) != 1:
                raise CliError("Usage: playlist create <name>")
            name = args[0]
            self.service.create_playlist(name)
            self.io.print_line(f"Playlist created: {name}")
            return True

        if action == "list":
            self._ensure_exact_arg_len(args, 0, "playlist list")
            playlists = self.service.list_playlists()
            if not playlists:
                self.io.print_line("No playlists")
                return True
            for index, playlist in enumerate(playlists, start=1):
                self.io.print_line(f"{index}. {playlist.name} ({len(playlist.videos)} videos)")
            return True

        if action == "add":
            if len(args) != 2:
                raise CliError("Usage: playlist add <name> <video_title>")
            name, video_title = args
            self.service.add_to_playlist(name, video_title)
            self.io.print_line(f"Added '{video_title}' to playlist '{name}'")
            return True

        if action == "remove":
            if len(args) != 2:
                raise CliError("Usage: playlist remove <name> <video_title>")
            name, video_title = args
            self.service.remove_from_playlist(name, video_title)
            self.io.print_line(f"Removed '{video_title}' from playlist '{name}'")
            return True

        if action == "show":
            if len(args) != 1:
                raise CliError("Usage: playlist show <name>")
            name = args[0]
            playlist = self.service.show_playlist(name)
            if not playlist.videos:
                self.io.print_line(f"Playlist '{name}' is empty")
                return True
            for index, video in enumerate(playlist.videos, start=1):
                self.io.print_line(
                    f"{index}. {video.title} ({video.format_ext}, {video.duration_seconds}s)"
                )
            return True

        if action == "select":
            if len(args) != 2:
                raise CliError("Usage: playlist select <name> <video_title>")
            name, video_title = args
            self.service.select_from_playlist(name, video_title)
            self.io.print_line(
                f"Selected '{video_title}' from playlist '{name}' for playback"
            )
            return True

        raise CliError("Usage: playlist <create|list|add|remove|show|select> ...")

    def _handle_volume(self, command: Command) -> bool:
        if len(command.args) != 2 or command.args[0].lower() != "set":
            raise CliError("Usage: volume set <0-100>")
        value = self._parse_int(command.args[1], "volume")
        self.service.set_volume(value)
        self.io.print_line(f"Volume set to {value}")
        return True

    def _handle_brightness(self, command: Command) -> bool:
        if len(command.args) != 2 or command.args[0].lower() != "set":
            raise CliError("Usage: brightness set <0-100>")
        value = self._parse_int(command.args[1], "brightness")
        self.service.set_brightness(value)
        self.io.print_line(f"Brightness set to {value}")
        return True

    def _parse_int(self, raw: str, field_name: str) -> int:
        try:
            return int(raw)
        except ValueError as error:
            raise CliError(f"{field_name} must be an integer") from error

    def _ensure_arg_count(self, command: Command, expected: int, usage: str) -> None:
        self._ensure_exact_arg_len(command.args, expected, usage)

    def _ensure_exact_arg_len(self, args: list[str], expected: int, usage: str) -> None:
        if len(args) != expected:
            raise CliError(f"Usage: {usage}")
