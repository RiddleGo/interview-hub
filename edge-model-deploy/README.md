# 杈圭紭妯″瀷閮ㄧ讲 路 闈㈢粡涓庡疄鎴樿棰榒n
> interview-hub 瀛愮洰褰?路 30 棰?+ EdgeDeployLab

# 边缘模型部署 · 面试题与实战课题

昇腾端侧模型部署：**30 道面试题实录** + **可跟练全链路课题**（YOLOv5s → ONNX → PTQ → ATC → 上板）。

## 内容导航

| 材料 | 说明 |
|------|------|
| [边缘模型部署-面试题.md](边缘模型部署-面试题.md) | 30 题口述问答（导出 / 量化 / NPU / 上板 / 综合） |
| [edge-deploy-lab/](edge-deploy-lab/) | **转身课题**：7 阶段文档 + 脚本，覆盖全部 30 题 |
| `*_Pro.md` | 专栏深读（单点展开，配合课题各阶段） |

## 快速开始（课题）

```bash
cd edge-deploy-lab
pip install -r requirements.txt
python scripts/run_pc_smoke.py --minimal   # 无 NPU 先验流程
# 完整实战见 edge-deploy-lab/README.md
```

## 专栏索引（深读）

- [从训练到边缘上线全链路_Pro.md](从训练到边缘上线全链路_Pro.md)
- [双端精度验证与ADB上板_Pro.md](双端精度验证与ADB上板_Pro.md)
- [芯片模型转换工具_Pro.md](芯片模型转换工具_Pro.md)
- [NPU与GPU部署差异_Pro.md](NPU与GPU部署差异_Pro.md)
- [量化可上线标准_Pro.md](量化可上线标准_Pro.md)
- [边缘部署工程师日常_Pro.md](边缘部署工程师日常_Pro.md)
- 更多见仓库根目录 `*_Pro.md`

