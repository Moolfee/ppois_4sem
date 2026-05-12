from pathlib import Path
import sys


def ensure_lab1_on_path() -> None:
    lab1_src = Path(__file__).resolve().parents[3] / "LAB_1" / "src"
    lab1_src_raw = str(lab1_src)
    if lab1_src_raw not in sys.path:
        sys.path.insert(0, lab1_src_raw)


ensure_lab1_on_path()

from video_player_cli.application.services import PlayerService
from video_player_cli.domain.exceptions import DomainError
from video_player_cli.domain.playlist import Playlist
from video_player_cli.domain.video_file import VideoFile


__all__ = ["DomainError", "PlayerService", "Playlist", "VideoFile"]
