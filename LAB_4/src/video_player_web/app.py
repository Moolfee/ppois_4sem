from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from video_player_web.lab1_bridge import DomainError, PlayerService, Playlist, VideoFile


STATIC_DIR = Path(__file__).with_name("static")

app = FastAPI(title="LAB_4 Video Player Web", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_service = PlayerService()


class VideoCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    format_ext: str = Field(..., min_length=1)
    duration_seconds: int = Field(..., gt=0)


class PlaylistCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)


class SettingValueRequest(BaseModel):
    value: int = Field(..., ge=0, le=100)


async def get_service() -> PlayerService:
    return _service


def domain_error_to_http(error: DomainError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(error))


def serialize_video(video: VideoFile) -> dict[str, str | int]:
    return {
        "title": video.title,
        "format_ext": video.format_ext,
        "duration_seconds": video.duration_seconds,
    }


def serialize_playlist(playlist: Playlist) -> dict[str, str | list[dict[str, str | int]]]:
    return {
        "name": playlist.name,
        "videos": [serialize_video(video) for video in playlist.videos],
    }


def build_state(service: PlayerService) -> dict:
    return {
        "status": service.status(),
        "videos": [serialize_video(video) for video in service.list_videos()],
        "playlists": [
            serialize_playlist(playlist) for playlist in service.list_playlists()
        ],
        "supported_formats": service.list_supported_formats(),
    }


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/state")
async def read_state(service: PlayerService = Depends(get_service)) -> dict:
    return build_state(service)


@app.get("/api/formats")
async def read_formats(service: PlayerService = Depends(get_service)) -> list[str]:
    return service.list_supported_formats()


@app.get("/api/videos")
async def read_videos(service: PlayerService = Depends(get_service)) -> list[dict]:
    return [serialize_video(video) for video in service.list_videos()]


@app.post("/api/videos")
async def create_video(
    payload: VideoCreateRequest,
    service: PlayerService = Depends(get_service),
) -> dict:
    try:
        service.add_video(
            payload.title,
            payload.format_ext,
            payload.duration_seconds,
        )
    except DomainError as error:
        raise domain_error_to_http(error) from error
    return build_state(service)


@app.delete("/api/videos/{title}")
async def delete_video(
    title: str,
    service: PlayerService = Depends(get_service),
) -> dict:
    try:
        service.remove_video(title)
    except DomainError as error:
        raise domain_error_to_http(error) from error
    return build_state(service)


@app.post("/api/videos/{title}/select")
async def select_video(
    title: str,
    service: PlayerService = Depends(get_service),
) -> dict:
    try:
        service.select_video(title)
    except DomainError as error:
        raise domain_error_to_http(error) from error
    return build_state(service)


@app.post("/api/playback/{action}")
async def update_playback(
    action: str,
    service: PlayerService = Depends(get_service),
) -> dict:
    actions = {
        "play": service.play,
        "pause": service.pause,
        "stop": service.stop,
    }
    if action not in actions:
        raise HTTPException(status_code=404, detail="Unknown playback action")
    try:
        actions[action]()
    except DomainError as error:
        raise domain_error_to_http(error) from error
    return build_state(service)


@app.put("/api/settings/volume")
async def update_volume(
    payload: SettingValueRequest,
    service: PlayerService = Depends(get_service),
) -> dict:
    try:
        service.set_volume(payload.value)
    except DomainError as error:
        raise domain_error_to_http(error) from error
    return build_state(service)


@app.put("/api/settings/brightness")
async def update_brightness(
    payload: SettingValueRequest,
    service: PlayerService = Depends(get_service),
) -> dict:
    try:
        service.set_brightness(payload.value)
    except DomainError as error:
        raise domain_error_to_http(error) from error
    return build_state(service)


@app.get("/api/playlists")
async def read_playlists(service: PlayerService = Depends(get_service)) -> list[dict]:
    return [serialize_playlist(playlist) for playlist in service.list_playlists()]


@app.post("/api/playlists")
async def create_playlist(
    payload: PlaylistCreateRequest,
    service: PlayerService = Depends(get_service),
) -> dict:
    try:
        service.create_playlist(payload.name)
    except DomainError as error:
        raise domain_error_to_http(error) from error
    return build_state(service)


@app.get("/api/playlists/{name}")
async def read_playlist(
    name: str,
    service: PlayerService = Depends(get_service),
) -> dict:
    try:
        return serialize_playlist(service.show_playlist(name))
    except DomainError as error:
        raise domain_error_to_http(error) from error


@app.post("/api/playlists/{name}/videos/{title}")
async def add_video_to_playlist(
    name: str,
    title: str,
    service: PlayerService = Depends(get_service),
) -> dict:
    try:
        service.add_to_playlist(name, title)
    except DomainError as error:
        raise domain_error_to_http(error) from error
    return build_state(service)


@app.delete("/api/playlists/{name}/videos/{title}")
async def remove_video_from_playlist(
    name: str,
    title: str,
    service: PlayerService = Depends(get_service),
) -> dict:
    try:
        service.remove_from_playlist(name, title)
    except DomainError as error:
        raise domain_error_to_http(error) from error
    return build_state(service)


@app.post("/api/playlists/{name}/videos/{title}/select")
async def select_video_from_playlist(
    name: str,
    title: str,
    service: PlayerService = Depends(get_service),
) -> dict:
    try:
        service.select_from_playlist(name, title)
    except DomainError as error:
        raise domain_error_to_http(error) from error
    return build_state(service)
