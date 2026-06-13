#!/usr/bin/env python3
"""Phase 1/5: Preprocess image to input.bin (YOLOv5 letterbox, RGB, NCHW, /255)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import ensure_parent, file_md5, load_config, resolve_path  # noqa: E402


def imread_unicode(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def letterbox(
    img: np.ndarray,
    new_shape: tuple[int, int] = (640, 640),
    color: tuple[int, int, int] = (114, 114, 114),
) -> tuple[np.ndarray, float, tuple[float, float]]:
    shape = img.shape[:2]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]
    dw /= 2
    dh /= 2
    if shape[::-1] != new_unpad:
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return img, r, (dw, dh)


def preprocess(cfg: dict, img_bgr: np.ndarray, wrong_norm: bool = False) -> np.ndarray:
    _, _, h, w = cfg["input_shape"]
    if cfg.get("letterbox", True):
        img_bgr, _, _ = letterbox(img_bgr, (h, w), tuple(cfg.get("letterbox_color", [114, 114, 114])))

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    x = img_rgb.astype(np.float32)

    if wrong_norm:
        # Deliberate bug for learning exercise (Q12): ImageNet norm instead of /255
        x /= 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        x = (x - mean) / std
    else:
        x /= 255.0

    x = x.transpose(2, 0, 1)[np.newaxis, ...]
    return np.ascontiguousarray(x, dtype=np.float32)


def find_sample_image(root: Path) -> Path | None:
    sample_dir = root / "data" / "sample"
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp"):
        files = list(sample_dir.glob(ext))
        if files:
            return files[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--image", default=None, help="Input image path")
    parser.add_argument("--output", default=None, help="Output .bin path")
    parser.add_argument("--wrong-norm", action="store_true", help="Bug injection: ImageNet norm (Q12 exercise)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    root = cfg["_root"]

    if args.image:
        img_path = Path(args.image)
    else:
        img_path = find_sample_image(root)
        if img_path is None:
            print("No sample image; generating synthetic ...")
            import subprocess

            subprocess.run([sys.executable, str(SCRIPT_DIR / "00_make_sample_image.py")], check=True)
            img_path = root / "data" / "sample" / "test.jpg"

    out_path = Path(args.output) if args.output else resolve_path(cfg, "input_bin")
    ensure_parent(out_path)

    img = imread_unicode(img_path)
    if img is None:
        print(f"ERROR: cannot read {img_path}")
        return 1

    tensor = preprocess(cfg, img, wrong_norm=args.wrong_norm)
    tensor.tofile(str(out_path))

    print(f"Image: {img_path}")
    print(f"Shape: {list(tensor.shape)}, dtype float32")
    print(f"Wrote: {out_path}")
    print(f"MD5:  {file_md5(out_path)}")
    if args.wrong_norm:
        print("NOTE: --wrong-norm enabled (deliberate preprocessing bug for Q12 exercise)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
