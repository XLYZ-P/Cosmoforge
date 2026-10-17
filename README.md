# 模拟宇宙 · Simulated Universe

> **可解释的世界观生成器。**
> 从物理常数出发，把「宇宙大爆炸 → 平行宇宙 → 行星 → 随机事件」的每一步因果，
> 画成一棵可以逐节点展开的思维导图。
> 一句话卖点：**每一步为什么发生，我都画给你看。**

> ⚠️ 命名待定：当前 Python 包名 / 命令行为 `cosmoforge`（该名字在 PyPI 上已被占用）。
> 显示名定为「模拟宇宙 / Simulated Universe」，标识符候选见文末 [命名](#命名待定)。

---

## 它解决什么问题

市面上的工具基本分成两类，各自缺一半：

| 类别 | 代表 | 缺什么 |
|---|---|---|
| 程序化世界生成器 | WorldEngine、GenGen、ProceduralGalaxy | 确定性、物理驱动，但**只造"一个"世界**，不解释"为什么是这个命运" |
| LLM 世界/社会模拟 | Generative Agents、Project Sid、Emergence World | 智能体行为丰富，但**结构会漂移**，且输出是日志而非可检查的因果 |

模拟宇宙站在两者之间：**结构由确定性随机数生成，LLM 只负责写散文。**
于是你既能拿到可复现、可解释的因果骨架，又能拿到有文采的叙事。

## 设计依据（不是灵感，是证据）

把 LLM 直接当"世界模拟器"是**不可靠**的。arXiv [2406.06485](https://arxiv.org/abs/2406.06485)
的实测结论是：单步状态预测准确率约 **0.599**，于是 10 步之后累积准确率约为
`0.599^10 < 1%`。

所以本框架做了一个刻意的分工：

- **确定性内核**（`random.Random(seed)`）负责一切结构与数值：物理常数、宜居度、命运、
  行星参数、事件的时间与严重度。→ 相同 seed 永远重建出同一套宇宙。
- **LLM 只负责叙事**：把已经确定的事实写成一段好读的文字。
  → 模型再好也只是"换个说法"，不会把宇宙改乱。

这不是巧合式的好运，而是把"哪一层必须确定、哪一层可以自由"想清楚之后的结果。
**哪天你让 LLM 接管"事件推进"，它就会迅速漂移——这是本框架要避免的头号失败模式。**

## 流程

```
                         宇宙大爆炸
                              │
        ┌──────────┬──────────┼──────────┬──────────┐
        ▼          ▼          ▼          ▼          ▼
      宇宙 A     宇宙 B     宇宙 C     宇宙 D     （…）
       │           │          │          │
       │  ← 每个宇宙采样自己的物理常数：引力 / 强力 / 暗能量 / 熵 / 维度
       │      ↓ 常数决定 宜居度 与 命运（热寂 / 大撕裂 / 大挤压 / 大反弹 / 真空衰变 / 永恒停滞）
       │
       ├── 行星 1 ── 事件 ── 事件        ← 轨道、重力、温度、大气、生物圈
       ├── 行星 2 ── 事件 ── 事件
       └── 行星 3 ── 事件 ── 事件
                              │
                              ▼
                     交互式思维导图（HTML / SVG）
```

1. **大爆炸**：内置 11 个真实宇宙纪元（普朗克、暴胀、核合成、复合、再电离…）。
2. **平行宇宙**：围绕"我们这套常数（=1.0）"采样每个宇宙自己的常数，推导宜居度与命运；
   还能**分支**出继承父宇宙常数的子宇宙。
3. **行星**：类型、轨道、质量、半径、重力、平衡温度、大气成分全部由常数推导，
   再据此算出宜居度，并由宜居度决定初始**生物圈**（无菌 → 前生命 → 微生物 → 多细胞 → 复杂 → 智慧）。
4. **随机事件**：27 个加权模板，按上下文（宜居度门槛、时间窗口）抽样，同一条时间线不重复同类，
   按年代排序，并可**因果地**推动生物圈升级（首次生命、大氧化、智慧觉醒…）或降低宜居度（大灭绝、气候崩溃…）。
5. **叙事**：`rule` 叙事者给出完全确定的文字；`llm` 叙事者调用任意模型写更生动的段落，
   **任何网络/解析失败都自动回退**，模拟永不中断。

## 输出：交互式思维导图（主产物）

单文件、无 CDN、可离线打开：

- `大爆炸 / 纪元` 与 `宇宙 → 行星 → 事件` 同屏展开。
- 点击节点**折叠/展开**子树；右侧面板显示完整叙事与属性表。
- **时间线面板**（点工具栏「时间线」）：上方是**对数时间轴**上的 11 个大爆炸纪元
  （把"暴胀一瞬、然后长达数十亿年的等待"直观压在一屏里）；下方是**线性 Gyr 轴**，
  每个宇宙/行星一行，事件按年代落点、按严重度着色。点任意事件可在思维导图里定位并高亮。
  面板顶部的拖拽条可**调整时间线高度**；「▶ 播放」会让事件按年代**逐个亮起**，
  同步在导图里闪烁对应节点。
- **缩放**：工具栏滑块（8%–350%）、＋/－ 按钮、`适应`、`100%` 复位，
  以及滚轮在光标处缩放；快捷键 `+` `-` `0` `F`。
- **触屏手势**：单指拖拽平移、双指捏合缩放（以双指中点为锚）、轻点节点折叠/展开、
  双击空白处放大；时间线拖拽条也支持触摸。
- **动画**：新节点弹出、连线绘制、镜头平滑移动、时间线播放、流式文字逐字出现。
- **动态演化**：工具栏「动态演化」会持续随机扩展节点，树和时间线**边生成边生长**；
  `serve --provider mock` 时自动开启（离线、免费），上限 420 个节点。
- **种子**：工具栏输入种子后回车，后端用同一确定性 RNG 重新生成整个宇宙；留空则随机。
- **存档**：工具栏「存档」把当前整棵树（含 LLM 展开/续写的节点）保存为服务器上的 JSON，
  可读取、下载；默认目录 `archives/`（可用 `--archive-dir` 或 `COSMOFORGE_ARCHIVE_DIR` 改）。
- **随时展开 / 随时续写（由 LLM）**：见下一节。用 `cosmoforge serve` 打开时才启用。
- 节点按类型配色；**事件按严重度从紫到红渐变**。
- **可解释性被做成了 UI**：因果链是一棵树，而不是一段日志。

其它产物：

| 产物 | 选项 |
|---|---|
| HTML 思维导图（主产物） | `--out cosmos.html` |
| JSON 宇宙数据（可二次开发） | `--json-out cosmos.json` |
| Markdown 大纲 | `--md-out cosmos.md` |

## 随时展开 / 随时续写（由 LLM 驱动）

浏览器不能直接调用模型 API（密钥会暴露、还有 CORS），所以这一功能由一个**本地小服务**中转：

```bash
# 离线试玩（用 mock 后端，不需要任何密钥）
cosmoforge serve --provider mock --open

# 接真实模型
set DEEPSEEK_API_KEY=sk-...
cosmoforge serve --provider deepseek --model deepseek-chat --port 8765 --open
```

服务启动后，在页面里点任意节点，右侧面板会出现两个按钮：

- **✨ 展开子节点**：让模型为这个节点补出新的子节点。
  子节点的**种类受物理层级约束**（`宇宙 → 行星/事件`、`行星 → 事件`、`大爆炸 → 纪元`、`纪元不可展开`），
  模型越界会被服务端过滤掉。
- **✍ 续写叙事**：让模型在这段叙事后面继续写，追加到同一节点。

服务端接口（也可直接 curl）：

```http
POST /api/expand
{"id": "<节点 id>", "action": "expand" | "continue"}
→ {"narrative": "<节点的完整新文本>", "children": [ {label, kind, detail, meta} ], "added": 2}

POST /api/expand/stream     # 同一请求，Server-Sent Events 流式返回
event: phase → delta（逐字）→ node（每长出一个子节点）→ done

POST /api/regenerate {"seed": 2026}       # 确定性重建整个宇宙
POST /api/save       {"name": "演示存档"}  # 把当前整棵树存档
POST /api/load       {"id": "20261017-..."} # 读取存档
GET  /api/archives                        # 存档列表
GET  /api/archive?id=...                  # 下载存档 JSON

GET /api/bootstrap  # {title, seed, live, provider, tree} —— 前端启动时拉取
GET /api/health     # 当前后端与是否已配置
GET /api/tree       # 当前完整的树（含你展开出来的部分）
```

页面会优先走 `/api/expand/stream`：叙事在面板里**逐字出现**，新子节点**边生成边长出来**；
后端不支持流式时自动回退到普通 `/api/expand`。

服务把树**保存在内存里**，所以刷新页面不会丢掉你长出来的分支。
结构仍然由确定性种子生成，LLM 只增加内容——这条边界不会被"续写"打破。

## 前后端分离

- **前端**：`cosmoforge/web/` 下的 `index.html` + `styles.css` + `app.js`。
  纯静态、无构建、无第三方运行时；所有数据通过 `fetch` 从 API 获取，
  启动时读取 `/api/bootstrap`。也可以把这三个文件放到任意静态服务器，
  用 `window.COSMOS_API_BASE = "http://<backend>"` 指向后端（API 已开 CORS）。
- **后端**：`serve.py` 只提供 JSON / SSE 接口，不再把数据渲染进 HTML：
  `/api/bootstrap`、`/api/tree`、`/api/health`、`/api/expand`、`/api/expand/stream`。
- **离线单文件**：`to_html()` 仍会把同一套前端资源与数据打包成一个 HTML，
  所以不跑服务也能打开、平移、缩放、看时间线（只有 LLM 展开按钮需要后端）。


## 安装与快速开始

> **跨平台**：需要 Python ≥ 3.9 + 现代浏览器，零第三方依赖。
> Windows / macOS / Linux / Android(Termux) / iOS 的差异与浏览器要求见
> [COMPATIBILITY.md](COMPATIBILITY.md)。

```bash
cd cosmoforge
pip install -e .            # 安装后可用 `cosmoforge` 命令
# 或免安装：
python -m cosmoforge demo --out cosmos.html --open

python -m cosmoforge demo --universes 6 --planets 3-6 --seed 7
python -m cosmoforge run examples/multiverse.json --out vela.html --json-out vela.json --md-out vela.md
python -m cosmoforge providers                 # 列出所有模型供应商
python -m cosmoforge serve --provider mock --open   # 带实时 LLM 展开/续写的本地服务
```

Python：

```python
from cosmoforge import Scenario, Cosmogenesis, to_html

scenario = Scenario.demo().with_overrides(universes=5, seed=2026)
cosmos = Cosmogenesis(scenario).run()

to_html(cosmos, path="cosmos.html")            # 输出 HTML 思维导图
print(cosmos.universes[0].planets[0].narrative)
```

## 多模型供应商

任何需要"叙事"的地方都能接模型。19 家内置后端，**零第三方依赖**（HTTP 走标准库 `urllib`）：

```bash
set COSMOFORGE_PROVIDER=deepseek
set DEEPSEEK_API_KEY=sk-...
python -m cosmoforge demo --narrator llm --language zh --out cosmos.html

python -m cosmoforge demo --narrator llm --provider anthropic
python -m cosmoforge demo --narrator llm --provider ollama --model llama3.2   # 本地、免密钥
```

| 类别 | 供应商 |
|---|---|
| OpenAI 协议 | `openai` `azure` `deepseek` `moonshot`(Kimi) `zhipu`(GLM) `dashscope`(Qwen) `mistral` `groq` `together` `openrouter` `xai` `fireworks` `perplexity` |
| 本地 / 自托管 | `ollama` `lmstudio` `vllm` |
| 原生协议 | `anthropic` `google`(Gemini) |
| 离线 | `mock`（确定性、免密钥，用于测试与演示） |

别名：`gpt→openai`、`claude→anthropic`、`gemini→google`、`qwen→dashscope`、`glm→zhipu`、`kimi→moonshot`、`local→ollama`、`offline/none→mock`。

**回退链**（多后端按序尝试，第一个可用者胜出）：

```python
from cosmoforge import resolve_providers, LLMNarrator, Cosmogenesis

provider = resolve_providers([
    {"provider": "anthropic", "model": "claude-3-5-sonnet-latest"},
    {"provider": "deepseek"},
    {"provider": "ollama"},          # 本地兜底
])
cosmos = Cosmogenesis(Scenario.demo(), narrator=LLMNarrator(provider)).run()
```

## 场景文件

```jsonc
{
  "name": "The Vela Branch",
  "seed": 2026,                 // 随机种子，决定一切结构
  "universes": 5,
  "branching": 0.4,             // 每个宇宙分支出子宇宙的概率
  "max_generation": 2,
  "law_sigma": 0.22,            // 物理常数采样标准差（越大越离奇）
  "planets_per_universe": [2, 6],
  "universe_events": [4, 8],
  "planet_events": [3, 6],
  "narrator": "rule",           // "rule" 或 "llm"
  "language": "en"              // LLM 叙事语言，例如 "zh"
}
```

## 目录结构

```
cosmoforge/
  models.py  lore.py  genesis.py  planets.py  events.py
  narrate.py  simulation.py  scenario.py  util.py
  providers/  base.py openai.py anthropic.py google.py ollama.py mock.py __init__.py
  render/     mindmap.py  markdown.py
  web/        index.html  styles.css  app.js   # 独立前端（无构建、无 CDN）
  serve.py            # 后端 API：bootstrap / expand / regenerate / 存档
  archives/           # 运行后生成的存档 JSON（默认位置）
  cli.py      __init__.py  __main__.py
examples/multiverse.json
tests/  test_cosmoforge.py  test_providers.py  test_serve.py
```

## 扩展

- **新增供应商**：继承 `OpenAICompatProvider` 只改 4 个类属性，或继承 `Provider` 实现 `_complete()`，再 `register_provider(...)`。
- **新增事件**：往 `lore.PLANET_EVENTS` / `lore.UNIVERSE_EVENTS` 加一条 `EventTemplate`（权重、严重度、时间窗、`min_habitability`、`unlock_biosphere`）。
- **新增叙事者**：实现 `Narrator` 的三个方法，传给 `Cosmogenesis(..., narrator=...)`。
- **新增命运 / 行星类型**：扩展 `models.DESTINIES` / `models.PLANET_TYPES`，并在 `genesis.destiny_from_laws` / `planets.KIND_WEIGHTS` 给出规则。

## 测试

```bash
python -m unittest discover -s tests -v
# 或
pytest tests
```

覆盖：确定性（同 seed 逐字节一致）、结构约束、事件门槛、
供应商注册/别名/解析、四种协议对本地桩服务器的请求-响应、回退链、
HTML 自包含性与 `<script>` 转义安全、时间线/缩放标记、
以及 `serve` 的 `/api/expand` 全链路（展开/续写/越界过滤/错误码）。

## 命名（待定）

显示名已定为 **模拟宇宙 / Simulated Universe**。
但标识符（`pip install` 名 + 命令行名）需要避开冲突——**PyPI 实测**：

| 候选 | PyPI 状态 | 说明 |
|---|---|---|
| `simuverse` | ❌ 已占 | 原定方案；官网/教育/医疗站多个同名 |
| `cosmoforge` | ❌ 已占 | 本仓库当前用的名字 |
| **`simverse`** | ✅ 空闲 | **推荐**：与你原定的 `simuverse` 几乎同音，命令 `simverse demo` 顺口 |
| `cosmogenesis` | ✅ 空闲 | 与引擎类 `Cosmogenesis` 同名，语义最贴「从大爆炸生成」，但较长 |
| `simuni` | ✅ 空闲 | 最短（simulated universe），风格直板 |
| `simcosmos` | ✅ 空闲 | 兼顾 sim + cosmos |

```bash
# 检查任意名字是否可用（404 = 空闲）
curl -s -o NUL -w "%{http_code}" https://pypi.org/pypi/<name>/json
```
