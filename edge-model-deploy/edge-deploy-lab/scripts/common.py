"""Shared helpers for edge-deploy-lab scripts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    root = repo_root()
    path = Path(config_path) if config_path else root / "configs" / "project.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_root"] = root
    cfg["_config_path"] = path
    return cfg


def resolve_path(cfg: dict[str, Any], key: str) -> Path:
    root = cfg["_root"]
    return (root / cfg["paths"][key]).resolve()


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_flat = a.reshape(-1).astype(np.float64)
    b_flat = b.reshape(-1).astype(np.float64)
    dot = np.dot(a_flat, b_flat)
    norm = np.linalg.norm(a_flat) * np.linalg.norm(b_flat)
    return float(dot / (norm + 1e-12))


def mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))


def snr_db(a: np.ndarray, b: np.ndarray) -> float:
    signal = np.mean(a.astype(np.float64) ** 2)
    noise = np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2)
    if noise < 1e-20:
        return float("inf")
    return float(10 * np.log10(signal / noise))


def input_shape_str(cfg: dict[str, Any]) -> str:
    n, c, h, w = cfg["input_shape"]
    name = cfg["input_name"]
    return f"{name}:{n},{c},{h},{w}"
