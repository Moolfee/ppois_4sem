from dataclasses import dataclass
from enum import Enum


class PlaybackStatus(str, Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass(slots=True)
class PlaybackControl:
    status: PlaybackStatus = PlaybackStatus.STOPPED

    def play(self) -> None:
        self.status = PlaybackStatus.PLAYING

    def pause(self) -> None:
        if self.status == PlaybackStatus.PLAYING:
            self.status = PlaybackStatus.PAUSED

    def stop(self) -> None:
        self.status = PlaybackStatus.STOPPED
