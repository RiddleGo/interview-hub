# leetcode-python

`leetcode-master` 的 Python 化迁移子项目（嵌入 `interview-hub/leetcode-python/`）。

## 目录

- `problems/`：迁移后的题解文档（代码块统一为 Python 语法块，无法可靠转换时为占位实现）。
- `solutions/`：按题目/文档生成的 Python 文件（可通过语法编译）。
- `assets/`：文档引用图片资源。
- `scripts/`：迁移与清洗脚本。
- `templates/`：统一 Python 解题模板。
- `migration-report.md`：迁移统计、规则与已知限制。

## 快速使用

- 浏览入口页：`index.html`
- 查看迁移报告：`migration-report.md`
- 校验语法：

```bash
python -m compileall leetcode-python/solutions
```

## 来源与说明

- 上游来源：`https://github.com/youngyangyang04/leetcode-master`
- 本目录聚焦“Python-first 学习与检索”，对无法自动可靠转换的片段，保留了原始代码文本并以 Python 占位实现标记，便于后续人工补全。
