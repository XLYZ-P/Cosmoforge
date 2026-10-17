"""Interactive HTML mind map.

The front end is a plain static app (``cosmoforge/web/``: ``index.html``,
``styles.css``, ``app.js``). It loads its data from the backend API
(``/api/bootstrap``) and talks to the live-generation endpoints over ``fetch``.
Nothing is templated into the page at request time, so the same assets can be
hosted on any static server.

For offline use, :func:`to_html` still bundles those assets plus a
``window.COSMOS_BOOTSTRAP`` payload into one self-contained HTML file — no CDN,
no build step, opens straight from disk.

In the browser:

* a tidy, foldable tree layout for the mind map;
* a **timeline** panel (log-scale Big Bang strip + linear Gyr event axis,
  with playback);
* **live expansion**: ``expand`` / ``continue`` streamed from ``/api/expand/stream``
  so prose appears character by character and child nodes grow in place.

Layout is computed in the browser so nodes fold and unfold without a Python
round-trip.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import Cosmos, DESTINIES, LAW_HELP, MapNode, format_age

KIND_ICONS = {
    "root": "✦",
    "bigbang": "✷",
    "epoch": "·",
    "universe": "◆",
    "planet": "●",
    "event": "▲",
}

#: Kinds an LLM is allowed to add underneath a given kind (server-side guard).
CHILD_KINDS: Dict[str, List[str]] = {
    "root": ["universe"],
    "bigbang": ["epoch"],
    "universe": ["planet", "event"],
    "planet": ["event"],
    "event": ["event"],
    "epoch": [],
}

#: Directory with the static front end (index.html / styles.css / app.js).
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

_ASSET_NAMES = ("index.html", "styles.css", "app.js")
_STYLE_TAG = '<link rel="stylesheet" href="/static/styles.css" />'
_SCRIPT_TAG = '<script src="/static/app.js"></script>'


@lru_cache(maxsize=None)
def asset_text(name: str) -> str:
    """Return a static front-end asset, cached in memory."""
    return (WEB_DIR / name).read_text(encoding="utf-8")


def page_html(title: str) -> str:
    """The static app shell with the title filled in (assets stay external)."""
    import html as _html

    safe_title = _html.escape(title or "Cosmos", quote=True).replace("<", "&lt;")
    return asset_text("index.html").replace("__TITLE__", safe_title)


def _event_node(event, planet_id: Optional[str] = None) -> MapNode:
    return MapNode(
        id=event.id,
        label=event.title,
        kind="event",
        detail=event.description,
        meta={
            "age": f"{event.age_gyr:.2f} Gyr",
            "age_gyr": round(event.age_gyr, 3),
            "severity": round(event.severity, 2),
            "scope": event.scope,
            "tags": ", ".join(event.tags) if event.tags else "—",
        },
    )


def _planet_node(planet) -> MapNode:
    gas = max(planet.atmosphere, key=planet.atmosphere.get) if planet.atmosphere else "none"
    meta: Dict[str, Any] = {
        "kind": planet.kind.replace("_", " "),
        "orbit": f"{planet.orbit_au:g} AU",
        "gravity": f"{planet.gravity_g:g} g",
        "temperature": f"{planet.temperature_k:.0f} K",
        "atmosphere": gas,
        "habitability": round(planet.habitability, 2),
        "biosphere": planet.biosphere,
        "moons": planet.moons,
    }
    if planet.civilization:
        meta["civilization"] = planet.civilization
    node = MapNode(
        id=planet.id,
        label=planet.name,
        kind="planet",
        detail=planet.narrative,
        meta=meta,
    )
    node.children = [_event_node(e, planet.id) for e in planet.events]
    return node


def _universe_node(universe) -> MapNode:
    meta: Dict[str, Any] = {
        "generation": universe.generation,
        "destiny": universe.destiny.replace("_", " "),
        "age": f"{universe.age_gyr:.1f} Gyr",
        "age_gyr": round(universe.age_gyr, 3),
        "habitability": round(universe.habitability, 2),
        "expansion": round(universe.expansion_rate, 2),
        "worlds": len(universe.planets),
    }
    for key, value in universe.laws.items():
        meta[key] = value
    node = MapNode(
        id=universe.id,
        label=universe.name,
        kind="universe",
        detail=universe.narrative,
        meta=meta,
    )
    node.children = [_planet_node(p) for p in universe.planets]
    node.children += [_event_node(e) for e in universe.events]
    return node


def _epoch_node(epoch) -> MapNode:
    return MapNode(
        id=f"epoch:{epoch.name}",
        label=epoch.name,
        kind="epoch",
        detail=epoch.summary,
        meta={
            "age": format_age(epoch.age_years),
            "age_years": epoch.age_years,
            "temperature": f"{epoch.temperature_k:.0e} K",
        },
    )


def build_tree(cosmos: Cosmos) -> MapNode:
    """Turn a :class:`Cosmos` into the tree the renderer draws."""
    root = MapNode(
        id="root",
        label=cosmos.name,
        kind="root",
        detail=(
            f"A cosmos of {len(cosmos.universes)} parallel universes and "
            f"{len(cosmos.planets)} worlds, generated from seed {cosmos.seed}."
        ),
        meta={
            "seed": cosmos.seed,
            "universes": len(cosmos.universes),
            "planets": len(cosmos.planets),
            "events": cosmos.event_count,
            "provider": cosmos.provider or "rule",
            "model": cosmos.model or "—",
        },
    )

    big_bang = MapNode(
        id="bigbang",
        label="Big Bang",
        kind="bigbang",
        detail=cosmos.big_bang.narrative,
        meta={"epochs": len(cosmos.big_bang.epochs), "seed": cosmos.seed},
    )
    big_bang.children = [_epoch_node(e) for e in cosmos.big_bang.epochs]
    root.children.append(big_bang)
    root.children.extend(_universe_node(u) for u in cosmos.universes)
    return root


def tree_to_html(tree: MapNode, title: str, live: bool = False) -> str:
    """Render an already-built :class:`MapNode` tree to a self-contained page.

    The static front-end assets are inlined so the result works from ``file://``
    with no server. The data is injected as ``window.COSMOS_BOOTSTRAP``.
    """
    payload = json.dumps(
        {"tree": tree.as_dict(), "title": title, "live": bool(live)},
        ensure_ascii=False,
    ).replace("<", "\\u003c")
    html = page_html(title)
    html = html.replace(
        _STYLE_TAG, "<style>\n" + asset_text("styles.css") + "\n</style>"
    )
    html = html.replace(
        _SCRIPT_TAG,
        "<script>window.COSMOS_BOOTSTRAP = " + payload + ";</script>\n"
        "<script>\n" + asset_text("app.js") + "\n</script>",
    )
    return html


def to_html(
    cosmos: Cosmos,
    title: Optional[str] = None,
    path: Optional[str] = None,
    live: bool = False,
) -> str:
    """Render ``cosmos`` as a self-contained HTML mind map.

    Returns the HTML string; also writes it to ``path`` when given.
    ``live=True`` enables the on-demand LLM expand/continue buttons (only useful
    when the page is served by ``cosmoforge serve``).
    """
    html = tree_to_html(build_tree(cosmos), title or cosmos.name, live=live)
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
    return html


__all__ = [
    "build_tree",
    "to_html",
    "tree_to_html",
    "page_html",
    "asset_text",
    "WEB_DIR",
    "KIND_ICONS",
    "CHILD_KINDS",
]
