#!/usr/bin/env bash
# Phase 3: AMCT PTQ wrapper for Ascend CANN
# Prerequisite: source ${ASCEND_HOME}/bin/setenv.bash (or your CANN set_env.sh)
#
# Usage:
#   bash scripts/05_amct_quantize.sh
#   bash scripts/05_amct_quantize.sh --dry-run

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${ROOT}/configs/project.yaml"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

# Parse paths from yaml (minimal grep — avoid yq dependency)
ONNX_ADAPT="${ROOT}/deliverables/02_adapt/model_adapt.onnx"
if [[ ! -f "$ONNX_ADAPT" ]]; then
  ONNX_ADAPT="${ROOT}/deliverables/01_export/model_fp32.onnx"
fi
OUT_DIR="${ROOT}/deliverables/03_quant"
AMCT_CFG="${ROOT}/configs/amct_cfg.cfg"
INPUT_SHAPE="images:1,3,640,640"

mkdir -p "$OUT_DIR"

if ! command -v amct_onnx &>/dev/null; then
  echo "ERROR: amct_onnx not in PATH."
  echo "  source your CANN environment, e.g.:"
  echo "  source /usr/local/Ascend/ascend-toolkit/set_env.sh"
  echo ""
  echo "Fallback (PC-only exercise): use ORT static quantization"
  echo "  python scripts/05_ort_quantize.py --config configs/project.yaml"
  exit 1
fi

echo "=== AMCT PTQ ==="
echo "Input ONNX: $ONNX_ADAPT"
echo "Output dir: $OUT_DIR"
echo "Config:     $AMCT_CFG"

CMD=(amct_onnx calibration
  --model "$ONNX_ADAPT"
  --save_path "$OUT_DIR"
  --input_shape "$INPUT_SHAPE"
)

if [[ -f "$AMCT_CFG" ]]; then
  CMD+=(--config_file "$AMCT_CFG")
fi

echo "Command: ${CMD[*]}"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "(dry-run, not executing)"
  exit 0
fi

"${CMD[@]}" 2>&1 | tee "${OUT_DIR}/amct_quant.log"

# Normalize output name
INT8_ONNX="${OUT_DIR}/model_int8.onnx"
if [[ ! -f "$INT8_ONNX" ]]; then
  FOUND="$(find "$OUT_DIR" -name '*quant*.onnx' -o -name '*int8*.onnx' 2>/dev/null | head -1)"
  if [[ -n "$FOUND" ]]; then
    cp "$FOUND" "$INT8_ONNX"
    echo "Copied $FOUND -> $INT8_ONNX"
  fi
fi

echo "Done. Check ${OUT_DIR}/amct_quant.log and verify QDQ nodes in Netron."
