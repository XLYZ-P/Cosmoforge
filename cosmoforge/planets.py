"""Planet formation inside a universe.

Every property is derived, not invented: kind flows from a weighted draw, orbit
and kind set equilibrium temperature, temperature and gravity set habitability,
and habitability gates which biosphere a world starts with.
"""
from __future__ import annotations

import random
from typing import Dict, List, Sequence

from .genesis import planets_supported
from .lore import CIVILIZATION_STYLES, GASES, PLANET_PREFIXES, PLANET_SUFFIXES, biosphere_rank
from .models import Planet, Universe, clamp, roman
from .util import log_uniform, weighted_choice

KIND_WEIGHTS: Dict[str, float] = {
    "terrestrial": 2.2,
    "oceanic": 1.1,
    "desert": 1.3,
    "ice": 1.2,
    "lava": 0.9,
    "carbon": 0.6,
    "gas_giant": 1.6,
    "rogue": 0.5,
}

KIND_HABITABILITY: Dict[str, float] = {
    "terrestrial": 0.95,
    "oceanic": 1.0,
    "desert": 0.5,
    "ice": 0.4,
    "lava": 0.1,
    "carbon": 0.35,
    "gas_giant": 0.05,
    "rogue": 0.2,
}

KIND_GREENHOUSE: Dict[str, float] = {
    "terrestrial": 1.06,
    "oceanic": 1.12,
    "desert": 1.28,
    "ice": 1.0,
    "lava": 1.35,
    "carbon": 1.3,
    "gas_giant": 1.0,
    "rogue": 0.55,
}

_KIND_SIZE: Dict[str, tuple] = {
    "terrestrial": (0.2, 3.0, 4000, 9000),
    "oceanic": (0.5, 3.0, 6000, 9500),
    "desert": (0.2, 2.2, 4000, 8000),
    "ice": (0.3, 5.0, 3000, 8500),
    "lava": (0.3, 3.0, 5000, 9500),
    "carbon": (0.5, 4.0, 6000, 10000),
    "gas_giant": (50.0, 400.0, 30000, 70000),
    "rogue": (0.3, 8.0, 4000, 12000),
}


def planet_name(rng: random.Random) -> str:
    return (rng.choice(PLANET_PREFIXES) + rng.choice(PLANET_SUFFIXES)).capitalize()


def _orbit(rng: random.Random, kind: str) -> float:
    if kind == "gas_giant":
        return log_uniform(rng, 1.5, 12.0)
    if kind == "ice":
        return log_uniform(rng, 1.2, 20.0)
    if kind == "rogue":
        return log_uniform(rng, 4.0, 60.0)
    return log_uniform(rng, 0.25, 3.2)


def _atmosphere(rng: random.Random, kind: str, temperature_k: float) -> Dict[str, float]:
    mixes: Dict[str, Dict[str, float]] = {
        "gas_giant": {"H2": 6.0, "He": 3.0, "CH4": 0.8, "NH3": 0.4},
        "ice": {"N2": 4.0, "CH4": 1.0, "CO2": 0.6},
        "lava": {"CO2": 5.0, "SO2": 1.2, "H2O": 0.8},
        "desert": {"CO2": 6.0, "N2": 1.5, "Ar": 0.4},
        "carbon": {"CO2": 5.0, "CO": 1.5, "N2": 0.6},
        "oceanic": {"N2": 4.0, "O2": 1.2, "H2O": 2.0, "CO2": 0.6},
        "terrestrial": {"N2": 5.0, "O2": 1.5, "CO2": 0.5, "Ar": 0.3},
        "rogue": {"H2": 1.0, "He": 0.5, "CH4": 0.3},
    }
    raw = dict(mixes.get(kind, {"N2": 1.0}))
    for gas in list(raw):
        raw[gas] *= rng.uniform(0.6, 1.4)
    if temperature_k < 150:
        raw.pop("H2O", None)
    total = sum(raw.values()) or 1.0
    return {gas: round(value / total, 4) for gas, value in raw.items()}


def _equilibrium_temp(rng: random.Random, star_factor: float, orbit: float, kind: str) -> float:
    if kind == "rogue":
        return rng.uniform(15.0, 120.0)
    base = 278.5 * star_factor / max(orbit, 0.05) ** 0.5
    base *= KIND_GREENHOUSE.get(kind, 1.0) * rng.uniform(0.92, 1.08)
    return clamp(base, 3.0, 6000.0)


def _habitability(
    rng: random.Random,
    universe: Universe,
    kind: str,
    temperature_k: float,
    gravity_g: float,
    atmosphere: Dict[str, float],
) -> float:
    temp_score = clamp(1.0 - abs(temperature_k - 288.0) / 190.0)
    grav_score = clamp(1.0 - abs(gravity_g - 1.0) / 1.5)
    atm_score = 0.95 if atmosphere else 0.0
    if "O2" in atmosphere and atmosphere["O2"] > 0.05:
        atm_score = min(1.0, atm_score + 0.1)
    kind_score = KIND_HABITABILITY.get(kind, 0.3)
    raw = (
        0.45 * temp_score
        + 0.20 * grav_score
        + 0.20 * atm_score
        + 0.15 * kind_score
    )
    raw *= 0.45 + 0.55 * universe.habitability
    return clamp(raw * rng.uniform(0.92, 1.08))


def initial_biosphere(rng: random.Random, habitability: float) -> str:
    roll = rng.random()
    if habitability < 0.20:
        return "sterile"
    if habitability < 0.35:
        return "prebiotic" if roll < 0.5 else "sterile"
    if habitability < 0.55:
        return "microbial" if roll < 0.6 else "prebiotic"
    if habitability < 0.75:
        return weighted_choice(rng, ["microbial", "multicellular"], [0.5, 0.5])
    return weighted_choice(
        rng, ["multicellular", "complex"], [0.55, 0.45]
    )


def make_civilization(rng: random.Random) -> str:
    return f"{rng.choice(CIVILIZATION_STYLES)} civilization"


def form_planets(
    rng: random.Random,
    universe: Universe,
    count_range: Sequence[int],
    star_factor: float = 1.0,
) -> List[Planet]:
    count = planets_supported(rng, universe, count_range)
    kinds = list(KIND_WEIGHTS.keys())
    weights = [KIND_WEIGHTS[k] for k in kinds]
    planets: List[Planet] = []
    for index in range(count):
        kind = weighted_choice(rng, kinds, weights)
        orbit = round(_orbit(rng, kind), 3)
        mass_low, mass_high, radius_low, radius_high = _KIND_SIZE[kind]
        mass = round(rng.uniform(mass_low, mass_high), 3)
        radius = round(rng.uniform(radius_low, radius_high), 1)
        radius_earth = max(radius / 6371.0, 0.05)
        gravity_g = round(mass / (radius_earth ** 2), 3)
        temperature_k = round(_equilibrium_temp(rng, star_factor, orbit, kind), 1)
        atmosphere = _atmosphere(rng, kind, temperature_k)
        habitability = round(
            _habitability(rng, universe, kind, temperature_k, gravity_g, atmosphere), 3
        )
        biosphere = initial_biosphere(rng, habitability)
        moons = (
            rng.randint(0, 30) if kind == "gas_giant" else rng.randint(0, 4)
        )
        planets.append(
            Planet(
                name=f"{planet_name(rng)} {roman(index + 1)}",
                universe_id=universe.id,
                kind=kind,
                orbit_au=orbit,
                mass_earth=mass,
                radius_km=radius,
                gravity_g=gravity_g,
                temperature_k=temperature_k,
                atmosphere=atmosphere,
                habitability=habitability,
                biosphere=biosphere,
                civilization=(
                    make_civilization(rng)
                    if biosphere_rank(biosphere) >= biosphere_rank("sapient")
                    else None
                ),
                moons=moons,
                index=index,
            )
        )
    return planets


__all__ = ["form_planets", "planet_name", "make_civilization", "KIND_WEIGHTS"]
