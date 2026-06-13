#!/usr/bin/env python3
"""Phase 3/6: Layer-wise cosine screening between FP32 and INT8 ONNX via ORT."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from onnx import helper

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import cosine_similarity, load_config, resolve_path  # noqa: E402


def add_output_nodes(model_path: Path, out_path: Path, max_layers: int = 30) -> list[str]:
    model = onnx.load(str(model_path))
    existing = {o.name for o in model.graph.output}
    names = []
    count = 0
    for node in model.graph.node:
        if count >= max_layers:
            break
        for out in node.output:
            if out in existing or not out:
                continue
            model.graph.output.append(
                helper.make_tensor_value_info(out, onnx.TensorProto.FLOAT, None)
            )
            existing.add(out)
            names.append(out)
            count += 1
            break
    onnx.save(model, str(out_path))
    return names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--fp32", default=None)
    parser.add_argument("--int8", default=None)
    parser.add_argument("--threshold", type=float, default=0.98)
    parser.add_argument("--max-layers", type=int, default=30)
    args = parser.parse_args()

    cfg = load_config(args.config)
    fp32_path = Path(args.fp32) if args.fp32 else resolve_path(cfg, "onnx_fp32")
    int8_path = Path(args.int8) if args.int8 else resolve_path(cfg, "onnx_int8")

    if not fp32_path.exists() or not int8_path.exists():
        print("Need both FP32 and INT8 ONNX. Run export + quant first.")
        return 1

    input_bin = resolve_path(cfg, "input_bin")
    if not input_bin.exists():
        print("Run scripts/03_preprocess.py first.")
        return 1

    shape = tuple(cfg["input_shape"])
    x = np.fromfile(str(input_bin), dtype=np.float32).reshape(shape)
    input_name = cfg["input_name"]

    dump_dir = cfg["_root"] / "deliverables" / "05_verify" / "layerwise"
    dump_dir.mkdir(parents=True, exist_ok=True)
    fp32_dump = dump_dir / "fp32_dump.onnx"
    layer_names = add_output_nodes(fp32_path, fp32_dump, args.max_layers)

    sess_fp32 = ort.InferenceSession(str(fp32_dump), providers=["CPUExecutionProvider"])
    sess_int8 = ort.InferenceSession(str(int8_path), providers=["CPUExecutionProvider"])
    out_fp32 = dict(zip([o.name for o in sess_fp32.get_outputs()], sess_fp32.run(None, {input_name: x})))
    out_int8 = dict(zip([o.name for o in sess_int8.get_outputs()], sess_int8.run(None, {input_name: x})))

    print(f"{'layer':40s} {'cosine':>10s} {'flag':>6s}")
    print("-" * 60)
    candidates = []
    for name in layer_names:
        if name not in out_int8:
            continue
        a, b = out_fp32[name], out_int8[name]
        if a.shape != b.shape:
            print(f"{name:40s} shape_mismatch")
            continue
        cos = cosine_similarity(a, b)
        flag = "SKIP?" if cos < args.threshold else "OK"
        print(f"{name:40s} {cos:10.6f} {flag:>6s}")
        if cos < args.threshold:
            candidates.append(name)

    skip_file = cfg["_root"] / "configs" / "skip_layers.txt"
    if candidates:
        print(f"\nLayers below {args.threshold} — consider skip_layers:")
        for c in candidates:
            print(f"  {c}")
        existing = skip_file.read_text(encoding="utf-8") if skip_file.exists() else ""
        with open(skip_file, "a", encoding="utf-8") as f:
            for c in candidates:
                if c not in existing:
                    f.write(f"{c}\n")
        print(f"Appended candidates to {skip_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
