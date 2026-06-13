#!/usr/bin/env python3
"""Phase 5: Compare ORT vs NPU outputs — cosine, MSE, SNR; JSON report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import cosine_similarity, file_md5, load_config, mse, resolve_path, snr_db  # noqa: E402


def load_bin(path: Path, shape: tuple | None = None) -> np.ndarray:
    arr = np.fromfile(str(path), dtype=np.float32)
    if shape is not None:
        return arr.reshape(shape)
    return arr


def compare_pair(gt: np.ndarray, npu: np.ndarray, name: str) -> dict:
    if gt.shape != npu.shape:
        return {
            "name": name,
            "error": f"shape mismatch {gt.shape} vs {npu.shape}",
        }
    return {
        "name": name,
        "shape": list(gt.shape),
        "cosine": cosine_similarity(gt, npu),
        "mse": mse(gt, npu),
        "snr_db": snr_db(gt, npu),
    }


def find_output_bins(directory: Path, prefix: str) -> list[Path]:
    single = directory / f"{prefix}.bin"
    if single.exists():
        return [single]
    multi = sorted(directory.glob(f"{prefix}_*.bin"))
    return multi


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--gt", default=None, help="Golden output bin or prefix dir")
    parser.add_argument("--npu", default=None, help="NPU output bin or prefix dir")
    parser.add_argument("--input", default=None, help="Verify input.bin md5")
    args = parser.parse_args()

    cfg = load_config(args.config)
    verify_dir = resolve_path(cfg, "input_bin").parent

    gt_paths = find_output_bins(verify_dir, "output_ort")
    npu_paths = find_output_bins(verify_dir, "output_npu")

    if args.gt:
        p = Path(args.gt)
        gt_paths = [p] if p.is_file() else find_output_bins(p.parent, p.stem)

    if args.npu:
        p = Path(args.npu)
        npu_paths = [p] if p.is_file() else find_output_bins(p.parent, p.stem)

    if not gt_paths:
        print("ERROR: no output_ort*.bin. Run scripts/04_ort_golden.py")
        return 1
    if not npu_paths:
        print("ERROR: no output_npu*.bin. Run board infer or copy ort output for smoke test:")
        print("  copy deliverables/05_verify/output_ort.bin deliverables/05_verify/output_npu.bin")
        return 1

    report: dict = {"layers": [], "thresholds": cfg.get("thresholds", {})}

    input_path = Path(args.input) if args.input else resolve_path(cfg, "input_bin")
    if input_path.exists():
        report["input_md5"] = file_md5(input_path)
        report["input_path"] = str(input_path)

    if len(gt_paths) != len(npu_paths):
        print(f"WARN: output count mismatch ort={len(gt_paths)} npu={len(npu_paths)}")

    for i, (g, n) in enumerate(zip(gt_paths, npu_paths)):
        gt = load_bin(g)
        npu = load_bin(n)
        name = g.stem.replace("output_ort", "output").replace("output", f"branch_{i}", 1)
        if len(gt_paths) > 1:
            name = f"output_{i}"
        result = compare_pair(gt, npu, name)
        report["layers"].append(result)
        if "error" in result:
            print(f"{name}: ERROR {result['error']}")
        else:
            print(f"{name}: cosine={result['cosine']:.6f} mse={result['mse']:.8f} snr={result['snr_db']:.2f}dB")

    cosines = [r["cosine"] for r in report["layers"] if "cosine" in r]
    if cosines:
        report["global_cosine"] = float(np.mean(cosines))
        report["min_cosine"] = float(np.min(cosines))
        print(f"\nglobal_mean_cosine={report['global_cosine']:.6f} min={report['min_cosine']:.6f}")

    out_json = resolve_path(cfg, "compare_report")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
