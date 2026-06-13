# ATC 编过了还慢，转换工具到底改了啥？

> **导读**：把 ONNX 交给 ATC，吐出来 `.om`，很多人以为「部署完成了」。其实这一步叫 **编译**——芯片在这时候决定哪些层走 NPU、哪些层踢给 CPU、中间数据怎么摆放。编过只代表「能跑」，不代表「跑得快、跑得准」。  
> **阅读时间**：约 25 分钟  
> **适合谁**：会训模型、会导出 ONNX，但第一次碰 `atc` / 芯片 `.om`，看编译 log 一脸懵的同学。

---

## 读这篇之前，你只需要知道三件事

1. **ONNX** 是通用「计算说明书」，不绑定任何一块芯片；**.om** 是昇腾专用「施工方案」，换芯片要重编。  
2. **编译**（生成 om）和 **推理**（加载 om 跑图）是两回事——log 里的 fallback、融合失败，推理程序改不了，只能 **改 ONNX 或编译参数后重编**。  
3. **编过 ≠ 部署完成**。后面还有上板、测延迟、测精度、读 log；log 里的 Warning 必须存档。

下面按「先懂故事 → 再懂名词 → 再懂六步流水线 → 再动手」的顺序写。若开篇黑话太多，可直接跳到下一节「故事里那些词分别指什么」。

---

## 文件夹里两种文件，别当成一回事

某次检测项目，新人把训练好的 YOLOv5s 导出成 `yolov5s.onnx`，交给昇腾的编译工具 **ATC** 跑了一遍。十分钟后生成 `yolov5s.om`，他以为部署完成了。

上板一测：处理一张图要 **45 毫秒**（产品要求可能只要 20ms）；打开性能分析工具 **msprof**，发现 NPU 的算力单元 **MAC** 大部分时间在空转，利用率不到四分之一。再和 PC 上用 **ORT**（ONNX 推理引擎）跑的结果比检测精度 **mAP**，掉了 8 个点——团队先怀疑 **INT8 校准集** 没选好，换了三版 **calib** 毫无变化。

最后翻 **编译 log** 才发现：`Resize` 用了和标准不完全一样的近似算法；`GridSample` 被标记成 **CPU fallback**（这层不在 NPU 上算，改去 CPU）；中间还自动插了四个 **Transpose**（张量维度重排），把本来可以合并执行的 **Conv+BN+ReLU** 链全打断了。

用大白话总结：**模型能跑，但编译时已经选了一条「又慢又容易算不准」的路，而且这条路写进了 om，上线后改不了。**

我后来跟新人说：ONNX 是「算什么」的图纸；om 是「在这块昇腾上怎么算、哪几层在 CPU、数据怎么码放」的施工图。ATC 是画施工图的总包——你不看施工记录（log），就只能碰运气。

---

## 故事里那些词，分别指什么

下面把开篇出现的词一次性讲清。不必背，用到时回来查即可。

**yolov5s.onnx** — 检测模型 YOLOv5s 的通用格式文件。Netron 打开能看到一层层 Conv、Relu 等，像 **建筑设计图**，还没指定哪家施工队。

**ATC（Ascend Tensor Compiler）** — 昇腾的 **离线编译器**。吃 ONNX，吐 om；里面做检查、优化、分块、改数据排布。

**yolov5s.om** — 编译产物，板子上加载它直接推理， **不再读 ONNX**。像 **竣工手册 + 预制件清单**，专给这块芯片用。

**msprof** — 昇腾上的 **性能分析工具**，看每层耗时、算力有没有吃满、有没有层跑在 CPU。像给流水线装监控，看哪一段在等料。

**单帧 45ms** — 一张图推理耗时 45 毫秒，大约每秒 22 帧。客户要 50 帧，就不达标。

**MAC 利用率** — NPU 里干卷积/矩阵乘的 **算力核心** 实际干活的时间占比。25% 意味着十个灶台大多在等菜，没在炒菜——常见原因是 CPU fallback、融合断了、数据搬运太多。

**ORT（ONNX Runtime）** — PC 上跑 ONNX 的引擎，团队里常当 **精度基准**：板子输出应该和 ORT 接近。

**mAP** — 检测任务的 **精度分数**。掉 8 个点通常是严重问题，不是误差范围内抖一下。

**校准集 calib** — 做 INT8 量化时，用一批样图统计每层数值范围。 **换 calib 只影响量化 scale**；若根因是编译路径错了，换 calib 没用——本篇翻车就是这种情况。

**Resize 近似 nearest** — 改特征图大小时的算子；「近似」表示芯片实现和 ONNX 标准略有差别，像素可能差几个灰度，后面层会放大。

**GridSample + CPU fallback** — 按坐标采样的算子；NPU 不支持时 **改到 CPU 算**，再拷回 NPU，这一层会特别拖慢。

**Transpose** — 改变数据在内存里的 **排列顺序**（比如 NCHW 变 NHWC），要读写一遍外存，还 **挡在 Conv 和 ReLU 中间**，导致没法合并计算。

**Conv+BN+ReLU 融合链** — 卷积、批归一化、激活本来可以 **一锅出**，中间结果不写外存；链被打断就变成炒完盛盘、再拿另一口锅，慢且费内存。

**runtime（推理运行时）** — 板子上加载 om 跑推理的程序（昇腾常用 ACL）。它 **不会** 把编译期拆开的算子再合并回去。

**编译 vs 推理**：编译在开发机做，决定 om 长什么样；推理在板子做，按 om 执行。 **问题出在编译，runtime 修不了。**

---

## 模型转换在部署链路里干什么

```
  PyTorch 模型 (.pt)
        │
        ▼  导出
  ONNX (.onnx)          ← 通用图纸，PC 上用 ORT 验收「算得对不对」
        │
        ▼  芯片编译（ATC 等）← 本篇
  芯片模型 (.om)         ← 专用施工图，决定「怎么算、快不快」
        │
        ▼  上板推理 + msprof + 和 ORT 比精度
  能不能发货
```

整条链里，**ORT 过了** 只说明数学上对；**编译** 才决定这颗 NPU 实际走哪条路。后面 msprof 里 MAC 低、mAP 掉，往往要 **回头查编译 log**，不是先瞎调参。

---

## 零基础：从训练到上板，中间多了哪一步

如果你只做过训练，可以这样理解整条路：

训练得到 `.pt`，里面是 PyTorch 的算子和权重。部署第一步 **导出 ONNX**——换成大家都能读的「标准算子名 + 权重」，像把内部文档翻译成行业通用格式。

第二步 **ORT 在 PC 上跑一遍**——确认导出没搞错输入输出名、shape、数值。

第三步才是 **ATC 编译**——这是本篇重点。编译器会：

- 查每个算子这块芯片 **支不支持**（算子映射）  
- 能合并的层 **合并**（融合），少写外存  
- 太大的中间结果 **切块**（Tiling），塞进片上小缓存  
- 数据排布 **改成芯片喜欢的顺序**（Layout）  
- 若做 INT8，把 **量化参数写进图**  
- 最后打包成 **om**

第四步 **板子加载 om 推理**，用 msprof 看快不快，用 ORT 对比看准不准。

所以：**ONNX 是中间合同，om 才是给这块芯片的交付物。** 只完成第三步里的「命令跑通」，不等于第四步验收过了。

---

## 转换工具到底是什么

**它是 AI 专用编译器**，不是「格式转换器」。

类比：GCC 把 C 代码编译成 x86 机器码；ATC 把 ONNX 计算图编译成昇腾机器码。输入是 **图 + 编译参数**（输入尺寸、芯片型号、FP16 还是 INT8 等）；输出是 **om 包**——指令、重排后的权重、内存地址、元数据。

能在编译期做的优化 **全在这里做完**：哪些层合并、怎么分块、数据怎么摆、INT8 的 scale 写在哪。推理程序主要负责 **加载 om、喂输入、取输出**——别指望上线后再「自动变快」。

---

## 为什么不是「改个后缀就完事」

| 常见误解 | 实际情况 |
|---------|---------|
| onnx 改名叫 om | 要重新生成指令、重排权重、规划内存 |
| 同系列芯片 om 通用 | 绑定具体型号，310 和 310P 也要分别编 |
| Warning 可以忽略 | 多是 fallback、近似、融合失败——后面扯皮的证据 |
| 编译很快 | 大图 + 参数搜索，几小时不少见 |
| 编译器全自动 | 只认标准图结构；复杂模型常要 **人工改 ONNX** |

表后一句：我见得最多的坑，是 **编译当黑盒、log 不存档**。半年后客户问「这版为什么慢」，没有 log 只能重编瞎猜。

---

## 编译时内部六步：用一条流水线来记

不必一次背六个名词。先记 **三个问题**，编译器按顺序回答：

1. **能不能在这颗 NPU 上跑？**（算子映射）  
2. **能不能跑快？**（融合 + Tiling + Layout）  
3. **INT8 的话，量化参数怎么嵌进去？**（量化，可选）

下面按 ATC 实际顺序展开。每步都写：**在干什么 → 打个比方 → 出问题时去哪查**。

---

### 第一步：算子映射——这层 NPU 接不接得住？

编译器 **从输入到输出，逐个算子过海关**。

ONNX 里每个方框（Conv、Softmax、GridSample…）都要查昇腾 **算子库**——可以理解成 **「NPU 会干的活」白名单**。不只查名字，还查 **参数**：

- 卷积核 **kernel** 是不是太大？（昇腾常见限制如 kernel ≤ 7，以你 CANN 文档为准）  
- **padding** 模式支不支持？  
- **Softmax** 是不是在芯片支持的那一维上算？（很多 NPU 只优化「最后一维」）

三种结果：

**① 完全匹配** — 例如 3×3 Conv、stride=1，直接映射到 NPU 的 Cube 单元。像护照、签证、照片规格全对，走快速通道。

**② 参数超限** — 类型是 Conv，但 kernel=11 太大。可能 **拆成两个小 Conv**，或 log 里 Warning。能跑，但多几次调度，数值路径也可能变。像货超高，拆成两趟运。

**③ 不支持** — 白名单里没有 GridSample 这类。 **CPU fallback**：这层改到 CPU 算，结果拷回 NPU；或干脆编译失败。像工序只能外包给杂工，主线等着，整体慢。

新人常 **跳过预检直接 full compile**，等设备编半小时才发现 log 里一堆 fallback。工程上我会先跑 **算子支持性检查**（昇腾 `atc --mode=1`），unsupported 列表当改图 todo。

---

### 第二步：图优化与融合——能不能少写几遍外存？

第一步解决「能不能跑」；这一步解决 **「能不能跑快」**。

神经网络一层层算，中间结果默认要 **写到 DDR（外存，板子上的主内存）**，下一层再读回来——慢。融合就是把 **数学上等价的多层合成一次执行**，比如 Conv → BN → ReLU，中间张量 **留在片上小缓存**，不写外存。

还有 **常量折叠**：BN 的均值、方差在编译期并进 Conv 权重，图里 BN 节点直接消失。**死代码消除**：没人用的分支删掉。

限制：**编译器只认固定模式**。中间插了 Transpose、非常规激活，融合链就断——像「炒→调味→出锅」中间非要 **换三个盘子**，就没法一锅完成。

改图引导融合是部署工程师的日常：导出前 BN folding、调整算子顺序，都是为了让编译器 **认得出** 可融合的模式。

---

### 第三步：Tiling——大张量怎么塞进小缓存？

NPU 片上 **SRAM（缓存）** 往往只有几 MB，一层 feature map 可能几十 MB。Tiling 把输入、输出、权重 **切成小块**，算完一块再搬下一块——像大桌菜 **分盘端**，厨房（缓存）装得下。

分块还涉及 **和硬件对齐**（如通道数凑 16 的倍数），以及 **搬数据和计算并行**，减少「算力等着数据」的时间。

默认分块策略偏保守。开 **AutoTune** 会让编译器 **试多组分块参数**，编译慢，但 msprof 里 MAC 和 DDR 比例常会好看不少（提升幅度因模型而异，别当固定数字背）。

若 MAC 利用率长期很低，除了 fallback，我会查 **Tiling 和下一步 Layout**，而不是先换 calib。

---

### 第四步：Layout——数据在内存里怎么排？

同一份数， **在内存里怎么排列** 会影响读速。PyTorch 常用 **NCHW**（批次、通道、高、宽）；昇腾 Cube 单元习惯 **16 通道一组** 读，常用 **NC1HWC0**（把通道按 16 一组拆开）。

Layout 不对，硬件读内存 **不连续**，算力闲着。编译器可能在图里 **自动插 Transpose** 做转换——若插在 Conv 和 Relu 之间， **第二步的融合直接废掉**。

所以 Layout 和融合是连着的：Transpose 一多，既慢又碎。

---

### 第五步：量化嵌入（仅 INT8 时）

若只做 FP16，这步可以跳过。

开 INT8 时，编译器读 **校准阶段产出的 scale**，写进每个算子；权重从 FP32/FP16 转成 INT8，并按硬件要求 **重排内存**；必要时插入量化/反量化节点，或 **fuse 进主算子**。

注意：**只改 `precision_mode`、不做 PTQ 校准**，scale 可能是错的——编过也不代表能用的 INT8。这和 AMCT 等量化工具是 **配套流程**，不是 ATC 单独完成的。

---

### 第六步：打包 om——生成最终交付物

把优化后的图 ** lowering（降级）成芯片指令**：每个算子对应指令序列；每个张量分配 **固定内存地址**；权重、指令、校验信息打成 **一个 om 文件**。

推理时 **load om → infer → 结束**，不再解析 ONNX。om 里是什么路径，runtime 就怎么走——所以开篇那些 fallback、Transpose， **早就写死了**。

---

## 六步对照：出问题先查哪

| 你的现象 | 优先怀疑哪一步 | 去哪看 |
|---------|---------------|--------|
| 编译失败 / 某 op unsupported | ① 算子映射 | log：not supported、fallback |
| 能跑但特别慢、MAC 很低 | ① fallback；② 融合断；③ Tiling/Layout | log + msprof |
| 比 ORT 慢但 MAC 还行 | ③ Tiling；④ Transpose 多 | msprof DDR 占比；图 dump |
| 比 ORT 精度差 | ① 近似实现；⑤ INT8 scale | log approximate；双端逐层比 |
| INT8 全错 | ⑤ 量化 | 是否走完整 PTQ |

---

## 编译前你要准备什么

| 你要告诉 ATC 的 | 为什么重要 | 新人常踩的坑 |
|----------------|-----------|-------------|
| 模型路径 | 吃哪张 ONNX | opset 和 CANN 版本不匹配 |
| 输入名 + shape | 编译期定死尺寸 | 和 Netron 里不一致；动态 shape 性能差 |
| soc_version | 绑定哪块芯片 | 310 的 om 给 310P 用 |
| 精度 FP16/INT8 | 走哪条路径 | INT8 没 calib |
| optimize 等级 | 图优化强度 | 默认太低或某融合有 bug 要关 |
| 是否 AutoTune | Tiling 搜索 | 编译时间暴涨 |

昇腾最小命令示例（按项目改路径和芯片型号）：

```bash
atc --model=yolov5s.onnx \
    --framework=5 \
    --output=yolov5s \
    --input_format=NCHW \
    --input_shape="images:1,3,640,640" \
    --soc_version=Ascend310P3 \
    --precision_mode=allow_fp32_to_fp16 \
    --optimize=2 \
    --log=info \
    2>&1 | tee yolov5s_310p_fp16_20250612.log
```

`tee` 把 log 存盘—— **和 om 放同一目录**。Netron 里确认输入节点叫 `images`、shape 是 `1,3,640,640`，再写进 `--input_shape`，别手滑。

---

## 编译 log 里的 Warning：为什么必须留档

Warning 不是「无关紧要」。精度掉了、mAP 变了、变慢了，我 **第一个翻当时的 log**。

**CPU fallback** — `Operator XXX is not supported, fallback to CPU`。这层在 CPU 跑，延迟可能崩。必须改图或自研 NPU 算子，不能「能跑就行」。

**近似实现** — `Resize uses approximate nearest` 等。和 ONNX 行为有数值差，INT8 下更容易放大。精度不达标时 **先查这类层**。

**参数拆分** — `Conv kernel size exceeds limit, split...`。大 kernel 被拆成多个小 Conv，性能和数值都可能变。

**融合失败** — `Cannot fuse Conv+BN+ReLU, interrupted by Transpose`。中间结果被迫写外存。要把 Transpose 挪走或导出前对齐 Layout。

**对齐填充** — `Channel padded from 250 to 256`。通道凑 16 的倍数，一般 **正常现象**，写进 release note 即可。

留档习惯：log 命名 `模型_芯片_精度_日期.log`；高危 Warning 摘录进版本说明；和 om、CANN 版本、校准集 hash 放一起。

---

## 最常见坑（附排查顺序）

**坑 1：编过就交付，log 不看。**  
现象：能 infer，慢或精度飘。原因：fallback、近似、融合失败全在 log。怎么查：`grep fallback approximate "Cannot fuse"`。怎么改：按 Warning 改图重编，log 归档。

**坑 2：动态 shape 图省事。**  
现象：编过但延迟长。原因：编译期没法做满内存规划。怎么改：固定机位用静态 shape；要多分辨率就 **多份 om** 或查芯片动态支持度。

**坑 3：同系列芯片共用 om。**  
现象：加载失败或结果偶发错。怎么改：**每块目标硬件单独编**，soc_version 和板子一致。

**坑 4：INT8 只改 precision，不做 PTQ。**  
现象：前几层输出就错。怎么改：calib → INT8 ONNX 或量化节点 → 再 ATC。

**坑 5：Layout 全交给编译器，Transpose 一堆。**  
现象：msprof 碎 kernel 多、DDR 高。怎么查：图 dump，看 Conv 和 Relu 之间有没有 Transpose。怎么改：导出前对齐 layout，或挪 Transpose 到 block 边界。

**坑 6：模型改了不重编、不对比 log。**  
现象：某次 silent 变慢。怎么改：CI 里 **编 om + 扫 log 高危词** 当门禁。

建议排查顺序：**log（fallback/近似/融合）→ shape/soc 是否对 → FP16 双端精度 → msprof → INT8 calib → AutoTune**。

---

## 和 GPU TensorRT 比：心态别带错

| | NPU（ATC） | GPU（TensorRT） |
|--|-----------|----------------|
| 优化主要在 | 编译期，一次定 om | 编译期 + 运行时都较灵活 |
| 算子支持 | 白名单，fallback 常见 | 相对宽，plugin 多 |
| 换硬件 | om 基本重来 | 同架构 engine 有时能复用 |

不是谁更好，是 **NPU 把赌注压在编译期**。GPU 工程师第一次上 NPU，最容易栽在「编过就行」——其实 **log 和 msprof 才是第二步**。

---

## 面试追问

### 1

**问：** 芯片模型转换工具一般在干什么？

**答：** 本质是 AI 编译器：ONNX 等通用图 → 芯片指令包 om。核心几步：算子映射（不支持的 fallback CPU）；融合少写外存；Tiling 塞缓存；Layout 转换；INT8 时嵌 scale；最后打包。编译期定的，runtime 改不了，log 必须留档。

### 2

**问：** 编译通过了，为什么还慢？

**答：** 编过只说明能跑，不说明全在 NPU MAC 上。常见是 log 里已有 CPU fallback、融合被 Transpose 打断、Tiling 保守或 DDR 打满。先 grep log，再 msprof 看 MAC 和 DDR，别先换 calib。AutoTune 和改图往往比 runtime 调参管用。

### 3

**问：** 转换时要给哪些关键输入？

**答：** 模型路径、静态 input shape、目标 soc、精度（INT8 要配校准产物）、优化级别、是否 AutoTune。昇腾例：`--input_shape="images:1,3,640,640"`、`--soc_version=Ascend310P3`、`--optimize=2`。shape 或 soc 错了，编过也可能错或慢。

### 4

**问：** 编译日志里哪些 Warning 必须记？

**答：** CPU fallback、近似实现（Resize/GELU 等）、融合失败（中间 Transpose）、参数超限拆分（大 kernel Conv）。和性能精度扯皮直接相关。完整 log tee 存档，高危项写进版本说明。

### 5

**问：** ONNX 和 om 能跨芯片用吗？

**答：** ONNX 一般可以当「数学合同」跨芯片复用；om 绑定具体 soc，同系列不同型号也要重编。换芯片通常 ONNX 微调后整条转换链重做。

---

## 附录 A：checklist（可打印）

```
[ ] PC 侧 ORT 已验收 ONNX 数学正确
[ ] 已做算子支持性预检（unsupported 当改图 todo）
[ ] Netron 核对 input 名、shape，NPU 优先静态 shape
[ ] soc_version 与实机板子一致
[ ] INT8：校准表 / INT8 ONNX 就绪，非只改 precision
[ ] optimize 等优化项已按项目配置
[ ] AutoTune：编译时间 vs 性能 tradeoff 已评估
[ ] 编译 log 已 tee，命名含模型/芯片/精度/日期
[ ] log 已 grep：fallback、approximate、Cannot fuse、not supported
[ ] 高危 Warning 已摘录进 release note
[ ] FP16 双端精度过关后再交 INT8 om
[ ] msprof 看过 MAC、DDR、CPU 算子
[ ] om 与 CANN 版本、校准集 hash 一并归档
```

---

## 附录 B：编译 log 高危项扫描脚本

```python
#!/usr/bin/env python3
"""扫描芯片模型编译 log 中的高危关键词。"""
import re
import sys
from pathlib import Path

PATTERNS = {
    "CPU Fallback": re.compile(r"fallback\s+to\s+CPU|not supported.*CPU", re.I),
    "近似实现": re.compile(r"approximate|using approximation", re.I),
    "融合失败": re.compile(r"cannot fuse|fusion failed|interrupted by", re.I),
    "参数拆分": re.compile(r"split into multiple|exceeds limit", re.I),
    "对齐填充": re.compile(r"padded from \d+ to \d+", re.I),
}


def scan(log_path: str) -> int:
    text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    hits = 0
    print(f"=== 扫描: {log_path} ===\n")
    for label, pat in PATTERNS.items():
        lines = [ln.strip() for ln in text.splitlines() if pat.search(ln)]
        if lines:
            hits += len(lines)
            print(f"[{label}] {len(lines)} 处")
            for ln in lines[:5]:
                print(f"  · {ln[:200]}")
            if len(lines) > 5:
                print(f"  … 另有 {len(lines) - 5} 处")
            print()
    if hits == 0:
        print("未发现预设高危关键词（仍建议人工过一遍完整 log）")
    else:
        print(f"合计命中 {hits} 行，请逐条评估是否改图/重编")
    return hits


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "compile.log"
    sys.exit(1 if scan(path) else 0)
```

用法：`python scan_compile_log.py your_compile.log`。CI 里 exit code 1 可阻断「有 fallback 仍交付」。

---

## 术语速查

| 术语 | 一句话 |
|------|--------|
| ONNX | 通用计算图，「算什么」 |
| om | 昇腾离线模型，「在这块芯片上怎么算」 |
| ATC | 昇腾编译器，ONNX → om |
| 编译 | 生成 om；决定算子路径、融合、分块 |
| runtime / ACL | 加载 om 推理；不改图结构 |
| 算子 | 图里一个节点，如 Conv、Relu |
| 白名单 | 芯片 NPU 实现了的算子列表 |
| CPU fallback | 不支持的算子改到 CPU 算 |
| 融合 | 多层合并，中间结果不写外存 |
| Tiling | 大张量切块，塞进片上缓存 |
| Layout | 数据在内存里的排列，如 NCHW |
| Transpose | 维度重排，常打断融合 |
| MAC | NPU 里干卷积/矩阵乘的算力单元 |
| DDR | 外存；和片上缓存相对 |
| msprof | 昇腾性能分析工具 |
| ORT | PC 上跑 ONNX，常当精度基准 |
| calib | INT8 量化用的样图集 |
| AutoTune | 编译期搜索 Tiling 等参数 |
| lowering | 计算图降到机器指令的过程 |

**开篇黑话、kernel 大小、Tiling 与加载推理** 的合并讲解见同目录 `芯片编译：开篇黑话、Kernel与Tiling从0搞懂.md`。
