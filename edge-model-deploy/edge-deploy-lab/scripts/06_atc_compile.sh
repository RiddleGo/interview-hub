#!/usr/bin/env bash
# Phase 2: Copy adapt ONNX if no changes needed (placeholder for graph surgery)
# Phase 4: ATC compile FP16 and INT8

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

copy_adapt() {
  SRC="${ROOT}/deliverables/01_export/model_fp32.onnx"
  DST="${ROOT}/deliverables/02_adapt/model_adapt.onnx"
  if [[ ! -f "$SRC" ]]; then
    echo "ERROR: $SRC missing. Run 01_export_onnx.py first."
    exit 1
  fi
  mkdir -p "$(dirname "$DST")"
  cp "$SRC" "$DST"
  echo "Adapt ONNX (copy-through): $DST"
  echo "If ATC reports unsupported ops, edit graph and replace $DST"
}

atc_compile() {
  local PRECISION="$1"   # fp16 | int8
  local ONNX="$2"
  local OUT="$3"
  local LOG="$4"
  local SOC
  SOC="$(grep '^soc_version:' configs/project.yaml | awk '{print $2}')"
  local INPUT_SHAPE
  INPUT_SHAPE="$(grep '^input_name:' configs/project.yaml | awk '{print $2}' | tr -d '\r'):1,3,640,640"
  # fix input_shape from yaml properly
  INPUT_SHAPE="images:1,3,640,640"

  if ! command -v atc &>/dev/null; then
    echo "ERROR: atc not in PATH. source CANN set_env.sh"
    echo ""
    echo "Dry-run command:"
    echo "  atc --model=$ONNX --output=${OUT%.om} --framework=5 \\"
    echo "      --input_format=NCHW --input_shape=\"$INPUT_SHAPE\" \\"
    echo "      --soc_version=$SOC --output_type=FP16 --log=error"
    return 1
  fi

  mkdir -p "$(dirname "$OUT")"
  local OUTPUT_TYPE="FP16"
  local EXTRA=()
  if [[ "$PRECISION" == "int8" ]]; then
    OUTPUT_TYPE="INT8"
    EXTRA+=(--insert_op_conf="${ROOT}/configs/amct_cfg.cfg")
  fi

  echo "=== ATC $PRECISION ==="
  atc --model="$ONNX" \
      --output="${OUT%.om}" \
      --framework=5 \
      --input_format=NCHW \
      --input_shape="$INPUT_SHAPE" \
      --soc_version="$SOC" \
      --output_type="$OUTPUT_TYPE" \
      --log=error \
      "${EXTRA[@]}" \
      2>&1 | tee "$LOG"

  echo "Wrote $OUT (see $LOG for fallback/approx warnings)"
}

mode="${1:-all}"

case "$mode" in
  adapt)
    copy_adapt
    ;;
  check)
    if ! command -v atc &>/dev/null; then
      echo "atc not found — skip operator check"
      exit 0
    fi
    copy_adapt
    ONNX="${ROOT}/deliverables/02_adapt/model_adapt.onnx"
    atc --model="$ONNX" --mode=1 --framework=5 2>&1 | tee "${ROOT}/deliverables/02_adapt/atc_mode1.log"
    ;;
  fp16)
    copy_adapt
    atc_compile fp16 \
      "${ROOT}/deliverables/02_adapt/model_adapt.onnx" \
      "${ROOT}/deliverables/04_compile/model_fp16.om" \
      "${ROOT}/deliverables/04_compile/atc_fp16.log"
    ;;
  int8)
    INT8="${ROOT}/deliverables/03_quant/model_int8.onnx"
    if [[ ! -f "$INT8" ]]; then
      INT8="${ROOT}/deliverables/02_adapt/model_adapt.onnx"
      echo "WARN: no INT8 ONNX, compiling adapt model as INT8 input"
    fi
    atc_compile int8 "$INT8" \
      "${ROOT}/deliverables/04_compile/model_int8.om" \
      "${ROOT}/deliverables/04_compile/atc_int8.log"
    ;;
  all)
    copy_adapt
    atc_compile fp16 \
      "${ROOT}/deliverables/02_adapt/model_adapt.onnx" \
      "${ROOT}/deliverables/04_compile/model_fp16.om" \
      "${ROOT}/deliverables/04_compile/atc_fp16.log" || true
    if [[ -f "${ROOT}/deliverables/03_quant/model_int8.onnx" ]]; then
      atc_compile int8 \
        "${ROOT}/deliverables/03_quant/model_int8.onnx" \
        "${ROOT}/deliverables/04_compile/model_int8.om" \
        "${ROOT}/deliverables/04_compile/atc_int8.log" || true
    fi
    ;;
  *)
    echo "Usage: $0 {adapt|check|fp16|int8|all}"
    exit 1
    ;;
esac
