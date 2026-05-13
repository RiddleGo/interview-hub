# interview-hub

本站 **`index.html` 为学习总入口**：顶部可进入 **《人工智能系统》教材**（目录 `ai-system-textbook/`，微软 [AI-System/Textbook](https://github.com/microsoft/AI-System/tree/main/Textbook) 在线阅读），下方为面经题库导航。

面经合集 **导航站**：用浏览器访问下方 Pages 地址，可一键进入四个题库仓库与各自的单页 `study.html`。页面底部含 **微信公众号 · TrustZone** 配图（`images/gongzhonghao.webp` / `gongzhonghao-sm.png`，压缩后约数十 KB，加载更快）。

各题库「单页学习」直达 **`https://riddlego.github.io/<仓库名>/study.html`**（GitHub Pages），不再经过中转页。

## 在线访问

启用 GitHub Pages（见下）后，站点一般为：

**https://riddlego.github.io/interview-hub/index.html**（推荐；根路径 `/interview-hub/` 偶发 CDN 旧缓存）

备用：`https://riddlego.github.io/interview-hub/?v=1`

（若使用自定义域名，以仓库 Settings → Pages 显示为准。）

## GitHub Pages 说明

当前使用 **Deploy from a branch**：分支 **`main`**、目录 **`/`（根目录）**，由 GitHub 直接发布静态文件（无需 Actions）。  
若你在 Settings 里改过，请保持为 **Branch: `main` / folder: `/ (root)`**。

## 本地预览

直接用浏览器打开根目录的 `index.html` 即可（相对链接在本地同样可用）。教材页位于 `ai-system-textbook/index.html`；更新教材目录清单可在该目录执行：`python scripts/build_manifest.py`。
