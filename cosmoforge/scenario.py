"""Scenario loading: JSON config -> built Cosmogenesis engine."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

Range = Union[int, Sequence[int]]

DEFAULTS: Dict[str, Any] = {
    "name": "The Observable Multiverse",
    "seed": 42,
    "universes": 4,
    "branching": 0.25,
    "max_generation": 1,
    "law_sigma": 0.18,
    "planets_per_universe": [2, 5],
    "universe_events": [3, 6],
    "planet_events": [2, 5],
    "narrator": "rule",
    "language": "en",
}


def _as_range(value: Any, fallback: Tuple[int, int]) -> Tuple[int, int]:
    if value is None:
        return fallback
    if isinstance(value, int):
        return (value, value)
    seq = list(value)
    if not seq:
        return fallback
    if len(seq) == 1:
        return (int(seq[0]), int(seq[0]))
    return (int(seq[0]), int(seq[-1]))


@dataclass
class Scenario:
    """Declarative description of a worldbuilding run, loadable from JSON."""

    name: str = DEFAULTS["name"]
    seed: int = DEFAULTS["seed"]
    universes: int = DEFAULTS["universes"]
    branching: float = DEFAULTS["branching"]
    max_generation: int = DEFAULTS["max_generation"]
    law_sigma: float = DEFAULTS["law_sigma"]
    planets_per_universe: Tuple[int, int] = (2, 5)
    universe_events: Tuple[int, int] = (3, 6)
    planet_events: Tuple[int, int] = (2, 5)
    narrator: Any = "rule"
    language: str = "en"
    provider: Any = None
    model: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    # -- construction ------------------------------------------------------
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scenario":
        known = set(DEFAULTS) | {"provider", "model", "extras"}
        extra = {k: v for k, v in data.items() if k not in known}
        extra.update(dict(data.get("extras", {})))
        return cls(
            name=str(data.get("name", DEFAULTS["name"])),
            seed=int(data.get("seed", DEFAULTS["seed"])),
            universes=max(1, int(data.get("universes", DEFAULTS["universes"]))),
            branching=float(data.get("branching", DEFAULTS["branching"])),
            max_generation=max(0, int(data.get("max_generation", DEFAULTS["max_generation"]))),
            law_sigma=max(0.0, float(data.get("law_sigma", DEFAULTS["law_sigma"]))),
            planets_per_universe=_as_range(data.get("planets_per_universe"), (2, 5)),
            universe_events=_as_range(data.get("universe_events"), (3, 6)),
            planet_events=_as_range(data.get("planet_events"), (2, 5)),
            narrator=data.get("narrator", "rule"),
            language=str(data.get("language", DEFAULTS["language"])),
            provider=data.get("provider"),
            model=data.get("model"),
            extra=extra,
        )

    @classmethod
    def from_file(cls, path: str) -> "Scenario":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    # -- derived config ----------------------------------------------------
    def narrator_spec(self) -> Dict[str, Any]:
        """Normalise the narrator config into one dict the factory understands."""
        spec = dict(self.narrator) if isinstance(self.narrator, dict) else {"type": self.narrator}
        spec.setdefault("language", self.language)
        if self.provider is not None:
            spec.setdefault("provider", self.provider)
        if self.model is not None:
            spec.setdefault("model", self.model)
        return spec

    def with_overrides(self, **overrides: Any) -> "Scenario":
        clean = {k: v for k, v in overrides.items() if v is not None}
        return replace(self, **clean)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "seed": self.seed,
            "universes": self.universes,
            "branching": self.branching,
            "max_generation": self.max_generation,
            "law_sigma": self.law_sigma,
            "planets_per_universe": list(self.planets_per_universe),
            "universe_events": list(self.universe_events),
            "planet_events": list(self.planet_events),
            "language": self.language,
            "extra": dict(self.extra),
        }

    # -- building ----------------------------------------------------------
    def build(self, narrator: Any = None) -> "Cosmogenesis":
        from .simulation import Cosmogenesis

        return Cosmogenesis(self, narrator=narrator)

    # -- built-in demo -----------------------------------------------------
    @classmethod
    def demo(cls) -> "Scenario":
        return cls.from_dict(DEMO_SCENARIO)


DEMO_SCENARIO: Dict[str, Any] = {
    "name": "The Aeloria Multiverse",
    "seed": 1337,
    "universes": 4,
    "branching": 0.3,
    "max_generation": 1,
    "law_sigma": 0.2,
    "planets_per_universe": [2, 5],
    "universe_events": [3, 6],
    "planet_events": [2, 5],
    "narrator": "rule",
    "language": "en",
}


__all__ = ["Scenario", "DEMO_SCENARIO", "DEFAULTS"]
