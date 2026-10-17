"""Markdown outline of a cosmos (the terminal-friendly sibling of the mind map)."""
from __future__ import annotations

from typing import List

from ..models import Cosmos, DESTINY_HELP


def to_markdown(cosmos: Cosmos) -> str:
    lines: List[str] = []
    w = lines.append

    w(f"# {cosmos.name} — Cosmos Report")
    w("")
    w(
        f"- Seed: `{cosmos.seed}` · Universes: **{len(cosmos.universes)}** · "
        f"Planets: **{len(cosmos.planets)}** · Events: **{cosmos.event_count}**"
    )
    if cosmos.provider:
        w(f"- Narrator: `{cosmos.provider}` / `{cosmos.model}`")
    w("")

    w("## Big Bang")
    w("")
    if cosmos.big_bang.narrative:
        w(f"> {cosmos.big_bang.narrative}")
        w("")
    w("| epoch | age | temperature |")
    w("|---|---|---|")
    for epoch in cosmos.big_bang.epochs:
        w(f"| {epoch.name} | {epoch.as_dict()['age']} | {epoch.as_dict()['temperature']} |")
    w("")

    w("## Universes")
    w("")
    for universe in cosmos.universes:
        w(f"### {universe.name}")
        w("")
        laws = ", ".join(f"{k} {v:g}" for k, v in universe.laws.items())
        w(
            f"- Laws: {laws} · Destiny: **{universe.destiny.replace('_', ' ')}** "
            f"({DESTINY_HELP.get(universe.destiny, '')})"
        )
        w(
            f"- Habitability **{universe.habitability:.2f}** · Age "
            f"**{universe.age_gyr:.1f} Gyr** · Generation {universe.generation} · "
            f"Worlds {len(universe.planets)}"
        )
        if universe.narrative:
            w(f"- _{universe.narrative}_")
        w("")
        if universe.events:
            w("**Universe events**")
            w("")
            for event in universe.events:
                w(f"- `{event.age_gyr:.2f} Gyr` — **{event.title}** ({event.severity:.2f}) — {event.description}")
            w("")
        for planet in universe.planets:
            w(f"#### {planet.name}")
            w("")
            gas = max(planet.atmosphere, key=planet.atmosphere.get) if planet.atmosphere else "none"
            w(
                f"- Kind: {planet.kind.replace('_', ' ')} · Orbit {planet.orbit_au:g} AU · "
                f"Gravity {planet.gravity_g:g}g · Temp {planet.temperature_k:.0f} K · "
                f"Atmosphere: {gas}-dominant · Moons {planet.moons}"
            )
            w(
                f"- Habitability **{planet.habitability:.2f}** · Biosphere **{planet.biosphere}**"
                + (f" · Civilization: **{planet.civilization}**" if planet.civilization else "")
            )
            if planet.narrative:
                w(f"- _{planet.narrative}_")
            w("")
            if planet.events:
                for event in planet.events:
                    w(f"  - `{event.age_gyr:.2f} Gyr` — **{event.title}** ({event.severity:.2f}) — {event.description}")
                w("")
    return "\n".join(lines)


__all__ = ["to_markdown"]
