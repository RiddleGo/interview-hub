# 算子知识库

**对应面试题 Q17**：可检索，不是写 wiki。

## 一条记录模板

```markdown
## 算子：Softmax @ 昇腾 310B

- **芯片 / 工具版本**：Ascend310B1, CANN 8.0.RC2
- **支持精度**：FP16 OK；INT8 检测头敏感
- **限制**：仅 axis=-1 且 dim<128（以官方表为准）
- **推荐替代**：Transpose 到 channel 末维；或 Exp+ReduceSum+Div
- **Tiling 备注**：—
- **踩坑案例**：2025-06 YOLOv5s 检测头 axis=1 Softmax → atc unsupported → 改 axis=-1 后编过，mAP -0.3%
```

## 维护习惯

- 编译 log 里每遇一条 fallback/approx，查是否已有记录
- 命名：`{芯片}_{模型简述}.md`
- 新人先搜再改图
