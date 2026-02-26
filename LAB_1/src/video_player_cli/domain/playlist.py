from dataclasses import dataclass, field

from video_player_cli.domain.video_file import VideoFile


@dataclass(slots=True)
class Playlist:
    name: str
    videos: list[VideoFile] = field(default_factory=list)

    def add_video(self, video: VideoFile) -> None:
        self.videos.append(video)

    def remove_video(self, title: str) -> bool:
        for index, video in enumerate(self.videos):
            if video.title == title:
                del self.videos[index]
                return True
        return False
