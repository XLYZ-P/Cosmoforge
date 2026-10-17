"""Core data structures for the Cosmoforge universe generator."""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

SECONDS_PER_YEAR = 31_557_600.0

_counter = itertools.count(1)


def new_id(prefix: str) -> str:
    return f"{prefix}:{next(_counter):04d}"


def reset_ids() -> None:
    """Restart the id sequence so a seeded run produces identical identifiers."""
    global _counter
    _counter = itertools.count(1)


def reserve_ids(existing_ids) -> None:
    """Continue the id sequence above every numeric suffix already in use.

    Used after loading an archive: newly generated nodes must never collide with
    identifiers that came from disk.
    """
    global _counter
    highest = 0
    for node_id in existing_ids:
        tail = str(node_id).rsplit(":", 1)[-1]
        if tail.isdigit():
            highest = max(highest, int(tail))
    _counter = itertools.count(highest + 1)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def roman(number: int) -> str:
    numerals = (
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    )
    out = []
    for value, glyph in numerals:
        while number >= value:
            out.append(glyph)
            number -= value
    return "".join(out) or "0"


def format_age(years: float) -> str:
    """Human-readable cosmic age, from the Planck time to gigayears."""
    seconds = float(years) * SECONDS_PER_YEAR
    if seconds < 1.0:
        return f"{seconds:.0e} s"
    if seconds < 60.0:
        return f"{seconds:.1f} s"
    if seconds < 3600.0:
        return f"{seconds / 60.0:.1f} min"
    if seconds < 86400.0:
        return f"{seconds / 3600.0:.1f} h"
    if years < 1.0:
        return f"{seconds / 86400.0:.1f} d"
    if years < 1e3:
        return f"{years:.0f} yr"
    if years < 1e6:
        return f"{years / 1e3:.1f} kyr"
    if years < 1e9:
        return f"{years / 1e6:.1f} Myr"
    return f"{years / 1e9:.2f} Gyr"


def format_temperature(kelvin: float) -> str:
    if kelvin >= 1e6:
        return f"{kelvin:.0e} K"
    if kelvin >= 1e4:
        return f"{kelvin:.0f} K"
    return f"{kelvin:.0f} K"


#: Physical constants every universe samples around 1.0 ("our" universe).
LAW_KEYS = ("gravity", "strong_force", "dark_energy", "entropy", "dimensions")

LAW_HELP = {
    "gravity": "Strength of the gravitational coupling.",
    "strong_force": "Strength of the strong nuclear force.",
    "dark_energy": "Vacuum energy driving accelerated expansion.",
    "entropy": "The rate at which order decays into disorder.",
    "dimensions": "Number of large spatial dimensions.",
}

PLANET_KINDS = (
    "terrestrial", "oceanic", "desert", "ice", "lava",
    "carbon", "gas_giant", "rogue",
)

BIOSPHERES = ("sterile", "prebiotic", "microbial", "multicellular", "complex", "sapient")

DESTINIES = (
    "heat_death", "big_rip", "big_crunch",
    "big_bounce", "vacuum_decay", "eternal_stagnation",
)

DESTINY_HELP = {
    "heat_death": "Expansion wins; the cosmos cools toward maximum entropy.",
    "big_rip": "Dark energy tears every bound structure apart.",
    "big_crunch": "Gravity reverses expansion; everything collapses again.",
    "big_bounce": "Collapse overshoots into a fresh inflationary rebound.",
    "vacuum_decay": "A false vacuum bubble rewrites the laws from within.",
    "eternal_stagnation": "A frozen, low-energy equilibrium that never meaningfully changes.",
}

EVENT_SCOPES = ("universe", "planet")


@dataclass
class Epoch:
    """One phase of the early universe, anchored to cosmic time."""

    name: str
    age_years: float
    temperature_k: float
    summary: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "age": format_age(self.age_years),
            "age_years": self.age_years,
            "temperature": format_temperature(self.temperature_k),
            "summary": self.summary,
        }


@dataclass
class BigBang:
    """The shared origin: the timeline every branch descends from."""

    seed: int = 0
    epochs: List[Epoch] = field(default_factory=list)
    narrative: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "epochs": [e.as_dict() for e in self.epochs],
            "narrative": self.narrative,
        }


@dataclass
class Event:
    """A single random happening on a universe or planet timeline."""

    kind: str
    title: str
    description: str
    age_gyr: float
    severity: float = 0.5
    scope: str = "planet"
    planet_id: Optional[str] = None
    unlocks: str = ""      # biosphere stage this event raises a planet to
    tags: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("evt"))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "description": self.description,
            "age": f"{self.age_gyr:.2f} Gyr",
            "age_gyr": round(self.age_gyr, 3),
            "severity": round(self.severity, 3),
            "scope": self.scope,
            "planet_id": self.planet_id,
            "unlocks": self.unlocks,
            "tags": list(self.tags),
        }


@dataclass
class Planet:
    """A world inside a universe."""

    name: str
    universe_id: str
    kind: str = "terrestrial"
    orbit_au: float = 1.0
    mass_earth: float = 1.0
    radius_km: float = 6371.0
    gravity_g: float = 1.0
    temperature_k: float = 288.0
    atmosphere: Dict[str, float] = field(default_factory=dict)
    habitability: float = 0.0
    biosphere: str = "sterile"
    civilization: Optional[str] = None
    moons: int = 0
    events: List[Event] = field(default_factory=list)
    narrative: str = ""
    index: int = 0
    id: str = field(default_factory=lambda: new_id("pln"))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "universe_id": self.universe_id,
            "kind": self.kind,
            "orbit_au": round(self.orbit_au, 3),
            "mass_earth": round(self.mass_earth, 3),
            "radius_km": round(self.radius_km, 1),
            "gravity_g": round(self.gravity_g, 3),
            "temperature": format_temperature(self.temperature_k),
            "temperature_k": round(self.temperature_k, 1),
            "atmosphere": {k: round(v, 3) for k, v in self.atmosphere.items()},
            "habitability": round(self.habitability, 3),
            "biosphere": self.biosphere,
            "civilization": self.civilization,
            "moons": self.moons,
            "narrative": self.narrative,
            "events": [e.as_dict() for e in self.events],
        }


@dataclass
class Universe:
    """A parallel branch of the cosmos with its own physical constants."""

    name: str
    index: int
    laws: Dict[str, float] = field(default_factory=dict)
    destiny: str = "heat_death"
    age_gyr: float = 13.8
    habitability: float = 0.0
    expansion_rate: float = 1.0
    generation: int = 0
    parent_id: Optional[str] = None
    seed: int = 0
    planets: List[Planet] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    narrative: str = ""
    id: str = field(default_factory=lambda: new_id("uni"))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "index": self.index,
            "generation": self.generation,
            "parent_id": self.parent_id,
            "seed": self.seed,
            "laws": {k: round(v, 3) for k, v in self.laws.items()},
            "destiny": self.destiny,
            "age_gyr": round(self.age_gyr, 3),
            "habitability": round(self.habitability, 3),
            "expansion_rate": round(self.expansion_rate, 3),
            "narrative": self.narrative,
            "planets": [p.as_dict() for p in self.planets],
            "events": [e.as_dict() for e in self.events],
        }


@dataclass
class Cosmos:
    """The finished artifact: one Big Bang plus every branch it produced."""

    name: str
    seed: int
    big_bang: BigBang
    universes: List[Universe] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    provider: Optional[str] = None
    model: Optional[str] = None
    narration: Dict[str, Any] = field(default_factory=dict)

    @property
    def planets(self) -> List[Planet]:
        return [p for u in self.universes for p in u.planets]

    @property
    def event_count(self) -> int:
        return sum(len(u.events) for u in self.universes) + sum(
            len(p.events) for p in self.planets
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "seed": self.seed,
            "provider": self.provider,
            "model": self.model,
            "config": self.config,
            "narration": self.narration,
            "big_bang": self.big_bang.as_dict(),
            "universes": [u.as_dict() for u in self.universes],
        }


@dataclass
class MapNode:
    """A node in the mind-map tree (renderer-facing, not domain state)."""

    id: str
    label: str
    kind: str
    detail: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)
    children: List["MapNode"] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "detail": self.detail,
            "meta": self.meta,
            "children": [c.as_dict() for c in self.children],
        }


__all__ = [
    "SECONDS_PER_YEAR",
    "new_id",
    "reset_ids",
    "reserve_ids",
    "clamp",
    "lerp",
    "roman",
    "format_age",
    "format_temperature",
    "LAW_KEYS",
    "LAW_HELP",
    "PLANET_KINDS",
    "BIOSPHERES",
    "DESTINIES",
    "DESTINY_HELP",
    "EVENT_SCOPES",
    "Epoch",
    "BigBang",
    "Event",
    "Planet",
    "Universe",
    "Cosmos",
    "MapNode",
]
