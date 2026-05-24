"""Centralised settings. Loaded once at process startup. Everything else
reads `get_settings()`; nothing else touches env vars.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ASSET_FORGE_",
        extra="ignore",
    )

    # --- flax-mcp connection ---
    mcp_url: str = "http://127.0.0.1:8765"
    mcp_timeout_seconds: int = 60

    # --- LLM ---
    anthropic_key: str = ""
    openai_key: str = ""
    deepseek_key: str = ""
    ollama_url: str = "http://127.0.0.1:11434"

    # --- Asset-gen route preferences ---
    gen_routes: str = "fal-trellis,fal-triposr,triposr-local,trellis-hf,hunyuan-mini-local,fal-hunyuan3d-21,rodin-trial"

    # --- fal.ai ---
    fal_api_key: str = ""

    # --- Kaggle (free 30 GPU hrs/wk per account) ---
    kaggle_username: str = ""
    kaggle_api_token: str = ""
    kaggle_username_secondary: str = ""
    kaggle_api_token_secondary: str = ""

    # --- Blender ---
    blender_path: str = ""
    blender_headless: bool = True

    # --- Retopology ---
    retopo_backend: Literal[
        "quadriflow", "instant-meshes", "voxel-remesh", "decimate", "quadremesher"
    ] = "quadriflow"
    instant_meshes_path: str = ""

    # --- Marketplace credentials (manifest-side; first 6 months are manual upload) ---
    fab_publisher_id: str = ""
    unity_publisher_id: str = ""
    itchio_user: str = ""
    gumroad_key: str = ""

    # --- Output paths ---
    output_root: Path = Field(default=Path("./out"))
    cache_root: Path = Field(default=Path("./cache"))

    # --- Render backend ---
    render_backend: Literal["local", "cloud-blender", "sheepit"] = "local"
    render_threads: int = 8

    @property
    def gen_routes_list(self) -> list[str]:
        return [r.strip() for r in self.gen_routes.split(",") if r.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
