# FLOPs 差不多，为什么 7×7 比 3×3 堆叠还慢？

> **导读**：Profiler 里两颗 Conv 理论乘加量只差几个百分点，实机延迟却差两三倍——多半是利用率没吃满，或者中间 buffer 把 DDR 打满了。FLOPs 只数乘加，不算搬货。  
> **阅读时间**：约 18 分钟  
> **适合谁**：会看 Netron、能编过芯片模型，但换大核后 fps 反而掉、想搞清「算力指标和实机延迟为什么对不上」的工程师。

---

## 面试一句：FLOPs 能代表推理速度吗？

常被追问：两个 Conv 的 FLOPs 差不多，为什么 7×7 比三个 3×3 堆叠慢很多？

我一般会先否定「FLOPs 等于速度」。**FLOPs（Floating Point Operations，浮点运算次数）** 只统计乘法和加法有多少次，不管数据从哪搬、硬件吃不吃满。真实延迟大致是：**计算量 ÷ 利用率 + 访存开销 + 调度开销**。FLOPs 相近时，后两项往往决定谁快谁慢。7×7 在多数 NPU 上矩阵单元利用率常见只有 20% 左右，三个 3×3 堆叠能到 40%～60% 并不稀奇——还没算大核中间 buffer 更大、更难和 BN 融合带来的额外 DDR 往返。所以结构替换（大核拆小核、depthwise 改 pointwise+depthwise）常常是 **手工改图** 的事，别指望 converter 自动帮你变快。

---

## 卷积核尺寸在部署链路里干什么

选 3×3 还是 7×7，发生在 **算子搜索 / 网络改图** 阶段——在 ONNX 导出之后、交给 converter 之前。Converter 能做的是 layout、融合、tiling；**不能把 7×7  magically 变成三个 3×3** 还不动精度，因为那属于网络结构级变换。

```
  .pt (FP32)
      │
      ▼  torch.onnx.export
  ONNX (FP32)  ── ORT 验收：数学正确
      │
      ▼  算子搜索 / graph surgery          ← 本文主题落在这里
  ┌─────────────────────────────────────────────┐
  │ · 大核拆 3×3×3 或 1×7+7×1                  │
  │ · depthwise 7×7 → 更小核 + pointwise       │
  │ · 对照 profiler：利用率、DDR、能否 Conv+BN fuse │
  └─────────────────────────────────────────────┘
      │
      ▼  converter（ATC / trtexec / 厂商工具）
  ┌─────────────────────────────────────────────┐
  │ 编译期：im2col→GEMM、tiling、fusion         │
  │ 7×7 往往走通用 GEMM；3×3 常有专用引擎       │
  └─────────────────────────────────────────────┘
      │
      ▼  芯片模型 → 实机 profiling + 任务验收
  交付
```

我在项目里习惯：**ORT 上 FLOPs 相近的两版结构，各编一版芯片模型，profiler 分层对比**——比只在 PyTorch 里数 FLOPs 靠谱得多。

---

## 零基础先搞懂：本篇会反复出现的名词

下面按「直觉 → 部署里怎么用」写。后文再出现这些词，可以直接当复习。

### FLOPs 和 MAC：数的是「算了多少次」，不是「算得多快」

**FLOPs** 统计一次推理里浮点乘加的总次数。一层 3×3 Conv 的粗算：输出每个位置要做 `C_in × 3 × 3` 次乘加，再乘输出像素数和通道数。

**MAC（Multiply-Accumulate，乘加）** 是硬件口径，一次 MAC ≈ 一次乘法 + 一次加法；厂商 peak 算力常写「多少 TOPS/MAC」。FLOPs 和 MAC 在卷积里往往差一个常数因子，面试里混用问题不大，但要清楚：**两者都不含访存、不含 launch、不含利用率**。

打个比方：FLOPs 像「这桌菜一共要切多少刀」；实机延迟还要看刀够不够快、案板够不够近、帮厨有没有空着。

### 利用率（Utilization）：硬件算力吃满了几成

**利用率** 指实际达到的算力占芯片 **理论峰值** 的比例。峰值是 datasheet 上的理想数；真实 Conv 常因矩阵形状不规整、并行度不够、等 DDR 数据，利用率掉得很厉害。

NPU 上 7×7 利用率 15%～25%、3×3 堆叠 40%～70%，这类对比我在 profiling 里见过很多次——具体数字因芯片、分辨率、通道数而异，但 **大核普遍更难喂饱** 是稳定规律。FLOPs 相近时，利用率差一倍，延迟差一倍并不奇怪。

### 访存瓶颈（Memory-bound）和计算瓶颈（Compute-bound）

**Memory-bound（访存瓶颈）**：时间主要耗在 **把数据从 DDR 搬到计算单元**，算术本身不忙。大核要缓存更多行输入、权重更大，容易落在这。

**Compute-bound（计算瓶颈）**：数据已经在片上或缓存里，**乘加单元才是主角**。3×3 在不少 backbone 层上更接近 compute-bound，所以 FLOPs 和延迟的相关性更好。

直觉：FLOPs 只描述「切多少刀」；memory-bound 时，刀还没举起来，菜还在仓库（DDR）里。

### DDR 和片上 SRAM / L2 缓存

**DDR（Double Data Rate，片外内存）** 容量大（GB 级），带宽相对算力往往偏低。大张量默认住这里，读一次延迟远高于一次浮点运算——常说 **内存墙（Memory Wall）**：算力涨得快，带宽涨得慢。

**L2 / 片上 SRAM** 是芯片上的高速缓存，容量通常 **几百 KB 到几 MB**。算 Conv 时，编译器会尽量把 **滑动窗口需要的几行输入** 留在缓存里；窗口越大（7 行 vs 3 行），需要的缓存越多，装不下就 **反复从 DDR 读**，实际访存量远超理论值，这叫 **缓存抖动（Cache Thrashing）**。

### im2col 和 GEMM：卷积在芯片里常变成矩阵乘

**im2col（image to column）** 把每个卷积窗口摊平成矩阵的一行。3×3 窗口一行 9 个数，7×7 窗口一行 49 个数。

**GEMM（General Matrix Multiply，通用矩阵乘）** 是 `C = A × B`。im2col 之后，Conv 就变成一次大矩阵乘——GPU 的 Tensor Core、NPU 的 Cube 引擎本质上都在干 GEMM。

关键：**硬件矩阵单元喜欢规整的块**（如 16×16、32×32）。3×3 的 9 元素行较容易打包进这些块；7×7 的 49 元素行常常 **填不满、要对齐补零**，空转的单元就是低利用率。这不是数学错，是 **形状和硬件块尺寸不匹配**。

### 3×3 堆叠 vs 单颗 7×7：数学感受野类似，硬件友好度差很多

三个 3×3 堆叠的有效感受野也是 7×7 量级（中间有重复计算，FLOPs 可调到接近），但 **每一层的卷积核都是 3×3**——im2col 行宽 9、缓存只需 3 行输入、权重更小、厂商对 3×3 的 **专用引擎和融合规则** 通常更成熟。

单颗 7×7 一次搞定感受野，图里节点少，但 **单层对硬件和缓存的压力集中在一刀里**，profiler 上往往更慢。

### Depthwise 卷积（DWConv）：大核里更惨的一类

**Depthwise 卷积** 每个输入通道单独做空间卷积，通道之间不混合。7×7 depthwise 每个通道只有 49 个权重，**矩阵乘的「块」极小**，很难并行，利用率有时 **低于 10%**，几乎完全被访存限制。

MobileNet、RepLKNet 里的大核 depthwise，是我见过 **FLOPs 看着不高、实机却慢得离谱** 的重灾区。改法常见：拆成 `1×7 + 7×1`、或 depthwise + pointwise（1×1）组合，让计算粒度变大。

### BN 融合（Conv+BN fuse）：大核常常融不上

**BN（Batch Normalization，批归一化）** 推理时可折叠进 Conv 权重（见算子融合专题）。**Conv+BN+ReLU 融合** 能省中间 feature 的 DDR 往返。

很多 NPU 算子库对 **3×3 Conv+BN** 支持完善，7×7 却走 **通用实现**，融不了或只能分步执行——多一次读写中间结果。FLOPs 不变，延迟又多一截。改图前我会 dump 融合图，看大核层是不是 **Conv、BN 各一颗 kernel**。

### Converter：能优化实现，不能替你改网络结构

**Converter**（ATC、TensorRT、CANN 等）做常数折叠、layout、融合、tiling、量化——都是 **同一张图上的编译优化**。**大核拆小核** 改变的是图结构，可能影响精度，需要重训或微调，converter **不会自动做**。这是面试里常考的边界：编译优化 vs 结构搜索，两层事。

---

## FLOPs 相近时，慢在哪里

一句话：**FLOPs 只量「乘加次数」；实机还看利用率、DDR 流量、能不能 fuse。** 7×7 在这三项上通常同时吃亏。

下面分三块说，每块都尽量带「怎么在 profiler 里认出来」。

### 利用率：大核喂不满矩阵单元

Conv 经 im2col 变成 GEMM 后，硬件按固定块做矩阵乘。7×7 窗口 → 每行 49 元素，和 16/32 的块尺寸对不齐，**大量 MAC 单元空转**。三个 3×3 每层行宽 9，虽然堆叠后总 FLOPs 可调得接近，但 **每一层的 GEMM 形状更友好**，利用率往往高出一截。

若是 7×7 depthwise，通道间不合并，单次任务粒度更小，利用率更难看——FLOPs 甚至更低，延迟却可能更高，别被纸面算力骗。

**怎么查**：厂商 profiler 里的 MAC/Cube 利用率、或「算力理论值 vs 实际吞吐」。同输入 shape 下对比 7×7 与 3×3×3，利用率差 2～3 倍我见过不少，视芯片而定。

### 访存：窗口越大，缓存越装不下

算一行输出，通常要在缓存里保留 **卷积核高度那么多行输入**。3×3 要 3 行，7×7 要 7 行；通道多、分辨率高时，一行输入可能就是几十 KB 到上百 KB。

举例（帮助建立数量级直觉，不是死数）：256 通道、宽 56 的特征图，一行输入约 256×56×4B ≈ 56KB（FP32）。3×3 需约 168KB 行缓存，很多 NPU 的 L2 能装下；7×7 需约 392KB，**超过部分嵌入式 NPU 的 L2（如 256KB）** 时，输入行反复从 DDR 拉，带宽占比能到 70%～80%，计算单元在等数据。

权重也是：7×7 权重数是 3×3 的 (7×7)/(3×3) ≈ **5.4 倍**。batch=1 时，权重加载占 DDR 的比例更高。中间 buffer 更大还会 **挤占** 输入和权重的缓存空间，形成恶性循环。

**怎么查**：profiler 的 DDR 读写带宽占比、分层 DRAM traffic。7×7 层带宽占比明显高于相邻 3×3 层，而 FLOPs 差不多，基本就坐实访存主导。

### 融合与专用路径：3×3 是「一等公民」

多数芯片对 **3×3** 有专用卷积引擎或高度优化的 im2col 路径，甚至跳过 im2col 直接算；**7×7** 常退化成通用 GEMM，且 **Conv+BN+Act 融合** 支持弱。多出来的 BN 单独 kernel = 多一次 feature 读写。

**怎么查**：编译 dump 图 + 分层 kernel 列表。7×7 若总是「Conv → BN → Relu」三颗，3×3 层是一颗 fused op，延迟差一截很正常。

---

## 数量级对比：同一输入下的直觉表

下面用 **同一输入特征图、FLOPs 故意调到接近** 的对比，说明「纸面算力接近、实机可以差很多」。数字来自常见 NPU 上的工程实测量级，**仅供建立直觉，换芯片/resolution 务必自己 profile**。

| 方案 | 理论 FLOPs（约） | 典型利用率 | DDR 带宽占比（约） | 相对延迟（约） |
|------|------------------|------------|-------------------|----------------|
| 单颗 7×7 Conv | ~10G | 15%～25% | 70%～85% | 基准 1×（慢） |
| 三个 3×3 堆叠 | ~10G | 40%～65% | 25%～40% | 常快 2～3× |
| 7×7 depthwise | 更低 | 常 <15% | 很高 | 有时最慢 |

表后要记一句：**FLOPs 列几乎一样时，看利用率和 DDR 列**——谁带宽占比高、利用率低，谁就是你要改结构的那层。

---

## 工程上怎么做：大核变慢时的五步

**1. 先 profile，再改图。** 不要只看 PyTorch 的 FLOPs 计数。同 ONNX、同输入，在目标芯片上分层看利用率、DDR、kernel 是否 fuse。验证项：能指出 **最慢的几层是 7×7 还是 depthwise 大核**。

**2. 结构替换优先于死调编译参数。** 常见等价改法：7×7 → 3×3×3；7×7 depthwise → 1×7 + 7×1；或加 1×1 pointwise 调整通道。改完 ORT 对一下输出，再微调或 QAT（若掉点超业务线）。验证项：ORT 余弦 / 任务指标在门槛内。

**3. 改图后重新走融合链。** 小核更容易 Conv+BN 折叠 + fuse。export 前 BN folding，Netron 看链是否连续。验证项：dump 图里新 3×3 链是 fused op。

**4. 分辨率与通道数一起考虑。** 大 feature 图 + 大核最容易 cache thrashing。若业务允许，可在 **更小 feature 上用大核**（算子重排），或先 stride/downsample 再卷。验证项：改前后同任务指标，latency 下降可复现。

**5. 别指望 converter 自动拆核。** 在算子搜索文档里记录：**「芯片 X + 7×7 → 3×3×3，利用率从 A 到 B，mAP 掉 0.x」**，下次同类 backbone 直接套。验证项：团队知识库有结构版与芯片版的对应关系。

---

## 最常见坑（附排查顺序）

### 坑 1：只比 FLOPs，不上板 profile

**典型做法**：论文或 Netron 里数乘加，认定 7×7 和 3×3×3「算力一样」，直接上大核。

**现象**：芯片上该层 latency 占整网 30%+，PC 上 ORT 反而差不多。

**原因**：FLOPs 不含利用率与 DDR；大核 memory-bound + 低利用率。

**怎么查**：芯片 profiler 分层；看 MAC 利用率与 DDR 占比。

**怎么改**：结构替换或换层位置；以 profile 为准迭代，不以 FLOPs 为唯一指标。

### 坑 2：7×7 depthwise 看着「参数少、FLOPs 低」就留

**典型做法**：MobileNet 系直接导出带 7×7 DW 的图。

**现象**：整网 fps 被一层 DW 拖死，利用率个位数。

**原因**：DW 无法形成大 GEMM，并行度极差。

**怎么查**：单层 profile；对比改为 1×7+7×1 或更小核。

**怎么改**：算子搜索阶段换等价子图；必要时该层 FP16 或混合精度（视芯片）。

### 坑 3：大核 Conv 融不上 BN，多两次 DDR

**典型做法**：未做 BN 折叠，7×7 后接独立 BN 节点。

**现象**：该层 kernel 数多、带宽高，比相邻 3×3 fused 层慢一截以上。

**原因**：工具链对大核融合支持弱，链断在 BN。

**怎么查**：dump 融合图；对比 3×3 层是否单 kernel。

**怎么改**：BN 折叠 + 改 3×3 堆叠；或接受该层 FP16 单独调。

### 坑 4：调 converter 参数指望「编译救 7×7」

**典型做法**：`optimize=2`、AutoTune 全开，结构不动。

**现象**：延迟有小幅波动，大核仍是最慢层。

**原因**：编译优化不改变 GEMM 形状本质和 cache 需求。

**怎么查**：改参数前后 profile diff，瓶颈层是否仍是 7×7。

**怎么改**：回到 graph surgery；编译参数是第二层，不是替代改图。

---

## 面试追问

### 1

**问：** FLOPs 和实际推理延迟是什么关系？

**答：** FLOPs 只统计乘加次数，不含数据搬运、硬件利用率、kernel launch。真实延迟大致是计算量除以利用率，再加上访存和调度。FLOPs 相近时，谁利用率高、谁少打 DDR，谁往往更快。部署里必须以芯片 profiler 为准，不能只看 FLOPs 计数器。

### 2

**问：** 为什么 7×7 在 NPU 上利用率常常比 3×3 低？

**答：** 卷积常经 im2col 变成 GEMM，硬件矩阵块多是 16×16、32×32 这类规整尺寸。3×3 窗口一行 9 个元素，较容易打包；7×7 一行 49 个，对齐补零多，空转多。若是 7×7 depthwise，每通道单独算，矩阵更小，利用率往往更差。这是形状和硬件不匹配，不是公式算错。

### 3

**问：** 三个 3×3 和一颗 7×7 感受野类似，为什么部署更偏爱 3×3 堆叠？

**答：** 感受野类似，但每层 im2col 行宽是 9 不是 49，缓存只需 3 行输入不是 7 行，权重也更小。芯片侧通常对 3×3 有专用引擎和 Conv+BN 融合，7×7 常走通用 GEMM 且难 fuse。FLOPs 可以调到接近，实机 2～3 倍差距我见过不少，视分辨率和芯片而定。

### 4

**问：** 大核拆小核为什么 converter 不会自动做？

**答：** 拆核改的是网络结构，可能动精度，要重训或微调；converter 做的是同图上的 layout、融合、tiling、量化。它不知道你的业务能掉几个点 mAP，也没有「试十种拆法再选最快」的搜索空间默认开启。所以算子搜索阶段要人工或 NAS 做结构替换，编译是第二层优化。

### 5

**问：** profile 上怎么判断一层是 memory-bound 还是 compute-bound？

**答：** 看 DDR 带宽占比和 MAC 利用率。带宽长期顶满、利用率低，多半是 memory-bound，大核、大 feature、未融合链常见。利用率高、带宽相对不高，更接近 compute-bound。7×7 慢且带宽占比 70% 以上，我会优先改结构或融合，而不是只加 optimize 等级。

---

## 附录 A：卷积核尺寸排查 checklist（可打印）

```
[ ] 已用芯片 profiler 分层，不仅对比 PyTorch/ONNX 的 FLOPs
[ ] 瓶颈层是否含 7×7 或更大 depthwise 卷积
[ ] 该层 MAC/Cube 利用率是否明显低于相邻 3×3 层
[ ] 该层 DDR 带宽占比是否偏高（如持续 >50%，视整网而定）
[ ] dump 图确认大核层 Conv+BN 是否未融合（多 kernel）
[ ] 已评估 7×7 → 3×3×3 或 1×7+7×1 等等价改法
[ ] 改图后 ORT 与任务指标（mAP 等）在业务线内
[ ] 改图后重新 BN 折叠并验证 fused op
[ ] 未指望仅调 converter 参数解决大核形状问题
[ ] 结论记入知识库：芯片型号、输入 shape、改前改后利用率与延迟
[ ] 工具链或分辨率变更后复测关键大核层
[ ] 新人能解释：FLOPs 相近 ≠ 实机一样快
```

---

## 附录 B：最小代码示例

下面脚本 **只算 FLOPs 和 im2col 行宽**，对比单颗 7×7 与三个 3×3 堆叠在纸面上的乘加量，以及 im2col 后矩阵行的「硬件友好度」直觉。不依赖 NPU SDK；真实延迟还要加上利用率与访存，请配合上板 profile。

```python
"""
对比 7×7 Conv 与 3×3×3 堆叠的 FLOPs（极简化）及 im2col 行宽。
行宽越小，通常越容易对齐硬件 GEMM 块——这是利用率差异的直觉来源之一。
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
    """单次 Conv2d 前向 MAC 数（乘加各算 1，FLOPs ≈ 2×MAC）。"""
    out_h, out_w = spec.h, spec.w  # 假设 same padding，简化
    if spec.groups == spec.c_in == spec.c_out:
        # depthwise
        mac = spec.c_in * spec.k * spec.k * out_h * out_w
    else:
        mac = spec.c_in * spec.c_out * spec.k * spec.k * out_h * out_w // spec.groups
    return mac * 2  # FLOPs


def im2col_row_width(k: int) -> int:
    return k * k


def main():
    c_in = 256
    h, w = 56, 56

    # 场景 A：输出通道相同——堆叠 FLOPs 通常更低（中间通道可加大来对齐，见场景 B）
    c_out = 256
    flops_7 = conv_flops(ConvSpec(c_in, c_out, k=7, h=h, w=w))
    flops_3_stack = sum(
        conv_flops(ConvSpec(c_in if i == 0 else c_out, c_out, 3, h, w))
        for i in range(3)
    )

    print("=== 场景 A：同输出通道 256 ===")
    print(f"输入特征图: {c_in}×{h}×{w}, 输出通道 {c_out}")
    print(f"单颗 7×7 FLOPs:     {flops_7 / 1e9:.2f} G")
    print(f"三个 3×3 堆叠 FLOPs: {flops_3_stack / 1e9:.2f} G")
    print()

    # 场景 B：把堆叠侧通道加大，使 FLOPs 接近 7×7（正文对比表用的就是这种对齐方式）
    c_out_stack = 460  # 粗调使 FLOPs ~10G，实项目按目标 FLOPs 反推
    flops_7_b = conv_flops(ConvSpec(c_in, 256, k=7, h=h, w=w))
    flops_3_matched = sum(
        conv_flops(ConvSpec(c_in if i == 0 else c_out_stack, c_out_stack, 3, h, w))
        for i in range(3)
    )

    print("=== 场景 B：FLOPs 故意对齐（7×7→256 通道，堆叠→460 通道）===")
    print(f"7×7 FLOPs:           {flops_7_b / 1e9:.2f} G")
    print(f"3×3×3 堆叠 FLOPs:    {flops_3_matched / 1e9:.2f} G")
    print(f"FLOPs 比值:          {flops_3_matched / flops_7_b:.2f}")
    print()
    print(f"im2col 行宽 7×7: {im2col_row_width(7)}  (每窗口元素数)")
    print(f"im2col 行宽 3×3: {im2col_row_width(3)}  (每层，堆叠每层都是 9)")
    print()
    print("说明：FLOPs 对齐后，49 vs 9 的行宽差异仍在；7×7 还要缓存 7 行输入。")
    print("实机谁快看 utilization 和 DDR——请 profile，勿只跑本脚本。")


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
| im2col | image to column | 卷积窗口摊平成行，好变矩阵乘 |
| GEMM | General Matrix Multiply | 通用矩阵乘；NPU/GPU 核心算子 |
| DDR | 片外内存 | 大仓库；带宽常是瓶颈 |
| L2 / SRAM | 片上缓存 | 小案板；装不下就多跑 DDR |
| Depthwise | 逐通道卷积 | 大核时矩阵极小，利用率常很差 |
| BN 融合 | Conv+BN fuse | 中间 feature 少写一次 DDR |
| Converter | 模型转换工具 | 编译同一张图；不会自动拆 7×7 |
| Cache thrashing | 缓存抖动 | 缓存装不下，数据反复从 DDR 读 |
