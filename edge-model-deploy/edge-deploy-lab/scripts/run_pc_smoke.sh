#!/usr/bin/env bash
# PC-side smoke test (no CANN / no board required)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== EdgeDeployLab PC smoke test ==="

python scripts/00_make_sample_image.py

if [[ ! -f deliverables/01_export/yolov5s.pt ]]; then
  echo "Downloading yolov5s.pt ..."
  mkdir -p deliverables/01_export
  python -c "
import urllib.request
url='https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt'
urllib.request.urlretrieve(url, 'deliverables/01_export/yolov5s.pt')
print('Downloaded yolov5s.pt')
"
fi

python scripts/01_export_onnx.py --config configs/project.yaml
python scripts/02_check_onnx.py --config configs/project.yaml
bash scripts/06_atc_compile.sh adapt
python scripts/03_preprocess.py --config configs/project.yaml
python scripts/04_ort_golden.py --config configs/project.yaml

# Simulate NPU output = ORT (perfect cosine) for pipeline test
cp deliverables/05_verify/output_ort.bin deliverables/05_verify/output_npu.bin
python scripts/07_compare.py --config configs/project.yaml
python scripts/10_eval_detect.py --config configs/project.yaml

echo ""
echo "=== PC smoke test PASSED ==="
echo "Next: CANN env -> bash scripts/06_atc_compile.sh fp16"
echo "       Board -> INFER_BIN=... bash scripts/09_board_infer.sh fp16"
