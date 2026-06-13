#!/usr/bin/env python3
"""Phase 1: Export YOLOv5s to static ONNX and optional dynamic ONNX."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import onnx
import torch

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import ensure_parent, load_config, resolve_path  # noqa: E402


def export_via_ultralytics(weights: Path, out_path: Path, opset: int, imgsz: int, dynamic: bool) -> bool:
    try:
        from ultralytics import YOLO
    except ImportError:
        return False

    model = YOLO(str(weights))
    exported = model.export(
        format="onnx",
        opset=opset,
        imgsz=imgsz,
        dynamic=dynamic,
        simplify=True,
    )
    exported_path = Path(exported)
    ensure_parent(out_path)
    shutil.copy2(exported_path, out_path)
    if exported_path.resolve() != out_path.resolve() and exported_path.exists():
        try:
            exported_path.unlink()
        except OSError:
            pass
    return True


def export_via_torch_hub(weights: Path, out_path: Path, input_name: str, output_names: list[str],
                         input_shape: tuple, opset: int, dynamic: bool) -> None:
    model = torch.hub.load("ultralytics/yolov5", "custom", path=str(weights), trust_repo=True)
    net = model.model.eval()
    dummy = torch.randn(*input_shape)
    dynamic_axes = None
    if dynamic:
        dynamic_axes = {input_name: {0: "batch", 2: "height", 3: "width"}}
        for name in output_names:
            dynamic_axes[name] = {0: "batch"}

    ensure_parent(out_path)
    torch.onnx.export(
        net,
        dummy,
        str(out_path),
        opset_version=opset,
        input_names=[input_name],
        output_names=output_names,
        dynamic_axes=dynamic_axes,
        do_constant_folding=True,
        dynamo=False,
    )


def verify_and_log(out_path: Path, log_path: Path, opset: int, input_shape: tuple, weights: Path) -> None:
    onnx.checker.check_model(str(out_path))
    print(f"checker PASS: {out_path}")
    log_path.write_text(
        f"# Export log\n\n"
        f"- weights: `{weights.name}`\n"
        f"- torch: `{torch.__version__}`\n"
        f"- opset: `{opset}`\n"
        f"- input_shape: `{list(input_shape)}`\n"
        f"- onnx: `{out_path.name}`\n",
        encoding="utf-8",
    )
    print(f"Wrote {log_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export YOLOv5 to ONNX")
    parser.add_argument("--config", default=None)
    parser.add_argument("--weights", default=None)
    parser.add_argument("--dynamic", action="store_true")
    parser.add_argument("--opset", type=int, default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    weights = Path(args.weights) if args.weights else resolve_path(cfg, "pt")
    if not weights.exists():
        print(f"ERROR: weights not found: {weights}")
        print("Download: https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt")
        return 1

    input_shape = tuple(cfg["input_shape"])
    opset = args.opset or cfg["opset"]
    _, _, h, w = input_shape
    input_name = cfg["input_name"]
    output_names = cfg["output_names"]

    if args.dynamic:
        out_path = resolve_path(cfg, "onnx_fp32_dynamic")
    else:
        out_path = resolve_path(cfg, "onnx_fp32")

    print(f"Exporting {weights.name} -> {out_path.name} (dynamic={args.dynamic})")

    ok = export_via_ultralytics(weights, out_path, opset, h, args.dynamic)
    if not ok:
        print("ultralytics not available, falling back to torch.hub ...")
        export_via_torch_hub(weights, out_path, input_name, output_names, input_shape, opset, args.dynamic)

    verify_and_log(out_path, out_path.parent / "export_log.md", opset, input_shape, weights)
    return 0


if __name__ == "__main__":
    sys.exit(main())
