"""Settings loaded from environment / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    blender_bin: Path = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    ffmpeg_bin: str = "ffmpeg"

    models_dir: Path = ROOT / "models"
    blender_scripts_dir: Path = ROOT / "blender_scripts"
    lib_dir: Path = ROOT / "lib"
    workflows_dir: Path = ROOT / "workflows"
    studio_blend: Path = ROOT / "assets" / "studio.blend"
    patterns_blend: Path = ROOT / "assets" / "patterns.blend"


@lru_cache
def get_settings() -> Settings:
    return Settings()
