"""Command line interface: `cosmoforge run script.json` / `cosmoforge demo`."""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from typing import List, Optional, Tuple

from .providers import available as available_providers
from .render import to_html, to_markdown
from .scenario import Scenario


def _force_utf8_console() -> None:
    """Windows consoles often default to GBK/cp1252; never crash on unicode."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover - non-tty
            pass


def _parse_range(text: Optional[str]) -> Optional[Tuple[int, int]]:
    if not text:
        return None
    cleaned = text.replace(",", "-")
    if "-" in cleaned:
        low, high = cleaned.split("-", 1)
        return (int(low), int(high))
    value = int(cleaned)
    return (value, value)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cosmoforge",
        description="Cosmoforge: generate a cosmos from the Big Bang — parallel "
                    "universes, planets and random events — and render it as an "
                    "interactive HTML mind map.",
    )
    sub = parser.add_subparsers(dest="command")

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--seed", type=int, default=None, help="override the RNG seed")
        p.add_argument("--universes", type=int, default=None,
                       help="number of root universes")
        p.add_argument("--branching", type=float, default=None,
                       help="chance a universe spawns a child branch (0-1)")
        p.add_argument("--max-generation", type=int, default=None,
                       help="how many extra generations of branches to allow")
        p.add_argument("--planets", default=None,
                       help="planets per universe, e.g. 2-5 or 3")
        p.add_argument("--narrator", choices=["rule", "llm"], default=None,
                       help="prose engine (default: scenario)")
        p.add_argument("--provider", default=None,
                       help="model provider for the llm narrator (see `cosmoforge providers`)")
        p.add_argument("--model", default=None, help="model name override")
        p.add_argument("--language", default=None, help="narration language, e.g. zh or en")
        p.add_argument("--out", default=None, help="write the HTML mind map here")
        p.add_argument("--json-out", default=None, help="write the raw JSON cosmos here")
        p.add_argument("--md-out", default=None, help="write a markdown outline here")
        p.add_argument("--open", action="store_true",
                       help="open the HTML mind map in the default browser")
        p.add_argument("--quiet", action="store_true", help="do not print the summary")

    run_p = sub.add_parser("run", help="run a JSON scenario file")
    run_p.add_argument("scenario", help="path to a scenario .json file")
    common(run_p)

    demo_p = sub.add_parser("demo", help="run the built-in multiverse demo")
    common(demo_p)

    serve_p = sub.add_parser(
        "serve",
        help="serve the mind map with live LLM expand/continue (/api/expand)",
    )
    serve_p.add_argument("scenario", nargs="?", default=None,
                         help="optional scenario .json file (defaults to the demo)")
    serve_p.add_argument("--host", default="127.0.0.1", help="bind address")
    serve_p.add_argument("--port", type=int, default=8765, help="port")
    serve_p.add_argument("--seed", type=int, default=None)
    serve_p.add_argument("--universes", type=int, default=None)
    serve_p.add_argument("--planets", default=None,
                         help="planets per universe, e.g. 2-5 or 3")
    serve_p.add_argument("--branching", type=float, default=None)
    serve_p.add_argument("--provider", default=None,
                         help="model provider used for live expansion")
    serve_p.add_argument("--model", default=None)
    serve_p.add_argument("--title", default=None, help="override the map title")
    serve_p.add_argument("--archive-dir", default=None,
                         help="where saved archives live (default: ./archives)")
    serve_p.add_argument("--open", action="store_true", help="open a browser")

    sub.add_parser("providers", help="list registered model providers")
    return parser


def _print_providers() -> int:
    rows = available_providers()
    print(f"{len(rows)} providers registered\n")
    header = f"{'provider':<14} {'model':<38} {'key env':<28} default base url"
    print(header)
    print("-" * len(header))
    for row in rows:
        env = ", ".join(row["api_key_env"]) or "(none)"
        print(
            f"{row['provider']:<14} {row['default_model']:<38} {env:<28} {row['base_url']}"
        )
    print("\nAliases: " + ", ".join(f"{k}->{v}" for k, v in sorted(_aliases().items()) if k))
    print("\nSet COSMOFORGE_PROVIDER / COSMOFORGE_MODEL / COSMOFORGE_API_KEY to pick a default.")
    return 0


def _aliases():
    from .providers import ALIASES

    return ALIASES


def _run(args: argparse.Namespace) -> int:
    if args.command == "run":
        try:
            scenario = Scenario.from_file(args.scenario)
        except FileNotFoundError:
            print(f"error: scenario not found: {args.scenario}", file=sys.stderr)
            return 2
        except json.JSONDecodeError as exc:
            print(f"error: invalid JSON in {args.scenario}: {exc}", file=sys.stderr)
            return 2
    else:
        scenario = Scenario.demo()

    overrides = {
        "seed": args.seed,
        "universes": args.universes,
        "branching": args.branching,
        "max_generation": args.max_generation,
        "narrator": args.narrator,
        "provider": args.provider,
        "model": args.model,
        "language": args.language,
    }
    planets = _parse_range(args.planets)
    if planets is not None:
        overrides["planets_per_universe"] = planets
    scenario = scenario.with_overrides(**overrides)

    try:
        engine = scenario.build()
        cosmos = engine.run()
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - surface a clean message
        print(f"error: simulation failed: {exc}", file=sys.stderr)
        return 1

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(cosmos.as_dict(), fh, ensure_ascii=False, indent=2)
        print(f"json written to {args.json_out}")

    if args.md_out:
        with open(args.md_out, "w", encoding="utf-8") as fh:
            fh.write(to_markdown(cosmos))
        print(f"markdown written to {args.md_out}")

    html_path = args.out
    if html_path:
        to_html(cosmos, path=html_path)
        print(f"mind map written to {html_path}")
        if args.open:
            webbrowser.open(html_path)

    if not args.quiet:
        if args.out:
            print(_summary(cosmos))
        else:
            print("\n" + to_markdown(cosmos))
    return 0


def _summary(cosmos) -> str:
    lines = [
        "",
        f"{cosmos.name} — {len(cosmos.universes)} universes, "
        f"{len(cosmos.planets)} planets, {cosmos.event_count} events "
        f"(seed {cosmos.seed})",
    ]
    for universe in cosmos.universes:
        lines.append(
            f"  ◆ {universe.name:<16} habitability {universe.habitability:.2f}  "
            f"destiny {universe.destiny:<18} worlds {len(universe.planets)}"
        )
    return "\n".join(lines)


def _serve(args: argparse.Namespace) -> int:
    from .serve import serve

    if args.scenario:
        try:
            scenario = Scenario.from_file(args.scenario)
        except FileNotFoundError:
            print(f"error: scenario not found: {args.scenario}", file=sys.stderr)
            return 2
        except json.JSONDecodeError as exc:
            print(f"error: invalid JSON in {args.scenario}: {exc}", file=sys.stderr)
            return 2
    else:
        scenario = Scenario.demo()

    overrides = {
        "seed": args.seed,
        "universes": args.universes,
        "branching": args.branching,
    }
    planets = _parse_range(args.planets)
    if planets is not None:
        overrides["planets_per_universe"] = planets
    scenario = scenario.with_overrides(**overrides)

    provider_spec = None
    if args.provider is not None or args.model is not None:
        provider_spec = {"provider": args.provider or "", "model": args.model}
    return serve(
        scenario,
        provider_spec,
        host=args.host,
        port=args.port,
        title=args.title,
        open_browser=args.open,
        archive_dir=args.archive_dir,
    )


def main(argv: Optional[List[str]] = None) -> int:
    _force_utf8_console()
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        args.command = "demo"
        # default: write the mind map so the command always produces the artifact
        for field, value in (
            ("seed", None), ("universes", None), ("branching", None),
            ("max_generation", None), ("planets", None), ("narrator", None),
            ("provider", None), ("model", None), ("language", None),
            ("out", "cosmos.html"), ("json_out", None), ("md_out", None),
            ("open", False), ("quiet", True),
        ):
            setattr(args, field, value)

    if args.command == "providers":
        return _print_providers()
    if args.command == "serve":
        return _serve(args)
    return _run(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
