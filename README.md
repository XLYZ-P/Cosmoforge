# Cosmoforge · 模拟宇宙

> **可解释的世界观生成器。**
> 从物理常数出发，把「大爆炸 → 平行宇宙 → 行星 → 随机事件」的每一步因果，
> 画成一棵可逐节点展开的思维导图。
> 结构由确定性随机数决定，LLM 只负责把已经确定的事实写成散文。

An explainable worldbuilding engine: Big Bang → parallel universes → planets →
events, rendered as an interactive mind map and timeline. 19 model providers,
live streaming growth, seeds and archives. Zero runtime dependencies.

[![Release](https://img.shields.io/github/v/release/XLYZ-P/Cosmoforge?include_prereleases&label=release)](https://github.com/XLYZ-P/Cosmoforge/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](COMPATIBILITY.md)

> 当前为 **alpha** 预览：Release `alpha0.0.1`，包版本 `0.0.1a0`。

---

## 为什么是它

市面上的工具大致分两类，各自缺一半：

| 类别 | 代表 | 缺什么 |
|---|---|---|
| 程序化世界生成器 | WorldEngine、GenGen、ProceduralGalaxy | 确定性、物理驱动，但通常只造“一个”世界，不解释命运从何而来 |
| LLM 世界 / 社会模拟 | Generative Agents、Project Sid、Emergence World | 行为丰富，但结构会漂移，输出往往是日志而不是可检查的因果 |

Cosmoforge 站在两者之间：

- **确定性内核** `random.Random(seed)` 负责一切结构与数值：物理常数、宜居度、命运、
  行星参数、事件时间与严重度。**同一个 seed 永远重建出同一套宇宙。**
- **LLM 只写叙事**：润色已经确定的事实，不推进状态。

依据是 arXiv [2406.06485](https://arxiv.org/abs/2406.06485)：让 LLM 直接当世界模拟器，
单步准确率约 **0.599**，十步后约 `0.599¹⁰ < 1%`。因此本框架刻意不让 LLM 接管事件推进。

## 功能

**生成**

- 11 个真实宇宙纪元：普朗克、暴胀、核合成、复合、再电离……
- 平行宇宙：采样引力 / 强力 / 暗能量 / 熵 / 维度，推导宜居度与命运，并支持宇宙分支
- 行星：轨道、重力、温度、大气、生物圈（无菌 → … → 智慧）
- 27 个加权事件模板：按宜居度与时间窗抽样，可因果地推动生物圈升级或触发大灭绝
- 同 seed 完全可复现

**界面**

- 可折叠思维导图：大爆炸 / 纪元 + 宇宙 → 行星 → 事件同屏
- 时间线：对数纪元轴 + 线性 Gyr 轴，事件按严重度着色，支持播放
- 触屏：单指平移、双指捏合缩放、轻点展开、双击放大
- 缩放滑块（8%–350%）、适应窗口、100% 复位、快捷键 `+ - 0 F`
- 动画：节点弹出、连线绘制、镜头平滑移动、时间线播放、流式文字逐字出现
- 搜索、导出 SVG、节点属性面板

**实时生成**

- 节点级 `展开子节点` / `续写叙事`，优先走 SSE 流式接口
- 动态演化：持续随机生长，树和时间线边生成边更新；mock 模式自动开启，上限 420 节点
- 19 家模型供应商，任何失败自动回退到普通请求或 rule 叙事

**数据**

- 种子输入框：输入后确定性重建，留空随机
- 存档：把整棵树（含 LLM 内容）保存为服务器上的 JSON，可列表、读取、下载
- 离线单文件 HTML：不跑服务也能看导图、时间线、触屏与动画

## 快速开始

### 环境

- Python **≥ 3.9**
- 现代浏览器（Chrome / Edge / Firefox / Safari）
- **零第三方运行时依赖**

更多系统差异见 [COMPATIBILITY.md](COMPATIBILITY.md)。

### 安装

从 [Release](https://github.com/XLYZ-P/Cosmoforge/releases/tag/alpha0.0.1) 下载标准包：

```bash
pip install cosmoforge-0.0.1a0.tar.gz
# 或
pip install cosmoforge-0.0.1a0-py3-none-any.whl
```

从源码安装：

```bash
git clone https://github.com/XLYZ-P/Cosmoforge.git
cd Cosmoforge
pip install -e .
```

不安装也可以直接运行：

```bash
python -m cosmoforge demo --out cosmos.html --open
```

### 离线 demo

```bash
python -m cosmoforge demo --out cosmos.html --json-out cosmos.json --md-out cosmos.md
```

生成后直接打开 `cosmos.html`。时间线、触屏、缩放、动画都可用；
LLM 展开 / 动态演化按钮需要后端服务。

### 实时服务

```bash
# 离线 mock：不需要 key，动态演化会自动开始
python -m cosmoforge serve --provider mock --open

# 真实模型
export DEEPSEEK_API_KEY=sk-...
python -m cosmoforge serve --provider deepseek --model deepseek-chat --open
```

默认地址 `http://127.0.0.1:8765/`。局域网访问：

```bash
python -m cosmoforge serve --provider mock --host 0.0.0.0 --port 8765
```

### 接入模型

```bash
# DeepSeek
export DEEPSEEK_API_KEY=sk-...
python -m cosmoforge serve --provider deepseek --model deepseek-chat

# OpenAI
export OPENAI_API_KEY=sk-...
python -m cosmoforge serve --provider openai --model gpt-4o-mini

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python -m cosmoforge serve --provider anthropic

# Gemini
export GEMINI_API_KEY=...
python -m cosmoforge serve --provider google

# 本地 Ollama（无需 key）
python -m cosmoforge serve --provider ollama --model llama3.2
```

Windows 使用 `set VAR=value`（CMD）或 `$env:VAR = "value"`（PowerShell）。
查看全部供应商与对应的环境变量名：

```bash
cosmoforge providers
```

### Python API

```python
from cosmoforge import Scenario, Cosmogenesis, to_html

scenario = Scenario.demo().with_overrides(universes=5, seed=2026)
cosmos = Cosmogenesis(scenario).run()

to_html(cosmos, path="cosmos.html")
print(cosmos.universes[0].planets[0].narrative)
```

## 界面说明

| 操作 | 效果 |
|---|---|
| 点击 / 轻点节点 | 折叠或展开子树 |
| 拖拽 / 单指 | 平移画布 |
| 滚轮 / 双指捏合 | 以光标或双指中点为锚缩放 |
| 双击空白处 | 放大 |
| 工具栏「时间线」 | 打开时间线；「播放」按年代点亮事件 |
| 时间线上点事件 | 回到导图并定位高亮 |
| 工具栏「动态演化」 | 持续自动生长；mock 默认开启 |
| 工具栏种子框 | 输入后回车重新生成；留空随机 |
| 工具栏「存档」 | 保存 / 读取 / 下载当前整棵树 |

存档默认写到启动目录下的 `archives/`，可以用 `--archive-dir` 或
`COSMOFORGE_ARCHIVE_DIR` 修改。存档是普通 JSON，包含标题、种子、时间与完整树。

## 前后端分离

前端是 `cosmoforge/web/` 下的纯静态应用，无构建、无 CDN、无第三方运行时；
所有数据通过 `fetch` 从后端 API 获取。后端只返回 JSON / SSE，不把数据渲染进 HTML。

```
浏览区 (cosmoforge/web/)
  index.html   styles.css   app.js
        │  fetch / SSE
        ▼
后端 API (cosmoforge/serve.py)
  bootstrap · tree · expand · regenerate · archives
        │
        ▼
确定性生成器 + 模型供应商 (stdlib urllib)
```

前端也可以单独部署，设置后端地址即可（API 已开启 CORS）：

```html
<script>window.COSMOS_API_BASE = "http://<backend>:8765";</script>
```

### API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/bootstrap` | `{title, seed, live, provider, tree}`，前端启动时拉取 |
| GET | `/api/tree` | 当前完整树（兼容接口） |
| GET | `/api/health` | 后端与供应商状态 |
| GET | `/api/archives` | 存档列表 |
| GET | `/api/archive?id=...` | 下载存档 JSON |
| POST | `/api/expand` | `{"id", "action": "expand" \| "continue"}` |
| POST | `/api/expand/stream` | 同一请求，SSE：`phase → delta → node → done` |
| POST | `/api/regenerate` | `{"seed": 2026}`，确定性重建 |
| POST | `/api/save` | `{"name": "..."}`，保存当前树 |
| POST | `/api/load` | `{"id": "..."}`，读取存档 |

页面优先使用 `/api/expand/stream`：叙事逐字出现，子节点边生成边长出来；
不支持流式时自动回退到 `/api/expand`。服务把当前树保存在内存里，刷新页面不会丢失。

## 供应商

19 家内置后端，HTTP 全部走标准库 `urllib`：

| 类别 | 供应商 |
|---|---|
| OpenAI 协议 | `openai` `azure` `deepseek` `moonshot`(Kimi) `zhipu`(GLM) `dashscope`(Qwen) `mistral` `groq` `together` `openrouter` `xai` `fireworks` `perplexity` |
| 本地 / 自托管 | `ollama` `lmstudio` `vllm` |
| 原生协议 | `anthropic` `google`(Gemini) |
| 离线 | `mock`（确定性、免密钥） |

别名：`gpt→openai`、`claude→anthropic`、`gemini→google`、`qwen→dashscope`、
`glm→zhipu`、`kimi→moonshot`、`local→ollama`、`offline/none→mock`。

回退链（按顺序尝试，第一个成功者胜出）：

```python
from cosmoforge import Scenario, Cosmogenesis, LLMNarrator, resolve_providers

provider = resolve_providers([
    {"provider": "anthropic", "model": "claude-3-5-sonnet-latest"},
    {"provider": "deepseek"},
    {"provider": "ollama"},
])
cosmos = Cosmogenesis(Scenario.demo(), narrator=LLMNarrator(provider)).run()
```

## CLI

| 命令 | 说明 |
|---|---|
| `cosmoforge demo` | 生成内置示例 |
| `cosmoforge run scenario.json` | 运行场景文件 |
| `cosmoforge serve` | 启动前端 + API |
| `cosmoforge providers` | 列出供应商 |

常用参数：`--seed`、`--universes`、`--planets 2-5`、`--branching`、
`--narrator rule|llm`、`--provider`、`--model`、`--language`、
`--out`、`--json-out`、`--md-out`、`--open`。
`serve` 额外支持 `--host`、`--port`、`--title`、`--archive-dir`。

## 场景文件

```jsonc
{
  "name": "The Vela Branch",
  "seed": 2026,                 // 决定一切结构
  "universes": 5,
  "branching": 0.4,             // 分支出子宇宙的概率
  "max_generation": 2,
  "law_sigma": 0.22,            // 物理常数采样标准差
  "planets_per_universe": [2, 6],
  "universe_events": [4, 8],
  "planet_events": [3, 6],
  "narrator": "rule",           // "rule" 或 "llm"
  "language": "en"              // LLM 叙事语言，如 "zh"
}
```

## 目录结构

```
Cosmoforge/
├─ cosmoforge/
│  ├─ models.py  lore.py  genesis.py  planets.py  events.py
│  ├─ narrate.py  simulation.py  scenario.py  util.py
│  ├─ providers/   base · openai · anthropic · google · ollama · mock
│  ├─ render/      mindmap.py  markdown.py
│  ├─ web/         index.html  styles.css  app.js
│  ├─ serve.py
│  └─ cli.py  __init__.py  __main__.py
├─ examples/multiverse.json
├─ tests/          test_cosmoforge.py  test_providers.py  test_serve.py
├─ releases/       cosmoforge-0.0.1a0.tar.gz  SHA256SUMS
├─ COMPATIBILITY.md
├─ MANIFEST.in
└─ pyproject.toml
```

运行后还会生成 `archives/`（已加入 `.gitignore`）。

## 测试与打包

```bash
python -m unittest discover -s tests -v   # 43 tests
pytest tests                              # 如果安装了 pytest
python -m build --sdist --wheel
```

测试覆盖确定性、结构约束、事件门槛、供应商解析与回退链、
HTML 自包含与脚本转义、时间线 / 缩放标记，以及
`/api/expand`、`/api/expand/stream`、种子重建、存档保存 / 读取 / 下载全链路。

发布包：

- Release：[alpha0.0.1](https://github.com/XLYZ-P/Cosmoforge/releases/tag/alpha0.0.1)
- 包版本：`0.0.1a0`
- 校验：下载后执行 `sha256sum -c SHA256SUMS`

## 扩展

- **新增供应商**：继承 `OpenAICompatProvider` 改 4 个类属性，或继承 `Provider` 实现 `_complete()`
- **新增事件**：往 `lore.PLANET_EVENTS` / `lore.UNIVERSE_EVENTS` 加一条 `EventTemplate`
- **新增叙事者**：实现 `Narrator` 的三个方法，传给 `Cosmogenesis(..., narrator=...)`
- **新增命运 / 行星类型**：扩展 `models.DESTINIES` / `models.PLANET_KINDS`，
  并在 `genesis.destiny_from_laws` / `planets.KIND_WEIGHTS` 给出规则

## 说明

- 包名 `cosmoforge` 在 PyPI 上已被占用，因此当前通过 GitHub Release 或源码安装。
- 显示名「模拟宇宙 / Simulated Universe」用于主题展示，命令与包标识仍为 `cosmoforge`。
- 本版本为 alpha，API 与存档格式可能变化。

## License

[MIT](LICENSE) © 2026 AnoLuminescent
