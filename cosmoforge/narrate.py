"""Narrators: turn structured simulation state into prose.

Two implementations share one interface:

* :class:`RuleNarrator` composes deterministic sentences from templates and the
  numbers themselves. No network, fully reproducible.
* :class:`LLMNarrator` asks any registered provider for a short paragraph and
  silently falls back to the rule narrator on any error, so a run never breaks
  because a model is slow, rate-limited or misconfigured.
"""
from __future__ import annotations

import json
import random
import re
from typing import Any, Dict, List, Optional

from .models import BigBang, Planet, Universe, format_age
from .providers import ChatMessage, Provider, ProviderError

_JSON_DECODER = json.JSONDecoder()


def extract_json(text: str) -> Any:
    """Pull the first JSON object/array out of a model response."""
    if not text:
        raise ValueError("empty model response")
    cleaned = re.sub(r"```(?:json)?", "", text).strip("` \n")
    indices = [cleaned.find(opener) for opener in ("{", "[")]
    indices = [i for i in indices if i >= 0]
    if not indices:
        raise ValueError(f"no JSON found in: {text[:160]!r}")
    value, _ = _JSON_DECODER.raw_decode(cleaned[min(indices):])
    return value


class Narrator:
    """Common interface; subclasses fill in the domain-specific methods."""

    name = "narrator"
    language = "en"

    def big_bang(self, big_bang: BigBang, rng: random.Random) -> str:  # pragma: no cover
        raise NotImplementedError

    def universe(self, universe: Universe, rng: random.Random) -> str:  # pragma: no cover
        raise NotImplementedError

    def planet(self, planet: Planet, universe: Universe, rng: random.Random) -> str:  # pragma: no cover
        raise NotImplementedError

    def stats(self) -> Dict[str, Any]:
        return {"narrator": self.name}


class RuleNarrator(Narrator):
    """Deterministic prose assembled from the simulation's own numbers."""

    name = "rule"

    def big_bang(self, big_bang: BigBang, rng: random.Random) -> str:
        from .genesis import build_big_bang_narrative

        return build_big_bang_narrative(rng)

    def universe(self, universe: Universe, rng: random.Random) -> str:
        laws = universe.laws
        exotic = [
            f"{key} {value:g}"
            for key, value in laws.items()
            if abs(value - 1.0) > 0.25 and key != "dimensions"
        ]
        if exotic:
            flavour = "Constants run wild here: " + ", ".join(exotic) + "."
        else:
            flavour = "Its constants sit comfortably close to our own."
        if laws.get("dimensions", 3.0) != 3.0:
            flavour += f" It has {int(laws['dimensions'])} large spatial dimensions."
        habit = (
            "Life-friendly" if universe.habitability > 0.6
            else "Marginal" if universe.habitability > 0.35
            else "Hostile"
        )
        worlds = len(universe.planets)
        return (
            f"{universe.name} is a {habit.lower()} branch {universe.generation} "
            f"generation{'s' if universe.generation != 1 else ''} from the Big Bang. "
            f"{flavour} Given roughly {format_age(universe.age_gyr * 1e9)} of history, "
            f"it holds {worlds} notable world{'s' if worlds != 1 else ''} and expands "
            f"toward a {universe.destiny.replace('_', ' ')}."
        )

    def planet(self, planet: Planet, universe: Universe, rng: random.Random) -> str:
        gas = max(planet.atmosphere, key=planet.atmosphere.get) if planet.atmosphere else "no"
        air = f"{gas}-rich air" if planet.atmosphere else "airless vacuum"
        return (
            f"{planet.name} is a {planet.kind.replace('_', ' ')} world orbiting at "
            f"{planet.orbit_au:g} AU with {planet.gravity_g:g}g and a mean temperature "
            f"of {planet.temperature_k:.0f} K under {air}. "
            f"Its biosphere is {planet.biosphere}"
            + (f", home to a {planet.civilization}." if planet.civilization else ".")
        )


class LLMNarrator(Narrator):
    """Model-backed narrator with a rule-based safety net."""

    name = "llm"

    _SYSTEM = (
        "You are a cosmic historian writing concise entries for an interactive "
        "atlas of parallel universes. Stay strictly consistent with the facts you "
        "are given and invent nothing that contradicts them. "
        'Respond with ONLY a JSON object of the form {"narrative": "<2-4 vivid sentences>"}.'
    )

    def __init__(
        self,
        provider: Provider,
        fallback: bool = True,
        temperature: float = 0.85,
        max_tokens: int = 400,
        language: str = "en",
    ):
        self.provider = provider
        self.fallback = fallback
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.language = language or "en"
        self.rule = RuleNarrator()
        self._stats: Dict[str, Any] = {
            "narrator": "llm",
            "provider": provider.name,
            "model": getattr(provider, "model", ""),
            "calls": 0,
            "ok": 0,
            "fallback": 0,
            "errors": [],
        }

    # -- helpers ----------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        snapshot = dict(self._stats)
        snapshot["errors"] = list(snapshot["errors"][-5:])
        return snapshot

    def _language_clause(self) -> str:
        if self.language.lower().startswith("zh"):
            return " Write the narrative in Simplified Chinese (简体中文)."
        if self.language.lower() in ("en", "english", ""):
            return ""
        return f" Write the narrative in {self.language}."

    def _ask(self, payload: Dict[str, Any], domain: str, rng: random.Random, rule_fn) -> str:
        self._stats["calls"] += 1
        try:
            response = self.provider.complete(
                [
                    ChatMessage(
                        "system",
                        self._SYSTEM + self._language_clause(),
                    ),
                    ChatMessage("user", json.dumps(payload, ensure_ascii=False, indent=2)),
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            data = extract_json(response.text)
            narrative = ""
            if isinstance(data, dict):
                narrative = str(data.get("narrative", "")).strip()
            elif isinstance(data, str):
                narrative = data.strip()
            if not narrative:
                raise ValueError("model returned no narrative field")
            self._stats["ok"] += 1
            return narrative
        except (ProviderError, ValueError, KeyError, TypeError) as exc:
            self._stats["fallback"] += 1
            self._stats["errors"].append(f"{domain}: {exc}")
            if not self.fallback:
                raise
            return rule_fn()

    # -- interface --------------------------------------------------------
    def big_bang(self, big_bang: BigBang, rng: random.Random) -> str:
        payload = {
            "task": "Describe the birth of this cosmos as the Big Bang completes.",
            "epochs": [e.as_dict() for e in big_bang.epochs],
        }
        return self._ask(payload, "big_bang", rng, lambda: self.rule.big_bang(big_bang, rng))

    def universe(self, universe: Universe, rng: random.Random) -> str:
        payload = {
            "task": "Describe this parallel universe.",
            "universe": {
                "name": universe.name,
                "generation": universe.generation,
                "laws": universe.laws,
                "habitability": universe.habitability,
                "destiny": universe.destiny,
                "age_gyr": universe.age_gyr,
                "worlds": len(universe.planets),
                "events": [e.title for e in universe.events],
            },
        }
        return self._ask(
            payload, "universe", rng, lambda: self.rule.universe(universe, rng)
        )

    def planet(self, planet: Planet, universe: Universe, rng: random.Random) -> str:
        payload = {
            "task": "Describe this world.",
            "universe": universe.name,
            "planet": {
                "name": planet.name,
                "kind": planet.kind,
                "orbit_au": planet.orbit_au,
                "gravity_g": planet.gravity_g,
                "temperature_k": planet.temperature_k,
                "atmosphere": planet.atmosphere,
                "habitability": planet.habitability,
                "biosphere": planet.biosphere,
                "civilization": planet.civilization,
                "timeline": [f"{e.age_gyr:.2f} Gyr: {e.title}" for e in planet.events],
            },
        }
        return self._ask(
            payload,
            "planet",
            rng,
            lambda: self.rule.planet(planet, universe, rng),
        )


def make_narrator(spec: Any = "rule", **overrides: Any) -> Narrator:
    """Build a narrator from ``"rule"``, ``"llm"`` or a config dict."""
    from .providers import resolve_many

    if isinstance(spec, Narrator):
        return spec
    if spec is None:
        spec = "rule"
    if isinstance(spec, str):
        spec = {"type": spec}
    if not isinstance(spec, dict):
        raise TypeError(f"cannot build narrator from {spec!r}")

    kind = str(spec.get("type", spec.get("narrator", "rule"))).lower()
    if kind in ("rule", "deterministic", "offline", "template"):
        return RuleNarrator()

    # kind == "llm"
    chain = spec.get("providers") or spec.get("chain")
    if chain:
        provider = resolve_many(chain)
    else:
        provider = resolve_provider_spec(spec)
    language = overrides.pop("language", spec.get("language", "en"))
    return LLMNarrator(
        provider=provider,
        fallback=bool(spec.get("fallback", True)),
        temperature=float(spec.get("temperature", 0.85)),
        max_tokens=int(spec.get("max_tokens", 400)),
        language=language,
    )


def resolve_provider_spec(spec: Dict[str, Any]) -> Provider:
    """Extract the provider sub-spec out of a narrator config."""
    from .providers import resolve

    provider_spec: Any = spec.get("provider")
    if provider_spec is None:
        provider_spec = {
            key: spec[key]
            for key in ("provider_name", "model", "api_key", "base_url", "timeout")
            if key in spec
        }
        if not provider_spec:
            provider_spec = None
    elif isinstance(provider_spec, str):
        provider_spec = {
            "provider": provider_spec,
            "model": spec.get("model"),
            "base_url": spec.get("base_url"),
            "api_key": spec.get("api_key"),
        }
    else:
        provider_spec = dict(provider_spec)
        provider_spec.setdefault("model", spec.get("model"))
    return resolve(provider_spec)


__all__ = ["Narrator", "RuleNarrator", "LLMNarrator", "make_narrator", "extract_json"]
