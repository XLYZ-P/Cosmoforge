# Cosmoforge releases

## `cosmoforge-0.1.0.tar.gz`

标准 Python 源码分发包（**sdist**），与操作系统和 CPU 架构无关。

安装：

```bash
pip install cosmoforge-0.1.0.tar.gz
```

或解压后直接运行（免安装）：

```bash
tar xzf cosmoforge-0.1.0.tar.gz
cd cosmoforge-0.1.0
python -m unittest discover -s tests -v   # 43 passed
python -m cosmoforge demo --out cosmos.html --open
```

包内包含：

- 完整的 `cosmoforge/` Python 包（零第三方依赖，Python ≥ 3.9）
- 独立前端 `cosmoforge/web/`（`index.html` + `styles.css` + `app.js`）
- 测试 `tests/` 与示例 `examples/multiverse.json`
- `COMPATIBILITY.md`（跨平台说明）

校验：

```bash
sha256sum -c SHA256SUMS
```

> 这是构建产物，请勿直接修改；源码改动后重新运行 `python -m build --sdist --wheel`。
