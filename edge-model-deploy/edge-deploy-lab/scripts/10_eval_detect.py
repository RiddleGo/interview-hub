#!/usr/bin/env python3
"""Phase 6: Simplified detection visual sanity check (not full COCO mAP)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from common import load_config, resolve_path  # noqa: E402
from importlib import import_module

_preprocess_mod = import_module("03_preprocess")
letterbox = _preprocess_mod.letterbox


def nms_boxes(boxes: np.ndarray, scores: np.ndarray, iou_thres: float = 0.45) -> list[int]:
    x1, y1, x2, y2 = boxes.T
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0, xx2 - xx1)
        h = np.maximum(0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        order = order[1:][iou <= iou_thres]
    return keep


def decode_yolov5_outputs(outputs: list[np.ndarray], conf_thres: float = 0.25) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decode multi-scale YOLOv5 ONNX outputs to boxes (xyxy), scores, class ids."""
    all_boxes, all_scores, all_cls = [], [], []
    for out in outputs:
        # out: (1, na, ny, nx, 85) or (1, 3*ny*nx, 85)
        if out.ndim == 5:
            _, na, ny, nx, no = out.shape
            pred = out.reshape(1, na * ny * nx, no)
        elif out.ndim == 3:
            pred = out
        else:
            continue
        pred = pred[0]
        obj = pred[:, 4]
        cls_scores = pred[:, 5:]
        cls_ids = np.argmax(cls_scores, axis=1)
        scores = obj * cls_scores[np.arange(len(cls_ids)), cls_ids]
        mask = scores > conf_thres
        if not np.any(mask):
            continue
        p = pred[mask]
        scores_m = scores[mask]
        cls_m = cls_ids[mask]
        cx, cy, w, h = p[:, 0], p[:, 1], p[:, 2], p[:, 3]
        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2
        all_boxes.append(np.stack([x1, y1, x2, y2], axis=1))
        all_scores.append(scores_m)
        all_cls.append(cls_m)

    if not all_boxes:
        return np.zeros((0, 4)), np.zeros(0), np.zeros(0, dtype=int)
    boxes = np.concatenate(all_boxes, axis=0)
    scores = np.concatenate(all_scores, axis=0)
    cls_ids = np.concatenate(all_cls, axis=0)
    keep = nms_boxes(boxes, scores)
    return boxes[keep], scores[keep], cls_ids[keep]


def draw_boxes(img: np.ndarray, boxes, scores, cls_ids) -> np.ndarray:
    out = img.copy()
    for box, sc, cid in zip(boxes, scores, cls_ids):
        x1, y1, x2, y2 = box.astype(int)
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(out, f"{cid}:{sc:.2f}", (x1, max(y1 - 5, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--onnx", default=None)
    parser.add_argument("--image", default=None)
    parser.add_argument("--output", default=None, help="Visualization output jpg")
    args = parser.parse_args()

    cfg = load_config(args.config)
    root = cfg["_root"]
    onnx_path = Path(args.onnx) if args.onnx else resolve_path(cfg, "onnx_fp32")
    if not onnx_path.exists():
        print(f"ERROR: {onnx_path}")
        return 1

    img_path = Path(args.image) if args.image else root / "data" / "sample" / "test.jpg"
    if not img_path.exists():
        import subprocess

        subprocess.run([sys.executable, str(SCRIPT_DIR / "00_make_sample_image.py")], check=True)

    img0 = _preprocess_mod.imread_unicode(img_path)
    if img0 is None:
        print(f"ERROR: cannot read {img_path}")
        return 1

    letterbox(img0, (640, 640))
    x = np.fromfile(str(resolve_path(cfg, "input_bin")), dtype=np.float32).reshape(tuple(cfg["input_shape"]))

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    outputs = sess.run(None, {cfg["input_name"]: x})
    boxes, scores, cls_ids = decode_yolov5_outputs(outputs)

    vis = draw_boxes(img0, boxes, scores, cls_ids)
    out_path = Path(args.output) if args.output else root / "deliverables" / "05_verify" / "eval_vis.jpg"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".jpg", vis)
    buf.tofile(str(out_path))

    report = root / "deliverables" / "05_verify" / "eval_report.md"
    report.write_text(
        f"# Eval report (sanity check)\n\n"
        f"- image: `{img_path.name}`\n"
        f"- onnx: `{onnx_path.name}`\n"
        f"- detections: {len(boxes)}\n"
        f"- vis: `{out_path.name}`\n\n"
        f"Full mAP requires COCO val + training-aligned postprocess. See docs/06.\n",
        encoding="utf-8",
    )
    print(f"Detections: {len(boxes)}")
    print(f"Wrote {out_path}")
    print(f"Wrote {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
