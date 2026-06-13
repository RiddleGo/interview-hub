#!/usr/bin/env python3
"""Create minimal multi-output ONNX for offline PC smoke test (no yolov5s.pt needed)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import onnx
import torch
import torch.nn as nn

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import ensure_parent, load_config, resolve_path  # noqa: E402


class TinyDetect(nn.Module):
    """Three-scale dummy head outputs similar to YOLO layout."""

    def __init__(self):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(inplace=True),
        )
        self.head3 = nn.Conv2d(16, 255, 1)  # 3*85 for 80 classes simplified
        self.head4 = nn.Conv2d(16, 255, 1)
        self.head5 = nn.Conv2d(16, 255, 1)

    def forward(self, x):
        f = self.stem(x)
        return self.head3(f), self.head4(f), self.head5(f)


def main() -> int:
    cfg = load_config()
    out = resolve_path(cfg, "onnx_fp32")
    ensure_parent(out)

    model = TinyDetect().eval()
    dummy = torch.randn(*cfg["input_shape"])
    names = cfg["output_names"]
    if len(names) != 3:
        names = ["output0", "output1", "output2"]

    torch.onnx.export(
        model,
        dummy,
        str(out),
        opset_version=cfg["opset"],
        input_names=[cfg["input_name"]],
        output_names=names,
        dynamic_axes=None,
        dynamo=False,
    )
    onnx.checker.check_model(str(out))

    pt_dir = resolve_path(cfg, "pt").parent
    pt_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), pt_dir / "minimal_dummy.pt")

    log = out.parent / "export_log.md"
    log.write_text(
        "# Export log (minimal smoke model)\n\n"
        "- mode: offline TinyDetect\n"
        f"- opset: {cfg['opset']}\n"
        f"- input_shape: {cfg['input_shape']}\n",
        encoding="utf-8",
    )
    print(f"Wrote minimal ONNX: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
