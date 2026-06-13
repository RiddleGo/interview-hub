# 阶段 4：ATC 编译与性能

**覆盖面试题**：Q14–Q16, Q18, Q22  
**深读**：[芯片编译：开篇黑话、Kernel与Tiling从0搞懂.md](../../芯片编译：开篇黑话、Kernel与Tiling从0搞懂.md)、[FLOPs与卷积核尺寸_Pro.md](../../FLOPs与卷积核尺寸_Pro.md)

---

## 操作步骤

```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh   # 你的 CANN 路径

bash scripts/06_atc_compile.sh fp16
bash scripts/06_atc_compile.sh int8   # 需先有 model_int8.onnx
```

日志：

- `deliverables/04_compile/atc_fp16.log`
- `deliverables/04_compile/atc_int8.log`

---

## 读 log（Q22）

全文搜索：

```
fallback
CPU
approx
unsupport
fusion failed
Transpose
```

每条 Warning 评估：影响精度还是性能？摘录到 `release/compile_warning_summary.txt`。

---

## 性能初测

```bash
msprof --application="your_infer ..." --output=./msprof_out
```

记录：单帧延迟、MAC 利用率、DDR 带宽。

---

## 口述要点

- **Q14 Tiling**：SRAM 放不下时 compiler 分块；块太小 launch 多，块太大 DDR 打满。
- **Q15 Fusion**：Conv+BN+ReLU 合成一 kernel，中间不写 DDR。
- **Q16**：FLOPs 差不多，7×7 可能比 3×3 堆叠慢——利用率 + 访存。
- **Q18**：INT8 不更快可能因为假 int8、CPU fallback、Transpose 多、Tiling 差。

---

## 验收标准

- [ ] `model_fp16.om` 编译成功
- [ ] log 已存档并摘录高危 Warning
- [ ] msprof 或等效延迟数字已记录

---

**下一步**：[05-双端验收与上板.md](05-双端验收与上板.md)
