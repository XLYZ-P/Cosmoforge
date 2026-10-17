"""Big Bang -> parallel universes.

A universe is defined by a set of physical constants sampled around our own
(1.0 = "our" values). Those constants then drive habitability, destiny and how
many planets the branch can support. Universes can branch off one another,
producing a small tree of parallel cosmologies.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence

from .lore import EPOCHS, GREEK, UNIVERSE_SUFFIXES, UNIVERSE_SYLLABLES
from .models import BigBang, Universe, clamp
from .util import gaussian_clamped

DEFAULT_LAWS: Dict[str, float] = {
    "gravity": 1.0,
    "strong_force": 1.0,
    "dark_energy": 1.0,
    "entropy": 1.0,
    "dimensions": 3.0,
}


def build_big_bang(seed: int) -> BigBang:
    """The shared origin: a fixed, real-world epoch timeline."""
    return BigBang(seed=seed, epochs=list(EPOCHS))


def build_big_bang_narrative(rng: random.Random) -> str:
    openers = (
        "From a singularity without a before, everything that can happen begins.",
        "There is no outside and no earlier; the cosmos is the whole of what is.",
        "A fluctuation in nothingness becomes the seed of every possible history.",
        "Time, space and law are born together in a single expanding instant.",
    )
    closers = (
        "Eleven epochs later, the stage is set for branches to diverge.",
        "What follows is not one universe but a family of them.",
        "The first stable atoms mark the point where histories can diverge.",
        "Structure is now possible; with it, difference; with difference, story.",
    )
    return f"{rng.choice(openers)} {rng.choice(closers)}"


def sample_laws(
    rng: random.Random,
    sigma: float = 0.18,
    base: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Sample physical constants around ``base`` (defaults to our universe)."""
    base = base or DEFAULT_LAWS
    laws: Dict[str, float] = {}
    for key in ("gravity", "strong_force", "dark_energy", "entropy"):
        center = float(base.get(key, 1.0))
        laws[key] = round(gaussian_clamped(rng, center, sigma, 0.05, 3.0), 3)
    dim_center = float(base.get("dimensions", 3.0))
    laws["dimensions"] = float(
        int(round(clamp(rng.gauss(dim_center, max(sigma, 0.4)), 2.0, 6.0)))
    )
    return laws


def habitability_from_laws(laws: Dict[str, float]) -> float:
    """Crude anthropic score: how close these constants are to life-friendly."""
    score = 1.0
    score -= 0.60 * min(abs(laws.get("gravity", 1.0) - 1.0), 1.0)
    score -= 0.50 * min(abs(laws.get("strong_force", 1.0) - 1.0), 1.0)
    score -= 0.75 * min(abs(laws.get("dark_energy", 1.0) - 1.0), 1.0)
    score -= 0.30 * min(abs(laws.get("entropy", 1.0) - 1.0), 1.0)
    score -= 0.15 * abs(laws.get("dimensions", 3.0) - 3.0)
    return clamp(score)


def destiny_scores(laws: Dict[str, float]) -> Dict[str, float]:
    """Relative plausibility of each fate under these constants."""
    gravity = laws.get("gravity", 1.0)
    dark = laws.get("dark_energy", 1.0)
    entropy = laws.get("entropy", 1.0)
    strong = laws.get("strong_force", 1.0)
    return {
        "heat_death": (
            1.0 + 2.0 * max(0.0, entropy - 1.0) + 1.5 * max(0.0, 1.0 - abs(dark - 1.1))
        ),
        "big_rip": 0.4 + 6.0 * max(0.0, dark - 1.05),
        "big_crunch": 0.4 + 6.0 * max(0.0, gravity - 1.0) * (1.0 if dark < 1.1 else 0.2),
        "big_bounce": 0.2 + 8.0 * max(0.0, gravity - 1.25) * (1.0 if dark < 1.0 else 0.1),
        "vacuum_decay": (
            0.2 + 10.0 * max(0.0, 0.7 - strong) + 2.0 * max(0.0, dark - 1.6)
        ),
        "eternal_stagnation": (
            0.5 + 3.0 * max(0.0, 1.0 - dark) * max(0.0, 1.15 - gravity)
        ),
    }


def destiny_from_laws(laws: Dict[str, float]) -> str:
    """Choose a fate.

    Unambiguous extremes are hard-coded; everything else is a *deterministic*
    weighted draw, so identical constants always produce the same destiny.
    """
    gravity = laws.get("gravity", 1.0)
    dark = laws.get("dark_energy", 1.0)
    strong = laws.get("strong_force", 1.0)
    if strong <= 0.45 or dark >= 2.4:
        return "vacuum_decay"
    if dark >= 1.75:
        return "big_rip"
    if gravity >= 1.75 and dark <= 0.85:
        return "big_bounce"
    if gravity >= 1.5 and dark <= 0.9:
        return "big_crunch"

    entropy = laws.get("entropy", 1.0)
    dims = laws.get("dimensions", 3.0)
    scores = destiny_scores(laws)
    names = list(scores)
    weights = [scores[name] for name in names]
    seed = int(round(gravity * 997 + dark * 991 + entropy * 983 + strong * 977 + dims * 971))
    roll = random.Random(seed).random() * sum(weights)
    upto = 0.0
    for name, weight in zip(names, weights):
        upto += weight
        if upto >= roll:
            return name
    return names[-1]


def universe_name(rng: random.Random) -> str:
    return (
        rng.choice(UNIVERSE_SYLLABLES) + rng.choice(UNIVERSE_SUFFIXES)
    ).capitalize()


def _make_universe(
    rng: random.Random,
    index: int,
    seed: int,
    generation: int = 0,
    parent: Optional[Universe] = None,
    law_sigma: float = 0.18,
) -> Universe:
    laws = sample_laws(rng, sigma=law_sigma, base=parent.laws if parent else None)
    habitability = habitability_from_laws(laws)
    destiny = destiny_from_laws(laws)
    # Expansion rate tracks dark energy plus a little noise.
    expansion = clamp(
        laws["dark_energy"] * rng.uniform(0.9, 1.1), 0.2, 3.0
    )
    age = clamp(rng.gauss(13.8, 1.6), 6.0, 22.0)
    name = universe_name(rng)
    if generation > 0:
        name = f"{name}-{GREEK[index % len(GREEK)]}"
    return Universe(
        name=name,
        index=index,
        laws=laws,
        destiny=destiny,
        age_gyr=ceil1(age),
        habitability=habitability,
        expansion_rate=ceil3(expansion),
        generation=generation,
        parent_id=parent.id if parent else None,
        seed=seed,
    )


def ceil1(value: float) -> float:
    return round(value, 1)


def ceil3(value: float) -> float:
    return round(value, 3)


def spawn_universes(
    rng: random.Random,
    count: int,
    law_sigma: float = 0.18,
    branching: float = 0.0,
    max_generation: int = 0,
    base_seed: int = 0,
) -> List[Universe]:
    """Create ``count`` root universes, then optionally let them branch.

    Child branches inherit their parent's constants with a tighter spread, so a
    branch feels like a variation on its parent rather than a fresh roll.
    """
    universes: List[Universe] = []
    for index in range(count):
        seed = base_seed * 100_003 + index + 1
        universes.append(
            _make_universe(
                random.Random(seed),
                index=index,
                seed=seed,
                generation=0,
                law_sigma=law_sigma,
            )
        )

    generation = 0
    while generation < max_generation and branching > 0:
        parents = [u for u in universes if u.generation == generation]
        for parent in parents:
            if rng.random() < branching:
                index = len(universes)
                child_seed = parent.seed * 7 + 13 + index
                universes.append(
                    _make_universe(
                        random.Random(child_seed),
                        index=index,
                        seed=child_seed,
                        generation=generation + 1,
                        parent=parent,
                        law_sigma=max(law_sigma * 0.5, 0.03),
                    )
                )
        generation += 1
    return universes


def planets_supported(
    rng: random.Random, universe: Universe, base_range: Sequence[int]
) -> int:
    """How many worlds a branch spawns, biased up by habitability."""
    low, high = sorted((int(base_range[0]), int(base_range[-1])))
    draws = [rng.randint(low, high)]
    if universe.habitability > 0.6:
        draws.append(rng.randint(low, high))
    return max(draws)


__all__ = [
    "DEFAULT_LAWS",
    "build_big_bang",
    "build_big_bang_narrative",
    "sample_laws",
    "habitability_from_laws",
    "destiny_scores",
    "destiny_from_laws",
    "universe_name",
    "spawn_universes",
    "planets_supported",
]
