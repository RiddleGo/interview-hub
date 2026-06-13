#!/usr/bin/env python3
"""Phase 1: ONNX checker, aten scan, operator summary."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import onnx

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import load_config, resolve_path  # noqa: E402


def scan_operators(model_path: Path) -> Counter:
    model = onnx.load(str(model_path))
    return Counter(n.op_type for n in model.graph.node)


def scan_aten(model_path: Path) -> list[str]:
    model = onnx.load(str(model_path))
    hits = []
    for init in model.graph.initializer:
        if "aten" in init.name.lower():
            hits.append(f"initializer: {init.name}")
    for node in model.graph.node:
        if "aten" in node.op_type.lower() or "aten" in node.name.lower():
            hits.append(f"node: {node.op_type} {node.name}")
    raw = model.SerializeToString().decode("latin1", errors="ignore")
    if "aten::" in raw:
        hits.append("SerializeToString contains 'aten::'")
    return hits


def check_dynamic_dims(model_path: Path) -> list[str]:
    model = onnx.load(str(model_path))
    issues = []
    for inp in model.graph.input:
        for dim in inp.type.tensor_type.shape.dim:
            if dim.dim_param or (dim.dim_value == 0 and not dim.HasField("dim_value")):
                issues.append(f"input {inp.name} has dynamic/param dim")
            elif dim.dim_value <= 0 and dim.dim_param == "":
                # dim_value 0 sometimes means dynamic in exported graphs
                pass
    for inp in model.graph.input:
        shape = []
        for dim in inp.type.tensor_type.shape.dim:
            if dim.dim_param:
                shape.append(dim.dim_param)
            else:
                shape.append(str(dim.dim_value))
        if any(s in ("-1", "batch", "height", "width") for s in shape):
            issues.append(f"input {inp.name} shape looks dynamic: {shape}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--onnx", default=None, help="ONNX path override")
    args = parser.parse_args()

    cfg = load_config(args.config)
    onnx_path = Path(args.onnx) if args.onnx else resolve_path(cfg, "onnx_fp32")
    if not onnx_path.exists():
        print(f"ERROR: {onnx_path} not found. Run scripts/01_export_onnx.py first.")
        return 1

    print(f"Checking {onnx_path} ...")
    onnx.checker.check_model(str(onnx_path))
    print("onnx.checker: PASS")

    aten = scan_aten(onnx_path)
    if aten:
        print("WARNING: possible aten residue:")
        for h in aten[:10]:
            print(f"  - {h}")
    else:
        print("aten scan: clean")

    dynamic = check_dynamic_dims(onnx_path)
    if dynamic:
        print("Dynamic shape hints:")
        for d in dynamic:
            print(f"  - {d}")
    else:
        print("Input shape: static (good for edge deploy)")

    ops = scan_operators(onnx_path)
    print(f"\nOperator count: {len(ops)} unique types, {sum(ops.values())} nodes")
    print("Top operators:")
    for op, cnt in ops.most_common(15):
        print(f"  {op:20s} {cnt}")

    report = onnx_path.parent / "onnx_check_report.txt"
    lines = ["onnx.checker: PASS", f"aten_issues: {len(aten)}", f"dynamic_hints: {len(dynamic)}", "", "operators:"]
    lines.extend(f"  {op} {cnt}" for op, cnt in ops.most_common())
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {report}")
    print("\nTip: open in Netron — https://netron.app")
    return 0


if __name__ == "__main__":
    sys.exit(main())
