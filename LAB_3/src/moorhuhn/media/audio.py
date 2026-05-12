from __future__ import annotations

import array
import hashlib
import math
import random
from pathlib import Path

import pygame

from ..config.game_config import AudioConfig
from ..config.settings import UserSettings

AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav")


def prepare_audio(audio_config: AudioConfig) -> None:
    if audio_config.enabled:
        pygame.mixer.pre_init(22050, -16, 2, 512)


class AudioManager:
    def __init__(self, config: AudioConfig, project_root: Path) -> None:
        self.config = config
        self.assets_root = project_root / "assets" / "audio"
        self.audio_cache_dir = project_root / "data" / "audio_cache"
        self.random = random.Random()
        self.available = False
        self.target_music_key = ""
        self.current_music_key = ""
        self.current_music_path = ""
        self.current_settings = UserSettings(0.0, 0.0, 0.0, 0.0, 0.0, False)
        self.music_files: dict[str, tuple[Path, ...]] = {}
        self.sound_banks: dict[str, tuple[pygame.mixer.Sound, ...]] = {}
        self.sound_categories: dict[str, str] = {}
        self.effect_channel: pygame.mixer.Channel | None = None

        if not config.enabled:
            return

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
        except pygame.error:
            return

        self.effect_channel = pygame.mixer.Channel(1)
        self._build_audio_bank()
        self.available = True

    def _build_audio_bank(self) -> None:
        shared_music = self._legacy_named_files("music_loop")
        self.music_files = {
            "menu": self._collect_audio_files(self.assets_root / "music_menu")
            or self._legacy_named_files("menu_music_loop")
            or shared_music,
            "game": self._collect_audio_files(self.assets_root / "music_gameplay")
            or self._legacy_named_files("game_music_loop")
            or shared_music,
        }

        hit_bank = self._merge_sound_banks(
            self._load_effect_group(
                directory=self.assets_root / "sfx_gameplay",
                prefixes=("hit", "score"),
            ),
            self._load_effect_group(
                directory=self.assets_root / "sfx_weapon",
                prefixes=("hit",),
            ),
            self._load_legacy_effect("hit"),
        )
        self.sound_banks = {
            "shot": self._load_effect_group(
                directory=self.assets_root / "sfx_weapon",
                prefixes=("shot", "fire"),
            )
            or self._load_legacy_effect("shot"),
            "reload": self._load_effect_group(
                directory=self.assets_root / "sfx_weapon",
                prefixes=("reload", "insert", "shell"),
            )
            or self._load_legacy_effect("reload"),
            "hit": hit_bank,
            "miss": self._load_effect_group(
                directory=self.assets_root / "sfx_gameplay",
                prefixes=("miss", "whiff"),
            )
            or self._load_legacy_effect("miss"),
            "ui_hover": self._load_effect_group(
                directory=self.assets_root / "sfx_ui",
                prefixes=("hover", "focus", "move"),
            ),
            "ui_confirm": self._load_effect_group(
                directory=self.assets_root / "sfx_ui",
                prefixes=("confirm", "click", "select", "accept"),
            ),
        }
        self.sound_categories = {
            "shot": "weapon",
            "reload": "weapon",
            "hit": "gameplay",
            "miss": "gameplay",
            "ui_hover": "ui",
            "ui_confirm": "ui",
        }
        self._fill_generated_effect_fallbacks()

    def _collect_audio_files(self, directory: Path) -> tuple[Path, ...]:
        if not directory.exists() or not directory.is_dir():
            return ()
        files = [
            path
            for path in sorted(directory.iterdir())
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
        ]
        return tuple(files)

    def _collect_prefixed_audio_files(self, directory: Path, prefixes: tuple[str, ...]) -> tuple[Path, ...]:
        if not directory.exists() or not directory.is_dir():
            return ()
        normalized_prefixes = tuple(prefix.lower() for prefix in prefixes)
        files: list[Path] = []
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            stem = path.stem.lower()
            if any(
                stem == prefix or stem.startswith(f"{prefix}_") or stem.startswith(f"{prefix}-")
                for prefix in normalized_prefixes
            ):
                files.append(path)
        return tuple(files)

    def _legacy_named_files(self, base_name: str) -> tuple[Path, ...]:
        matches = [
            self.assets_root / f"{base_name}{extension}"
            for extension in AUDIO_EXTENSIONS
            if (self.assets_root / f"{base_name}{extension}").exists()
        ]
        return tuple(matches)

    def _load_effect_group(
        self,
        *,
        directory: Path,
        prefixes: tuple[str, ...],
    ) -> tuple[pygame.mixer.Sound, ...]:
        return self._load_sound_paths(self._collect_prefixed_audio_files(directory, prefixes))

    def _load_legacy_effect(self, base_name: str) -> tuple[pygame.mixer.Sound, ...]:
        return self._load_sound_paths(self._legacy_named_files(base_name))

    def _load_sound_paths(self, paths: tuple[Path, ...]) -> tuple[pygame.mixer.Sound, ...]:
        sounds: list[pygame.mixer.Sound] = []
        for path in paths:
            try:
                sounds.append(pygame.mixer.Sound(self._resolved_audio_path(path).as_posix()))
            except pygame.error:
                continue
        return tuple(sounds)

    def _merge_sound_banks(self, *banks: tuple[pygame.mixer.Sound, ...]) -> tuple[pygame.mixer.Sound, ...]:
        merged: list[pygame.mixer.Sound] = []
        for bank in banks:
            merged.extend(bank)
        return tuple(merged)

    def apply_settings(self, settings: UserSettings) -> None:
        self.current_settings = settings.normalized()
        if not self.available:
            return

        pygame.mixer.music.set_volume(self._music_volume())
        for key, bank in self.sound_banks.items():
            volume = self._effect_volume(self.sound_categories.get(key, "gameplay"))
            for sound in bank:
                sound.set_volume(volume)

    def _music_volume(self) -> float:
        return self.current_settings.master_volume * self.current_settings.music_volume

    def _effect_volume(self, category: str) -> float:
        category_scale = {
            "gameplay": self.current_settings.gameplay_sfx_volume,
            "weapon": self.current_settings.weapon_sfx_volume,
            "ui": self.current_settings.ui_sfx_volume,
        }.get(category, self.current_settings.gameplay_sfx_volume)
        return self.current_settings.master_volume * category_scale

    def _fill_generated_effect_fallbacks(self) -> None:
        for name in ("shot", "reload", "hit", "miss", "ui_hover", "ui_confirm"):
            if self.sound_banks.get(name):
                continue
            generated = self._build_generated_sound(name)
            if generated is not None:
                self.sound_banks[name] = (generated,)

    def _build_generated_sound(self, name: str) -> pygame.mixer.Sound | None:
        specs = {
            "shot": (92.0, 0.12, 0.9, True),
            "reload": (220.0, 0.09, 0.5, False),
            "hit": (420.0, 0.08, 0.45, False),
            "miss": (180.0, 0.08, 0.35, False),
            "ui_hover": (540.0, 0.04, 0.2, False),
            "ui_confirm": (680.0, 0.06, 0.28, False),
        }
        spec = specs.get(name)
        if spec is None:
            return None
        frequency, duration_seconds, amplitude, noisy = spec
        sample_rate = 22050
        frame_count = max(1, int(sample_rate * duration_seconds))
        samples = array.array("h")

        for index in range(frame_count):
            progress = index / frame_count
            envelope = 1.0 - progress
            wave_value = math.sin(2.0 * math.pi * frequency * progress * duration_seconds)
            if noisy:
                wave_value += (self.random.random() * 2.0 - 1.0) * 0.38 * envelope
            value = int(max(-1.0, min(1.0, wave_value)) * 32767 * amplitude * envelope)
            samples.extend((value, value))

        try:
            return pygame.mixer.Sound(buffer=samples.tobytes())
        except pygame.error:
            return None

    def play_menu_loop(self) -> None:
        self._set_music_loop("menu")

    def play_game_loop(self) -> None:
        self._set_music_loop("game")

    def _set_music_loop(self, key: str) -> None:
        if not self.available:
            return
        self.target_music_key = key
        self._play_music_loop(key, force_switch=self.current_music_key != key)

    def update(self) -> None:
        if not self.available or not self.target_music_key:
            return
        if pygame.mixer.music.get_busy():
            return
        self._play_music_loop(self.target_music_key)

    def _play_music_loop(self, key: str, *, force_switch: bool = False) -> None:
        if not self.available:
            return

        tracks = self.music_files.get(key, ())
        if not tracks:
            pygame.mixer.music.stop()
            self.target_music_key = ""
            self.current_music_key = ""
            self.current_music_path = ""
            return

        if not force_switch and self.current_music_key == key and pygame.mixer.music.get_busy():
            return

        track = self._choose_music_track(key, tracks)
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(self._resolved_audio_path(track).as_posix())
            pygame.mixer.music.set_volume(self._music_volume())
            pygame.mixer.music.play()
        except pygame.error:
            return

        self.current_music_key = key
        self.current_music_path = track.as_posix()

    def _choose_music_track(self, key: str, tracks: tuple[Path, ...]) -> Path:
        if len(tracks) <= 1:
            return tracks[0]

        previous_path = self.current_music_path if self.current_music_key == key else ""
        candidates = [track for track in tracks if track.as_posix() != previous_path]
        if not candidates:
            candidates = list(tracks)
        return self.random.choice(candidates)

    def stop_all(self) -> None:
        if not self.available:
            return
        pygame.mixer.music.stop()
        pygame.mixer.stop()
        self.target_music_key = ""
        self.current_music_key = ""
        self.current_music_path = ""

    def play_shot(self) -> None:
        self._play_effect("shot")

    def play_hit(self) -> None:
        self._play_effect("hit")

    def play_miss(self) -> None:
        self._play_effect("miss")

    def play_reload(self) -> None:
        self._play_effect("reload")

    def play_ui_hover(self) -> None:
        self._play_effect("ui_hover")

    def play_ui_confirm(self) -> None:
        self._play_effect("ui_confirm")

    def _play_effect(self, name: str) -> None:
        if not self.available:
            return
        bank = self.sound_banks.get(name, ())
        if not bank:
            return
        sound = self.random.choice(bank)
        channel = pygame.mixer.find_channel()
        if channel is None:
            channel = self.effect_channel
        if channel is None:
            return
        channel.play(sound)

    def _resolved_audio_path(self, path: Path) -> Path:
        if path.suffix.lower() != ".mp3":
            return path

        try:
            raw_bytes = path.read_bytes()
        except OSError:
            return path

        sanitized_bytes = self._strip_mp3_tags(raw_bytes)
        if sanitized_bytes == raw_bytes:
            return path

        digest = hashlib.sha1(path.as_posix().encode("utf-8") + raw_bytes[:64]).hexdigest()[:12]
        cache_path = self.audio_cache_dir / f"{path.stem}_{digest}.mp3"
        if cache_path.exists():
            return cache_path

        try:
            self.audio_cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(sanitized_bytes)
        except OSError:
            return path
        return cache_path

    def _strip_mp3_tags(self, payload: bytes) -> bytes:
        start_index = 0
        end_index = len(payload)

        if len(payload) >= 10 and payload[:3] == b"ID3":
            flags = payload[5]
            tag_size = self._decode_synchsafe(payload[6:10])
            start_index = min(len(payload), 10 + tag_size + (10 if flags & 0x10 else 0))

        if end_index - start_index >= 128 and payload[end_index - 128 : end_index - 125] == b"TAG":
            end_index -= 128

        if start_index >= end_index:
            return payload
        return payload[start_index:end_index]

    def _decode_synchsafe(self, payload: bytes) -> int:
        if len(payload) != 4:
            return 0
        return (
            ((payload[0] & 0x7F) << 21)
            | ((payload[1] & 0x7F) << 14)
            | ((payload[2] & 0x7F) << 7)
            | (payload[3] & 0x7F)
        )
