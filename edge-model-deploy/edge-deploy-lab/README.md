# EdgeDeployLab — YOLOv5s 昇腾 310 全链路实战

从零跟完一个 **检测模型边缘部署** 课题，产出可面试展示的作品集：ONNX → 改图 → PTQ → ATC → 双端验收 → 归档。

**载体**：YOLOv5s · **芯片**：昇腾 310 系列（`configs/project.yaml` 改 `soc_version`）  
**预计周期**：4 周 × 每天 2～3 小时  
**面试题覆盖**：[`../边缘模型部署-面试题.md`](../边缘模型部署-面试题.md) 全部 30 题

---

## 前置条件

| 项 | 要求 |
|----|------|
| Python | 3.8+ |
| PC | PyTorch、ONNX Runtime（`pip install -r requirements.txt`） |
| 昇腾 | CANN + AMCT + `atc` 在 PATH（`source set_env.sh`） |
| 开发板 | adb 可用，ACL infer 可执行文件（见 `docs/05`） |
| GPU | 可选，仅加速 PyTorch 侧 |

---

## 快速开始

```bash
cd edge-deploy-lab
pip install -r requirements.txt

# 1. 下载权重
mkdir -p deliverables/01_export
wget -O deliverables/01_export/yolov5s.pt \
  https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt

# 2. 生成示例图（或放自己的图到 data/sample/）
python scripts/00_make_sample_image.py

# 3. 按阶段执行（见 docs/01 起）
python scripts/01_export_onnx.py --config configs/project.yaml
python scripts/02_check_onnx.py
python scripts/03_preprocess.py
python scripts/04_ort_golden.py
bash scripts/06_atc_compile.sh adapt    # 复制 adapt ONNX
bash scripts/06_atc_compile.sh check    # atc 算子预检（需 CANN）
# ... 量化、编译、上板见各阶段文档

# PC 侧冒烟（无 NPU / 无网络时）
python scripts/run_pc_smoke.py --minimal
```

---

## 七阶段导航

| 阶段 | 文档 | 核心脚本 | 交付物 |
|------|------|----------|--------|
| 0 环境 | [docs/00-环境准备.md](docs/00-环境准备.md) | — | CANN/atc 可用 |
| 1 导出 | [docs/01-导出与图.md](docs/01-导出与图.md) | `01_export_onnx.py` `02_check_onnx.py` | `model_fp32.onnx` |
| 2 改图 | [docs/02-算子兼容与改图.md](docs/02-算子兼容与改图.md) | `06_atc_compile.sh check` | `model_adapt.onnx` |
| 3 量化 | [docs/03-量化与校准.md](docs/03-量化与校准.md) | `05_prepare_calib.py` `05_amct_quantize.sh` | `model_int8.onnx` |
| 4 编译 | [docs/04-ATC编译与性能.md](docs/04-ATC编译与性能.md) | `06_atc_compile.sh` | `model_*.om` + log |
| 5 双端 | [docs/05-双端验收与上板.md](docs/05-双端验收与上板.md) | `09_board_infer.sh` `07_compare.py` | `compare_report.json` |
| 6 业务 | [docs/06-进阶选题.md](docs/06-进阶选题.md) | `10_eval_detect.py` | `eval_report.md` |
| 7 归档 | [docs/07-转身作品集.md](docs/07-转身作品集.md) | — | `release/v1.0/` |

可打印清单：[checklists/7phase_checklist.md](checklists/7phase_checklist.md)

---

## 30 题 → 阶段 → 脚本 → 验收

| 题号 | 主题 | 阶段 | 脚本 / 动作 | 验收标准 |
|------|------|------|-------------|----------|
| Q1 | .pt / ONNX / 芯片模型 | 1 | `01_export_onnx.py` | 能口述三者职责 |
| Q2 | 静态 / 动态 shape | 1 | `01_export_onnx.py --dynamic` | Netron 见静态 `[1,3,640,640]` |
| Q3 | Opset | 1 | `02_check_onnx.py` | checker 通过，opset 写入 export_log |
| Q4 | ORT vs NPU | 1,5 | `04_ort_golden.py` + 板端 | 理解双端差异 |
| Q5 | Softmax unsupported | 2 | `06_atc_compile.sh check` | log 无致命 unsupported |
| Q6 | 对称量化公式 | 3 | docs/03 手算练习 | 手算 round-trip 误差 |
| Q7 | 校准集 | 3 | `05_prepare_calib.py` | ≥100 张，预处理一致 |
| Q8 | PTQ vs QAT | 3 | `05_amct_quantize.sh` | 默认 PTQ 流程跑通 |
| Q9 | per-tensor/channel | 3 | Netron 看 QDQ | 能口述权重/激活策略 |
| Q10 | 余弦 99% 能上线吗 | 5,6 | `07_compare.py` | 分层 + 业务指标 |
| Q11 | QDQ vs QOperator | 3 | Netron | INT8 图为 QDQ |
| Q12 | mAP 掉点排查 | 3,5 | `--wrong-norm` 踩坑 | 预处理优先 |
| Q13 | 算子搜索 | 2 | operator_kb | 至少 5 条记录 |
| Q14 | Tiling | 4 | msprof / log | 能解释 Tiling |
| Q15 | Fusion | 4 | 读 atc log | 找 fusion failed |
| Q16 | 7×7 vs 3×3 | 4 | docs/06 选修 | FLOPs≠延迟 |
| Q17 | 知识库格式 | 2–7 | `operator_kb/` | 按模板写记录 |
| Q18 | INT8 更慢 | 4 | msprof | 列 5 类原因 |
| Q19 | NPU vs GPU | 0 | 读 NPU与GPU Pro | 一句话对比 |
| Q20 | 同 input.bin | 5 | `03_preprocess.py` | MD5 一致 |
| Q21 | ADB 流程 | 5 | `09_board_infer.sh` | pull output 成功 |
| Q22 | 转换工具干什么 | 4 | `06_atc_compile.sh` | log 归档 |
| Q23 | 余弦高框乱 | 6 | `10_eval_detect.py` | head 分支 + 后处理 |
| Q24 | skip_layers | 3,6 | `08_layerwise_dump.py` | skip 列表有依据 |
| Q25 | 全链路 | 7 | docs/07 | 7 阶段讲稿 |
| Q26 | 动态多分辨率 | 6 选修 | 多档 om | 可选 |
| Q27 | 量化上线标准 | 7 | release_note | 四维表填实 |
| Q28 | FLOPs vs 延迟 | 6 选修 | profiler | 可选 |
| Q29 | 动静态 PTQ | 3 | docs/03 | 边缘用静态 PTQ |
| Q30 | 部署工程师日常 | 7 | docs/07 | 3 分钟口述 |

---

## 目录结构

```
edge-deploy-lab/
├── README.md              ← 你在这里
├── configs/project.yaml   ← 改 soc_version、路径
├── docs/00–07             ← 分阶段教程
├── scripts/               ← 可运行脚本
├── operator_kb/           ← 踩坑记录（Q17）
├── calib/images/          ← 校准图片
├── deliverables/          ← 各阶段产物（大文件 gitignore）
└── release/               ← 最终作品集模板
```

---

## 深读专栏（主仓库）

| 阶段 | 推荐 |
|------|------|
| 全链路 | [从训练到边缘上线全链路_Pro.md](../从训练到边缘上线全链路_Pro.md) |
| 双端 | [双端精度验证与ADB上板_Pro.md](../双端精度验证与ADB上板_Pro.md) |
| 编译 | [芯片模型转换工具_Pro.md](../芯片模型转换工具_Pro.md) |
| 量化 | [量化可上线标准_Pro.md](../量化可上线标准_Pro.md) |
| 面试 | [边缘模型部署-面试题.md](../边缘模型部署-面试题.md) |

---

## 常见问题

**没有 CANN 环境？**  
PC 侧可完成阶段 1～3（用 `05_ort_quantize.py` 代替 AMCT），阶段 4～5 用 `run_pc_smoke.sh` 模拟双端。

**atc 编不过？**  
看 `deliverables/02_adapt/atc_mode1.log`，按 [docs/02](docs/02-算子兼容与改图.md) 改图后替换 `model_adapt.onnx`。

**板端 infer？**  
本仓库不捆绑 C++ demo；设置 `INFER_BIN=/path/to/your/main bash scripts/09_board_infer.sh fp16`。
