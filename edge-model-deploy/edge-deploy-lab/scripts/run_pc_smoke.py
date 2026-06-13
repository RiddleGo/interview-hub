#!/usr/bin/env python3
"""Cross-platform PC smoke test (Windows/Linux, no CANN required)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(cmd: list[str], **kwargs) -> None:
    print(f"\n>>> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True, **kwargs)


def export_onnx(minimal: bool) -> None:
    if minimal:
        run([PY, "scripts/create_minimal_onnx.py"])
        run([PY, "scripts/02_check_onnx.py", "--config", "configs/project.yaml"])
        return

    pt = ROOT / "deliverables" / "01_export" / "yolov5s.pt"
    pt.parent.mkdir(parents=True, exist_ok=True)

    if not pt.exists():
        print("yolov5s.pt not found — trying download (may be slow) ...")
        try:
            url = "https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt"
            urllib.request.urlretrieve(url, pt)
            print("Downloaded yolov5s.pt")
        except Exception as e:
            print(f"Download failed ({e}), using minimal offline ONNX")
            run([PY, "scripts/create_minimal_onnx.py"])
            run([PY, "scripts/02_check_onnx.py", "--config", "configs/project.yaml"])
            return

    run([PY, "scripts/01_export_onnx.py", "--config", "configs/project.yaml"])
    run([PY, "scripts/02_check_onnx.py", "--config", "configs/project.yaml"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimal", action="store_true", help="Use TinyDetect ONNX (no download)")
    args = parser.parse_args()

    print("=== EdgeDeployLab PC smoke test ===")
    run([PY, "scripts/00_make_sample_image.py"])
    export_onnx(args.minimal)

    src = ROOT / "deliverables" / "01_export" / "model_fp32.onnx"
    dst = ROOT / "deliverables" / "02_adapt" / "model_adapt.onnx"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Copied adapt ONNX: {dst}")

    run([PY, "scripts/03_preprocess.py", "--config", "configs/project.yaml"])
    run([PY, "scripts/04_ort_golden.py", "--config", "configs/project.yaml"])

    verify = ROOT / "deliverables" / "05_verify"
    ort_bins = sorted(verify.glob("output_ort*.bin"))
    if not ort_bins:
        print("ERROR: no output_ort*.bin from golden run")
        return 1
    for ob in ort_bins:
        nb = verify / ob.name.replace("output_ort", "output_npu")
        shutil.copy2(ob, nb)
    print(f"Simulated NPU outputs: {len(ort_bins)} file(s)")
    run([PY, "scripts/07_compare.py", "--config", "configs/project.yaml"])
    run([PY, "scripts/10_eval_detect.py", "--config", "configs/project.yaml"])

    print("\n=== PC smoke test PASSED ===")
    print("Next: CANN -> bash scripts/06_atc_compile.sh fp16")
    return 0


if __name__ == "__main__":
    sys.exit(main())
