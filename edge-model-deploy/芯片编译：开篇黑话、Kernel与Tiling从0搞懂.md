# 芯片编译：开篇黑话、Kernel 与 Tiling 从 0 搞懂

> **导读**：ATC 编出 `.om` 后上板又慢又掉点，log 里全是看不懂的英文——这篇把翻车故事里的词讲清，再补上两个新人必问：**卷积 kernel 大小是什么**、**Tiling 怎么和加载推理配合、写不写进模型文件**。  
> **阅读时间**：约 28 分钟  
> **适合谁**：会导出 ONNX、第一次跑 ATC，看 msprof / 编译 log 需要查词典的同学。

---

## 编过了还慢：先把故事读白

某次检测项目，新人把 `yolov5s.onnx` 交给 **ATC**（昇腾编译器），十分钟后拿到 `yolov5s.om`，以为部署完成了。上板 **msprof**（性能分析）一看：单帧 **45ms**，**MAC 利用率**不到 25%；和 PC 上 **ORT** 比 **mAP**，掉了 8 个点。团队先怀疑 **校准集 calib**，换了三版没变化。

翻 **编译 log** 才发现：`Resize` 走了近似 nearest；`GridSample` **CPU fallback**；中间插了四个 **Transpose**，**Conv+BN+ReLU 融合链**全断了。更隐蔽的还有：某层 **Conv kernel=11** 被拆成两个小卷积；大 feature map 的 **Tiling**（分块）切得保守，DDR 搬数多、MAC 空等。

用大白话：**人以为「格式转好了 = 部署好了」，其实编译时已选了一条又慢又容易偏的路，而且写进了 om，推理程序改不了。**

下面分三块讲：① 故事里每个词什么意思；② 编译第一步常查的 **kernel 大小**；③ 编译第三步 **Tiling** 怎么和加载、推理配合。三块都围绕同一件事——**编译期在 om 里写了什么**。

---

## 这三块知识在部署链里哪一段

```
  .pt → ONNX          ORT 验收：算得对不对
           │
           ▼  ATC 编译（本篇）
  ┌────────────────────────────────────────────┐
  │ ① 算子映射     ← kernel 大小、白名单、fallback │
  │ ② 融合                                           │
  │ ③ Tiling       ← 大张量怎么塞进片上缓存         │
  │ ④ Layout / ⑤ 量化 / ⑥ 打包 om                  │
  └────────────────────────────────────────────┘
           │
           ▼  加载 om + infer + msprof
  快不快、准不准
```

**ONNX 里没有 kernel 限制检查、也没有 Tiling**——只有数学上的 Conv 和 tensor shape。**om 里才有**「这层 Conv 是否被拆分」「这层按几块算、怎么搬数」。

---

## 第一部分：开篇黑话，逐个拆开

不必一次背完。每个词三块：**是什么 → 打个比方 → 在这句话里意味着什么**。

### 文件与工具

**yolov5s.onnx** — YOLOv5s 检测模型的通用格式。Netron 里一层层 Conv、Relu，像 **建筑设计图**，不绑定任何芯片。

**ATC（Ascend Tensor Compiler）** — 昇腾 **离线编译器**。吃 ONNX，做算子检查、融合、Tiling、Layout，吐 **om**。像 **施工总包**：谁干、怎么分段、材料怎么码，都在这定。

**yolov5s.om** — 编译产物。芯片指令、权重排布、内存地址、**Tiling 方案** 都在里面。像 **竣工手册 + 预制件清单**，专给这块昇腾用。拿到 om **≠ 部署完成**，还要上板、msprof、比精度、存 log。

### 性能相关

**msprof** — 板子上看每层耗时、MAC 吃没吃满、DDR 搬了多少、有没有层跑 CPU。像流水线 **监控**，看哪段在等料。

**单帧 45ms** — 一张图推理 45 毫秒，约每秒 22 帧。产品若要 50 帧就不达标。

**MAC 利用率** — NPU 里干卷积/矩阵乘的 **算力核心** 实际干活占比。25% 像十个灶台只开两三个——在等 **DDR** 搬数据、在 **CPU fallback**、或 **碎 kernel 太多**。和 45ms 对得上：**不是芯片坏了，是编译出的执行方式让算力空转**。

### 精度相关

**ORT（ONNX Runtime）** — PC 上跑 ONNX 的引擎，常当 **精度基准**。板子 om 的输出应和 ORT 接近。

**mAP** — 检测 **精度分数**。掉 8 个点通常是严重问题，不是误差范围内抖一下。

**calib（校准集）** — INT8 量化用的一批样图，用来定 **scale**。**换 calib 只动量化标定**；若根因是 fallback、近似 Resize、融合失败，换 calib 没用——本篇翻车就是排查方向错了。

### 编译 log 里的「元凶」

**Resize 近似 nearest** — 改特征图大小的算子；「近似」= 芯片实现和 ONNX 标准略有差别，像素差几个灰度，后面层会放大。INT8 下常是掉点嫌疑。

**GridSample + CPU fallback** — 按坐标采样；NPU 不支持就 **改 CPU 算**，再拷回 NPU。一层就能拖死延迟，还可能和 ORT 不一致。

**Transpose** — 张量 **维度重排**（如 NCHW→NHWC）。要读写一遍外存，挡在 Conv 和 ReLU 中间就 **断融合**。

**Conv+BN+ReLU 融合链** — 卷积、批归一化、激活 ideally **一锅出**，中间不写外存。Transpose 一插，变成炒完盛盘再换锅——慢且费 DDR。

### 编译 vs 推理 runtime（必分清）

| | 编译（ATC → om） | 推理（ACL 加载 om） |
|--|------------------|---------------------|
| 何时 | 开发机，部署前 | 板子，每次推理 |
| 干什么 | 映射、融合、**Tiling**、Layout、写进 om | 加载 om、喂输入、取输出 |
| 能改什么 | 改 ONNX、改参数、**重编** | batch、绑核等，**很有限** |

「不是 runtime 能修的」= 近似、fallback、融合断、**Tiling 方案** 都已写进 om；要修只能 **改图或重编**。

---

## 第二部分：kernel 大小——算子映射在查什么

log 里若出现 `Conv kernel size exceeds limit, split into multiple convolutions`，就是在说 **卷积核尺寸** 这颗芯片接不住。这是编译 **第一步「算子映射」** 里的典型检查。

### kernel 大小指的是什么

在 **Conv（卷积）** 里，**kernel** 是滑动的小窗口；**kernel 大小** 通常指 **高 × 宽**：

- **3×3**：窗口 3 行 3 列，看 9 个位置  
- **7×7**：看 49 个位置  
- **11×11**：看 121 个位置  

PyTorch / ONNX 里还有 **stride**（步长）、**padding**（边缘补零）、**channels**（通道数）。文档里「kernel ≤ 7」一般指 **卷积核单边最长不超过 7**（3×3、5×5、7×7 常见 OK；11×11 可能超限），**以你 CANN 版本文档为准**。

### 和「通道数」别混

| 概念 | 指什么 | 例子 |
|------|--------|------|
| **kernel 大小** | 窗口 **空间** 多大 | 3×3、11×11 |
| **通道数 channels** | 特征图 **有多厚** | 64 通道、256 通道 |

3×3 卷积、输出 256 通道 → 窗口仍是 3×3，不是 256×256。256 是有 **256 个不同的 3×3 卷积核** 在并行扫图。

### 打个比方

特征图是大地图，kernel 是 **放大镜口径**。3×3 看局部，11×11 看更大一片。口径越大，硬件实现越复杂，NPU 常对 **最大 kernel** 设上限。

### 编译器为什么要查

算子映射不只问「是不是 Conv」，还问 **参数芯片能不能直接跑**：

- **完全匹配**：3×3 Conv → 映射到 Cube 硬件  
- **参数超限**：11×11 → 可能 **拆成多个小 Conv**，或 Warning；能跑，但多 launch、数值路径可能变  
- **不支持**：整类算子不在白名单 → CPU fallback 或编不过  

YOLO、ResNet 主干 **3×3 居多**，一般没事；自定义头、大感受野里 **9×9、11×11** 要留意 log。

### Netron 里怎么看

点 **Conv** 节点，找 `kernel_shape`：`[3, 3]` 是 3×3，`[11, 11]` 可能触发拆分。

### 和开篇故事怎么连

MAC 低、延迟高，有时不全是 GridSample fallback——**大 kernel 被拆** 也会多几次调度、碎 kernel 变多，msprof 里 DDR 和 launch 开销上去。grep log 时 **fallback 和 kernel split 都要看**。

---

## 第三部分：Tiling——大张量怎么塞进小缓存

NPU **片上 SRAM（缓存）** 往往几 MB，一层 feature map 可能几十 MB。**Tiling** 把输入、输出、权重 **切成小块**，算完一块再搬下一块——像大桌菜 **分盘端**，厨房装得下。

### Tiling 信息在不在模型文件里

| 文件 | 有没有 Tiling |
|------|----------------|
| **ONNX** | **没有**。只有数学图和 shape |
| **om / engine** | **有**。编译期算好，和指令、权重一起打包 |

所以：**换 input shape、换芯片、开关 AutoTune 后重编，Tiling 都会变**。它不是训练出来的，是 ATC 为「这颗芯片 + 这个 shape」算的 **施工方案**。

### 编译、加载、推理怎么配合

**① 编译（ATC）——定方案**

对每一层：tensor 多大、SRAM 多大 → 决定沿 **高/宽/通道** 怎么切、每块多大、块之间怎么衔接 → 规划 **DMA 搬数** 和 **MAC 计算** 是否流水线（算当前块时搬下一块）。

开 **AutoTune** 会试多组分块参数，选更快的一组，**写进 om**。

**② 加载（ACL 等）——把方案装进设备**

`aclmdlLoadFromFile("xxx.om")` 加载的不只是权重，还有指令、内存规划、**Tiling/调度元数据**。加载 **不会重新算 Tiling**，只是按 om 分配 buffer、准备执行上下文。

**③ 推理（infer）——按方案一块块跑**

喂一张 640×640 图，NPU 不会整层几十 MB 一次塞进 SRAM，而是按 om 里计划，例如：

```
某层 Conv 输出很大时：
  块1：H=0~127    ← MAC 在算
  块2：H=128~255  ← DMA 可能在搬块2需要的数
  …
  全块算完 → 下一层再按它的 Tiling 来
```

加载 = 把手册和预制菜搬进厨房；推理 = 按手册 **一盘盘做**。Tiling 是手册里 **每道工序怎么分段**，不是 infer 时临时决定的。

```
  ONNX（无 Tiling）
       │
       ▼  ATC：算分块 → 写进 om
  .om（含 Tiling 方案）
       │
       ▼  Load：权重 + 指令 + Tiling 元数据上板
       │
       ▼  Infer：DMA 搬块 k → MAC 算块 k → 下一块 …
```

### 和融合、Layout 别混

| 步骤 | 解决什么 | 写进 om 吗 |
|------|----------|-----------|
| 融合 | 多层合并，少写外存 | 是 |
| **Tiling** | **单层太大**，拆块 fit 缓存 | **是** |
| Layout | 数据在内存里怎么排 | 是 |

三者都在 **编译期** 定死；runtime **改不了 Tiling**，只能重编或换 om。

### 和开篇故事怎么连

MAC 25%、45ms 延迟，除了 fallback 和 Transpose，还可能是 **Tiling 保守或切得差** → DDR 顶满、MAC 空等。msprof 里 DDR 占比高时，别先换 calib，先看 log 里有没有 fusion 问题，再考虑 **重编 + AutoTune**。

**改 batch 或输入分辨率**：Tiling 与编译时 `--input_shape` 绑定；静态 om 换尺寸常要 **重新编译**。

---

## 四块拼在一起：慢和不准从哪查

| 你看到的现象 | 可能原因 | 第一眼看哪 |
|-------------|----------|-----------|
| 以为 onnx→om 就部署完 | 还有 msprof、mAP、log | 交付 checklist |
| 单帧慢、MAC 低 | fallback；融合断；**Tiling 差**；Transpose 多 | log + msprof |
| mAP 掉很多 | 近似 Resize；CPU 算子 | FP16 双端；log approximate |
| 换 calib 无效 | 主因不在量化 | log fallback / 近似 |
| log：kernel split | 大卷积被拆 | Netron 查 kernel_shape；评估是否改小 kernel |
| DDR 高、MAC 低 | Tiling / Layout | 重编、AutoTune；减 Transpose |

建议排查顺序：**grep log（fallback / approximate / split / fuse）→ shape/soc 是否对 → FP16 双端 → msprof MAC/DDR → 再 INT8 calib → AutoTune**。

---

## 常见坑（我都见过）

**坑 1：编过就交付，log 不看。**  
现象：能跑但慢或飘。改：grep 后按 Warning 改图 **重编**，log 归档。

**坑 2：把 kernel 和通道数搞混。**  
现象：Netron 看到 256 以为 kernel 256。改：只看 `kernel_shape`，那是窗口大小。

**坑 3：以为 Tiling 是推理时临时切图。**  
现象：换分辨率不 recompile，结果错或慢。改：Tiling 在 **om 里**；换 shape 要 **重编**（静态图）。

**坑 4：DDR 高只调 runtime。**  
现象：绑核、改 batch 没用。改：**重编 + AutoTune**，或改图减 tensor、减 Transpose。

**坑 5：换 calib 治 fallback。**  
现象：三版 calib 纹丝不动。改：calib 只管 INT8 scale；fallback / 近似 / 融合要 **改 ONNX 或编译选项**。

---

## 面试追问

### 1

**问：** 编译 log 里 `Conv kernel size exceeds limit` 是什么意思？

**答：** 这层卷积核太大，超过芯片 NPU 直接支持的上限（文档里常见 kernel 单边 ≤7，以 CANN 为准）。编译器可能拆成多个小 Conv 或打 Warning。能编过但可能更慢、数值路径也变。Netron 看 `kernel_shape`；大 kernel 要主动改结构或接受拆分。

### 2

**问：** Tiling 是什么？在 ONNX 里还是在 om 里？

**答：** 单层 tensor 太大、片上 SRAM 放不下，编译器把它切成小块依次算，叫 Tiling。ONNX 只有数学图，没有 Tiling；方案在 ATC 编译时算出，写进 om。推理时 NPU 按 om 里计划一块块 DMA+MAC，runtime 不会现场重算 Tiling。

### 3

**问：** 加载 om 和 Tiling 什么关系？

**答：** Load 把 om 里的权重、指令和 Tiling 调度元数据一起载入设备；infer 按这套方案执行。Load 不重新算 Tiling。换 shape、换芯片、关开 AutoTune 都要重编 om，Tiling 才会变。

### 4

**问：** MAC 利用率很低，可能和 kernel、Tiling 有关吗？

**答：** 有关。CPU fallback、融合被 Transpose 打断会让 MAC 空等；大 kernel 被拆会增加碎 kernel 和 DDR；Tiling 差会让搬数多、算力等数据。先 grep log 看 fallback/split/fuse，再 msprof 看 MAC 和 DDR，别先换 calib。

### 5

**问：** 开篇故事里换 calib 为什么没用？

**答：** mAP 掉点来自 Resize 近似、GridSample fallback、融合失败等 **编译路径** 问题，换 calib 只动 INT8 的 scale，治不了算子跑 CPU 或近似实现。要先翻编译 log；若根本没做 INT8，换 calib 更没意义。

---

## 附录：checklist（可打印）

```
[ ] 能用自己的话解释：onnx vs om、编译 vs runtime
[ ] 开篇黑话（msprof/MAC/ORT/mAP/fallback 等）看到 log 能对上号
[ ] Netron 会看 Conv 的 kernel_shape，区分 kernel 大小 vs 通道数
[ ] 知道 Tiling 在 om 里，不在 ONNX；换 shape 静态 om 要重编
[ ] 编译 log 已 tee 存档，已 grep：fallback、approximate、split、Cannot fuse
[ ] FP16 双端精度过关后再纠结 INT8 calib
[ ] msprof 看过 MAC、DDR、CPU 算子
[ ] 慢且 DDR 高时，排查顺序含 Tiling/AutoTune，不只调 runtime
```

---

## 术语速查

| 术语 | 一句话 |
|------|--------|
| ONNX | 通用计算图，「算什么」 |
| om | 昇腾离线模型，含指令、权重、Tiling 等 |
| ATC | 昇腾编译器 |
| kernel 大小 | Conv 卷积窗口高×宽，如 3×3、11×11 |
| 算子映射 | 每个 ONNX 节点能否上 NPU、参数是否合规 |
| CPU fallback | 不支持的算子改 CPU 算 |
| 融合 | 多层合并，中间不写外存 |
| Tiling | 大张量分块 fit 片上缓存；写在 om 里 |
| AutoTune | 编译期搜索 Tiling 等参数 |
| MAC | NPU 卷积/矩阵乘算力单元 |
| DDR | 外存；和片上 SRAM 相对 |
| msprof | 昇腾性能分析 |
| ORT | PC 跑 ONNX，精度基准 |
| mAP | 检测精度指标 |
| calib | INT8 量化样图集 |
| runtime | 加载 om 推理；不改 Tiling/融合 |
