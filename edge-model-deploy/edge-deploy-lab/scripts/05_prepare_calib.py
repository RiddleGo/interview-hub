#!/usr/bin/env python3
"""Prepare calibration npy files from calib/images using same preprocess as inference."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import load_config  # noqa: E402
from importlib import import_module

_preprocess_mod = import_module("03_preprocess")
preprocess = _preprocess_mod.preprocess


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--max", type=int, default=200, help="Max images to convert")
    args = parser.parse_args()

    cfg = load_config(args.config)
    root = cfg["_root"]
    img_dir = root / cfg["calib"]["dir"]
    out_dir = root / "calib" / "npy"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not img_dir.exists():
        img_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created {img_dir} — add JPG/PNG calibration images and re-run.")
        return 1

    images = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp"):
        images.extend(img_dir.glob(ext))
    images = sorted(images)[: args.max]

    if not images:
        print(f"No images in {img_dir}. Copy 100+ scene images for PTQ.")
        return 1

    for i, p in enumerate(images):
        img = cv2.imread(str(p))
        if img is None:
            continue
        arr = preprocess(cfg, img)
        np.save(out_dir / f"calib_{i:04d}.npy", arr)

    print(f"Wrote {len(list(out_dir.glob('*.npy')))} npy files to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
