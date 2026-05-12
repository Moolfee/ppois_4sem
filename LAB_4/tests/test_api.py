import anyio
from httpx import ASGITransport, AsyncClient

from video_player_web.app import app, build_state, get_service
from video_player_web.lab1_bridge import PlayerService


def set_test_service() -> PlayerService:
    service = PlayerService()

    async def override_service() -> PlayerService:
        return service

    app.dependency_overrides[get_service] = override_service
    return service


def run_async(test_func) -> None:
    anyio.run(test_func, backend="asyncio")


def test_index_and_initial_state() -> None:
    async def scenario() -> None:
        set_test_service()
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/state")
            assert response.status_code == 200
            data = response.json()
            assert data["status"]["current_video"] is None
            assert data["status"]["playback"] == "stopped"
            assert data["videos"] == []
            assert data["playlists"] == []
            assert data["supported_formats"] == ["avi", "mkv", "mp4"]

            response = await client.get("/api/formats")
            assert response.status_code == 200
            assert response.json() == ["avi", "mkv", "mp4"]

    run_async(scenario)


def test_video_crud_and_playback_flow() -> None:
    async def scenario() -> None:
        set_test_service()
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/videos")
            assert response.status_code == 200
            assert response.json() == []

            response = await client.post(
                "/api/videos",
                json={
                    "title": "Demo",
                    "format_ext": "mp4",
                    "duration_seconds": 90,
                },
            )
            assert response.status_code == 200
            assert response.json()["status"]["library_size"] == 1

            response = await client.get("/api/videos")
            assert response.status_code == 200
            assert response.json() == [
                {"title": "Demo", "format_ext": "mp4", "duration_seconds": 90}
            ]

            response = await client.post("/api/videos/Demo/select")
            assert response.status_code == 200
            assert response.json()["status"]["current_video"] == "Demo"

            response = await client.post("/api/playback/play")
            assert response.status_code == 200
            assert response.json()["status"]["playback"] == "playing"

            response = await client.post("/api/playback/pause")
            assert response.status_code == 200
            assert response.json()["status"]["playback"] == "paused"

            response = await client.post("/api/playback/stop")
            assert response.status_code == 200
            assert response.json()["status"]["playback"] == "stopped"

            response = await client.delete("/api/videos/Demo")
            assert response.status_code == 200
            assert response.json()["status"]["library_size"] == 0

    run_async(scenario)


def test_settings_flow() -> None:
    async def scenario() -> None:
        set_test_service()
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put("/api/settings/volume", json={"value": 75})
            assert response.status_code == 200
            assert response.json()["status"]["volume"] == 75

            response = await client.put("/api/settings/brightness", json={"value": 25})
            assert response.status_code == 200
            assert response.json()["status"]["brightness"] == 25

    run_async(scenario)


def test_playlist_flow() -> None:
    async def scenario() -> None:
        set_test_service()
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/playlists")
            assert response.status_code == 200
            assert response.json() == []

            await client.post(
                "/api/videos",
                json={
                    "title": "Clip",
                    "format_ext": "avi",
                    "duration_seconds": 45,
                },
            )
            response = await client.post("/api/playlists", json={"name": "Favorites"})
            assert response.status_code == 200
            assert response.json()["status"]["playlists_size"] == 1

            response = await client.get("/api/playlists")
            assert response.status_code == 200
            assert response.json() == [{"name": "Favorites", "videos": []}]

            response = await client.post("/api/playlists/Favorites/videos/Clip")
            assert response.status_code == 200
            assert response.json()["playlists"][0]["videos"][0]["title"] == "Clip"

            response = await client.get("/api/playlists/Favorites")
            assert response.status_code == 200
            assert response.json()["videos"][0]["title"] == "Clip"

            response = await client.post("/api/playlists/Favorites/videos/Clip/select")
            assert response.status_code == 200
            assert response.json()["status"]["current_video"] == "Clip"

            response = await client.delete("/api/playlists/Favorites/videos/Clip")
            assert response.status_code == 200
            assert response.json()["playlists"][0]["videos"] == []

    run_async(scenario)


def test_errors_are_returned_as_http_responses() -> None:
    async def scenario() -> None:
        set_test_service()
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/playback/play")

            assert response.status_code == 400
            assert response.json()["detail"] == "Cannot play without selected video"

            response = await client.post("/api/playback/restart")
            assert response.status_code == 404
            assert response.json()["detail"] == "Unknown playback action"

            response = await client.post(
                "/api/videos",
                json={
                    "title": "Bad",
                    "format_ext": "mov",
                    "duration_seconds": 60,
                },
            )
            assert response.status_code == 400
            assert response.json()["detail"] == "Unsupported format: mov"

            response = await client.post("/api/videos/Missing/select")
            assert response.status_code == 400
            assert response.json()["detail"] == "Video not found: Missing"

            response = await client.delete("/api/videos/Missing")
            assert response.status_code == 400
            assert response.json()["detail"] == "Video not found: Missing"

            response = await client.post("/api/playlists", json={"name": "P"})
            assert response.status_code == 200

            response = await client.post("/api/playlists", json={"name": "P"})
            assert response.status_code == 400
            assert response.json()["detail"] == "Playlist already exists: P"

            response = await client.get("/api/playlists/Missing")
            assert response.status_code == 400
            assert response.json()["detail"] == "Playlist not found: Missing"

            response = await client.post("/api/playlists/Missing/videos/Clip")
            assert response.status_code == 400
            assert response.json()["detail"] == "Playlist not found: Missing"

            response = await client.delete("/api/playlists/P/videos/Missing")
            assert response.status_code == 400
            assert response.json()["detail"] == "Video not found in playlist 'P': Missing"

            response = await client.post("/api/playlists/P/videos/Missing/select")
            assert response.status_code == 400
            assert response.json()["detail"] == "Video not found in playlist 'P': Missing"

    run_async(scenario)


def test_build_state_contains_existing_model_data() -> None:
    service = PlayerService()
    service.add_video("Local", "mkv", 120)
    service.create_playlist("Queue")
    service.add_to_playlist("Queue", "Local")
    service.select_from_playlist("Queue", "Local")

    state = build_state(service)

    assert state["status"]["current_video"] == "Local"
    assert state["videos"] == [
        {"title": "Local", "format_ext": "mkv", "duration_seconds": 120}
    ]
    assert state["playlists"] == [
        {
            "name": "Queue",
            "videos": [
                {"title": "Local", "format_ext": "mkv", "duration_seconds": 120}
            ],
        }
    ]
