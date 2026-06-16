"""Configuration loading for DragonFlow-KronosGraph."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dragonflow.utils.io import resolve_path


def load_model_config(path: str | Path = "configs/model_v1.yaml") -> dict[str, Any]:
    p = resolve_path(path)
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_device_name(requested: str = "auto") -> str:
    if requested != "auto":
        return requested
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"
