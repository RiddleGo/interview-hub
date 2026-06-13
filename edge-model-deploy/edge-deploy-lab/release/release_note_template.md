# Release Note — EdgeDeployLab v1.0

> 复制本模板到 `release/v1.0/release_note.md` 并填实数（Q27 四维上线表）

---

## 版本信息

| 项 | 值 |
|----|-----|
| 模型 | YOLOv5s |
| 输入 shape | [1, 3, 640, 640] |
| PyTorch | |
| ONNX Opset | |
| CANN | |
| 驱动 / 固件 | |
| soc_version | |
| 校准集 hash | |
| 日期 | |

---

## 一、张量门禁

| 层级 | 余弦阈值 | 实测 | 通过 |
|------|----------|------|------|
| backbone 最差层 | ≥ 0.98 | | [ ] |
| head 分支 | ≥ 0.99 | | [ ] |
| 整网 min | | | [ ] |

附：`compare_report.json`

---

## 二、任务门禁

| 指标 | FP32 基线 | INT8 实测 | 掉点上限 | 通过 |
|------|-----------|-----------|----------|------|
| mAP@0.5 | | | ≤ 2% | [ ] |
| 误检率 | | | | [ ] |

坏例 3 张：

1. 
2. 
3. 

---

## 三、系统门禁

| 指标 | 要求 | 实测 | 通过 |
|------|------|------|------|
| P99 延迟 (ms) | | | [ ] |
| 峰值内存 (MB) | | | [ ] |
| 稳态功耗 (W) | | | [ ] |
| 温升 (°C, 1h) | | | [ ] |

---

## 四、编译 Warning 摘要

```
（从 atc_*.log 摘录 fallback / approx / fusion failed）
```

---

## 五、交付文件清单

- [ ] model_fp32.onnx
- [ ] model_int8.onnx
- [ ] model_int8.om
- [ ] input.bin / output_ort.bin / output_npu.bin
- [ ] compare_report.json
- [ ] eval_report.md
- [ ] compile log
- [ ] operator_kb 更新

---

## 回滚

上一稳定版路径：

---

## 签字 / 评审

| 角色 | 姓名 | 日期 |
|------|------|------|
| 部署 | | |
| 算法 | | |
| 测试 | | |
