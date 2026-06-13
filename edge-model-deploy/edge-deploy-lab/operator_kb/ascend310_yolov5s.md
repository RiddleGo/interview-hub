# 昇腾 310 + YOLOv5s 算子记录（示例）

> 跟练时替换为你自己的 log 结论。以下为 plausible 工程示例。

---

## SiLU / Swish 激活

- **芯片 / 工具版本**：Ascend310P3, CANN 8.0
- **支持精度**：FP16 支持；部分版本 INT8 近似
- **限制**：—
- **推荐替代**：ReLU（掉点需 ORT 验证）；或保留 FP16 skip
- **踩坑案例**：2025-06 全 INT8 后 conf 分布偏移 → skip 最后 Detect 前 2 层 Conv

---

## Resize (opset 11+)

- **芯片 / 工具版本**：Ascend310P3
- **支持精度**：FP16
- **限制**：部分模式仅 nearest；linear 可能近似
- **推荐替代**：固定 scale 时用固定 shape 导出，减少 Resize 次数
- **踩坑案例**：log 提示 approximate nearest → 小目标 mAP -1.2%，换静态 640 减少一层 Resize

---

## GridSample（若模型含）

- **芯片 / 工具版本**：Ascend310
- **支持精度**：常 fallback CPU
- **限制**：NPU 不支持时整段变慢
- **推荐替代**：bilinear 手写等价子图；或改检测头结构
- **踩坑案例**：msprof 显示 GridSample CPU 120ms → 改图后整网 18ms
