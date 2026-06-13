# 双端精度对比，为什么必须同一份 input.bin？

> **导读**：PC 上 ORT 和 NPU 上 `.om` 比精度，差一个字节的输入，余弦相似度就失去意义——你会把预处理问题当成量化问题，白调一周校准集。  
> **阅读时间**：约 18 分钟  
> **适合谁**：能编过芯片模型、第一次做「PC Golden vs 设备实机」双端对比，或面试被问到「上板精度怎么验」的工程师。

---

## 排查现场：余弦 0.62，真不一定是量化不行

某次 YOLOv5s 上昇腾 310，PC 侧 ORT FP16 的 mAP 约 0.85，INT8 量化后设备上只有 0.62。新人连换三种量化策略、改了十版校准集，精度纹丝不动。

最后对了一下输入：PC 侧 `cv2.resize(..., INTER_LINEAR)`，设备侧推理 demo 里用的是 `PIL.Image.BILINEAR`。名字都叫双线性，像素差 0.1～0.5 很常见。浮点模型有时还能扛，INT8 在量化边界附近会把这点差异放大——整网输出余弦看着还行，检测 head 已经飘了，mAP 掉二十多个点不稀奇。

这类翻车我见得不少：**输出差异只能来自量化、converter、驱动实现**；输入若不一致，你算的余弦是在比两件不同的事，还会误判成「量化不行」去瞎调 calib。

---

## 精度验证在部署链路里干什么

```
  .pt → ONNX (FP32)
              │
              ▼  ORT 验收：数学正确
  ONNX ──────────────────────────────┐
              │                      │
              ▼  PTQ + 校准集        │  PC 侧 Golden
  INT8 ONNX（可选）                  │
              │                      │
              ▼  ATC / converter     │
  芯片模型 (.om)                     │
              │                      │
              ▼  ADB 上板推理  ◄─────┼── 同一份 input.bin 喂两端
  ┌──────────────────────────────────────────────────────────┐
  │ 双端精度验证（本篇）                                        │
  │ · PC：预处理一次 → input.bin + output_gt.bin              │
  │ · 设备：只读 bin 推理 → output_npu.bin                    │
  │ · 对比：余弦 / MSE / 逐层；再叠业务指标                      │
  └──────────────────────────────────────────────────────────┘
              │
              ▼  任务指标 + 坏例回归
  上线门禁
```

整条链里，双端对比卡在 **「芯片模型能跑」和「业务能发货」之间**。它不负责证明训练对不对——那是 ORT 阶段的事；它负责证明 **同输入下，NPU 输出和 PC Golden 差多少**，差在哪一层，该不该继续调量化。

---

## 零基础先搞懂：本篇会反复出现的名词

### input.bin 是什么

`input.bin` 是把预处理后的张量 **按内存布局原样落盘** 的二进制文件，没有头信息、没有 shape 元数据——读的时候你必须自己知道 `dtype`（常见 `float32`）和 `shape`（如 `1,3,640,640`）。

它的作用就一个：**让 PC 和设备吃完全相同的字节流**。`np.ndarray.tofile()` 写出，`np.fromfile()` 读回，中间不做 JSON、不做图片编码，避免二次解析引入差异。

### 控制变量法（精度对比的第一原则）

做科学实验要控制变量。双端对比里，**唯一允许不同的变量是推理设备**（PC 的 ORT vs 设备的 NPU runtime）。输入、模型结构、权重精度路径、后处理参数都应一致；若你故意测「端到端 pipeline」，那两端必须走 **同一套** 预处理流程，而不是各写各的。

### 余弦相似度（Cosine Similarity）

两个同 shape 张量拉成向量后，算夹角余弦，范围理论上是 `[-1, 1]`，部署里多在 `0.95～1.0` 之间讨论。它对 **整体缩放** 不敏感——输出整体乘个常数，余弦可能仍很高，但检测框解码可能已经错了。

所以余弦是 **层对齐的筛查门槛**，不是发货门禁。我会同时看 MSE（均方误差）、关键 head 分支的余弦，以及 mAP 等业务指标。

### MSE（Mean Squared Error，均方误差）

对应元素差的平方再平均。比余弦更「抠数值」，对 outlier 敏感。层输出对比时，我会余弦 + MSE 一起看：余弦高但 MSE 大，往往是少数位置差很多（检测 head、Softmax 尖峰处常见）。

### Golden / Ground Truth（基准输出）

这里 Golden 指 **PC 侧在标准输入下跑出来的参考输出**，存成 `output_gt.bin`。不是训练标签，是「 believed-correct 的推理结果」。设备输出 `output_npu.bin` 跟它对。

### ADB（Android Debug Bridge）

PC 和设备之间的调试桥：`adb push` 推文件、`adb shell` 进设备执行命令、`adb pull` 拉回结果。昇腾开发板、不少边缘 Linux 板子都走这套。第一次联调卡在 `adb devices` 找不到设备，比卡在精度上还常见——先把链路打通再谈余弦。

### ORT（ONNX Runtime）

微软开源的 ONNX 推理引擎，PC 上常用 CPU/CUDA EP 做 Golden。团队里 ORT FP32/FP16 是 **验收基准**，不是最终交付物；交付物是芯片侧二进制 + 锁版本的工具链。

---

## 为什么双端对比必须同一份 input.bin？

### 输入差异会被网络放大

神经网络对输入很敏感。预处理里 resize 插值、RGB/BGR 顺序、`mean/std` 归一化、letterbox 填充色，任何一处和 PC 不一致，进网络后都会经过几十层卷积、激活、归一化 **累积放大**。

INT8 更麻烦。**PTQ（Post-Training Quantization，后训练量化）** 把连续浮点映射到 `-128～127` 整数；输入值若在量化边界附近，0.1 的浮点差可能导致整数格完全不同。后面层全跟着歪。

### 最常见的输入不一致来源

| 来源 | 典型后果 | 怎么避 |
|------|----------|--------|
| resize 插值算法不同（OpenCV vs PIL） | 全图像素微差，INT8 后放大 | 预处理只在 PC 做一次，写 bin |
| RGB / BGR 搞反 | 通道全错，余弦可能仍「凑合」 | 在 PC 侧统一转好再落盘 |
| 重复归一化（bin 已 `/255` 设备又除一次） | 数值量级全错 | 设备只 `fromfile`，不做预处理 |
| `float32` vs `float16` 存 bin | 字节不同，对比无意义 | 统一 `float32` 生成 input |
| shape 差 1（如 640 vs 672 letterbox） | 全网错位 | 严格约定 NCHW 与尺寸 |
| 推理时仍开随机增强 | 每次输入不同 | 验收阶段关掉所有 aug |

表后补一句：**只要设备侧还藏着预处理代码，就没法保证和 PC 一致**。工程上最稳的做法是 PC 侧生成 `input.bin`，两端都只读 bin 推理；设备侧 demo 里的 `resize`、`cvtColor` 在精度验证阶段应关掉或绕开。

若你测的就是 **端到端业务 pipeline**（相机采集 → 驱动预处理 → 推理），可以两端各走完整流程——但那是另一个验收项，不能和「同 bin 比 converter/量化」混为一谈。

---

## 三种错误对比方式（我都见过）

**错误 1：两端各读同一张 jpg，各做一遍预处理。**

现象：余弦偏低，疯狂调校准集无效。原因：预处理实现细节不同，输入早就不一致了。怎么查：把两端进网络的 tensor `tofile`，用 `md5sum` 或逐字节 `diff`。怎么改：PC 生成 bin，设备只加载 bin。

**错误 2：PC 生成 bin，设备加载后又做归一化。**

现象：余弦极差，输出数量级不对。原因：bin 里已是 `0～1` 浮点，又 `/255` 一次。怎么查：打印设备侧进 session 前的 `min/max/mean`。怎么改：删掉设备侧多余预处理，或 PC 改存原始 `0～255` float，两端约定一致。

**错误 3：只比 mAP，不比中间 tensor。**

现象：mAP 掉了不知道怪量化还是怪后处理。原因：业务指标离网络输出隔了 NMS、解码、阈值好几层。怎么查：先比最后一层网络输出余弦，再比加后处理后的框。怎么改：分层验收——网络输出对齐了再查 C++ 后处理。

---

## 正确的对比顺序（建议照这个做）

多数项目我会拆成三道门禁，别一上来就 INT8：

1. **FP32/FP16 对齐**：PC ORT 与设备 FP16 `.om`，同 `input.bin`，最后一层余弦应非常接近（具体阈值视任务，检测 head 常要求更严）。不过这一关，问题在 **converter、算子、layout**，和 INT8 无关。
2. **INT8 对齐**：在 FP16 过关后再比 INT8 `.om` 与 PC ORT INT8（或 FP16 Golden，看团队约定）。这时余弦掉一点通常算量化误差，要结合校准集和混合精度策略看。
3. **业务指标**：同测试集、同后处理，看 mAP、召回、误检率；坏例图人工扫一遍。张量像不像和业务对不对，不是一回事。

逐层对比是定位手段：某层余弦先掉到 98% 以下，从该层往前查是量化、fuse 还是算子近似。昇腾可在编译时开 layer dump；PC 侧可在 ONNX 里插 identity 输出各层。先找 **第一个明显分叉的层**，别盲目改全网。

---

## 标准 ADB 上板精度验证流程

下面按昇腾 310 类板子写；其他 NPU 把 `infer` 可执行文件和库路径换成厂商的，思路一样。

### 步骤 1：PC 侧生成标准输入和 Golden 输出

所有预处理 **只在这里做一次**。读图、resize、归一化、转 NCHW、扩 batch，然后 `tofile`。ORT 跑同一 `input_data`，输出存 `output_gt.bin`。

验证项：记下 `input.bin` 的字节数和 `md5`；`input_data.shape` 和 `dtype` 与设备侧约定一致。

### 步骤 2：ADB 推送

```bash
adb devices
adb shell mkdir -p /data/infer
adb push model.om /data/infer/
adb push input.bin /data/infer/
adb push infer /data/infer/
adb shell chmod +x /data/infer/infer
```

依赖库若不在系统路径，一并 `push`，后面用 `LD_LIBRARY_PATH` 指过去。验证项：`adb shell ls -l /data/infer` 能看到文件且 `infer` 可执行。

### 步骤 3：设备侧推理

```bash
adb shell "cd /data/infer && export LD_LIBRARY_PATH=/data/infer:\$LD_LIBRARY_PATH && ./infer ./model.om ./input.bin ./output_npu.bin 1,3,640,640"
```

参数含义因厂商 demo 而异，一般是：模型路径、输入路径、输出路径、输入 shape。验证项：推理返回 0，`output_npu.bin` 非空且字节数等于 `输出元素个数 × sizeof(float)`。

### 步骤 4：拉回输出并算余弦 / MSE

```bash
adb pull /data/infer/output_npu.bin ./
```

Python 侧 `fromfile` 读两个 bin，`reshape` 成同一 shape，算余弦和 MSE。具体多少算过关 **没有全行业统一标准**，要和业务线对齐；层对比时我常把 head 和 backbone 分开算，避免大 tensor 把坏分支平均掉。

### 步骤 5（可选）：逐层 dump

最终输出差得多，就逐层比。找到第一个余弦明显掉下去的层，查该算子在芯片上的支持、量化参数、是否 CPU fallback。这一步才值得翻 converter 日志里的 warning。

---

## 最常见坑（附排查顺序）

### 坑 1：`adb devices` 空列表

典型做法：线插上直接 push。现象：命令超时或 `device not found`。原因：USB 调试未开、驱动未装、线只充电。怎么查：`adb kill-server && adb start-server`，换线换口。怎么改：开发者选项里开 USB 调试，Windows 装厂商驱动；不少项目第一次联调就卡在这，先别怀疑模型。

### 坑 2：`error while loading shared libraries`

典型做法：只 push 了 `infer` 没 push 依赖 `.so`。现象：shell 里一运行就报缺库。原因：`LD_LIBRARY_PATH` 没设或 CANN 版本和编译时不一致。怎么查：`ldd ./infer` 看缺哪几个；对比编译机和板子驱动版本。怎么改：push 齐库或 `export LD_LIBRARY_PATH`；长期应把版本写进 release note。

### 坑 3：`infer: No such file or directory` 或 `Exec format error`

典型做法：把 x86 编的二进制 push 到 arm64 板子。现象：无法执行。原因：ABI 不匹配。怎么查：`file infer` 看是不是 `ARM aarch64`。怎么改：用 `arm64-v8a` 交叉编译的 demo，或直接在板子上编。

### 坑 4：推理成功但输出全零或文件为空

典型做法：shape 字符串写错。现象：余弦 0 或 NaN。原因：`1,3,640,640` 写成 `3,640,640` 少 batch，或模型输入名和 demo 硬编码不一致。怎么查：对照 ONNX `input` 的 shape 和名称；看 infer 日志。怎么改：参数与导出时静态 shape 对齐。

### 坑 5：余弦低却一直在调校准集

典型做法：两端各预处理。现象：怎么换 calib 都没用。原因：输入不一致（本篇核心）。怎么查：**先对 input.bin 的 md5**，再对 FP16 是否过关。怎么改：同 bin；先 FP16 再 INT8。

### 坑 6：全局余弦 99%+，框全是乱的

典型做法：只比整段输出一个数。现象：张量「像」但业务废了。原因：YOLO 多 stride，坏一个分支平均余弦仍高；或后处理 letterbox 逆变换、NMS 阈值和 Python 不一致。怎么查：按 stride/分支拆开算余弦；对一下 C++ 后处理和训练脚本。怎么改：**业务指标门禁高于张量余弦**；网络对齐后再查解码。

建议排查顺序：**adb 通 → 库和 ABI → 输出文件非空 → input md5 一致 → FP16 双端 → INT8 双端 → 逐层 → 后处理与 mAP**。

---

## 验收标准怎么定

没有银弹，我会和客户对齐一张表，并写进 release note：

| 维度 | 常见做法 | 说明 |
|------|----------|------|
| 张量 | 关键层余弦、MSE；head 与 backbone 分开 | 阈值视模型而定，检测 head 常更严 |
| 任务 | mAP / 召回 / 误检相对 FP32 掉点上限 | 安防、智驾、工业质检线差很多 |
| 系统 | P99 延迟、峰值内存、温升 | 精度过了但延迟不达标也不能发 |
| 可复现 | 校准集 hash、CANN 版本、驱动版本 | 半年后要能复现同一数字 |

余弦 99% 在层对比里往往算「可以继续往下查」的门槛，不是「能发货」。我遇到过全局 99.6%，某个 stride 的 box 分支 94%，画出来框全飘——平均被 backbone 大 tensor 淹没了。

---

## 面试追问

### 1

**问：** 为什么双端精度对比必须用同一份 `input.bin`？

**答：** 因为要控制变量——输出差异只能来自量化、converter 或驱动，输入差一个字节余弦就没意义。做法是 PC 侧 ORT 预处理一次，把输入和 Golden 输出都落盘；`adb push` 同一份 `input.bin` 到设备，pull 回 `output_npu.bin` 再比。设备侧不要再做 resize/归一化，除非你就是测端到端 pipeline，那两端必须同一套流程。

### 2

**问：** ADB 上板做精度验证，口述流程是什么？

**答：** `adb push` 模型和 `input.bin`（和 infer 可执行文件、缺的 `.so`）→ `adb shell` 里设好 `LD_LIBRARY_PATH` 跑 infer，参数里写模型路径、输入输出路径、shape → `adb pull output.bin` → PC 脚本算余弦和 MSE。注意 arm64 ABI、库版本和编译时 CANN 一致。第一次联调先保证 `adb devices` 能见到设备。

### 3

**问：** 余弦相似度 99% 能直接上线吗？

**答：** 不能单凭这一个数。余弦对缩放不敏感，全局 99% 可能掩盖检测 head 某条分支已经坏了。我会拆 head/backbone 看余弦和 MSE，再上 mAP 和坏例图。张量对齐是必要条件，发货还要看业务指标和延迟功耗。

### 4

**问：** FP16 双端不过，该先调量化吗？

**答：** 不该。FP16 不过说明问题在模型转换、算子实现或 layout，和 INT8 校准无关。顺序永远是：同 `input.bin` 先把 FP16（或 FP32）对齐，再比 INT8。否则你在错误的基础上调 calib，只会浪费时间。

### 5

**问：** 全局余弦很高，检测框全乱，你先查什么？

**答：** 先怀疑后处理和 head，不是先加校准图。把输出按 stride 拆开算余弦，看是不是某一个分支坏了；对 C++ 里 sigmoid/exp 解码、letterbox 逆变换、NMS 阈值是否和 Python 训练一致。网络最后一层对齐后，再查 head 是否该 skip quant、Softmax 是否被近似实现。

---

## 附录 A：checklist（可打印）

```
[ ] 所有预处理在 PC 侧完成，已生成 input.bin
[ ] 设备侧推理路径无 resize/归一化/颜色转换（除非测端到端）
[ ] PC 与设备使用同一 input.bin（md5 一致）
[ ] input/output 的 dtype、shape、layout 文档化且两端一致
[ ] 已先比 FP16（或 FP32），过关后再比 INT8
[ ] 推理阶段关闭随机增强与随机数
[ ] adb devices / push / shell / pull 全流程跑通
[ ] infer 为 arm64，依赖 .so 齐全，LD_LIBRARY_PATH 正确
[ ] CANN/驱动版本与编译机一致并记入 release note
[ ] 除全局余弦外，head 关键分支单独对比
[ ] 最终输出对齐后，才做后处理与 mAP/坏例验收
[ ] converter 日志中的 fallback/warning 已存档
```

---

## 附录 B：最小可运行脚本（PC 生成 + 对比 + ADB 推理）

以下脚本把「生成 bin → 推板 → 推理 → 拉回 → 算余弦」串在一起。`infer` 需换成你板子上的厂商 demo；`OUTPUT_SHAPE` 换成你模型的输出 shape。

**generate_and_compare.py**

```python
import hashlib
import subprocess
import sys

import cv2
import numpy as np
import onnxruntime as ort

# ---------- 配置（按项目改） ----------
IMAGE_PATH = "test.jpg"
ONNX_PATH = "model.onnx"
INPUT_NAME = "images"  # 与 ONNX 一致
INPUT_SHAPE = (1, 3, 640, 640)
OUTPUT_SHAPE = (1, 25200, 85)  # 示例：YOLOv5 类输出
REMOTE_DIR = "/data/infer"
INPUT_BIN = "input.bin"
GT_BIN = "output_gt.bin"
NPU_BIN = "output_npu.bin"
OM_NAME = "model.om"  # push 到板子后的文件名


def run(cmd: str) -> str:
    print(f">>> {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        raise RuntimeError(f"命令失败: {cmd}")
    return r.stdout


def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def preprocess(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = INPUT_SHAPE[2], INPUT_SHAPE[3]
    img = cv2.resize(img, (w, h), interpolation=cv2.INTER_LINEAR)
    img = img.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))
    return np.expand_dims(img, axis=0)


def gen_golden():
    x = preprocess(IMAGE_PATH)
    x.tofile(INPUT_BIN)
    print(f"input.bin md5={md5_file(INPUT_BIN)} bytes={x.nbytes}")

    sess = ort.InferenceSession(ONNX_PATH, providers=["CPUExecutionProvider"])
    y = sess.run(None, {INPUT_NAME: x})[0]
    y.tofile(GT_BIN)
    print(f"output_gt.bin shape={y.shape} dtype={y.dtype}")


def cosine_mse(a: np.ndarray, b: np.ndarray):
    af, bf = a.flatten().astype(np.float64), b.flatten().astype(np.float64)
    cos = float(np.dot(af, bf) / (np.linalg.norm(af) * np.linalg.norm(bf) + 1e-12))
    mse = float(np.mean((a - b) ** 2))
    return cos, mse


def adb_infer():
    shape_str = ",".join(str(x) for x in INPUT_SHAPE)
    run(f"adb shell mkdir -p {REMOTE_DIR}")
    run(f"adb push {INPUT_BIN} {REMOTE_DIR}/")
    run(f"adb push {OM_NAME} {REMOTE_DIR}/")
    run(f"adb push infer {REMOTE_DIR}/")
    run(f"adb shell chmod +x {REMOTE_DIR}/infer")
    run(
        f'adb shell "cd {REMOTE_DIR} && '
        f'export LD_LIBRARY_PATH={REMOTE_DIR}:$LD_LIBRARY_PATH && '
        f'./infer ./{OM_NAME} ./{INPUT_BIN} ./{NPU_BIN} {shape_str}"'
    )
    run(f"adb pull {REMOTE_DIR}/{NPU_BIN} ./{NPU_BIN}")


def compare():
    gt = np.fromfile(GT_BIN, dtype=np.float32).reshape(OUTPUT_SHAPE)
    npu = np.fromfile(NPU_BIN, dtype=np.float32).reshape(OUTPUT_SHAPE)
    cos, mse = cosine_mse(gt, npu)
    print(f"\n=== 精度对比 ===")
    print(f"余弦相似度: {cos:.6f}")
    print(f"MSE: {mse:.6f}")
    return cos, mse


if __name__ == "__main__":
    gen_golden()
    adb_infer()
    compare()
```

用法：把 `model.onnx`、`model.om`、`infer`、`test.jpg` 放同一目录，装好 `opencv-python`、`onnxruntime`，板子连好 USB，执行 `python generate_and_compare.py`。

---

## 术语速查

| 术语 | 全称 / 含义 | 一句话直觉 |
|------|------------|-----------|
| input.bin | 预处理张量裸二进制 | 两端吃同一串字节，杜绝预处理差 |
| Golden | 基准输出 | PC 在标准输入下的参考 `output_gt.bin` |
| 余弦相似度 | Cosine Similarity | 看方向像不像；不代替 mAP |
| MSE | Mean Squared Error | 抠数值差，补余弦盲点 |
| PTQ | Post-Training Quantization | 训后量化；输入微差会被放大 |
| ADB | Android Debug Bridge | push / shell / pull 上板调试 |
| ORT | ONNX Runtime | PC 侧 Golden 常用引擎 |
| ATC | Ascend Tensor Compiler | 昇腾 ONNX→`.om`；精度扯皮看其日志 |
| 控制变量 | — | 只能设备不同，输入必须一致 |
| CPU fallback | 回退 CPU | 某 op 不在 NPU 上跑；profiler 里 Device=CPU |
