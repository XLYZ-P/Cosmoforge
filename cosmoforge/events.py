"""Random event generation.

Events are sampled from the lore tables with weights, filtered by scope and
context (habitability, age window), then stamped onto a timeline. The generator
never repeats a kind on the same timeline, so a branch's history reads as a
sequence of distinct turning points.
"""
from __future__ import annotations

import random
from typing import Dict, Iterable, List, Sequence, Set

from .lore import EVENT_TEMPLATES, EventTemplate
from .models import Event, clamp
from .util import weighted_choice


def _eligible(
    templates: Sequence[EventTemplate],
    habitability: float,
) -> List[EventTemplate]:
    return [
        t for t in templates
        if habitability >= t.min_habitability
    ]


def generate_events(
    rng: random.Random,
    scope: str,
    count: int,
    universe_age_gyr: float,
    habitability: float = 1.0,
    context: Dict[str, str] = None,
    exclude: Iterable[str] = (),
) -> List[Event]:
    """Sample up to ``count`` distinct-kind events for one timeline."""
    context = dict(context or {})
    pool = _eligible(EVENT_TEMPLATES.get(scope, ()), habitability)
    used: Set[str] = set(exclude)
    pool = [t for t in pool if t.kind not in used]
    if not pool:
        return []

    events: List[Event] = []
    horizon = max(0.2, universe_age_gyr)
    for _ in range(int(count)):
        if not pool:
            break
        template = weighted_choice(rng, pool, [t.weight for t in pool])
        pool = [t for t in pool if t.kind != template.kind]

        upper = min(horizon, template.max_age_gyr if template.max_age_gyr < 1e8 else horizon)
        lower = 0.05 if scope == "universe" else 0.1
        if upper <= lower:
            continue
        age = round(rng.uniform(lower, upper), 3)
        severity = clamp(template.severity * rng.uniform(0.75, 1.25))
        title = template.title.format(**context)
        description = template.description.format(**context)
        events.append(
            Event(
                kind=template.kind,
                title=title,
                description=description,
                age_gyr=age,
                severity=severity,
                scope=scope,
                planet_id=context.get("planet_id"),
                unlocks=template.unlock_biosphere,
                tags=list(template.tags),
            )
        )

    events.sort(key=lambda e: e.age_gyr)
    return events


__all__ = ["generate_events"]
