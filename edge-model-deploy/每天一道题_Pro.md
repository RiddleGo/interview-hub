# 算子知识库怎么记？INT8 比 PC FP32 还慢先查什么？

> **导读**：官方文档写「支持 Softmax」，不会写「第 2 维做 Softmax 整层 6ms」；INT8 文件名也不代表真走硬件 MAC。两件事都靠 **可检索的经验** 和 **profiler 分层数据**，别靠猜。  
> **阅读时间**：约 22 分钟  
> **适合谁**：能编过芯片模型、带过新人上板，想建立团队避坑记录、或遇到「INT8 反而慢」的工程师。

---

## 交付文件夹里两样事：Wiki 搜不到，Profiler 才说话

口头说「量化模型上线了」，文件夹里往往有三种东西：ORT 用的 FP32 ONNX、校准过的 INT8 ONNX、芯片侧 `.om` / `.bin`。新人遇到 unsupported，先去翻 **Notion/语雀里有没有「Softmax + 昇腾 310」**——没有记录，就要从零改图；遇到「INT8 比笔记本 FP32 还慢」，老板问是不是 NPU 假的——**先别改模型，先查对比是否公平、INT8 是否真的在 MAC 上跑**。

这两题在部署链路里位置不同：**算子知识库** 沉淀在算子搜索和 unsupported 处理阶段；**INT8 性能异常** 出现在 PTQ 之后、上板 profiling 阶段。但习惯一样：**现象 → 日志/profiler → 改什么 → 写回知识库**。

---

## 它们在部署链路里干什么

```
  .pt → ONNX (FP32) → ORT 验收
              │
              ▼  算子搜索 / graph surgery
  ┌──────────────────────────────────────────────┐
  │  unsupported？先搜算子知识库                    │  ← 主题一
  │  记录：限制、替代、tiling、踩坑（日期+模型）     │
  └──────────────────────────────────────────────┘
              │
              ▼  PTQ / 校准 → INT8 ONNX
              │
              ▼  converter（ATC / trtexec 等）
  芯片模型
              │
              ▼  实机 profiling                      ← 主题二
  ┌──────────────────────────────────────────────┐
  │  INT8 比 PC 慢？：公平对比 → MAC 路径 →        │
  │  内存型算子 → CPU fallback → tiling → 动态 shape │
  └──────────────────────────────────────────────┘
              │
              ▼  任务验收 + 知识库更新
  交付
```

---

## 零基础先搞懂：本篇会反复出现的名词

### 算子（Operator）和算子知识库

**算子** 是计算图里的节点：`Conv`、`Softmax`、`Transpose` 等。Netron 里每个方框基本对应一个算子。

**算子知识库** 不是把官方 PDF 抄一遍，而是团队 **踩坑后可检索** 的记录：某芯片、某 CANN 版本下，这个算子 **真正有什么限制、用什么替代、哪次项目翻过车**。价值在 **搜「算子名 + 芯片」能立刻翻到替代方案**，而不是写百科全书。

### 官方文档 vs 知识库

厂商文档回答「支不支持、参数范围是什么」。它通常 **不会写**：某 axis 上 Softmax 慢一个数量级、某 CANN 小版本的 INT8 会插满 Cast、某 kernel 要拆成 3×3 才稳。这些只有项目里摔过才知道——知识库补的就是这层。

### CANN、ATC、converter

**CANN** 是昇腾的芯片软件栈（算子库、编译器、驱动等）。**ATC（Ascend Tensor Compiler）** 是把 ONNX 转成 `.om` 的 converter 之一。面试里说「看 ATC 日志」≈ 看编译阶段有没有 fallback、量化了多少层、有没有动态 shape 警告。其他芯片对应 trtexec、SNPE 等，思路相同。

### INT8 与「假量化」

**INT8** 用 8 位整数存权重和激活，硬件 MAC 算力常比 FP16 高，**前提是算子真走 INT8 引擎**。假量化指：图里名字是 INT8，但大量 **Quantize/Dequantize（Q/DQ）** 或 **Cast** 在 FP16/FP32 和 INT8 之间来回倒，MAC 没吃满，有时比纯 FP16 还慢。编译日志和 `op_summary` 里的 **Precision 列** 能看出来。

### MAC 利用率

**MAC（Multiply-Accumulate，乘加）** 是 NPU 算力单位。**MAC 利用率** = 实际吞吐 ÷ 芯片峰值。INT8 路径正常时，利用率 often 比 FP16 高一些；若 INT8 和 FP16 利用率差不多，却更慢，多半 **没在真 INT8 上算**，或 **DDR 在等数据**。

### 内存型算子（Memory-bound ops）

**Transpose、Slice、Gather、Concat、Resize** 等，主要时间在 **搬数据**，算术很少。INT8 只能加速 Conv、MatMul 这类 **计算型** 算子；内存型算子 INT8/FP16 差距不大，Cast 多了还可能更慢。Profiler 按耗时排序，若前几名全是这类，整网 INT8 加速会有限。

### CPU fallback（回退 CPU）

某算子 **NPU 不支持** 或编译失败时，runtime 把该节点放到 **CPU** 上跑。日志常有 `CPU fallback`、`Host`、`unsupported` 字样；profiler 里 **Device=CPU**。一两个小 op 不一定致命，attention 里关键路径 fallback 会让延迟崩掉。

### Tiling（分块）

**Tiling** 是把大张量切成块塞进片上 SRAM。**Tiling 极差** 时 MAC 闲着、DDR 带宽顶满——INT8 算得更快，更容易暴露访存瓶颈。INT8 和 FP16 的 **最优 tile 往往不同**，换精度后有时要重跑 AutoTune。

### 动态 shape（Dynamic Shape）

输入 batch 或高宽 **运行时变**，编译器无法一次规划死内存。很多 NPU 的 INT8 对动态轴支持弱：**每次新尺寸走慢路径或重新编译**。静态 shape 延迟更稳；动态需求要先查 toolchain release note。

### Profiler（msprof 等）

**Profiler** 导出 **算子级耗时、精度、设备、DDR 带宽**。别猜「是不是 Softmax 慢」——打开 `op_summary.csv` 按 Time 排序。INT8 排查和知识库验证（改图后快多少）都应以 profiler 为准。

---

## 主题一：算子知识库一条记录写什么

### 它到底是什么

一条记录 = **一个算子 + 一颗芯片（或系列）+ 一个工具版本范围** 下的 deploy 事实。不是论文笔记，是 **下次同类问题 30 秒能搜到答案** 的卡片。

### 七个字段（最少要有）

| 字段 | 写什么 | 直觉 |
|------|--------|------|
| 算子名 | 与 ONNX 一致，变种写清（如 `DepthwiseConv`） | 搜的就是这个词 |
| 芯片型号 / 工具版本 | 如昇腾 310，CANN 5.1～6.0 | 换版本可能整表作废 |
| 支持精度 | FP16 / INT8 / 仅 FP32 | 「支持 INT8」≠ 「INT8 更快」 |
| 限制 | axis、kernel、shape 上限、对齐、是否动态 | 官方不全写，这是核心价值 |
| 推荐替代 | 数学等价或近似等价子图 | 附精度/性能大致影响 |
| tiling 备注 | 某 input shape 下较优 tile | 来自 AutoTune 或实测 |
| 踩坑案例 | 日期 + 模型 + 现象 → 改法 → 效果 | 新人最爱抄作业 |

口述版面试答法：**至少算子名、芯片/版本、支持精度、限制、推荐替代、tiling 备注、踩坑案例（带日期和模型）**。价值在于 **可检索**，不是写 wiki。新人先搜「Softmax + 昇腾 310」有没有记录，再决定要不要改图。

### 一条完整示例（可直接当模板）

```
【算子名】Softmax
【芯片型号/工具版本】昇腾 310，CANN 5.1.RC1～6.0.RC1
【支持精度】FP16，INT8（对称）
【限制】
  · 硬件友好路径多在最后一维 axis=-1
  · 最后一维长度常见上限约 8192（以当前算子表为准）
  · 中间维 Softmax 可能极慢或需拆图
【推荐替代】
  · 中间维：Reshape → 最后一维 Softmax → Reshape
  · 维度过大：分块 Softmax
【Tiling 备注】
  · 分类头 [1,1000]：默认即可；Transformer 大维注意 channel 对齐 16
【踩坑案例】
  · 2023-05，YOLOv8，axis=1 Softmax 单层 ~6ms → Reshape 方案 ~0.5ms
  · 2024-01，某 DETR 头，unsupported → 拆 Exp+ReduceSum+Div，ORT 对齐后再编
```

表后补一句：**限制 + 推荐替代 + 踩坑** 三列是别人搜你这条记录的原因；只抄官方「支持列表」没必要单独建页。

### 怎么建、怎么维护

初始：从 **团队历史 incident** 和 **最常 unsupported 的十个算子** 开始（Conv、MatMul、Softmax、LayerNorm、Resize、Transpose…），别企图一天填完厂商整本手册。

日常：**每次改图/换 CANN 解决一个问题，当天补一条或更新版本号**。升级 CANN 后，把 release note 里 Fusion/算子变更和知识库 **对一遍**，过时条目标「已修复于 x.x」。

工具：用 **Notion / Confluence / 语雀** 等能全文搜的；纯 Excel 难检索。一 Op 一页，标题里带芯片型号。

我见过最浪费时间的模式：同一个 Softmax 坑三个人各踩一遍，因为第一次解决的人只写在 IM 里。**解决完不写库 = 下次还从零排查。**

---

## 主题二：INT8 芯片模型比 PC FP32 还慢

### 先建立正确预期

INT8 的主战场通常是 **吞吐和功耗**（大 batch、常在线推理），不是「文件名带 int8 单 batch 一定比 PC FP32 快」。PC 上 ORT+CUDA/TensorRT 优化了多年；NPU 上 INT8 若没走满 MAC、或图里全是搬数据的 op，**单帧比 PC 慢不稀奇**。要先 **公平对比**，再 **profiler 分层**，别先改 backbone。

### 排查顺序（按优先级）

**第 0 步：对比是否公平。** 坑我见得最多的：PC 用 GPU FP32 **batch=8**，设备 INT8 **batch=1**；或 PC 用 TensorRT、设备用未开优化的原生推理；或 NPU 第一次推理含编译时间、PC 已预热十轮。公平对比至少对齐：**同 batch（常 1）、同输入 shape、同预热轮数、空载环境**。吞吐对比另说——INT8 在大 batch 下往往才拉开差距。

**第 1 步：INT8 是否真的走 MAC。** 查 ATC/convert 日志：多少层量化成 INT8；Quantize/Dequantize 是否过多。Profiler 看各 op 的 **Precision**：若大量 FP16 + 来回 Cast，就是假量化或敏感层未量化成功。MAC 利用率若和 FP16 差不多，却标 INT8，要怀疑路径。常见原因：校准集分布不对、LayerNorm/Softmax 等 INT8 支持差被回退、老 CANN 量化 bug、手动插 Q/DQ 打断融合。

**第 2 步：内存型算子是否占大头。** `Transpose`、`Slice`、`Gather`、`Concat` 在 `op_summary` 里按耗时靠前，且 DDR 带宽占比高 → 整网 memory-bound，INT8 加速 Conv 也拉不动整图。改法：graph surgery 减 Transpose、改 layout（如少 NCHW↔NHWC 来回）、能 fuse 的链 fuse 掉——和算子知识库里「替代/布局」条目联动。

**第 3 步：CPU fallback。** 日志搜 `CPU fallback`、`unsupported`；profiler 看 Device=CPU 的 op。RoPE、自定义 op、老版本不支持的 Norm 都见过。改法：换等价子图、拆 op、或登记厂商复合算子—— **fallback 的节点写进知识库「踩坑案例」**。

**第 4 步：Tiling / 融合。** INT8 算得快，更容易 **等 DDR**。MAC 低、DDR 高 → 重跑 AutoTune 或调 fusion 开关；看 Conv+BN 是否融成一颗、Q/DQ 是否把链打断。INT8 的最优 tile **不一定等于** FP16，换精度后我会单独 profile 一层。

**第 5 步：动态 shape。** 每次推理耗时抖动大、或日志有 dynamic shape 警告 → 查是否 runtime 反复编译或走通用慢路径。能静态就静态；必须动态则查 toolchain 对 **动态 INT8** 的支持边界。

用厂商 profiler 看 **算子耗时排行**，别猜。结论要带 **版本 + 输入 shape + 哪几步有效**，方便写回知识库。

---

## 最常见坑

### 坑 1：知识库写成官方文档复印件

**做法**：把算子表 PDF 贴进 Notion，没有踩坑和替代。

**现象**：新人搜「Softmax 慢」仍不知道从哪维改起。

**原因**：缺限制、替代、实测 case，不可检索。

**怎么查**：随机让同事搜三个历史 incident，能否在 1 分钟内找到。

**怎么改**：每条必须有 **推荐替代 + 至少一条踩坑（日期+模型）**；官方有的只留链接到芯片，正文写「我们实测差异」。

### 坑 2：INT8 慢就回头改 QAT，对比其实不公平

**做法**：PC batch=8 GPU，板端 batch=1，得出「INT8 骗局」。

**现象**：报告里数字对不上，团队互相不信。

**原因**：吞吐 vs 延迟、预热、引擎不一致。

**怎么查**：对齐 batch、预热、shape，再比单帧。

**怎么改**：报告分 **latency@batch=1** 和 **throughput@batch=N** 两栏写清。

### 坑 3：看到 INT8 文件名就认定走了 INT8 MAC

**做法**：不打开 profiler，直接和客户吹 INT8 加速比。

**现象**：op 大量 FP16 Cast，延迟比 FP16 模型还高。

**原因**：假量化或回退。

**怎么查**：`op_summary` 的 Precision + MAC 利用率。

**怎么改**：校准/混合精度/换敏感层 FP16；记录到知识库「某层必须 FP16」。

### 坑 4：解决过的问题不写库

**做法**：改图一周，上线后只口头交接。

**现象**：换同事或换 CANN 版本，同一 unsupported 再耗三天。

**原因**：经验不可检索。

**怎么查**：团队有没有「Softmax+310」条目。

**怎么改**：上线 checklist 加一条 **「新 incident 是否已写入算子库」**。

---

## 面试追问

### 1

**问：** 算子知识库一条记录至少写什么？

**答：** 至少算子名、芯片型号和工具版本、支持精度、限制（axis/kernel/shape 等）、推荐替代、tiling 备注、踩坑案例（日期+模型+现象+改法）。价值是可检索，让新人搜「算子+芯片」就能决定要不要改图，不是抄官方 wiki。

### 2

**问：** 官方有算子文档，为什么还要自建知识库？

**答：** 官方写「支不支持」和参数范围，很少写 **特定 axis 慢十倍、某版本 INT8 假量化、某 kernel 要拆 3×3** 这类项目经验。知识库存的是 **限制+替代+实测 case**，换人不丢，避免同一坑反复踩。

### 3

**问：** INT8 芯片模型比 PC FP32 慢，你第一查什么？

**答：** 先查对比是否公平：batch、预热、shape、引擎是否一致。再 profiler 看 INT8 是否真走 MAC（Precision 列、Cast/QDQ 是否过多），然后按耗时看 memory-bound 算子、CPU fallback、tiling、动态 shape。别先大改模型。

### 4

**问：** 什么叫 INT8 假量化？

**答：** 图里标了 INT8，但很多算子在 FP16/FP32 和 INT8 之间 Cast 或 Q/DQ 来回，MAC 没吃满，有时比纯 FP16 还慢。看编译日志量化层数和 profiler 的 Precision；敏感层回退、校准不对、手动插 Q/DQ 打断融合都常见。

### 5

**问：** 知识库和 INT8 排查怎么配合？

**答：** 排查得到稳定结论（某 op 必须替代、某层必须 FP16、某 tile 有效）就 **写进知识库**。下次同类模型先搜库再改图；INT8 慢若是 Transpose 堆叠，库里有 layout 改法就直接用。Profiler 验证效果，知识库沉淀规则，两件事闭环。

---

## 附录 A：checklist（可打印）

**算子知识库**

```
[ ] 每条含：算子名、芯片/版本、精度、限制、替代、tiling、踩坑（日期+模型）
[ ] 标题/标签可搜「算子名 + 芯片型号」
[ ] 优先覆盖团队最常 unsupported 的算子
[ ] 升级 CANN/换芯片后已复核或标注过时
[ ] 新人能用库解决至少一个历史 incident（做过抽测）
[ ] 解决新问题后 48h 内补录或更新
```

**INT8 比 PC 慢排查**

```
[ ] 已对齐 batch、shape、预热、对比引擎
[ ] 已看 convert 日志：量化层数、Q/DQ、fallback 关键字
[ ] 已开 profiler：op 耗时排序、Precision、Device、DDR/MAC
[ ] 已区分计算型 vs 内存型算子占比
[ ] 已查 CPU fallback 与 unsupported
[ ] 已查 tiling/融合（INT8 是否重 tune）
[ ] 已查动态 shape 与编译/抖动
[ ] 结论与改法已写入算子知识库（若可复用）
[ ] 报告区分 latency@batch=1 与 throughput@batch=N
```

---

## 附录 B：知识库条目 + 排查记录最小模板

复制下面两段，分别填「算子卡片」和「一次 INT8 慢 incident」——不依赖厂商 CLI，纯文本可进 Notion/语雀。

```markdown
## 算子卡片模板

【算子名】
【芯片型号/工具版本】
【支持精度】
【限制】
【推荐替代】
【Tiling 备注】
【踩坑案例】
  - YYYY-MM-DD，模型名，现象 → 改法 → profiler 前后（ms 或 MAC%）

---

## INT8 性能 incident 模板

【日期】【模型】【芯片/CANN】
【对比基线】PC：引擎 / batch / shape / 延迟 ms；设备：同上
【是否公平】是 / 否（说明）
【Profiler  top3 算子】1. … 2. … 3. …
【Precision 概况】INT8 层数 / FP16 回退 / Cast 是否过多
【根因】假量化 / memory-bound / CPU fallback / tiling / 动态 shape / 其他
【改法】
【效果】改前 ms → 改后 ms；是否写入算子库：是 / 否
```

---

## 术语速查

| 术语 | 全称 / 含义 | 一句话直觉 |
|------|------------|-----------|
| 算子知识库 | — | 可搜的踩坑+替代，不是官方手册复印件 |
| CANN / ATC | 昇腾栈 / 编译器 | 看 convert 日志、量化、fallback |
| INT8 假量化 | — | 名字 INT8，实际大量 FP16+Cast，MAC 没吃满 |
| MAC 利用率 | — | 真 INT8 路径通常应比 FP16 更「算力忙」 |
| Memory-bound | 访存瓶颈 | Transpose 等搬数据为主，INT8 加速有限 |
| CPU fallback | 回退 CPU | NPU 不支持的 op 在 CPU 跑，延迟易爆 |
| Tiling | 分块 | 切大块 fit SRAM；INT8 常要重 tune |
| 动态 shape | Dynamic Shape | 尺寸变→慢路径或重编译，INT8 更敏感 |
| Profiler | msprof 等 | 按 op 看耗时/精度/设备，别猜 |
| Q/DQ | Quantize/Dequantize | 量化边界；过多会打断融合、拖慢 |
