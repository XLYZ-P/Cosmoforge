# 跨平台兼容性 / Compatibility

## 结论

Cosmoforge 是**纯 Python 标准库**实现（零第三方运行时依赖），前端是**无构建、无 CDN**
的静态 HTML/CSS/JS。因此只要目标设备同时具备下面两个条件，就能运行：

1. **Python ≥ 3.9**
2. **现代浏览器**（Chrome / Edge / Firefox / Safari）

不需要 Node.js、npm、数据库、编译器或任何系统服务。

---

## 支持矩阵

| 系统 | 状态 | 说明 |
|---|---|---|
| Linux (x86_64 / arm64) | ✅ 已验证 | 当前开发与测试环境为 Android Termux / arm64 / Python 3.14 |
| Windows 10/11 | ✅ 理论支持 | 纯标准库；控制台已强制 UTF-8；首次监听 `0.0.0.0` 可能弹防火墙 |
| macOS (Intel / Apple Silicon) | ✅ 理论支持 | 系统自带 Python 3.9 即可；建议用 python.org 或 Homebrew 版本 |
| FreeBSD / 其它 POSIX | ✅ 理论支持 | 仅依赖标准库与 `http.server` |
| Android | ✅ 需 Termux | 本次即在 Termux 中开发；需安装 Python 包 |
| iOS / iPadOS | ❌ 不能直接跑后端 | 无 Python 运行时；可把后端跑在电脑/服务器，用 Safari 访问前端 |
| 无 Python 的 Windows | ⚠️ 需先安装 Python | 从 python.org 安装 3.9+ 并勾选 pip |

### 已验证范围

- 26 个 Python 文件全部通过 **Python 3.9 语法检查**（`ast.parse(..., feature_version=(3, 9))`）
- 所有 import 均为标准库（`urllib` / `http.server` / `json` / `pathlib` / `threading` …）
- wheel 标签为 `py3-none-any`，与操作系统、CPU 架构无关
- 在当前 Termux / Linux / Python 3.14 上 **43 项测试全绿**
- 从标准 `tar.gz` 解压后再次运行，43 项测试同样全绿
- 尚未在 Windows / macOS 实机上执行测试；兼容性结论基于“纯标准库 + Python 3.9 语法检查”

---

## 前端浏览器要求

| 能力 | 用途 | 最低要求 |
|---|---|---|
| Pointer Events | 单指平移 / 双指缩放 | Chrome 55+ / Safari 13+ / Firefox 59+ |
| `fetch` + `ReadableStream` | 实时流式生成 | Chrome 43+ / Safari 14.1+ / Firefox 65+ |
| SVG | 思维导图 / 时间线 | 所有现代浏览器 |
| `ResizeObserver` | 时间线自适应 | 已做存在性判断，旧浏览器自动跳过 |
| `CSS.escape` | 节点高亮 | 已做 try/catch 回退 |

浏览器不支持流式读取时，前端会自动回退到普通 `/api/expand` 请求；功能不丢失，只是没有逐字动画。

---

## 两种运行模式

### 1. 离线单文件（最简单，跨平台）

```bash
python -m cosmoforge demo --out cosmos.html
```

生成的 `cosmos.html` 内联了全部前端资源，双击即可在任意现代浏览器中打开：
时间线、触屏手势、缩放、动画都可用。**只有 LLM 展开/续写/动态演化需要后端。**

### 2. 前后端分离（完整功能）

```bash
python -m cosmoforge serve --provider mock --host 0.0.0.0 --port 8765
```

- 前端：`http://localhost:8765/`
- 同一局域网其它设备：`http://<你的内网 IP>:8765/`
- 云端模型需要网络和 API key；`mock` 模式完全离线

前端也可以单独部署到任意静态服务器，只需设置：

```html
<script>window.COSMOS_API_BASE = "http://<后端地址>:8765";</script>
```

后端已开启 CORS，并允许 `GET/POST/OPTIONS`。

---

## 各系统设置 API key

### Linux / macOS / Termux

```bash
export DEEPSEEK_API_KEY=sk-...
python -m cosmoforge serve --provider deepseek --model deepseek-chat --host 0.0.0.0
```

### Windows CMD

```bat
set DEEPSEEK_API_KEY=sk-...
python -m cosmoforge serve --provider deepseek --model deepseek-chat --host 0.0.0.0
```

### Windows PowerShell

```powershell
$env:DEEPSEEK_API_KEY = "sk-..."
python -m cosmoforge serve --provider deepseek --model deepseek-chat --host 0.0.0.0
```

### 本地 Ollama（无需 key）

```bash
python -m cosmoforge serve --provider ollama --model llama3.2 --host 0.0.0.0
```

---

## 已知限制

- **种子 / 存档**依赖后端；离线单文件模式下这两个按钮会禁用。
  存档默认写到启动目录的 `archives/`，可用 `--archive-dir` 或
  `COSMOFORGE_ARCHIVE_DIR` 修改。
- **Windows 控制台**：已通过 `_force_utf8_console()` 把 stdout/stderr 设为 UTF-8；
  若使用老旧终端仍出现乱码，可先执行 `chcp 65001`。
- **端口占用**：默认 `8765`，冲突时用 `--port` 指定其它端口。
- **`0.0.0.0` 监听**：允许局域网访问；仅本机使用可改为 `--host 127.0.0.1`。
- **iOS**：不能本地跑 Python 后端；浏览器端体验不受影响。

---

## 自检命令

```bash
python -m unittest discover -s tests -v   # 期望 43 passed
python -m cosmoforge demo --out check.html
python -m cosmoforge serve --provider mock --port 8765
```

---

## 可选：Docker

如果希望“任意系统表现完全一致”，可以把项目放进 Docker 镜像（本项目目前未内置
Dockerfile）。核心思路：

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
EXPOSE 8765
CMD ["python", "-m", "cosmoforge", "serve", "--provider", "mock", "--host", "0.0.0.0", "--port", "8765"]
```
