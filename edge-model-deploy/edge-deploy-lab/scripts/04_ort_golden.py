#!/usr/bin/env python3
"""Phase 1/5: Run ORT on ONNX with input.bin, save golden output."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import cosine_similarity, ensure_parent, load_config, resolve_path  # noqa: E402


def load_input_bin(path: Path, shape: tuple[int, ...]) -> np.ndarray:
    return np.fromfile(str(path), dtype=np.float32).reshape(shape)


def save_outputs(outputs: list, out_dir: Path, prefix: str = "output_ort") -> list[Path]:
    ensure_parent(out_dir / "dummy")
    paths = []
    for i, arr in enumerate(outputs):
        p = out_dir / (f"{prefix}.bin" if len(outputs) == 1 else f"{prefix}_{i}.bin")
        arr.astype(np.float32).tofile(str(p))
        paths.append(p)
        print(f"  saved {p.name} shape={list(arr.shape)}")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--onnx", default=None, help="ONNX model path")
    parser.add_argument("--input", default=None, help="input.bin path")
    parser.add_argument("--output", default=None, help="Single output bin (first output only)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    onnx_path = Path(args.onnx) if args.onnx else resolve_path(cfg, "onnx_fp32")
    if not onnx_path.exists():
        onnx_path = resolve_path(cfg, "onnx_adapt")
    if not onnx_path.exists():
        print("ERROR: no ONNX found. Run export first.")
        return 1

    input_path = Path(args.input) if args.input else resolve_path(cfg, "input_bin")
    if not input_path.exists():
        print(f"ERROR: {input_path} not found. Run scripts/03_preprocess.py first.")
        return 1

    shape = tuple(cfg["input_shape"])
    x = load_input_bin(input_path, shape)
    input_name = cfg["input_name"]

    print(f"ORT session: {onnx_path.name}")
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    outputs = sess.run(None, {input_name: x})

    out_dir = input_path.parent
    if args.output:
        ensure_parent(Path(args.output))
        outputs[0].astype(np.float32).tofile(str(args.output))
        print(f"Wrote {args.output}")
    else:
        primary = resolve_path(cfg, "output_ort")
        if len(outputs) == 1:
            ensure_parent(primary)
            outputs[0].astype(np.float32).tofile(str(primary))
            print(f"Wrote {primary}")
        else:
            print(f"Model has {len(outputs)} outputs:")
            save_outputs(outputs, out_dir, "output_ort")

    return 0


if __name__ == "__main__":
    sys.exit(main())
