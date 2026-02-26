from dataclasses import dataclass, field

from video_player_cli.domain.exceptions import (
    DuplicateVideoError,
    PlaybackError,
    PlaylistAlreadyExistsError,
    PlaylistNotFoundError,
    UnsupportedFormatError,
    VideoNotFoundError,
)
from video_player_cli.domain.playback import PlaybackControl
from video_player_cli.domain.playlist import Playlist
from video_player_cli.domain.settings import DisplaySettings, SoundSettings
from video_player_cli.domain.supported_formats import SupportedFormats
from video_player_cli.domain.video_file import VideoFile


@dataclass(slots=True)
class VideoPlayer:
    library: list[VideoFile] = field(default_factory=list)
    playlists: list[Playlist] = field(default_factory=list)
    current_video: VideoFile | None = None
    sound: SoundSettings = field(default_factory=SoundSettings)
    display: DisplaySettings = field(default_factory=DisplaySettings)
    formats: SupportedFormats = field(default_factory=SupportedFormats)
    playback: PlaybackControl = field(default_factory=PlaybackControl)

    def add_video(self, video: VideoFile) -> None:
        if not self.formats.is_supported(video.format_ext):
            raise UnsupportedFormatError(f"Unsupported format: {video.format_ext}")
        if self._find_video(video.title) is not None:
            raise DuplicateVideoError(f"Video already exists: {video.title}")
        self.library.append(video)

    def list_videos(self) -> list[VideoFile]:
        return list(self.library)

    def remove_video(self, title: str) -> None:
        for index, video in enumerate(self.library):
            if video.title == title:
                del self.library[index]
                self._remove_video_from_all_playlists(title)
                if self.current_video and self.current_video.title == title:
                    self.current_video = None
                    self.playback.stop()
                return
        raise VideoNotFoundError(f"Video not found: {title}")

    def select_video(self, title: str) -> None:
        video = self._find_video_or_raise(title)
        self.current_video = video

    def play(self) -> None:
        if self.current_video is None:
            raise PlaybackError("Cannot play without selected video")
        self.playback.play()

    def pause(self) -> None:
        self.playback.pause()

    def stop(self) -> None:
        self.playback.stop()

    def set_volume(self, value: int) -> None:
        self.sound.set_volume(value)

    def set_brightness(self, value: int) -> None:
        self.display.set_brightness(value)

    def create_playlist(self, name: str) -> None:
        if self._find_playlist(name) is not None:
            raise PlaylistAlreadyExistsError(f"Playlist already exists: {name}")
        self.playlists.append(Playlist(name=name))

    def list_playlists(self) -> list[Playlist]:
        return list(self.playlists)

    def get_playlist(self, name: str) -> Playlist:
        playlist = self._find_playlist(name)
        if playlist is None:
            raise PlaylistNotFoundError(f"Playlist not found: {name}")
        return playlist

    def add_video_to_playlist(self, playlist_name: str, video_title: str) -> None:
        playlist = self.get_playlist(playlist_name)
        video = self._find_video_or_raise(video_title)
        playlist.add_video(video)

    def remove_video_from_playlist(self, playlist_name: str, video_title: str) -> None:
        playlist = self.get_playlist(playlist_name)
        removed = playlist.remove_video(video_title)
        if not removed:
            raise VideoNotFoundError(
                f"Video not found in playlist '{playlist_name}': {video_title}"
            )

    def select_video_from_playlist(self, playlist_name: str, video_title: str) -> None:
        playlist = self.get_playlist(playlist_name)
        for video in playlist.videos:
            if video.title == video_title:
                self.current_video = video
                return
        raise VideoNotFoundError(
            f"Video not found in playlist '{playlist_name}': {video_title}"
        )

    def status(self) -> dict[str, str | int | None]:
        current_title = self.current_video.title if self.current_video else None
        return {
            "current_video": current_title,
            "playback": self.playback.status.value,
            "volume": self.sound.volume,
            "brightness": self.display.brightness,
            "library_size": len(self.library),
            "playlists_size": len(self.playlists),
        }

    def list_supported_formats(self) -> list[str]:
        return self.formats.list_formats()

    def _find_video(self, title: str) -> VideoFile | None:
        for video in self.library:
            if video.title == title:
                return video
        return None

    def _find_video_or_raise(self, title: str) -> VideoFile:
        video = self._find_video(title)
        if video is None:
            raise VideoNotFoundError(f"Video not found: {title}")
        return video

    def _find_playlist(self, name: str) -> Playlist | None:
        for playlist in self.playlists:
            if playlist.name == name:
                return playlist
        return None

    def _remove_video_from_all_playlists(self, title: str) -> None:
        for playlist in self.playlists:
            playlist.remove_video(title)
