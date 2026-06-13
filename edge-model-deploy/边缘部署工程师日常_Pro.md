# 边缘部署工程师日常到底在干什么？

> **导读**：训练组交的是 FP32 大图，客户要的是某颗芯片上 INT8 实时跑——中间每一层都可能吃精度。部署工程师的日常，就是在硬件硬约束下把「能编过、够准、够快、够省」四件事拉到平衡。  
> **阅读时间**：约 28 分钟  
> **适合谁**：懂一点深度学习、还没系统做过边缘上板，或面试被问「部署工程师一天在干嘛」的同学。

---

## 交付物界定：口头说「量化模型」，文件夹里其实有四样东西

某次周会，算法同学说「量化模型已经交了」，PM 问「能不能下周上试点」。我打开共享盘：一个 `model_int8.onnx`、一份没写版本的校准图片文件夹、converter 默认参数编出来的 `.om`，没有双端对比报告，也没有 profiler 截图。

现场跑了一下：编译 0 error，mAP 从云端 0.86 掉到 0.71，fps 只有目标的一半。算法说「量化掉点正常」；我翻 log 发现检测头两个算子 **fallback 到 CPU**，整帧 38ms 里有 22ms 耗在 CPU 上——这不是「INT8 掉点」，是 **图没编对 + 性能没验**。

这类误会我见得不少：**「模型文件」只是交付物的一角**。边缘部署工程师真正交付的，是一套 **能在指定芯片、指定版本工具链、指定输入 shape 下复现** 的方案包。口头上的「量化完成」，在工程上通常要拆成四件事是否都过关：能编过、够准、够快、够省。下面按这个顺序展开。

---

## 面试一句：用几分钟讲清楚你在干什么？

常被追问：边缘部署工程师日常到底在干什么？和算法工程师、训练工程师有什么区别？

我一般会先拉齐四件事：**精度、延迟、功耗、能不能在这颗芯片上编过**。训练给的是通用 FP32 大模型，客户要的是固定场景下 INT8 实时推理。中间导出算子变了、校准分布偏了、converter 用了近似实现、后处理写错了——每一环都可能掉点或变慢。我的日常大量时间在：**同一份输入对齐 PC 和设备**、读 convert 和 profiler 日志、把「这颗芯片这样改」记进算子知识库。同类 YOLO 检测头 unsupported，新人查三天，熟手半天——靠的不是聪明，是沉淀。

**面试 30 秒口述模板**（可按项目改数字）：我们是把训练模型落到边缘芯片的搭桥人。训练交 FP32，客户要某颗 NPU 上 INT8 实时跑。我负责算子能不能编过、双端精度对齐、profiler 压延迟和功耗，并把踩过的坑写进知识库。和算法的边界是：他们追结构和 mAP，我追实机能不能编、掉多少点、fps 和功耗过不过线。

---

## 这个岗位在部署链路里干什么

部署工程师不是「把 `.pt` 丢给工具链就完事」，而是 **训练模型到边缘芯片之间的落地搭桥人**。整条链路上，算法同学定结构和 loss，训练同学追 mAP，部署同学要在 **特定芯片、特定工具链、特定功耗预算** 下交付可维护的方案。

```
  训练交付
  ┌──────────────────────────────────────┐
  │ FP32 / FP16 大模型 + ONNX（有时）     │
  │ 指标在云端 GPU 上测过，未必适合边缘   │
  └──────────────────────────────────────┘
              │
              ▼  部署工程师接手（本篇主题落在这里）
  ┌──────────────────────────────────────────────────────────┐
  │ ① 能编过：算子白名单、unsupported 改图、编译通关          │
  │ ② 够准：双端对齐、逐层 dump、量化 / skip / 混合精度        │
  │ ③ 够快：profiler 定位瓶颈、Tiling、融合、AutoTune          │
  │ ④ 够省：稳态功耗、峰值内存、长时间压测                     │
  └──────────────────────────────────────────────────────────┘
              │
              ▼  converter（ATC / trtexec / 厂商工具）
  芯片模型（.om / .engine / …）
              │
              ▼  ADB / 实机推理 + 任务验收
  可上线交付物：模型 + 编译配置 + 测试报告 + 知识库条目
```

我在项目里习惯把交付物写清楚：不只是「一个能跑的模型文件」，还包括 **编译参数、校准集版本、双端对比报告、profiler 截图、后处理参数**——半年后要能复现，靠的是这些归档，不是当时的记忆。

### 一份「能复现」的交付包长什么样

| 交付项 | 典型内容 | 为什么必须留 |
|--------|----------|--------------|
| 芯片模型 | `.om` / `.engine` 等 | 上线推理用 |
| 编译配置 | converter 版本、命令行、json 配置 | 换人不换结果 |
| 校准集 | 图片列表 + 版本号 + 制作说明 | 量化争议时可追溯 |
| 双端报告 | input.bin、层余弦/MSE、mAP、坏例图 | 证明「准」不是口头 |
| Profiler 报告 | 瓶颈层、利用率、带宽、前后对比 | 证明「快」有依据 |
| 后处理参数 | anchor、NMS、letterbox 脚本版本 | 余弦高但框乱时救命 |
| 知识库条目 | 芯片型号 + 改图记录 + 掉点 | 下次同类项目省天 |

表后补一句：PM 问「能不能上线」，我习惯拿 **任务指标 + 资源指标 + 归档是否齐全** 三样东西答，而不是只报一个 mAP 数字。

---

## 零基础先搞懂：本篇会反复出现的名词

下面按「直觉 → 部署里怎么用」写。后文再出现这些词，可以直接当复习。

### FP32、INT8 与 PTQ（Post-Training Quantization，后训练量化）

**FP32** 是 32 位浮点，训练和普通 PC 推理的默认精度，数值范围宽、表达细，但算力和访存都贵。边缘芯片算力有限，客户口头要的「量化模型」多数指 **INT8（8 位整数）推理**：权重和激活用更少的 bit，乘加走整数单元，延迟和功耗通常能明显下降——具体幅度因芯片、是否 memory-bound 而异，不能默认「INT8 一定快一倍」。

**PTQ** 是在 **训练完成之后** 对浮点模型做量化：用校准集（calibration set）统计各层激活分布，定 `scale` 和 `zero_point`，不需要重新训练。多数检测、分类项目的首选路径，周期短。若 PTQ 掉点超业务线，才考虑 QAT（Quantization-Aware Training，量化感知训练）或混合精度。

量化里两个符号反复出现：

    q = round(x / scale) + zero_point
    x_dequant = (q - zero_point) * scale

`scale` 把浮点范围映射到 int8 格点；校准集就是在估各层 `scale` 该取多少。校准集偏了（比如全是白天图、没有夜间），夜间场景 scale 就不准，掉点往往从「某几类」开始。

### ONNX 与 converter

**ONNX（Open Neural Network Exchange）** 是中间交换格式，把 PyTorch / TensorFlow 的算子图导出成统一描述，方便换后端跑。部署里 ONNX 常承担 **「数学正确性验收」**：先在 ONNX Runtime（ORT）上跑通，再交给芯片 converter。

**Converter** 是各芯片厂商的模型转换工具（如昇腾 ATC、TensorRT 的 `trtexec`）。它读 ONNX，做算子映射、图优化、量化、Tiling，输出 **只能在该芯片上跑的模型文件**。Converter 不会帮你改网络结构——大核拆小核、检测头改写法，是部署工程师在进 converter 之前的事。

### 算子兼容与 fallback

每个芯片只支持 **算子白名单** 里的一部分算子和参数组合。不支持的节点会报错（unsupported），或 **fallback（回退）** 到 CPU 跑——整网延迟可能被一层 CPU 算子拖死。日常第一件事往往是：对照白名单扫一遍图，列 unsupported 清单，再决定改图还是换实现。

我见过最坑的一种：**编译 0 error，log 里一行小字写某算子 fallback CPU**。新人以为「能跑就行」，profile 一看单层 CPU 占 60% 帧时间——整网优化全白做。

### 双端精度对齐与 input.bin

**双端对比** 指 PC 侧（ORT 或浮点参考）和设备侧（NPU 实机）用 **完全相同的输入** 跑推理，比输出差多少。标准做法是预处理在 PC 做一次，存成 `input.bin`（原始字节流），设备只读 bin 推理，避免两端各写一套 resize / normalize。

**余弦相似度** 把两个同 shape 张量拉成向量后算夹角余弦：`cos(a,b) = dot(a,b) / (norm(a) × norm(b))`。层对齐常用门槛，例如 backbone 层余弦 > 0.99。但它对整体缩放不敏感——余弦 99.8% 而检测框全乱，我见过很多次，问题往往在后处理而不是张量数值。

### Profiler 与 MAC 利用率

**Profiler** 是芯片侧性能分析工具，告诉你 **每一层 / 每一个 kernel 花了多少时间**，以及 MAC（Multiply-Accumulate，乘加）利用率、DDR 带宽占比。性能优化 **不靠拍脑袋改模型**，先 profile 再动刀。

**MAC 利用率** 指实际达到的算力占芯片理论峰值的比例。利用率 20% 意味着大量时间在等数据或空转——FLOPs 减半不代表延迟减半，常见原因就是利用率没拉满。

读 profiler 时我习惯先看三列：**算子名、耗时占比、MAC 利用率**。某层耗时 30% 但利用率 15%，多半是 Tiling 或融合问题；耗时不高但 DDR 带宽顶满，可能是 memory-bound，改结构比加 optimize 等级管用。

### 算子融合（Fusion）与 Tiling

**融合** 把多个算子合成一个 kernel 执行，例如 Conv + BN + ReLU，中间 feature 少写一次 DDR。图里多一个 Transpose 或 unsupported 激活，融合链就会断。

**Tiling（分块）** 是编译期把大矩阵切成小块以适应片上缓存和计算单元粒度。默认 Tiling 不对，大卷积 MAC 利用率可能只有百分之二十——调 Tiling、开 AutoTune 搜参，是日常性能活的重要组成部分。

### ADB 与上板联调

**ADB（Android Debug Bridge）** 是 PC 和设备之间的调试桥：`adb push` 推模型和 `input.bin`、`adb shell` 跑推理、`adb pull` 拉回 `output.bin`。昇腾开发板、不少边缘 Linux 板子都走这套。第一次联调卡在 `adb devices` 找不到设备，比卡在精度上还常见——链路没通之前，别急着调校准集。

---

## 跟一条模型走完全链路：新人两周在忙什么

下面用 **YOLOv5s 上某颗 NPU** 虚构一条时间线，数字是 plausible 的工程量级，帮新人建立「每天都在哪一环」的直觉。不同芯片、不同工具链会差很多，但 **关卡顺序** 差不多。

| 阶段 | 典型耗时（新人） | 在干什么 | 常见卡点 |
|------|------------------|----------|----------|
| Day 1～2 | 1～2 天 | 导出 ONNX、ORT 验收、mAP 对齐训练脚本 | opset 版本、动态轴、BN 未折叠 |
| Day 3～5 | 2～4 天 | 算子白名单扫描、清 unsupported | 检测头 GridSample、SiLU 变种、大核 Conv |
| Day 6～8 | 2～3 天 | PTQ、校准集、双端 input.bin 对齐 | 预处理不一致、校准集偏场景 |
| Day 9～11 | 2～3 天 | 逐层 dump、定位掉点层、skip / 混合精度 | 近似激活、head 分支余弦低 |
| Day 12～14 | 2～3 天 | Profiler、Tiling、融合、AutoTune | CPU fallback、Transpose 断融合 |
| 之后 | 持续 | 功耗长稳、归档、知识库 | 温升、内存峰值、版本漂移 |

熟手把同类型 YOLO 压到 **两天～三天**，靠的不是跳过步骤，而是 **unsupported 改法、校准集规模、编译参数** 都有现成条目——这就是下文说的沉淀。

---

## 日常核心：四道关，循环推进

我把日常工作收成四道关：**能跑、够准、够快、够省**。不是严格线性——编不过根本测不了精度，精度不对也不敢猛优化性能，但成熟项目里四件事会并行穿插，比如上午看编译结果，下午啃精度，傍晚 profile 性能。

### 第一关：先解决「能不能跑」——算子适配与编译通关

这是所有工作的前提，也是新人最容易卡一周的环节。

拿到训练好的 ONNX，第一件事 **不是测 fps**，而是 **过编译**：对照芯片算子白名单，扫所有节点是否支持、参数是否超限（kernel size、stride、channel 对齐粒度等）。编译日志里每一条 Warning 都要过一遍：哪些算子 fallback 到了 CPU、哪些用了近似实现、哪些融合被打断了——先记下来，后面精度、性能问题往往都能追溯到这几行。

遇到 unsupported，不能干等厂商修。常见等价改造包括：

| 原算子 / 结构 | 常见改法 | 精度影响 | 性能影响 |
|---------------|----------|----------|----------|
| 大核 7×7 Conv | 拆成 3×3×3 或 1×7+7×1 | 通常可保持，需 ORT 验证 | 利用率常明显提升 |
| 中间维 Softmax | Transpose 到 channel 末维 | 注意 layout | 避免 CPU fallback |
| GridSample / 自定义采样 | 改 bilinear 手写或近似 grid | 检测头可能掉点 | 去掉 CPU 瓶颈 |
| SiLU / 冷门激活 | 换 ReLU / 分段近似 | 看层位置 | 融合链可能恢复 |
| 动态 shape | 固定 batch、固定分辨率各编一版 | 无 | 编译器才能做满优化 |

同样是「YOLO 检测头某个算子不支持」，新人要查三天文档试五六种写法；熟手翻算子知识库，十分钟能判断改哪种、精度影响大概多少、性能代价多大。这一步 **最吃经验沉淀**。

**我过编译的习惯动作**（每步都可勾选）：

1. Netron 打开 ONNX，数一下节点类型，和大纲里的「高危算子」对照（GridSample、LayerNorm 变种、TopK 等）。
2. 跑 converter 的 check / dry-run（若有），先不量化，确认 FP16/FP32 路径能过。
3. 全文搜 log：`fallback`、`CPU`、`approx`、`unsupport`、`fusion failed`。
4. unsupported 清零后，再开 INT8 和 AutoTune——别在坏图上调校准。

验证项：编译 0 error；关键 Warning 已评估；无意外 CPU fallback 拖死整网。

### 第二关：死磕「准不准」——全链路精度对齐

占时间最多、也最容易踩坑的部分。核心原则是 **控制变量，逐层对齐**。

基础动作永远是 **同一份 input.bin 双端对比**：预处理统一在 PC 侧做完，设备侧只做推理，输入字节级一致，排除 resize 差一个像素这类干扰。精度出问题不瞎猜，按顺序定位：先看整网或关键层余弦对不对；再拆分支、逐层 dump 找误差从哪一层开始放大；再区分是量化引入的、编译器近似引入的、还是后处理写错的。

精度排查我建议固定走这条链（别跳步）：

```
  输入 bin 字节级一致？
        │ 否 → 停：修预处理，别调校准
        ▼ 是
  整网 / backbone 余弦达标？
        │ 否 → 逐层 dump，找「第一层明显变差」的层
        ▼ 是
  head 分支余弦 + MSE？
        │ 否 → 量化 skip、混合精度、近似算子
        ▼ 是
  任务 mAP / 准确率？
        │ 否 → 后处理：anchor、letterbox、NMS、class 序
        ▼ 是
  坏例可视化通过 → 精度关过关
```

最经典的坑：**余弦 99.8%，检测框全乱**。这时候不能死磕张量，要去查后处理——anchor 参数对不对、letterbox 逆变换有没有算错、类别顺序和训练是否一致、NMS 阈值是否和验证集脚本一致。量化调优也是日常重点：校准集是否覆盖真实场景、哪些层要 skip 量化、混合精度怎么选性价比最高，都是一遍遍测出来的，没有万能模板。

**校准集** 我一般会跟算法一起定三条：① 和训练分布同族（别只用验证集里好看的图）；② 覆盖光照、距离、遮挡等部署会见的工况；③ 数量多数项目在 100～500 张区间，检测分割偏多、分类可偏少——最终以业务为准。一张过曝图在 MinMax 策略下把 scale 拉歪，整类夜间场景崩掉，我见过。

验证项：关键层余弦 / MSE 达内部门槛；任务指标（mAP、准确率等）在业务线内；坏例回归通过。

### 第三关：优化「快不快」——性能深度调优

能跑、精度对了，才进入性能优化。核心工具永远是 profiler，绝不靠「感觉这层高应该慢」来改图。

先跑一轮性能分析，看三个核心指标：**MAC 利用率、DDR 带宽、算子耗时排行**。瓶颈可能是计算没跑满、内存供不上、还是调度 / launch 开销太大——对策完全不同。

| Profiler 信号 | 多半是什么 | 优先尝试 |
|---------------|------------|----------|
| MAC 利用率低、DDR 不高 | 形状不规整、Tiling 差、融合断 | AutoTune、改 Tiling、消 Transpose |
| DDR 带宽长期顶满 | memory-bound | 融合、减中间 tensor、改结构 |
| 单层 CPU 耗时异常 | fallback | 改图清 unsupported |
| 很多小 kernel、launch 多 | 融合差 | BN 折叠、改激活、减碎算子 |
| 某大 Conv 慢、利用率 20% | 大核 / 默认 Tiling | 拆核、针对性 Tiling |

优化手段多数是编译期静态优化：开 AutoTune 搜最优 Tiling、调整图结构引导算子最大化融合、对齐硬件 channel 粒度、替换高代价算子或改等价子图。

永远记住：**FLOPs 减半不代表延迟减半**。很多时候不改模型结构，只是把融合做全、Tiling 调对，延迟就能砍一大截——靠的是把硬件利用率拉满，不是少算几次乘法。我见过同一图，默认编 38ms，只调融合和 Tiling 到 21ms，mAP 不动。

验证项：延迟 / fps 达产品规格；瓶颈层利用率有改善记录；profile 报告已归档。

### 第四关：守住「够不够省」——功耗与资源合规

边缘端和云端最大的区别：**功耗、内存、散热全是硬约束**。性能再快，功耗超了或内存 OOM，也不能上线。

要测稳态功耗、峰值内存、长时间运行的温升。超了就要继续压：更激进的量化、剪枝冗余计算、优化内存复用、降低输入分辨率或帧率——和产品一起砍需求，而不是只闷头调参。还要做稳定性压测：连续跑几小时甚至几天，看有没有内存泄漏、延迟漂移、精度退化。

车载、无人机类项目，**P99 延迟** 有时比平均 fps 还硬——平均 15ms、偶尔抖到 45ms，产线或飞控不认。长稳时若温升导致降频，平均延迟会慢慢爬，这种要靠压测曲线说话，不是跑十次取平均就交差。

验证项：功耗 / 内存 / 温升在规格内；长稳压测无异常；资源占用可复现。

---

## 四道关怎么选优先级？（和算法 / 训练的分工）

| 维度 | 训练 / 算法同学主责 | 部署同学主责 |
|------|---------------------|--------------|
| 模型结构、mAP | 设计 backbone、head、loss | 结构是否能在目标芯片上编过、要不要改图 |
| 数据与标注 | 训练集、增强策略 | 校准集是否代表真实部署场景 |
| 精度指标 | 云端验证集 mAP | 设备上 INT8 mAP + 双端张量对齐 |
| 延迟 / 吞吐 | 通常不背 KPI | fps、单帧延迟、端到端 pipeline |
| 功耗 / 内存 | 通常不背 KPI | 稳态功耗、峰值内存、长稳 |
| 工具链 | 偶尔关心导出 | converter 版本、编译参数、算子库 |

表后补一句：边界不是死的。检测头改一版可能要算法一起评估掉点，但 **「这颗芯片能不能编过、实机快不快」** 一般是部署同学扛。面试里讲清分工，比背定义加分。

### 和 PM / 客户沟通时，怎么说才「稳」

客户问「量化掉几个点能接受」，别答「一般 1～2 个点」——要答 **业务线**：例如 mAP 0.85 以上、某类检出率不低于 xx%。问「多久能上线」，别答「三天量化完」，要答 **四道关**：unsupported 清完、双端对齐、fps 和功耗过线、归档齐全——哪关卡了哪关需要时间。这样不容易被一句「模型已经交了」带进坑里。

---

## 一个普通工作日的节奏（具象版）

更具象一点，工作日往往长这样——不同项目会打乱顺序，但活儿的类型差不多。

**上午（9:00～12:00）**：先看隔夜跑的编译和 AutoTune 结果。拉编译日志和 profiler 报告，看有没有新的算子 fallback、融合失败，对比上一版的精度和延迟变化，有结论就记进知识库。若编译挂了，优先清 unsupported 清单，别在坏图上调量化。

典型一幕：AutoTune 跑了八小时，延迟从 24ms 到 22ms，但 log 里多了一行某层用近似 `Sigmoid`——上午先补一版双端 dump，确认 mAP 没掉再合入。

**中午前后（12:00～14:00）**：定位前一天遗留的精度问题。拆分支、逐层 dump 输出，常见结论是某层激活函数用了近似实现，或某层 scale 不合适。改编译配置或量化策略重编一版，跑双端验证。

**下午（14:00～18:00）**：啃性能瓶颈。例如某层大卷积 MAC 利用率只有 20%，排查出是默认 Tiling 分块太小；调分块参数、开针对性 AutoTune，同时看图结构里有没有 Transpose 打断融合链，能不能移到算子链末尾。

**下班前（18:00 前）**：把今天踩的坑、验证过的最优参数、算子替代方案更新到团队算子知识库；归档模型、编译日志和测试报告，写好版本说明。半年后还能复现，靠的是这些，不是微信聊天记录。

### 算子知识库一条合格记录长什么样

```
芯片：昇腾 310B，CANN 8.0.RC2
模型：YOLOv5s，输入 1×3×640×640
问题：检测头 GridSample unsupported，编译 fallback CPU
改法：export 前换为固定 grid 的 bilinear 手写子图（附 onnx 节点截图）
精度：mAP 0.853 → 0.849（业务线 0.84）
性能：单帧 38ms → 19ms（去掉 CPU 瓶颈）
编译参数：soc_version=Ascend310B1，precision_mode=allow_mix_precision
验证人 / 日期：……
```

新人能照着抄，熟手能直接检索「310B + GridSample」，这就是知识库的价值。

---

## 最常见坑（附排查顺序）

### 坑 1：编译过了就以为「能交付」

**典型做法**：converter 0 error，直接报「模型已量化完成」。

**现象**：实机 fps 极低，或某些输入 shape 才 crash。

**原因**：Warning 里藏着 CPU fallback、动态 shape 未覆盖、近似算子未评估。

**怎么查**：全文搜 log 里的 fallback、approx、unsupport；实机 profile 看有没有 CPU 算子耗时异常。

**怎么改**：按 Warning 改图或改配置；unsupported 清零后再谈优化。

### 坑 2：双端对比输入不一致

**典型做法**：PC 用 OpenCV resize，设备 demo 用另一套预处理。

**现象**：整网余弦偏低，或 INT8 掉点离谱，调校准集无效。

**原因**：输入差一个像素，量化边界上误差会被放大。

**怎么查**：hexdump 或逐元素比 `input.bin`；确认 dtype、shape、layout（NCHW vs NHWC）。

**怎么改**：PC 预处理一次写 bin，设备只读 bin 推理；端到端验收则两端同一套代码。

### 坑 3：余弦很高，业务指标却崩了

**典型做法**：只盯 backbone 层余弦 > 0.99。

**现象**：mAP 掉很多，或检测框全乱。

**原因**：余弦对缩放不敏感；head 分支、后处理、类别映射错一点，框就飞了。

**怎么查**：单独 dump head 输出；核对 anchor、letterbox、NMS、class 顺序。

**怎么改**：张量对齐过关后，必须跑任务指标和坏例可视化；后处理参数跟训练验证脚本对齐。

### 坑 4：只改模型结构，不重新 profile

**典型做法**：听说「换轻量 backbone」就换，不跑 profiler。

**现象**：延迟反而变差，或内存暴涨。

**原因**：新结构可能更 memory-bound、融合更差、或引入新的 unsupported。

**怎么查**：换结构前后各 profile 一层；看瓶颈层是否变化。

**怎么改**：结构改动 = 重新走四道关至少前三关；别跳过编译和双端对比。

### 坑 5：校准集当验证集随便抓

**典型做法**：从验证集随机抽 50 张当 calib，场景单一。

**现象**：实验室 mAP 还行，现场某工况掉得厉害。

**原因**：校准集不代表部署分布，scale 估偏。

**怎么查**：看坏例是否集中在某一光照 / 距离；换 calib 重编对比。

**怎么改**：按部署场景补 calib；检测分割建议多于分类，数量视任务调整。

### 坑 6：工具链版本漂移

**典型做法**：同事用 CANN 8.0 编的版本，自己用 8.1 复现。

**现象**：同配置延迟差 10%、或某算子行为变了。

**原因**：converter、驱动、近似实现随版本变。

**怎么查**：对比 `ascend-toolkit` / 驱动版本号；查 release note。

**怎么改**：交付包锁版本；升级走完整回归，不单测 fps。

### 坑 7：个人经验不沉淀，同类项目反复踩坑

**典型做法**：问题解决了就关 ticket，不写文档。

**现象**：三个月后来个同芯片 YOLO 项目，又从 Day 1 查 unsupported。

**原因**：工具链版本、算子限制、最优 Tiling 没进知识库。

**怎么查**：团队有没有可检索的「芯片 + 算子 + 改法 + 掉点」记录。

**怎么改**：每条 verified 方案写进知识库：输入 shape、converter 版本、编译参数、前后指标。

---

## 这个岗位拼的是沉淀，不是聪明

很多人觉得部署要懂很多算法、数学要很好。实际日常里，八成问题都是 **前人踩过的坑**：这个算子在这个工具链版本有 bug、这种结构会打断融合、这组 Tiling 对这个 shape 最优、这个近似实现对检测头影响大。

新人做一个模型两周，熟手做同类型两天——差距很少是智商，是 **算子知识库厚不厚、踩过的坑够不够多**。你记下的每一条算子限制、每一组 verified 编译参数，都是核心竞争力。

算法创新在论文里，部署创新常常体现在：**同精度下延迟再砍 15%，或同延迟下功耗再降一截**——客户和面试官都认这种交付。面试时若能讲一个「从 38ms 到 19ms、mAP 几乎不动」的具体故事，比背「我会用 ATC」有力得多。

### 日常工具箱（不涉及厂商 CLI 细节，只列方向）

| 用途 | 常见工具 / 动作 |
|------|-----------------|
| 看图结构 | Netron、onnxsim 简化 |
| PC Golden | ONNX Runtime、PyTorch 对照 |
| 转模型 | 各芯片 converter（ATC、trtexec 等） |
| 性能 | msprof、nsys、厂商 profiler |
| 上板 | ADB、ssh、厂商 runtime demo |
| 张量对比 | numpy、自写 cos/MSE、逐层 dump |
| 任务指标 | 训练仓库里的 eval 脚本，勿另写一套 |
| 归档 | git tag、网盘版本号、知识库 wiki |

---

## 面试追问

### 1

**问：** 用几分钟介绍边缘部署工程师是干什么的？

**答：** 训练交 FP32 大图，客户要特定芯片上 INT8 实时跑。我负责在硬约束下把四件事拉齐：能不能编过、精度够不够、延迟够不够、功耗内存过不过线。日常是同一份 input.bin 对齐 PC 和设备、读编译和 profiler 日志、改图、调量化、压性能，并把踩过的坑写进知识库。本质是训练模型到真实芯片之间的搭桥和验收，交付的是可复现方案包而不只是一个模型文件。

### 2

**问：** 部署工程师和算法工程师工作边界在哪？

**答：** 算法定结构和 loss、追云端 mAP；部署盯算子能不能在目标芯片上编过、INT8 掉多少点、实机 fps 和功耗。改检测头、加新算子往往要一起评估，但 converter 日志、双端 dump、Tiling 参数一般是部署扛。面试时说清「同模型、不同 KPI」，比背岗位 JD 管用。

### 3

**问：** 精度对齐时为什么强调同一份 input.bin？

**答：** 双端对比要控制变量，唯一该不同的是推理设备。预处理各写一套，resize 差 0.1 像素在 INT8 边界上会被放大，你会误以为是量化或 converter 问题，白调一周校准集。input.bin 是预处理后的原始字节流，设备只读 bin 推理，输入才能字节级一致。

### 4

**问：** 余弦相似度 99% 能说明可以上线吗？

**答：** 不能单独作为门禁。余弦是层对齐筛查门槛，对整体缩放不敏感，backbone 余弦很高而 head 或后处理错了，框照样飞。我会同时看 head 分支余弦、MSE、任务 mAP 和坏例可视化。张量对齐过关只是中间态，业务指标过线才能谈上线。

### 5

**问：** 性能优化一般从哪入手？能先改模型结构吗？

**答：** 先 profiler，看 MAC 利用率、DDR 带宽和算子耗时排行，确认瓶颈是算力没吃满还是访存。优先编译期优化：融合、Tiling、AutoTune，很多项目不改结构就能砍掉可观延迟。改结构是手段不是默认第一步，改完必须重新编译、双端对齐、再 profile——新结构可能更慢或更吃内存。

### 6

**问：** 编译 0 error 为什么还可能不能上线？

**答：** error 只表示图能转完，Warning 里常有 CPU fallback、近似算子、融合失败。这些会让 fps 崩或精度悄悄掉。我习惯 0 error 之后仍搜 fallback 和 approx，并跑 profiler 看有没有单层 CPU 耗时异常。能上线要看四道关和交付包是否齐全，不是只看编译退出码。

### 7

**问：** 新人怎么较快上手边缘部署？

**答：** 跟完一条完整链路：ORT 验收 → 清 unsupported → 同 bin 双端对比 → profiler 读瓶颈 → 归档一条知识库。别一上来只调校准集。找一份同芯片的合格交付包对照缺什么。自己踩的坑当天记进 wiki，格式写清芯片版本、改法、前后 mAP 和延迟——三个月后会明显比只刷文档快。

---

## 附录 A：边缘部署日常 checklist（可打印）

```
[ ] 已对照芯片算子白名单扫 ONNX，列出 unsupported / 超限参数
[ ] 编译 0 error；log 已搜 fallback / approx / unsupport / fusion failed
[ ] unsupported 已清零或已评估 CPU 路径；无单层 CPU 拖死整网
[ ] ORT 验收 mAP 与训练脚本一致（导出没搞错）
[ ] 双端对比使用同一份 input.bin；dtype / shape / layout 已核对
[ ] 关键层余弦 + MSE 达内部门槛；head 分支单独看过
[ ] 任务指标（mAP 等）在业务线内；坏例已可视化
[ ] 后处理与训练验证脚本一致（anchor、letterbox、NMS、类别序）
[ ] 校准集覆盖真实场景；skip / 混合精度策略有记录
[ ] profiler 已跑：MAC 利用率、DDR 占比、算子耗时 Top N
[ ] 瓶颈层已尝试融合 / Tiling / AutoTune，改动前后有对比数据
[ ] 未仅凭 FLOPs 判断快慢；实机 profile 为准
[ ] 功耗、峰值内存、温升在规格内
[ ] 长稳压测（数小时～数天）无泄漏、无延迟漂移、P99 可接受
[ ] converter / 驱动版本已锁定并写入交付说明
[ ] 模型、编译参数、校准集版本、报告已归档，可半年后复现
[ ] 今日结论已写入算子知识库（芯片型号 + 改法 + 指标）
```

---

## 附录 B：最小代码示例

下面两个脚本可在本机理解 **双端对比** 和 **逐层余弦筛查** 的日常动作。不依赖 NPU SDK；实机把 `input.bin` push 到设备，拉回 `output.bin` 再跑对比即可。

### B.1 双端 input.bin 与输出对比

```python
"""
双端精度对比最小流程：预处理 → input.bin → 读回核对 → 对比输出。
"""

import numpy as np


def preprocess_image_mock(h: int = 640, w: int = 640) -> np.ndarray:
    rng = np.random.default_rng(42)
    img = rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
    x = img.astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    x = (x - mean) / std
    x = x.transpose(2, 0, 1)
    return x[np.newaxis, ...]


def save_bin(tensor: np.ndarray, path: str) -> None:
    tensor.astype(np.float32).tofile(path)


def load_bin(path: str, shape: tuple) -> np.ndarray:
    return np.fromfile(path, dtype=np.float32).reshape(shape)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_flat, b_flat = a.reshape(-1), b.reshape(-1)
    dot = np.dot(a_flat, b_flat)
    norm = np.linalg.norm(a_flat) * np.linalg.norm(b_flat)
    return float(dot / (norm + 1e-12))


def mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean((a - b) ** 2))


def main():
    shape = (1, 3, 640, 640)
    bin_path = "input.bin"

    x_pc = preprocess_image_mock()
    save_bin(x_pc, bin_path)
    x_device = load_bin(bin_path, shape)

    assert np.allclose(x_pc, x_device), "input 双端必须字节级一致"

    # 实机：out_gt 用 ORT，out_npu 用设备拉回的二进制
    out_gt = x_pc * 0.99 + 0.001
    out_npu = load_bin(bin_path, shape) * 0.99 + 0.001  # 演示用

    print(f"输出余弦: {cosine_similarity(out_gt, out_npu):.6f}")
    print(f"输出 MSE:  {mse(out_gt, out_npu):.8f}")


if __name__ == "__main__":
    main()
```

### B.2 逐层 dump 余弦筛查（定位「哪一层开始坏」）

```python
"""
假设已有多层 dump：layer_03_gt.bin / layer_03_npu.bin …
按层号扫余弦，找第一个明显低于门槛的层。
"""

import glob
import re
import numpy as np


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    af, bf = a.reshape(-1), b.reshape(-1)
    return float(np.dot(af, bf) / (np.linalg.norm(af) * np.linalg.norm(bf) + 1e-12))


def main():
    threshold = 0.99
    gt_files = sorted(glob.glob("layer_*_gt.bin"))
    first_bad = None

    for gt_path in gt_files:
        m = re.search(r"layer_(\d+)_gt", gt_path)
        if not m:
            continue
        idx = m.group(1)
        npu_path = f"layer_{idx}_npu.bin"
        a = np.fromfile(gt_path, dtype=np.float32)
        b = np.fromfile(npu_path, dtype=np.float32)
        cos = cosine(a, b)
        flag = "OK" if cos >= threshold else "LOW"
        print(f"layer {idx:>2}: cos={cos:.6f}  [{flag}]")
        if cos < threshold and first_bad is None:
            first_bad = idx

    if first_bad:
        print(f"建议从 layer {first_bad} 往前后查：量化 / 近似算子 / 融合")
    else:
        print("张量对齐过关，若 mAP 仍差请查后处理")


if __name__ == "__main__":
    main()
```

---

## 术语速查

| 术语 | 全称 / 含义 | 一句话直觉 |
|------|------------|-----------|
| PTQ | Post-Training Quantization | 训完再量化，靠校准集定 scale |
| QAT | Quantization-Aware Training | 训练里插 fake quant，周期长 |
| INT8 | 8 位整数推理 | 省算力省带宽；是否更快要看芯片与瓶颈 |
| scale / zero_point | 量化缩放与零点 | 把浮点映射到 int8 格点 |
| ONNX | Open Neural Network Exchange | 中间图；常先 ORT 验收再进 converter |
| ORT | ONNX Runtime | PC 侧 Golden 常用引擎 |
| Converter | 模型转换工具 | 编译优化；不会自动改网络结构 |
| Fallback | 算子回退 | 不支持的算子跑 CPU，易拖死整网 |
| input.bin | 预处理输入字节流 | 双端对比必须同一份 |
| Golden | 基准输出 | PC 侧参考 output，不是训练标签 |
| Profiler | 性能分析工具 | 看每层耗时、利用率、带宽 |
| MAC | Multiply-Accumulate | 乘加；利用率 = 实际算力 / 峰值 |
| Fusion | 算子融合 | Conv+BN+ReLU 合成一个 kernel |
| Tiling | 分块 | 编译期切矩阵，对齐缓存与硬件粒度 |
| AutoTune | 自动搜参 | 搜 Tiling 等，常隔夜跑 |
| ADB | Android Debug Bridge | push/pull 模型与张量 |
| memory-bound | 访存瓶颈 | 时间耗在搬数据，不是算力 |
| P99 延迟 | 99 分位延迟 | 比平均 fps 更严的实时指标 |
