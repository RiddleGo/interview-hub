# interview-hub

面经合集 **导航站**：用浏览器访问下方 Pages 地址，可一键进入四个题库仓库与各自的单页 `study.html`。

各题库单页经 **`open.html?repo=…`** 用 Blob+iframe 打开（避免部分浏览器/WebView 仍按纯文本展示）；备用直链见 `open.html` 顶栏。

## 在线访问

启用 GitHub Pages（见下）后，站点一般为：

**https://riddlego.github.io/interview-hub/index.html**（推荐；根路径 `/interview-hub/` 偶发 CDN 旧缓存）

备用：`https://riddlego.github.io/interview-hub/?v=1`

（若使用自定义域名，以仓库 Settings → Pages 显示为准。）

## GitHub Pages 说明

当前使用 **Deploy from a branch**：分支 **`main`**、目录 **`/`（根目录）**，由 GitHub 直接发布静态文件（无需 Actions）。  
若你在 Settings 里改过，请保持为 **Branch: `main` / folder: `/ (root)`**。

## 本地预览

直接用浏览器打开根目录的 `index.html` 即可（相对链接在本地同样可用）。
