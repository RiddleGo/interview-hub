# FLOPs 砍半怎么速度没涨？动静态量化怎么选？

> **导读**：FLOPs 只数乘加，不算搬货和调度；动态量化听起来省事，NPU 上往往比 FP16 还慢。两件事都指向同一条部署铁律——别脱离硬件和 profiler 谈理论指标。  
> **阅读时间**：约 22 分钟  
> **适合谁**：刚做边缘部署、被老板问「算力减半怎么 fps 没翻倍」，或在 NPU 项目里纠结「没校准集能不能上动态量化」的工程师。

---

## 排查现场：两个新人常踩的坑叠在一起

某次检测项目，算法同学把 backbone 从标准卷积换成 depthwise separable，Netron 里 FLOPs 从 12G 降到 4G，团队预期延迟能砍 2/3。上昇腾 310 编完 `.om`，msprof 一看：单帧只从 28ms 降到 22ms，MAC 利用率反而从 35% 掉到 22%——老板问「算力都减成三分之一了，怎么只快这么点？」

同期另一个项目，客户两周内要 INT8，校准集还没整理好。有人提议「先用 ONNX Runtime 动态量化顶上」。ORT 里确实能跑，转 NPU 后 INT8 比 FP16 还慢一截，精度也不稳。复盘才发现：**FLOPs 和延迟本来就不是线性关系**；**动态量化是 CPU 侧轻量方案，不是 NPU 的退路**。

这两题在部署链路里位置不同——FLOPs 问题出在 **改图 / 结构选型** 阶段；量化选型出在 **PTQ 校准** 阶段。但排查习惯一样：**固定输入、预热、profiler 分层、别拿纸面指标当验收**。

---

## 它们在部署链路里干什么

```
  .pt (FP32)
      │
      ▼  torch.onnx.export
  ONNX (FP32)  ── ORT 验收：数学正确
      │
      ▼  结构改图 / backbone 替换              ← 主题一：FLOPs 在这里变
  ┌─────────────────────────────────────────────┐
  │ · depthwise、通道剪枝、大核拆小核            │
  │ · 纸面 FLOPs 粗筛；实机靠 profiler 验收      │
  └─────────────────────────────────────────────┘
      │
      ▼  PTQ / 量化选型                         ← 主题二：动/静态在这里定
  ┌─────────────────────────────────────────────┐
  │ 静态 PTQ：校准集离线定 scale → NPU 主流      │
  │ 动态量化：推理时算 activation scale → ORT/CPU │
  └─────────────────────────────────────────────┘
      │
      ▼  converter（ATC / trtexec 等）
  芯片模型 (.om / engine)
      │
      ▼  实机 repeated benchmark + profiler
  ┌─────────────────────────────────────────────┐
  │ 延迟、MAC 利用率、DDR 带宽、P99 波动         │
  │ FLOPs 只用于粗筛，不能当 fps 预测器          │
  └─────────────────────────────────────────────┘
      │
      ▼  任务验收 + 上线
  交付
```

我在项目里习惯：**改结构前后各编一版芯片模型，同一输入 shape、同一 batch，预热 50 轮再测 200 轮**——比只在 PyTorch 里数 FLOPs 靠谱一个数量级。

---

## 零基础先搞懂：本篇会反复出现的名词

下面按「直觉 → 部署里怎么用」写。后文再出现这些词，可以直接当复习。

### FLOPs 和 MAC：数的是「算了多少次」，不是「算得多快」

**FLOPs（Floating Point Operations，浮点运算次数）** 统计一次推理里乘法和加法的总次数。一层卷积粗算：每个输出位置要做 `C_in × K × K` 次乘加，再乘输出像素数和通道数。

**MAC（Multiply-Accumulate，乘加）** 是硬件口径，一次 MAC ≈ 一次乘法 + 一次加法；厂商 peak 算力常写「多少 TOPS/MAC」。FLOPs 和 MAC 在卷积里往往差一个常数因子，面试里混用问题不大，但要清楚：**两者都不含访存、不含 launch、不含利用率**。

打个比方：FLOPs 像「这桌菜一共要切多少刀」；实机延迟还要看刀够不够快、案板够不够近、帮厨有没有空着。

### 利用率（Utilization）：硬件算力吃满了几成

**利用率** 指实际达到的算力占芯片 **理论峰值** 的比例。峰值是 datasheet 上的理想数；真实 Conv 常因矩阵形状不规整、并行度不够、等 DDR 数据，利用率掉得很厉害。

若一层 MAC 利用率只有 18%，82% 的算力在空转，这时候就算 FLOPs 减半，相当于活少了一半，干活的工人还是只有 18%，总耗时只会减少一点点——远达不到减半。具体数字因芯片、分辨率、通道数而异，但 **低利用率时减 FLOPs 收益很小** 是稳定规律。

### Memory-bound 和 Compute-bound

**Memory-bound（访存瓶颈）**：时间主要耗在 **把数据从 DDR 搬到计算单元**，算术本身不忙。`DWConv`、`Resize`、`Transpose`、`Concat` 等算子常见——计算量很小，但要完整读写特征图，DDR 带宽已经跑满，FLOPs 再低也省不出多少时间。

**Compute-bound（计算瓶颈）**：数据已经在片上或缓存里，**乘加单元才是主角**。大通道卷积、大矩阵乘更接近这类，FLOPs 和延迟的相关性会好一些，但也不是严格线性。

### 调度 / Launch 开销

每个 Kernel 启动都有固定成本：任务调度、上下文切换、数据搬移准备、同步等待。模型里若大量是小算子，这部分开销能占到总延迟的 50% 以上（视整网和芯片而定）。FLOPs 减半只减少了「计算成本」，**固定启动成本一分都不会少**——把三个并行小 MatMul 合成一个大 MatMul，FLOPs 不变、延迟却能降 60% 以上，减的就是多次 launch。

### 量化、scale 和 PTQ

**量化（Quantization）** 把 FP32 权重和激活映射到 INT8 等低位宽，靠更小的数据和专用 MAC 单元加速。

**scale（缩放因子）** 把浮点范围映射到整数：`q = round(x / scale) + zero_point`。权重和激活各有一套 scale；scale 定得准不准，直接决定 INT8 精度。

**PTQ（Post-Training Quantization，后训练量化）** 在模型训完后直接量化，不靠重新训练。**静态 PTQ** 用校准集离线算好所有 scale，推理时固定不变；**动态量化** 只离线量化权重，激活的 scale 在 **推理运行时** 根据当前输入实时统计。

### 校准集（Calibration Set）

**校准集** 是一批代表业务分布的样本（常见 100～500 张，分类可偏少、检测分割建议更多，视任务调整），用来统计激活的最大值/分布，定 INT8 的 scale。静态 PTQ 离不开它；动态量化 **不需要** 校准集，但 NPU 上通常也不该选这条路。

---

## FLOPs 减半，延迟会减半吗？

面试里常被追问：**「FLOPs 砍一半，fps 应该翻倍吧？」**

我一般会先否定线性关系。FLOPs 只描述「理论上要做多少次计算」，完全不涉及「数据要搬多久、调度要花多久、硬件算力能跑满多少」。在边缘 NPU 部署场景，绝大多数模型都不是纯计算瓶颈，FLOPs 和延迟的线性关联度极低，甚至会出现 **FLOPs 减了、延迟反而涨了** 的反直觉情况。

### 为什么不对等：四个常见根因

#### 1. 内存 bound 算子：计算量再减，延迟也不动

算子分两类。只有 **计算密集型** 算子的 FLOPs 才和延迟有一定相关性；**内存密集型** 算子的延迟主要由 DDR 带宽决定，FLOPs 再低也没用。

| 类型 | 典型算子 | 瓶颈 | FLOPs 与延迟 |
|------|---------|------|-------------|
| 计算密集型 | 大通道 Conv、大 MatMul | 算力 | 有一定相关性，仍非严格线性 |
| 内存密集型 | DWConv、Resize、Transpose、Add、Concat | 带宽 | FLOPs 低，延迟未必低 |

**典型例子**：3×3 标准卷积 vs 3×3 depthwise separable（DWConv + PWConv）。后者 FLOPs 常只有前者的 1/3～1/4，但在 NPU 上延迟通常只减少 20%～30%，远达不到 1/4。原因就是 DWConv 偏 memory-bound：计算量很小，却要完整读写一次特征图，带宽已经跑满。

反过来也成立：`Conv+BN+ReLU` 融合前后 FLOPs 完全没变，延迟却能降 2/3——本质减少了内存访问，和计算量无关。只减 FLOPs 不减内存访问，延迟不会有明显变化。

#### 2. 利用率不足：算力本来就没跑满

Tiling 策略差、shape 不对齐（昇腾常见 16 对齐）、算子太小等原因，会让 MAC 利用率本身就很低。那层 3×3 卷积默认 Tiling 下利用率只有 18% 的项目我见过不少——此时减 FLOPs，总耗时只会略降，远减不到一半。

#### 3. 调度启动开销：小算子的固定成本占比高

小通道卷积、大量逐元素算子，单次计算量很小，launch 开销盖过计算时间。FLOPs 减半省的是可变成本，固定成本一分不少，总延迟自然远减不到一半。

#### 4. 和 FLOPs 无关的隐性开销

推理延迟里还有大量固定成本，不随 FLOPs 变化：

- CPU ↔ NPU 数据拷贝
- NCHW 转 NC1HWC0 等 layout 转换
- 混合精度下的 Quantize/Dequantize
- NMS、坐标解码等后处理

若这些占总延迟的 40%，就算计算部分延迟减半，总延迟也只会减少约 30%（0.4 + 0.6×0.5 = 0.7）。

### FLOPs 的正确定位

1. **算法选型阶段粗筛**：几个 backbone 里先筛计算量更小的结构，缩小范围。
2. **不能用来预估实机延迟**：更不能当性能优化验收指标。
3. **结论必须实机验证**：固定输入、预热、重复 benchmark，配合 profiler 看 MAC 利用率、DDR 带宽、算子 Top 耗时。

FLOPs 是 **算法侧** 的指标，不是 **部署侧** 的性能标尺。优化到最后，纯计算密集型子网的相关性会高一些，但永远不会是严格的「减半就对半快」。

---

## 动态量化 vs 静态 PTQ：项目里怎么选？

第二个常见困惑：**「没有校准集，能不能先上动态量化？」**

核心差异就一句话：**激活的量化参数（scale）什么时候定**——推理时实时算，还是离线校准一次固化。

### 动态量化（Dynamic Quantization）

只提前把 **权重** 离线量化成 INT8；**激活** 的 scale 在推理运行时，根据当前输入的实际数值范围实时统计。

- 优点：不需要校准集，ORT 里几行配置就能试，适合快速验证。
- 代价：激活侧每帧要做 min/max 统计和 scale 计算，有额外 CPU 开销；统计有误差，激活量化粒度往往偏粗。
- 典型场景：ORT 在 **CPU** 上跑小模型、RNN/Transformer 的线性层、项目周期极短、只做轻量加速。

ORT 里对 RNN、部分线性层常见；**CNN 全图 INT8 加速未必赚**——卷积占大头，激活动态统计的开销和精度损失常常抵消收益。

### 静态 PTQ（Static Post-Training Quantization）

权重和激活的 **所有** 量化参数（scale、zero_point）都在离线阶段，通过校准集提前算好，完整固化到模型里。推理时直接用固定参数做硬件量化计算，**没有任何额外统计开销**。

- 优点：全链路参数确定，推理纯硬件加速；精度在校准集覆盖下通常优于动态量化；NPU 编译器能配合融合、Tiling 做深度优化。
- 代价：需要代表性校准集（多数项目 100～500 张）；离线校准和验证要排期。
- 典型场景：边缘 NPU、CNN 检测/分类、追求极致性能功耗——**工业界主流**。

### 多维度对比

| 对比维度 | 动态量化 | 静态 PTQ |
|---------|----------|---------|
| 量化参数时机 | 权重量化离线；激活 scale 推理时实时算 | 权重 + 激活全部离线校准固化 |
| 校准集 | 不需要 | 需要（视任务 100～500 张典型样本） |
| 推理额外开销 | 有：实时统计激活范围、算 scale | 无：参数固定，纯硬件指令 |
| 精度 | 一般；动态统计有误差 | 较好；校准覆盖下更稳 |
| 适用算子 | 线性层、FC、RNN 为主；CNN 全图收益低 | 全类型；Conv/MatMul 效果极佳 |
| NPU 适配 | 极差：编译型架构难深度优化 | 完美：编译期融合 + Tiling |
| 典型加速 | 有限，常见 10%～30%，不少场景负收益 | 显著，常见 30%～100%（视模型和芯片） |

表后一句：**动态量化是「省事」，静态 PTQ 是「上板」**——NPU 项目几乎只走后者。

### 为什么边缘 NPU 几乎只用静态 PTQ？

这和 NPU 的 **编译期静态优化** 架构深度绑定：

1. **优化都在编译期完成**：算子融合、Tiling、内存规划、指令调度，都依赖固定的算子参数和数据类型。动态量化需要运行时改 scale，打破静态图确定性，编译器无法做深度优化，大量算子只能走通用慢路径。
2. **硬件 MAC 单元只认固定 scale**：昇腾 Cube 等 INT8 引擎按固化 scale 设计，没有运行时动态调整量化参数的硬件逻辑。动态量化只能落 CPU 或通用单元，性能有时 **不如 FP16**。
3. **边缘要确定性延迟**：动态量化每帧输入不同，scale 就不同，延迟会波动——产线检测、车载感知通常不接受。

### 选型原则（口述版）

- **边缘 NPU、CNN、要性能功耗**：静态 PTQ + 编译期优化。
- **CPU 推理、小模型、RNN、没时间校准**：可以考虑动态量化（ORT）。
- **NPU 没校准集**：宁可用 FP16，也别硬上动态量化——性能、精度、稳定性都没有保障。

动态量化 **解决不了** 动态 shape 的性能问题；NPU 上动态 shape 也不会搭配动态量化，正确方案是 **多档固定 shape 的静态模型** 各编一版。

---

## 怎么做：FLOPs 改图与量化选型的可执行步骤

### A. 改结构后验证「FLOPs 收益是否兑现」

**第 1 步：纸面粗筛。** 用 `thop`、`fvcore` 或脚本数 FLOPs，确认改图方向合理——只用于缩小候选，不用于报 fps。

**第 2 步：ORT 对齐精度。** 改图后先在 ORT 上跑同一批输入，对比 FP32 输出余弦 / mAP，确认结构改法没把精度改崩。

**第 3 步：各编一版芯片模型。** 改前、改后各走一遍 converter，输入 shape、batch、精度策略保持一致。

**第 4 步：公平 benchmark。**

```
预热：≥ 50 轮（去掉首帧编译/缓存冷启动）
测试：≥ 200 轮，报 P50 / P99
固定：batch=1（边缘常见）、同一输入 tensor、空载或注明负载
```

**第 5 步：profiler 分层。** 看 MAC 利用率、DDR 带宽占比、算子 Top 耗时。若 FLOPs 大降但延迟小降，重点查是不是 memory-bound 层、低利用率层、或 launch 开销堆叠。

**第 6 步：写结论。** 记录改前改后 FLOPs、延迟、利用率——新人下次就不会再问「为什么算力减了速度没涨」。

### B. NPU 项目量化选型

**第 1 步：默认静态 PTQ。** 排期校准集（100～500 张，覆盖亮度/尺度/场景分布，和训练预处理一致）。

**第 2 步：ORT 或厂商工具离线校准。** 昇腾用 AMCT 等，产出 INT8 ONNX；检查有多少层真量化、有没有大量 Q/DQ 打断。

**第 3 步：编译 + profiler。** 对比 FP16 与 INT8 的延迟、MAC 利用率、任务指标掉点。

**第 4 步：掉点超业务线再调。** skip 敏感层、换校准方法、混合精度——不是先换动态量化。

动态量化仅作为 **PC 侧 ORT 快速试验** 的可选项，不作为 NPU 交付路径。

---

## 最常见坑（附排查顺序）

### 坑 1：用 FLOPs 当 fps 预测器

**典型做法**：backbone 换 depthwise，FLOPs 降 60%，直接跟客户报「延迟能降 60%」。

**现象**：实机只快 15%～25%，甚至被质疑「NPU 是不是假的」。

**原因**：DWConv 等 memory-bound；或改图后利用率更低。

**怎么查**：msprof 分层，看瓶颈层 MAC 利用率和 DDR 占比。

**怎么改**：profiler 驱动改图（融合、减 Transpose、大核拆小核），不以 FLOPs 为验收；对客户报数前必须上板。

### 坑 2：Conv+BN 未融合却指望减 FLOPs 见效

**典型做法**：只改通道数/卷积类型，不检查融合是否生效。

**现象**：FLOPs 变了，延迟几乎不动。

**原因**：瓶颈在 DDR 往返，不在乘加次数。

**怎么查**：dump 融合图，看 Conv、BN 是否各一颗 kernel。

**怎么改**：BN folding、促融合、水平融合小算子——FLOPs 不变也能大幅降延迟。

### 坑 3：NPU 没校准集就上动态量化

**典型做法**：「动态量化不用校准集，先顶上 INT8。」

**现象**：比 FP16 慢，精度抖，编译日志里大量 Cast/QDQ。

**原因**：NPU 硬件和编译器不为运行时 scale 优化。

**怎么查**：编译日志 Precision 列；MAC 利用率是否和 FP16 差不多。

**怎么改**：补校准集走静态 PTQ；来不及就 FP16 交付，别硬 INT8。

### 坑 4：忽视固定开销，局部优化白做

**典型做法**：只优化 backbone 计算，后处理和 H2D 拷贝占 40% 不动。

**现象**：backbone 延迟减半，端到端只快 15%。

**原因**：Amdahl 定律——非计算部分不随 FLOPs 变。

**怎么查**：profiler 端到端拆分：H2D、推理、D2H、后处理各占多少。

**怎么改**：Pipeline 并行、减拷贝、后处理下沉 NPU 或优化 NMS——别只盯 backbone FLOPs。

### 坑 5：benchmark 不公平导致误判

**典型做法**：改前没预热，改后预热了；或 batch、shape 不一致。

**现象**：「优化 50%」或「优化无效」都是假象。

**原因**：首帧编译、缓存、频率缩放未控制。

**怎么查**：核对预热轮数、测试轮数、输入是否 byte-level 相同。

**怎么改**：统一 benchmark 脚本；报 P50/P99，不只报一次。

---

## 面试追问

### 1

**问：** FLOPs 减半，延迟会减半吗？

**答：** 不会。FLOPs 只统计乘加次数，不含访存、利用率、kernel launch 和后处理。memory-bound 算子（如 DWConv）、低 MAC 利用率、小算子调度开销，都会让 FLOPs 白减。要以固定输入的 repeated benchmark 和 profiler 为准，FLOPs 只用于粗筛结构。

### 2

**问：** 为什么 depthwise separable 卷积 FLOPs 低很多，NPU 上却未必快很多？

**答：** DWConv 计算量小但要把整幅特征图读写一遍，常是 memory-bound，DDR 带宽先顶满。FLOPs 降到 1/4，延迟可能只降 20%～30%。还会遇到矩阵形状小、利用率低的问题。要看 profiler 里该层带宽占比和 MAC 利用率，不能只看 FLOPs。

### 3

**问：** 动态量化和静态 PTQ 本质区别是什么？

**答：** 权重都可以离线 INT8；差别在激活 scale——动态量化推理时按当前输入实时算 scale，静态 PTQ 用校准集离线定好、推理固定。动态量化省事、不要校准集，适合 ORT/CPU 上部分线性层；静态 PTQ 无运行时统计开销，精度更稳，是 NPU 和边缘 CNN 的主流。

### 4

**问：** NPU 项目没有校准集，能用动态量化吗？

**答：** 不建议。NPU 优化在编译期，硬件 MAC 认固定 scale，动态量化走不通专用 INT8 路径，常比 FP16 慢且精度抖。没校准集宁可用 FP16 交付，或尽快补 100～500 张代表性样本做静态 PTQ——别把动态量化当 NPU 的退路。

### 5

**问：** FLOPs 和延迟什么时候相关性会高一些？

**答：** 子网以大型 Conv/MatMul 为主、MAC 利用率高、memory-bound 算子少、融合做得好时，FLOPs 和延迟相关性会好一些——比如大通道 backbone 里纯 3×3 卷积堆叠。但仍有 launch 和后处理开销，永远不会严格线性。验收一律以 profiler + 实机 benchmark 为准。

---

## 附录 A：FLOPs 与量化选型 checklist（可打印）

```
[ ] 改结构前后已在 ORT 对齐精度，不只对比 FLOPs
[ ] 改前改后各编一版芯片模型，输入 shape / batch / 精度策略一致
[ ] benchmark 已预热 ≥50 轮，测试 ≥200 轮，报 P50 / P99
[ ] profiler 已看 MAC 利用率、DDR 带宽、算子 Top 耗时
[ ] 若 FLOPs 大降延迟小降：已排查 memory-bound 层和低利用率层
[ ] 已检查 Conv+BN 融合是否生效，未只盯乘加次数
[ ] 端到端已拆分 H2D、推理、后处理，确认非计算瓶颈占比
[ ] NPU 量化默认静态 PTQ，已准备 100～500 张代表性校准集
[ ] 校准集与线上预处理一致，覆盖亮度/尺度/典型场景
[ ] 未在 NPU 上用动态量化替代静态 PTQ
[ ] INT8 编译后已查 Precision 列 / 日志，确认真走 MAC 而非大量 Cast
[ ] 结论已写入记录：FLOPs、延迟、利用率、任务指标、芯片与 CANN 版本
[ ] 新人能解释：FLOPs 是算法指标，不是部署 fps 预测器
```

---

## 附录 B：最小代码示例

下面脚本演示两件事：（1）标准卷积 vs depthwise separable 的 FLOPs 比值；（2）用简单「计算时间 + 固定访存时间」模型说明 **FLOPs 减半 ≠ 延迟减半**。不依赖 NPU SDK；实机请配合 profiler。

```python
"""
FLOPs 对比 + 简化延迟模型（计算 + 固定访存/launch）。
说明：纸面 FLOPs 比值与「有效延迟比值」可以差很多。
"""

from dataclasses import dataclass


@dataclass
class ConvSpec:
    c_in: int
    c_out: int
    k: int
    h: int
    w: int
    groups: int = 1


def conv_flops(spec: ConvSpec) -> int:
    """单次 Conv2d 前向 FLOPs（乘加各算 1）。"""
    out_h, out_w = spec.h, spec.w
    if spec.groups == spec.c_in == spec.c_out:
        mac = spec.c_in * spec.k * spec.k * out_h * out_w
    else:
        mac = spec.c_in * spec.c_out * spec.k * spec.k * out_h * out_w // spec.groups
    return mac * 2


def estimate_latency_ms(
    flops: float,
    peak_gflops: float = 16.0,
    util: float = 0.25,
    memory_ms: float = 8.0,
    launch_ms: float = 2.0,
) -> float:
    """
    极简延迟模型（毫秒）：
      latency = flops / (peak * util) + memory_ms + launch_ms
    memory_ms / launch_ms 不随 FLOPs 变——模拟 memory-bound 和调度开销。
    """
    compute_ms = (flops / 1e9) / (peak_gflops * util) * 1000
    return compute_ms + memory_ms + launch_ms


def main():
    c_in, c_out, h, w = 256, 256, 56, 56

    # 标准 3x3 Conv
    flops_std = conv_flops(ConvSpec(c_in, c_out, 3, h, w))
    # Depthwise 3x3 + Pointwise 1x1
    flops_dw = conv_flops(ConvSpec(c_in, c_in, 3, h, w, groups=c_in))
    flops_pw = conv_flops(ConvSpec(c_in, c_out, 1, h, w))
    flops_sep = flops_dw + flops_pw

    print("=== FLOPs 对比（256 通道, 56x56）===")
    print(f"标准 3x3 Conv:        {flops_std / 1e9:.2f} G")
    print(f"DW+PW separable:      {flops_sep / 1e9:.2f} G")
    print(f"FLOPs 比值 (sep/std): {flops_sep / flops_std:.2f}")
    print()

    # 场景 A：标准卷积，利用率 35%
    lat_std = estimate_latency_ms(flops_std, util=0.35, memory_ms=4.0, launch_ms=1.5)
    # 场景 B：separable，FLOPs 低但 DW 层 memory-bound、利用率更低
    lat_sep = estimate_latency_ms(flops_sep, util=0.22, memory_ms=7.0, launch_ms=2.0)

    print("=== 简化延迟模型（说明用，非实机）===")
    print(f"标准 Conv 估计延迟:   {lat_std:.1f} ms")
    print(f"Separable 估计延迟:   {lat_sep:.1f} ms")
    print(f"延迟比值 (sep/std):   {lat_sep / lat_std:.2f}")
    print(f"FLOPs 降了 {(1 - flops_sep/flops_std)*100:.0f}%，延迟只降 {(1 - lat_sep/lat_std)*100:.0f}%")
    print()
    print("说明：DW 层访存固定成本高、利用率低时，FLOPs 收益会被吃掉。")
    print("实机请 msprof / 厂商 profiler，勿只跑本脚本。")


if __name__ == "__main__":
    main()
```

---

## 术语速查

| 术语 | 全称 / 含义 | 一句话直觉 |
|------|------------|-----------|
| FLOPs | Floating Point Operations | 乘加次数；不含量搬运和利用率 |
| MAC | Multiply-Accumulate | 一次乘加；和 FLOPs 差常数因子 |
| 利用率 | Utilization | 实际算力占芯片峰值的几成 |
| Memory-bound | 访存瓶颈 | 时间耗在搬数据，不是算力 |
| Launch 开销 | Kernel 启动成本 | 小算多时固定成本占比高 |
| PTQ | Post-Training Quantization | 训完再量化，不靠重训 |
| 静态 PTQ | — | 校准集离线定 scale；NPU 主流 |
| 动态量化 | Dynamic Quantization | 激活 scale 推理时算；ORT/CPU 轻量方案 |
| scale | 缩放因子 | 浮点映射到 INT8 的比例 |
| 校准集 | Calibration Set | 代表业务分布的离线样本，定 scale 用 |
