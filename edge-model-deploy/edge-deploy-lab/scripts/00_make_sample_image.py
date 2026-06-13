#!/usr/bin/env python3
"""Generate a synthetic sample image for smoke tests."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sample" / "test.jpg"


def imwrite_unicode(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(path.suffix if path.suffix else ".jpg", img)
    if not ok:
        raise RuntimeError(f"imencode failed: {path}")
    buf.tofile(str(path))


def main() -> int:
    rng = np.random.default_rng(42)
    img = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)
    cv2.rectangle(img, (100, 80), (300, 280), (0, 255, 0), 2)
    imwrite_unicode(OUT, img)
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
