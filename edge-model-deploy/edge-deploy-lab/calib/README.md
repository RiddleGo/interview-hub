# 校准集目录

PTQ 不需要标签，但需要 **与线上一致的预处理**。

## 目录结构

```
calib/
├── images/          # 100～500 张典型场景 JPG/PNG
└── npy/             # 由 scripts/05_prepare_calib.py 生成（可选）
```

## 组织规范（对应面试题 Q7）

1. **分布**：与部署场景同族（光照、距离、季节），不必与训练集同张图。
2. **数量**：建议 100～500 张；少于 50 张易 outlier 拉爆 scale。
3. **预处理**：与 `scripts/03_preprocess.py` 完全一致（letterbox、RGB、/255）。
4. **版本**：记录图片列表 hash，写入 `release/release_note_template.md`。

## 快速准备

```bash
# 将图片放入 calib/images/
python scripts/05_prepare_calib.py --config configs/project.yaml
```

若无真实场景图，可先用 COCO val 子集或 `data/sample/` 中的示例图练流程。
