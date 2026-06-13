# 混合精度 skip_layers，什么时候该用？

> **导读**：全 INT8 后 mAP 掉 1.2 个点，新人要么直接换回 FP16，要么把检测头十几层全 skip——前者浪费 INT8 吞吐，后者和全 FP16 差不多。混合精度的核心是 **用最少 FP16 层，换回业务能接受的精度**。  
> **阅读时间**：约 20 分钟  
> **适合谁**：PTQ 精度差一点、被问「哪些层要 skip」、或第一次调 `skip_layers` 的部署工程师。

---

## 决策卡点：掉 1.2 点 mAP，换还是 skip？

某次 YOLOv5s 上昇腾 310，全 INT8 延迟 10ms，mAP 从 0.852 掉到 0.840——掉了 1.2 个点，超出产品给的 0.5 点红线。新人第一反应是「量化不行，改全 FP16」，延迟涨到 14ms，功耗也上去一截；另一个同事把检测头三层卷积标成 FP16，mAP 回到 0.850，延迟只多了 1.2ms。

这就是混合精度（工具链里常叫 `skip_layers`）要解决的矛盾：**不是少数层敏感就放弃整网 INT8，而是只让敏感层保持 FP16，其余继续跑 INT8**。我见过更极端的反例：一口气 skip 了 backbone 后半段二十多层，延迟和全 FP16 差不到 1ms，INT8 几乎白量化——层数不是越多越好，每笔 skip 都要算性价比。

---

## 混合精度在部署链路里干什么

```
  .pt → ONNX (FP32) → ORT 验收
              │
              ▼  PTQ + 校准集
  全 INT8 ONNX / 芯片模型
              │
              ▼  双端精度对比 + 业务指标
  ┌──────────────────────────────────────────────────────────┐
  │ 精度不达标？                                              │
  │   · 先查校准集、预处理、算子实现（别一上来就 skip）          │
  │   · 仍不够 → 逐层定位敏感层 → skip_layers 混合精度（本篇）   │
  └──────────────────────────────────────────────────────────┘
              │
              ▼  增量 skip + profiling
  混合精度模型（大部分 INT8 + 少数 FP16）
              │
              ▼  业务指标 + 延迟门禁
  上线
```

混合精度卡在 **「全 INT8 差一点」和「全 FP16 太贵」之间**。它不是兜底万能药，而是 PTQ 调优里 **数据驱动的精细化手段**——每一层 skip 都要有逐层对比和 profiler 数据支撑，不能凭「检测头肯定敏感」拍板。

---

## 零基础先搞懂：本篇会反复出现的名词

### PTQ 与 INT8 量化

**PTQ（Post-Training Quantization，后训练量化）** 是在训练完成的浮点模型上，用校准集统计各层数值范围，把 FP32/FP16 权重和激活映射到 INT8（通常 -128～127）。映射公式常见写法：

    q = round(x / scale) + zero_point

`scale` 和 `zero_point` 由校准数据决定。不同算子对离散化误差的敏感度差很多——backbone 里大通道卷积往往很稳，检测头、Softmax、LayerNorm 容易掉点。

### skip_layers / 混合精度

**skip_layers** 是量化工具的配置项：列表里的层 **不做 INT8 权重量化**，保持 FP16 计算。工具链会在 INT8 与 FP16 交界处自动插入 Quantize/Dequantize（Q/DQ）节点做类型转换。最终模型里 **大部分算子跑 INT8，少数指定层跑 FP16**，所以叫混合精度。

注意：这里的「混合精度」指 **部署侧的 INT8+FP16 混合**，和训练里 AMP（Automatic Mixed Precision）不是一回事，别混谈。

### 余弦相似度（Cosine Similarity）

两个同 shape 张量拉平为向量 `a`、`b`：

    cos(a, b) = dot(a, b) / (norm(a) × norm(b))

余弦看 **方向是否一致**，对整体缩放不敏感。逐层对比时，我通常把 **关键区域余弦 < 98%** 当作敏感层初筛门槛——检测模型可看置信度 > 0.1 的前景区域，分类可看 logits Top-K 区域，避免背景低值把全局余弦「洗平」。

### 算子融合（Operator Fusion）

编译器会把 `Conv + BN + ReLU` 等链式算子合成一个 kernel，中间结果留片上、少写 DDR。**skip 链中间的某一个算子**，融合链会断，中间结果必须落地内存，还可能多一次反量化——隐性性能代价往往比「这层本身用 FP16 算」大得多。

### 性价比（本篇核心判断标准）

对每一层候选 skip，我会同时看两件事：**精度收益**（mAP/召回回升多少）和 **性能代价**（端到端延迟涨多少、DDR 带宽是否打满）。用最少的 skip 层数满足业务精度，才是合格方案。

---

## 三种精度方案，各自站什么位

| 方案 | 说明 | 精度 | 性能 | 典型场景 |
|------|------|------|------|----------|
| 全 FP16 | 权重和计算都用 16 位浮点 | 最高，接近训练端 | 最慢，算力/带宽约为 INT8 一半 | 精度红线极严、性能宽松 |
| **混合精度（skip_layers）** | 大部分 INT8，少数层 FP16 | 接近全 FP16 | 接近全 INT8 | 少数层敏感，全量化差一点 |
| 全 INT8 | 全部 8 位整数 | 有量化误差 | 最快，能效最好 | 精度冗余大、追求吞吐 |

表后补一句：**混合精度是折中态，不是默认选项**。项目里我仍先跑全 INT8；只有业务指标明确超标、且定位到少数量化敏感层时，才上 skip。若 skip 后延迟已接近全 FP16 的 70% 以上，维护成本还不如直接全 FP16。

---

## 什么时候该用 skip_layers？

### 场景一：逐层对比定位到少数量化敏感层

这是最标准、最推荐的路径。

触发条件通常是：全 INT8 后 **少数几层余弦 < 98%**，其余层在 99.9% 以上；业务指标掉点超出阈值但幅度不大（检测任务掉 0.5～2 个点不罕见）；敏感层计算量占比不高（多数项目 **< 10%** 算力）。

YOLOv5s 的例子：backbone 卷积余弦都在 99.9% 以上，Detect 头三层只有 97.2%，mAP 掉 1.2 点。只 skip 这三层，mAP 回到只掉 0.2 点，延迟 +1.2ms——用大约 15% 的性能代价换回了大部分精度损失，这笔账值得做。

### 场景二：校准集覆盖不足，特定场景劣化

通用测试集达标，但暗光、极小目标等边缘场景暴跌；短期内又补不齐对应校准数据。若定位到某条分支的量化 scale 和该场景分布不匹配，可以 **只 skip 该分支末端几层**，比全模型回 FP16 划算。

工业小目标检测我遇到过：正常光照 mAP 够，暗光漏检飙升。8 倍下采样分支最后两层 skip 成 FP16 后，暗光召回回来，整体延迟涨幅可控，不必等重新采数、重跑整套 PTQ。

### 场景三：算子 INT8 实现有缺陷

某类算子在特定 CANN/驱动版本上 INT8 实现有 bug 或强近似（老版本 INT8 Softmax 在置信度阈值附近误差大，导致误检增多）。算子本身计算量小、短期内等不到厂商修复时，skip 该算子保持 FP16 是务实做法——Softmax 这类 op skip 后延迟几乎无感，但误检率能恢复正常。

**先排除再 skip**：预处理不一致、校准集偏、CPU fallback、算子近似——这些不该用 skip 掩盖。skip 是 **定位清楚敏感层之后** 的手段，不是精度不行的第一选择。

---

## 科学选层：数据驱动，别凭经验

不要听「检测头一定要 skip」就全 skip。不同模型、数据集、芯片版本的敏感度差很大。我习惯按下面四步走，没有逐层数据就不动 `skip_layers`。

### 第一步：建立两个基准

做任何 skip 之前，先跑 **全 INT8** 和 **全 FP16** 两个版本，记下业务指标、端到端延迟、MAC 利用率、DDR 带宽。这是后面所有 trade-off 的标尺。

    可接受精度损失 = 产品给的指标红线（如 mAP 掉点 ≤ 0.5）
    可接受性能损失 = 延迟红线（如端到端 ≤ 12ms）

最终目标：**在满足精度红线的前提下，延迟尽量低**——也就是在两条边界之间找帕累托最优点。

### 第二步：拉出精度敏感候选池

用逐层对比工具跑全 INT8 模型，按误差从大到小排序。初筛指标我按可信度这样用：

1. **业务输出相关层的分布差异**（如检测 head 的 KL 散度，以 FP16 输出为基准分布 P、INT8 为 Q，KL 越大越敏感）
2. **关键区域余弦**（检测看前景高置信区域，分类看 Top-K logits）
3. **全局余弦 + MSE**（快速排序用，不能单独当决策依据）

数值误差大不等于业务影响大。浅层误差可能被后续层抵消；最准的做法是 **单层 ablation**：其余层保持 FP16，只把某一层量化为 INT8，看业务指标掉多少——这是该层真实业务敏感度，测试成本高但结论可靠。初筛候选池里取前 10～15 层做 ablation 通常够用。

同样余弦 97%，检测头对 mAP 的影响往往是 backbone 首层的数倍——**位置越深、越靠近输出，业务权重越高**。

### 第三步：评估每层 skip 的性能代价

| 代价类型 | 说明 | 怎么评 |
|---------|------|--------|
| 显性计算/内存 | FP16 权重和特征图体积是 INT8 的 2 倍 | 参数量、MAC 粗算 |
| 融合断裂 | skip 打断 Conv+BN+ReLU 等融合链，中间结果写 DDR | dump 计算图 + profiler 实测 |
| 带宽饱和 | 模型已是内存瓶颈时，额外 FP16 读写让延迟非线性涨 | msprof 看 DDR 占用 |

**最高危的坑**：单独 skip 融合链中间的 ReLU——原本三合一的 `Conv+BN+ReLU` 断成两截，多一次反量化、一次写 DDR、一次读 DDR，延迟涨幅可能是 ReLU 本身算力的十倍以上。若必须 skip 激活层，尽量 **整条链一起 skip**（Conv+BN+ReLU 统一 FP16），或 skip 链末端，不要从中间拦腰截断。

红线参考：某层 skip 后延迟涨幅超过全 FP16 涨幅的 20%，但精度收益不到总损失的 10%，直接放弃该层。

### 第四步：按性价比增量迭代

给每个候选层算：

    性价比 ≈ 业务精度收益 / 端到端延迟涨幅

精度收益高、延迟涨幅小的层优先。然后从排名第一的开始 **逐个叠加**，每加一层都重新编译、测完整业务指标和 profiler——精度达标就停，性能触线就回退，边际收益过低（比如多 skip 一层只回升 0.1 点 mAP 却涨 1ms）也停。

**高性价比，通常优先 skip：**

- 检测头/分类输出层（计算占比小、业务影响直接）
- Softmax、Sigmoid、LayerNorm（算力极小，skip 几乎无感）
- 小通道、小尺寸卷积
- 模型最后 2～3 层

**低性价比，尽量别 skip：**

- backbone 前中层大通道卷积（算力占比高）
- 残差里的 Add、夹在融合链中间的 BN/ReLU
- 计算量占总量 > 5% 的大算子

检测模型还可以 **按分支 skip**：YOLO 三条 head 敏感度常不同，小目标 8× 分支最敏感时，只 skip 这一条，中、大目标分支保持 INT8——用远低于「三头全 skip」的代价解决主矛盾。

---

## 最常见坑（附排查顺序）

### 坑 1：过度 skip，INT8 名存实亡

**典型做法**：精度不对就把 backbone 后半段、整个检测头一口气 skip 几十层。  
**现象**：延迟和全 FP16 差不到 2ms，文件体积也接近 FP16。  
**原因**：被 skip 层的计算量可能已占总算力 30% 以上，INT8 优势丧失。  
**怎么查**：统计 skip 层 MAC 占比；对比混合精度 vs 全 FP16 延迟比值。  
**怎么改**：回退到增量迭代的最小组合；若 skip 算力 > 30% 或延迟达全 FP16 的 80%，改全 FP16，维护更简单。

### 坑 2：凭经验选层，不做逐层验证

**典型做法**：「检测头肯定敏感」「LayerNorm 不能量化」——不跑数据直接写 skip 列表。  
**现象**：skip 了十层，mAP 只回升 0.1 点，延迟却涨 4ms。  
**原因**：该模型上真正敏感的可能只是输出前两层，其余 skip 是白亏性能。  
**怎么查**：逐层余弦 + 单层 ablation，按业务掉点排序。  
**怎么改**：删掉无效 skip；经验只作初筛参考，决策以 ablation 和增量实验为准。

### 坑 3：只看 mAP，不测延迟

**典型做法**：每加一层 skip 只跑验证集 mAP，不上板 profiling。  
**现象**：上线前才发现延迟从 10ms 涨到 18ms，超出产品要求，整版回退。  
**原因**：skip 带来带宽和融合断裂代价，纸面算力估算看不出来。  
**怎么查**：msprof 看 DDR 带宽、MAC 利用率、端到端延迟；对比每版 skip 列表。  
**怎么改**：**每加一层 skip 必跑 profiler**；和产品对齐「掉 0.5 点 mAP vs 多 3ms」的选项，别工程师单方面拍板。

### 坑 4：skip 位置打断融合链

**典型做法**：只把 `Conv+BN+ReLU` 里的 ReLU 标成 FP16。  
**现象**：单层 ReLU 理论上几乎不算力，整模块延迟却翻倍。  
**原因**：融合链断裂，Conv 输出写 DDR，再读入做 FP16 ReLU。  
**怎么查**：ATC 编译加 `--dump_graph=1`，看 skip 前后融合是否还在；profiler 看该段 DDR 读写是否异常。  
**怎么改**：整条链统一精度，或换 skip 到链末端；分组 skip（整个残差块、整个检测分支统一 FP16/INT8）往往比单层 skip 更划算。

### 坑 5：该补校准却直接 skip

**典型做法**：某层余弦低，不查校准集分布，直接 skip。  
**现象**：补了对应场景校准数据重跑 PTQ 后，该层余弦回到 99% 以上，之前的 skip 本不需要。  
**原因**：误差来自校准覆盖不足，不是算子本身敏感。  
**怎么查**：看该层激活 histogram 是否被少数 outlier 拉偏；补场景数据后重跑 PTQ 对比。  
**怎么改**：**先优化校准集，再考虑 skip**；校准无效再走 skip 流程。

---

## 昇腾 AMCT 实操要点

在 AMCT 量化配置里用 `skip_layers` 指定层名（与 ONNX 节点名一致，Netron 里可核对）：

```python
from amct.onnx import quantize_model

# 从少到多迭代：先只 skip 最高性价比层，不够再加
skip_layers = [
    "detect.head_conv_8x",   # 小目标检测头（示例名，按实际图改）
    # "detect.head_conv_16x",
    # "detect.head_conv_32x",
]

config = {
    "precision_mode": "int8",
    "skip_layers": skip_layers,
    "calibration_data": "./calib_data/",
    "quantize_algorithm": "kl",
}

quantize_model(
    model_file="model.onnx",
    output_file="model_quant.onnx",
    config=config,
)
```

skip 后 **必须验证融合**：ATC 编译时加 `--dump_graph=1` 导出图，确认 Q/DQ 没有插在融合链中间；msprof 实测 DDR 和 MAC，确认没有异常尖峰。

和产品沟通时，别只说「要做混合精度」，把选项摆清楚：

> 全 INT8：10ms，mAP 掉 1.2 点；skip 检测头三层：11.2ms，mAP 只掉 0.2 点；全 FP16：14ms，mAP 不掉。业务能接受哪种？

每个混合精度版本归档：**skip 列表、精度数据、profiler 数据、工具链版本**。芯片栈升级后重测一遍，以前必须的 skip 有时可以删掉。

---

## 分组 skip 与进阶技巧

与其单独 skip 融合链中间一个 op，不如 **按算子组统一精度**：

- `Conv+BN+ReLU` 要么全 INT8，要么全 FP16
- 一个残差块统一精度
- 一条检测分支统一精度

这样可能多 skip 一两个算子，但避免了融合断裂的隐性税，整网延迟反而更低。

收敛停止条件，满足任意一条即可停：

1. 业务指标达到产品要求  
2. 端到端延迟触及性能红线  
3. 新增一层 skip 的边际收益过低（例如 < 0.1 点 mAP / ms）

---

## 面试追问

### 1

**问：** 混合精度 / skip_layers 什么时候用？

**答：** 全 INT8 PTQ 后业务指标超标，且逐层对比定位到 **少数** 量化敏感层（常见关键区域余弦 < 98% 或单层 ablation 掉点明显）时用。只 skip 这些层保持 FP16，其余继续 INT8。不是精度不行就 skip，要先排除校准、预处理、算子实现问题；也不是层越多越好，skip 算力占比过高就失去混合精度意义。

### 2

**问：** skip 一层会带来哪些代价？怎么评估？

**答：** 三方面：FP16 权重和激活 **体积翻倍** 带来的带宽压力；**算子融合链断裂** 导致中间结果写 DDR（隐性代价最大）；模型文件变大、验证复杂度上升。不能只看参数量，必须 profiler 测端到端延迟和 DDR。我会和产品谈具体数字，比如「掉 0.5 点 mAP 换 3ms」。

### 3

**问：** 怎么科学决定 skip 哪些层？

**答：** 先跑全 INT8、全 FP16 两个基准定红线；逐层对比初筛敏感层，对 top 候选做 **单层 ablation** 看真实业务掉点；再评估每层 skip 的性能代价和融合风险，算性价比；从高性价比层开始 **增量叠加**，精度够就停。检测头、Softmax 等常是高性价比层，backbone 大卷积和残差 Add 通常是低性价比。

### 4

**问：** 为什么单独 skip 融合链中间的 ReLU 可能让延迟暴涨？

**答：** 编译器本可以把 `Conv+BN+ReLU` 合成一个 kernel，中间结果留片上。ReLU 被 skip 成 FP16 后，Conv 的 INT8 输出必须先 **反量化写 DDR**，再读入做 FP16 ReLU——融合链断了。这点额外访存和类型转换的开销，往往远大于 ReLU 本身。所以要整条链一起 skip，或 skip 链末端，skip 后 dump 图确认融合状态。

### 5

**问：** 混合精度和训练里的 AMP 是一回事吗？

**答：** 不是。训练 AMP 是在 backward 里混用 FP16/FP32 省显存、提速度。部署里的混合精度（skip_layers）是 **PTQ 之后** 在芯片模型里让大部分层跑 INT8、指定层跑 FP16，用来在精度和 NPU 吞吐之间折中。工具链会在 INT8/FP16 边界插 Q/DQ 节点。

---

## 附录 A：混合精度选型 checklist（可打印）

```
[ ] 已跑全 INT8 基准：业务指标、逐层余弦、延迟、MAC、DDR
[ ] 已跑全 FP16 基准：业务指标、延迟（作精度真值和性能下限）
[ ] 已明确产品精度红线和延迟红线
[ ] 已排除预处理不一致、校准集偏、CPU fallback、算子 bug
[ ] 尝试补充场景校准数据并重跑 PTQ（无效再 skip）
[ ] 逐层对比完成，候选敏感层 ≤ 总层数约 15%
[ ] 对 top 候选做了单层 ablation，有业务敏感度排序
[ ] 标记了融合链高危点（残差 Add、链中间 BN/ReLU）
[ ] 每层 skip 评估了显性代价 + 融合断裂风险
[ ] 按性价比从高到低增量叠加 skip，每步测 mAP + profiler
[ ] skip 后 dump 计算图，确认融合未被意外破坏
[ ] 最终全量测试集验收业务指标
[ ] 端到端延迟在性能红线内
[ ] skip 列表、精度/性能数据、工具链版本已归档
[ ] 和产品确认过 trade-off 选项（非工程师单方面决定）
```

---

## 附录 B：逐层余弦初筛 + 性价比粗算脚本

以下脚本演示：**ORT 跑 FP16 与 INT8 会话、逐层拉输出算余弦、按阈值筛候选**。层名需按你的 ONNX 改；INT8 模型需先用 AMCT 导出。单层 ablation 要多次改 skip 列表重跑量化，这里不展开，但初筛逻辑可直接复用。

```python
import numpy as np
import onnxruntime as ort

FP16_ONNX = "model_fp16.onnx"
INT8_ONNX = "model_int8.onnx"
INPUT_NAME = "images"
CALIB_NPY = "calib_sample.npy"  # shape: (1, 3, H, W)

COS_THRESHOLD = 0.98
# 按 Netron / 模型结构填写要对比的中间层输出名
LAYER_OUTPUTS = [
    "output0",           # 最终输出
    "/model/Detect/output",
    # ... 其他中间层
]


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    af = a.flatten().astype(np.float64)
    bf = b.flatten().astype(np.float64)
    return float(np.dot(af, bf) / (np.linalg.norm(af) * np.linalg.norm(bf) + 1e-12))


def run_layers(session, feed, output_names):
    return session.run(output_names, feed)


def main():
    x = np.load(CALIB_NPY).astype(np.float32)
    feed = {INPUT_NAME: x}

    fp16_sess = ort.InferenceSession(FP16_ONNX, providers=["CPUExecutionProvider"])
    int8_sess = ort.InferenceSession(INT8_ONNX, providers=["CPUExecutionProvider"])

    fp16_outs = run_layers(fp16_sess, feed, LAYER_OUTPUTS)
    int8_outs = run_layers(int8_sess, feed, LAYER_OUTPUTS)

    candidates = []
    print(f"{'layer':<40} {'cosine':>8}")
    print("-" * 50)
    for name, a, b in zip(LAYER_OUTPUTS, fp16_outs, int8_outs):
        cos = cosine(a, b)
        flag = "  <-- 候选" if cos < COS_THRESHOLD else ""
        print(f"{name:<40} {cos:>8.4f}{flag}")
        if cos < COS_THRESHOLD:
            candidates.append(name)

    print(f"\n初筛候选 ({len(candidates)} 层): {candidates}")
    print("下一步: 对候选做单层 ablation + profiler 估延迟，再写 skip_layers")


if __name__ == "__main__":
    main()
```

用法：准备同一张校准图 `calib_sample.npy` 和一对 FP16/INT8 ONNX，改好 `LAYER_OUTPUTS`，执行 `python layer_cosine_screen.py`。候选层再人工结合算力占比和融合位置排 skip 优先级。

---

## 术语速查

| 术语 | 全称 / 含义 | 一句话直觉 |
|------|------------|-----------|
| skip_layers | 跳过量化层列表 | 指定层保持 FP16，其余 INT8 |
| 混合精度（部署） | INT8 + FP16 混跑 | 不是训练 AMP；是 PTQ 后的精度折中 |
| PTQ | Post-Training Quantization | 训后量化；靠校准集定 scale |
| Q/DQ | Quantize / Dequantize | INT8 与 FP16 边界上的类型转换节点 |
| 余弦相似度 | Cosine Similarity | 逐层筛查用；关键区域 < 98% 进候选 |
| ablation | 单层控制变量实验 | 只量化一层，看真实业务掉点 |
| 算子融合 | Operator Fusion | skip 断链会多写 DDR，隐性变慢 |
| MAC 利用率 | — | skip 后若涨幅异常，查融合和带宽 |
| AMCT | Ascend Model Compression Toolkit | 昇腾量化工具；`skip_layers` 在此配置 |
| 性价比 | 精度收益 / 延迟代价 | 混合精度选层的核心标尺 |
