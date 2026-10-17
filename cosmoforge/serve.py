"""Backend API for the separate static front end (``cosmoforge/web/``).

The front end is plain HTML/CSS/JS and fetches everything from here, so it can
also be hosted on a different origin (CORS is enabled). The server exposes:

    GET  /api/bootstrap       title + seed + live flag + full tree
    GET  /api/tree            the tree alone (compatibility)
    GET  /api/health          provider status
    GET  /api/archives        saved archive index
    GET  /api/archive?id=...  download one archive JSON
    GET  /static/<asset>      app.js / styles.css for local development
    GET  /                    the app shell
    POST /api/regenerate      {"seed": n} rebuild the cosmos deterministically
    POST /api/save            {"name": "..."} save the whole tree to disk
    POST /api/load            {"id": "..."} replace the session from an archive

Browsers can't call model APIs directly — the key would be exposed and CORS
would block it. So this server also proxies model calls:

    POST /api/expand          {"id": "<node id>", "action": "expand" | "continue"}
    POST /api/expand/stream   the same request, streamed back as Server-Sent
                              Events (``phase`` → ``delta`` → ``node`` → ``done``)
                              so the page can type the prose and grow the tree live.

* ``expand``  — ask the model for new child nodes under this node (kinds are
  constrained by :data:`cosmoforge.render.mindmap.CHILD_KINDS`) plus a short
  chronicle line.
* ``continue`` — ask the model to keep writing this node's narrative.

The server keeps the tree in memory, so a page reload keeps everything you grew.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sys
import threading
import time
import uuid
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .models import MapNode, new_id, reserve_ids
from .narrate import extract_json
from .providers import ChatMessage, Provider, ProviderError, resolve
from .render.mindmap import CHILD_KINDS, WEB_DIR, build_tree, page_html

ID_PREFIX = {
    "root": "root",
    "bigbang": "bb",
    "epoch": "epoch",
    "universe": "uni",
    "planet": "pln",
    "event": "evt",
}

_SYSTEM = (
    "You are extending a generated cosmos inside an interactive atlas of "
    "parallel universes. The user clicked one node and asked you to grow it. "
    "Stay strictly consistent with the facts already given and with the node's "
    "own kind. Respect the physical scale: a universe cannot contain an epoch, "
    "a planet cannot contain a universe. "
    'Respond with ONLY a JSON object: {"narrative": "<one short paragraph that '
    'continues or enriches this node>", "children": [{"label": "<short title>", '
    '"kind": "<one of the allowed kinds>", "detail": "<1-2 sentences>", '
    '"meta": {"<key>": "<value>"}}]}. '
    "Return at most {max_children} children and use an empty list if nothing "
    "should be added."
)


def _sanitize_meta(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Any] = {}
    for key, value in list(raw.items())[:8]:
        if isinstance(value, (str, int, float, bool)):
            out[str(key)[:40]] = value if isinstance(value, str) else value
        else:
            out[str(key)[:40]] = str(value)[:120]
    return out


def _node_from_dict(raw: Any) -> MapNode:
    """Rebuild a :class:`MapNode` tree from archived JSON."""
    if not isinstance(raw, dict):
        raise ValueError("archive tree is malformed")
    meta = raw.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    node = MapNode(
        id=str(raw.get("id") or new_id("node")),
        label=str(raw.get("label", ""))[:200],
        kind=str(raw.get("kind", "event")),
        detail=str(raw.get("detail", "")),
        meta={str(key): value for key, value in meta.items()},
    )
    children = raw.get("children") or []
    if not isinstance(children, list):
        raise ValueError("archive children must be a list")
    node.children = [_node_from_dict(child) for child in children if isinstance(child, dict)]
    return node


def _collect_ids(node: MapNode) -> List[str]:
    ids = [node.id]
    for child in node.children:
        ids.extend(_collect_ids(child))
    return ids


def _count_nodes(node: MapNode) -> int:
    return 1 + sum(_count_nodes(child) for child in node.children)


class _State:
    """In-memory tree + provider; the single source of truth for the session."""

    def __init__(
        self,
        tree: MapNode,
        provider: Provider,
        title: str,
        scenario: Any = None,
        seed: Optional[int] = None,
        archive_dir: Any = None,
    ):
        self.tree = tree
        self.provider = provider
        self.title = title
        self.scenario = scenario
        self.seed = seed if seed is not None else getattr(scenario, "seed", None)
        base = (
            archive_dir
            or os.environ.get("COSMOFORGE_ARCHIVE_DIR")
            or (Path.cwd() / "archives")
        )
        self.archive_dir = Path(base)
        self.lock = threading.Lock()

    # -- payloads ---------------------------------------------------------
    def bootstrap(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "seed": self.seed,
            "live": True,
            "provider": self.provider.describe(),
            "tree": self.tree.as_dict(),
        }

    # -- generation -------------------------------------------------------
    def regenerate(self, seed: Any = None, universes: Any = None) -> Dict[str, Any]:
        """Rebuild the whole cosmos from a (possibly new) seed."""
        if self.scenario is None:
            raise ValueError("this server was started without a scenario")
        overrides: Dict[str, Any] = {}
        if seed is None or str(seed).strip() == "":
            seed = secrets.randbelow(1_000_000_000)
        try:
            seed = int(seed)
        except (TypeError, ValueError):
            raise ValueError("seed must be an integer")
        if seed < 0 or seed > 10**12:
            raise ValueError("seed must be between 0 and 10^12")
        overrides["seed"] = seed
        if universes is not None and str(universes).strip() != "":
            try:
                universes = int(universes)
            except (TypeError, ValueError):
                raise ValueError("universes must be an integer")
            if universes < 1 or universes > 24:
                raise ValueError("universes must be between 1 and 24")
            overrides["universes"] = universes
        scenario = self.scenario.with_overrides(**overrides)
        cosmos = scenario.build().run()
        self.tree = build_tree(cosmos)
        self.title = cosmos.name
        self.seed = cosmos.seed
        return self.bootstrap()

    # -- archives ---------------------------------------------------------
    def _archive_path(self, archive_id: str) -> Path:
        archive_id = str(archive_id or "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", archive_id):
            raise KeyError("invalid archive id")
        return self.archive_dir / (archive_id + ".json")

    def archive_bytes(self, archive_id: str) -> bytes:
        path = self._archive_path(archive_id)
        if not path.is_file():
            raise KeyError("archive not found")
        return path.read_bytes()

    def save_archive(self, name: Any = None) -> Dict[str, Any]:
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        archive_id = now.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        name = str(name or "").strip()[:80] or self.title
        payload = {
            "schema": 1,
            "id": archive_id,
            "name": name,
            "title": self.title,
            "seed": self.seed,
            "created": now.isoformat(timespec="seconds"),
            "nodes": _count_nodes(self.tree),
            "tree": self.tree.as_dict(),
        }
        path = self._archive_path(archive_id)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "id": archive_id,
            "name": name,
            "title": self.title,
            "seed": self.seed,
            "created": payload["created"],
            "nodes": payload["nodes"],
        }

    def list_archives(self, limit: int = 100) -> List[Dict[str, Any]]:
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        entries: List[Dict[str, Any]] = []
        paths = sorted(self.archive_dir.glob("*.json"), reverse=True)
        for path in paths:
            if len(entries) >= limit:
                break
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict) or not isinstance(data.get("tree"), dict):
                continue
            entries.append({
                "id": path.stem,
                "name": data.get("name") or data.get("title") or path.stem,
                "title": data.get("title") or "",
                "seed": data.get("seed"),
                "created": data.get("created") or "",
                "nodes": data.get("nodes") or 0,
            })
        return entries

    def load_archive(self, archive_id: str) -> Dict[str, Any]:
        path = self._archive_path(archive_id)
        if not path.is_file():
            raise KeyError("archive not found")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"cannot read archive: {exc}")
        tree = _node_from_dict(data.get("tree"))
        reserve_ids(_collect_ids(tree))
        self.tree = tree
        if data.get("title"):
            self.title = str(data["title"])[:200]
        seed = data.get("seed")
        if isinstance(seed, int):
            self.seed = seed
        return self.bootstrap()

    # -- lookup -----------------------------------------------------------
    def find(self, node_id: str) -> Tuple[Optional[MapNode], List[MapNode]]:
        stack: List[Tuple[MapNode, List[MapNode]]] = [(self.tree, [self.tree])]
        while stack:
            node, path = stack.pop()
            if node.id == node_id:
                return node, path
            for child in node.children:
                stack.append((child, path + [child]))
        return None, []

    # -- expansion --------------------------------------------------------
    def expand(self, node_id: str, action: str = "expand", max_children: int = 3) -> Dict[str, Any]:
        node, path = self.find(node_id)
        if node is None:
            raise KeyError(f"unknown node id: {node_id!r}")
        action = "continue" if str(action) == "continue" else "expand"
        allowed = list(CHILD_KINDS.get(node.kind, []))
        if action == "expand" and not allowed:
            raise KeyError(f"a {node.kind} node cannot be expanded")

        payload = {
            "cosmos": self.title,
            "path": [{"kind": n.kind, "label": n.label} for n in path],
            "node": {
                "kind": node.kind,
                "label": node.label,
                "detail": node.detail,
                "meta": node.meta,
            },
            "allowed_child_kinds": allowed,
            "max_children": max_children,
            "action": action,
        }
        system = _SYSTEM.replace("{max_children}", str(max_children))
        response = self.provider.complete(
            [ChatMessage("system", system), ChatMessage("user", json.dumps(payload, ensure_ascii=False, indent=2))],
            temperature=0.9,
            max_tokens=700,
        )
        data = extract_json(response.text)
        if not isinstance(data, dict):
            raise ProviderError("model did not return a JSON object")

        narrative = str(data.get("narrative", "")).strip()
        new_children: List[MapNode] = []
        if action == "expand":
            for item in (data.get("children") or [])[:max_children]:
                if not isinstance(item, dict):
                    continue
                kind = str(item.get("kind", "")).strip()
                if kind not in allowed:
                    continue
                label = str(item.get("label", "")).strip()[:80] or kind.title()
                child = MapNode(
                    id=new_id(ID_PREFIX.get(kind, "node")),
                    label=label,
                    kind=kind,
                    detail=str(item.get("detail", "")).strip()[:600],
                    meta=_sanitize_meta(item.get("meta")),
                )
                new_children.append(child)

        if narrative:
            node.detail = f"{node.detail}\n\n{narrative}".strip() if node.detail else narrative
        node.children.extend(new_children)

        return {
            "narrative": node.detail,
            "delta": narrative,
            "children": [c.as_dict() for c in new_children],
            "added": len(new_children),
            "provider": response.provider,
            "model": response.model,
        }


class _Handler(BaseHTTPRequestHandler):
    state: _State = None  # type: ignore[assignment]
    server_version = "Cosmoforge/0.1"

    # -- helpers ----------------------------------------------------------
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _send(
        self,
        code: int,
        body: Any,
        ctype: str = "application/json",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self._cors()
        self.end_headers()
        if data:
            self.wfile.write(data)

    def _error(self, code: int, message: str) -> None:
        self._send(code, json.dumps({"error": message}, ensure_ascii=False))

    # -- routes -----------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 - http.server API
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, page_html(self.state.title), "text/html")
        elif path == "/api/bootstrap":
            self._send(200, json.dumps(self.state.bootstrap(), ensure_ascii=False))
        elif path == "/api/tree":
            self._send(200, json.dumps(self.state.tree.as_dict(), ensure_ascii=False))
        elif path == "/api/archives":
            archives = self.state.list_archives()
            self._send(200, json.dumps({"archives": archives}, ensure_ascii=False))
        elif path == "/api/archive":
            query = parse_qs(urlparse(self.path).query)
            archive_id = (query.get("id") or [""])[0]
            try:
                data = self.state.archive_bytes(archive_id)
            except KeyError as exc:
                self._error(404, str(exc))
                return
            self._send(
                200, data, "application/json",
                headers={"Content-Disposition": f'attachment; filename="{archive_id}.json"'},
            )
        elif path == "/api/health":
            self._send(200, json.dumps({"ok": True, "provider": self.state.provider.describe()}))
        elif path.startswith("/static/"):
            name = path[len("/static/"):]
            types = {"app.js": "text/javascript", "styles.css": "text/css"}
            if name not in types:
                self._error(404, "not found")
                return
            try:
                data = (WEB_DIR / name).read_bytes()
            except OSError:
                self._error(404, "not found")
                return
            self._send(200, data, types[name])
        elif path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        else:
            self._error(404, "not found")

    def do_OPTIONS(self) -> None:  # noqa: N802 - http.server API
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    # -- streaming (server-sent events) -----------------------------------
    def _sse(self, event: str, data: Any) -> None:
        chunk = (
            f"event: {event}\n"
            f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        )
        self.wfile.write(chunk.encode("utf-8"))
        self.wfile.flush()

    def _stream_expand(self, payload: Dict[str, Any]) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self._cors()
        self.end_headers()
        self.close_connection = True
        self._sse("phase", {"message": "connecting"})
        try:
            self._sse("phase", {"message": "thinking"})
            with self.state.lock:
                result = self.state.expand(
                    str(payload.get("id", "")),
                    str(payload.get("action", "expand")),
                )
            delta = str(result.get("delta") or "")
            if delta:
                self._sse("phase", {"message": "writing"})
                for i in range(0, len(delta), 3):
                    self._sse("delta", {"text": delta[i:i + 3]})
                    time.sleep(0.018)
            for child in result.get("children") or []:
                self._sse("node", child)
                time.sleep(0.05)
            self._sse("done", {
                "narrative": result.get("narrative", ""),
                "added": result.get("added", 0),
                "provider": result.get("provider", ""),
                "model": result.get("model", ""),
            })
        except KeyError as exc:
            self._sse("error", {"error": str(exc)})
        except ProviderError as exc:
            self._sse("error", {"error": str(exc)})
        except ValueError as exc:
            self._sse("error", {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - report over the stream
            self._sse("error", {"error": f"{type(exc).__name__}: {exc}"})

    def _read_json(self) -> Optional[Dict[str, Any]]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            self._error(400, "invalid JSON body")
            return None
        if not isinstance(payload, dict):
            self._error(400, "JSON body must be an object")
            return None
        return payload

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        path = self.path.split("?", 1)[0]
        routes = {
            "/api/expand", "/api/expand/stream",
            "/api/regenerate", "/api/save", "/api/load",
        }
        if path not in routes:
            self._error(404, "not found")
            return
        payload = self._read_json()
        if payload is None:
            return
        if path == "/api/expand/stream":
            self._stream_expand(payload)
            return
        try:
            with self.state.lock:
                if path == "/api/expand":
                    result = self.state.expand(
                        str(payload.get("id", "")),
                        str(payload.get("action", "expand")),
                    )
                elif path == "/api/regenerate":
                    result = self.state.regenerate(
                        payload.get("seed"), payload.get("universes")
                    )
                elif path == "/api/save":
                    result = self.state.save_archive(payload.get("name"))
                else:
                    result = self.state.load_archive(str(payload.get("id", "")))
            self._send(200, json.dumps(result, ensure_ascii=False))
        except KeyError as exc:
            self._error(400, str(exc))
        except ProviderError as exc:
            self._error(502, str(exc))
        except ValueError as exc:
            self._error(502 if path == "/api/expand" else 400, str(exc))
        except OSError as exc:
            self._error(500, str(exc))
        except Exception as exc:  # noqa: BLE001 - never kill the server
            self._error(500, f"{type(exc).__name__}: {exc}")

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter logging
        sys.stderr.write("[cosmoforge] " + (fmt % args) + "\n")


def make_server(
    scenario,
    provider_spec: Any = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    title: Optional[str] = None,
    archive_dir: Any = None,
):
    """Build a ready-to-serve (server, state) pair without blocking."""
    cosmos = scenario.build().run()
    tree = build_tree(cosmos)
    provider = resolve(provider_spec)
    state = _State(
        tree, provider, title or cosmos.name,
        scenario=scenario, seed=cosmos.seed, archive_dir=archive_dir,
    )
    handler = type("BoundHandler", (_Handler,), {"state": state})
    server = ThreadingHTTPServer((host, port), handler)
    return server, state


def serve(
    scenario,
    provider_spec: Any = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    title: Optional[str] = None,
    open_browser: bool = False,
    archive_dir: Any = None,
) -> int:
    """Run the live server until interrupted."""
    server, state = make_server(scenario, provider_spec, host, port, title, archive_dir)
    url = f"http://{host}:{server.server_address[1]}/"
    descriptor = state.provider.describe()
    print(f"cosmoforge serve → {url}")
    print(f"  node provider: {descriptor.get('provider')} / {descriptor.get('model')} "
          f"(configured: {descriptor.get('configured')})")
    print(f"  structure: {state.title} — click expand / continue in the page")
    print(f"  archives: {state.archive_dir}")
    print("  Ctrl+C to stop")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping…")
    finally:
        server.server_close()
    return 0


__all__ = ["serve", "make_server"]
