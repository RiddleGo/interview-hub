#!/usr/bin/env bash
# Phase 5: ADB push / run infer / pull output for Ascend board
#
# Usage:
#   bash scripts/09_board_infer.sh fp16
#   bash scripts/09_board_infer.sh int8
#   INFER_BIN=/path/to/main bash scripts/09_board_infer.sh fp16

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PRECISION="${1:-fp16}"
REMOTE_DIR="/data/infer"
ADB="${ADB:-adb}"

if [[ "$PRECISION" == "fp16" ]]; then
  OM="${ROOT}/deliverables/04_compile/model_fp16.om"
else
  OM="${ROOT}/deliverables/04_compile/model_int8.om"
fi
INPUT="${ROOT}/deliverables/05_verify/input.bin"
OUTPUT_LOCAL="${ROOT}/deliverables/05_verify/output_npu.bin"
INFER="${INFER_BIN:-infer}"

if [[ ! -f "$OM" ]]; then
  echo "ERROR: $OM not found. Run scripts/06_atc_compile.sh $PRECISION"
  exit 1
fi
if [[ ! -f "$INPUT" ]]; then
  echo "ERROR: $INPUT not found. Run scripts/03_preprocess.py"
  exit 1
fi

echo "=== Board infer ($PRECISION) ==="
$ADB devices

$ADB shell "mkdir -p $REMOTE_DIR"
$ADB push "$OM" "$REMOTE_DIR/model.om"
$ADB push "$INPUT" "$REMOTE_DIR/input.bin"

if [[ -n "${INFER_BIN:-}" && -f "$INFER" ]]; then
  $ADB push "$INFER" "$REMOTE_DIR/infer"
  $ADB shell "chmod +x $REMOTE_DIR/infer"
fi

# Generic infer invocation — adjust to your CANN sample main
# Args: model.om input.bin output.bin input_shape
$ADB shell "cd $REMOTE_DIR && \
  export LD_LIBRARY_PATH=$REMOTE_DIR:\${LD_LIBRARY_PATH:-} && \
  if [ -x ./infer ]; then \
    ./infer ./model.om ./input.bin ./output_npu.bin 1,3,640,640; \
  else \
    echo 'Set INFER_BIN to your ACL infer executable'; \
    echo 'Example: INFER_BIN=/path/to/main bash scripts/09_board_infer.sh fp16'; \
    exit 2; \
  fi"

$ADB pull "$REMOTE_DIR/output_npu.bin" "$OUTPUT_LOCAL"
echo "Pulled $OUTPUT_LOCAL"
echo "Compare: python scripts/07_compare.py"
