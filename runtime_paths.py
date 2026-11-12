"""Resolução única dos caminhos persistentes do NARA.

Na FadeHost, /data é o volume persistente recomendado. Em ambiente local,
usa-se DATA_DIR quando definido ou ./data como fallback.
"""
from __future__ import annotations

import os
from pathlib import Path


def get_data_dir() -> Path:
    """Retorna o diretório de dados configurado sem depender do diretório atual."""
    configured = os.getenv("DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    persistent_volume = Path("/data")
    if persistent_volume.is_dir():
        return persistent_volume
    return Path(__file__).resolve().parent / "data"


def get_state_path(env_name: str, default_filename: str) -> Path:
    """Retorna caminho override por variável de ambiente ou arquivo dentro de DATA_DIR."""
    configured = os.getenv(env_name, "").strip()
    if configured:
        return Path(configured).expanduser()
    return get_data_dir() / default_filename
