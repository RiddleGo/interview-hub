# 七阶段验收 Checklist（可打印）

前一阶段全部打勾后再进下一阶段。

---

## 阶段 0 · 环境

```
[ ] Python 3.8+，pip install -r requirements.txt 成功
[ ] CANN 环境已 source，atc --help 可用
[ ] amct_onnx 可用（或已知用 05_ort_quantize.py 代替）
[ ] npu-smi info 或 adb devices 可见设备
[ ] yolov5s.pt 已放入 deliverables/01_export/
[ ] configs/project.yaml 中 soc_version 与板子一致
```

---

## 阶段 1 · 导出（Q1–Q4）

```
[ ] model.eval()，静态 input shape [1,3,640,640]
[ ] Opset 与 ORT + ATC 组合实测兼容
[ ] onnx.checker 通过，无 aten:: 残留
[ ] ORT 与 PyTorch/导出源输出余弦 > 0.999
[ ] export_log.md 已记录 torch/opset/shape
[ ] （练习）--dynamic 导出后 Netron 见动态维，已改回静态
```

---

## 阶段 2 · 改图（Q5, Q13, Q17）

```
[ ] atc --mode=1 预检已跑，log 已存档
[ ] 不兼容算子已等价替换或记录 workaround
[ ] model_adapt.onnx ORT 回归通过
[ ] operator_kb 至少新增 1 条记录
[ ] Netron 算子 Top15 已扫一眼
```

---

## 阶段 3 · 量化（Q6–Q12, Q24, Q29）

```
[ ] 手算对称量化 round-trip 1 题
[ ] 校准集 ≥100 张，预处理与 03_preprocess 一致
[ ] AMCT 或 ORT 静态量化产出 model_int8.onnx
[ ] Netron 可见 QDQ 节点（Q11）
[ ] ORT 跑 INT8，关键层余弦在门槛内
[ ] （练习）--wrong-norm 踩坑后已修复
[ ] skip_layers.txt 有初筛候选（08_layerwise_dump）
```

---

## 阶段 4 · 编译（Q14–Q16, Q18, Q22）

```
[ ] FP16 model_fp16.om 编译成功，log 已 tee
[ ] INT8 model_int8.om 编译成功（若有 INT8 ONNX）
[ ] log 中 fallback / approx / fusion failed 已摘录
[ ] msprof 或等效性能初测已做（延迟 + MAC 利用率）
[ ] 能解释 INT8 不一定更快（Q18）
```

---

## 阶段 5 · 双端（Q19–Q21, Q20, Q23）

```
[ ] PC 生成 input.bin，设备不再做预处理
[ ] input.bin MD5 双端一致
[ ] FP16 双端余弦过关后再比 INT8
[ ] head 各分支单独对比，不只全局余弦
[ ] compare_report.json 已生成
[ ] adb push/run/pull 流程跑通
```

---

## 阶段 6 · 业务（Q10, Q23, Q27）

```
[ ] eval_vis.jpg 可视化合理
[ ] 3 张坏例有分类结论（漏检/误检/框偏）
[ ] 后处理参数与训练脚本对齐（letterbox 逆变换等）
[ ] skip_layers 调优一轮（若 mAP/可视化不达标）
[ ] （选修 Q26/Q28）多档 om 或 FLOPs vs 延迟对比
```

---

## 阶段 7 · 归档（Q25–Q30）

```
[ ] release/v1.0/ 打包完整
[ ] release_note.md 四维上线表已填
[ ] operator_kb 本次踩坑已更新
[ ] 3 分钟「部署工程师日常」口述稿（Q30）
[ ] 7 阶段全链路讲解稿（Q25）
[ ] 随机 10 题快问快答自测通过
```
