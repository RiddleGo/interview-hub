#!/usr/bin/env python3
"""PC-only fallback: ORT static quantization when AMCT is unavailable."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import ensure_parent, load_config, resolve_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    src = resolve_path(cfg, "onnx_adapt")
    if not src.exists():
        src = resolve_path(cfg, "onnx_fp32")
    out = resolve_path(cfg, "onnx_int8")
    ensure_parent(out)

    calib_dir = cfg["_root"] / "calib" / "npy"
    if not calib_dir.exists() or not list(calib_dir.glob("*.npy")):
        print("Run scripts/05_prepare_calib.py first (or use AMCT on Ascend).")
        return 1

    try:
        from onnxruntime.quantization import CalibrationDataReader, QuantType, quantize_static
    except ImportError:
        print("Install onnxruntime with quantization support.")
        return 1

    import numpy as np

    input_name = cfg["input_name"]
    shape = tuple(cfg["input_shape"])

    class Reader(CalibrationDataReader):
        def __init__(self):
            self.files = sorted(calib_dir.glob("*.npy"))
            self.i = 0

        def get_next(self):
            if self.i >= len(self.files):
                return None
            arr = np.load(self.files[self.i])
            self.i += 1
            return {input_name: arr}

    print(f"Quantizing {src.name} -> {out.name} (ORT static, {len(list(calib_dir.glob('*.npy')))} calib samples)")
    quantize_static(
        str(src),
        str(out),
        Reader(),
        quant_format="QDQ",
        activation_type=QuantType.QUInt8,
        weight_type=QuantType.QInt8,
    )
    print(f"Wrote {out}")
    print("NOTE: ORT INT8 != Ascend INT8 path; use for learning QDQ flow only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
