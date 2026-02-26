from dataclasses import dataclass, field

from video_player_cli.domain.player import VideoPlayer
from video_player_cli.domain.playlist import Playlist
from video_player_cli.domain.video_file import VideoFile


@dataclass(slots=True)
class PlayerService:
    player: VideoPlayer = field(default_factory=VideoPlayer)

    def add_video(self, title: str, format_ext: str, duration_seconds: int) -> None:
        video = VideoFile(
            title=title,
            format_ext=format_ext.lower(),
            duration_seconds=duration_seconds,
        )
        self.player.add_video(video)

    def list_videos(self) -> list[VideoFile]:
        return self.player.list_videos()

    def remove_video(self, title: str) -> None:
        self.player.remove_video(title)

    def select_video(self, title: str) -> None:
        self.player.select_video(title)

    def play(self) -> None:
        self.player.play()

    def pause(self) -> None:
        self.player.pause()

    def stop(self) -> None:
        self.player.stop()

    def set_volume(self, value: int) -> None:
        self.player.set_volume(value)

    def set_brightness(self, value: int) -> None:
        self.player.set_brightness(value)

    def create_playlist(self, name: str) -> None:
        self.player.create_playlist(name)

    def list_playlists(self) -> list[Playlist]:
        return self.player.list_playlists()

    def show_playlist(self, name: str) -> Playlist:
        return self.player.get_playlist(name)

    def add_to_playlist(self, playlist_name: str, video_title: str) -> None:
        self.player.add_video_to_playlist(playlist_name, video_title)

    def remove_from_playlist(self, playlist_name: str, video_title: str) -> None:
        self.player.remove_video_from_playlist(playlist_name, video_title)

    def select_from_playlist(self, playlist_name: str, video_title: str) -> None:
        self.player.select_video_from_playlist(playlist_name, video_title)

    def status(self) -> dict[str, str | int | None]:
        return self.player.status()

    def list_supported_formats(self) -> list[str]:
        return self.player.list_supported_formats()
