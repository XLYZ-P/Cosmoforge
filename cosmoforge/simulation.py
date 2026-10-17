"""The engine: Big Bang -> universes -> planets -> events -> narration."""
from __future__ import annotations

import random
from typing import List, Optional

from . import genesis
from .events import generate_events
from .lore import biosphere_rank
from .models import BigBang, Cosmos, Planet, Universe, clamp, reset_ids
from .narrate import Narrator, make_narrator
from .planets import form_planets, make_civilization
from .scenario import Scenario
from .util import sample_range


class Cosmogenesis:
    """Runs one worldbuilding pass and returns a :class:`Cosmos`.

    Deterministic for the rule narrator: the same scenario and seed always
    rebuilds an identical cosmos. With an LLM narrator only the prose changes;
    the structure, numbers and event placement stay seed-stable.
    """

    def __init__(self, scenario: Scenario, narrator: Optional[Narrator] = None):
        self.scenario = scenario
        self.rng = random.Random(scenario.seed)
        self.narrator: Narrator = narrator or make_narrator(scenario.narrator_spec())

    # -- steps -------------------------------------------------------------
    def _big_bang(self) -> BigBang:
        big_bang = genesis.build_big_bang(self.scenario.seed)
        big_bang.narrative = self.narrator.big_bang(big_bang, self.rng)
        return big_bang

    def _populate_universe(self, universe: Universe) -> None:
        rng = random.Random(universe.seed)
        star_factor = rng.uniform(0.6, 1.5)
        universe.planets = form_planets(
            rng, universe, self.scenario.planets_per_universe, star_factor
        )

        universe.events = generate_events(
            rng,
            scope="universe",
            count=sample_range(rng, self.scenario.universe_events),
            universe_age_gyr=universe.age_gyr,
            habitability=universe.habitability,
            context={"universe": universe.name},
        )

        for planet in universe.planets:
            planet_rng = random.Random(universe.seed * 31 + planet.index + 1)
            planet.events = generate_events(
                planet_rng,
                scope="planet",
                count=sample_range(planet_rng, self.scenario.planet_events),
                universe_age_gyr=min(universe.age_gyr, 13.8),
                habitability=planet.habitability,
                context={
                    "planet": planet.name,
                    "universe": universe.name,
                    "planet_id": planet.id,
                },
            )
            self._evolve(planet, planet_rng)
            planet.narrative = self.narrator.planet(planet, universe, planet_rng)

        universe.narrative = self.narrator.universe(universe, rng)

    def _evolve(self, planet: Planet, rng: random.Random) -> None:
        """Apply the causal consequences of a planet's event timeline."""
        for event in sorted(planet.events, key=lambda e: e.age_gyr):
            if event.unlocks and biosphere_rank(event.unlocks) > biosphere_rank(planet.biosphere):
                planet.biosphere = event.unlocks
            if "cataclysm" in event.tags:
                planet.habitability = clamp(
                    planet.habitability - 0.04 * event.severity
                )
        if planet.biosphere == "sapient" and not planet.civilization:
            planet.civilization = make_civilization(rng)

    # -- entry point -------------------------------------------------------
    def run(self) -> Cosmos:
        reset_ids()
        big_bang = self._big_bang()
        universes = genesis.spawn_universes(
            self.rng,
            count=self.scenario.universes,
            law_sigma=self.scenario.law_sigma,
            branching=self.scenario.branching,
            max_generation=self.scenario.max_generation,
            base_seed=self.scenario.seed,
        )
        for universe in universes:
            self._populate_universe(universe)

        narration = self.narrator.stats()
        cosmos = Cosmos(
            name=self.scenario.name,
            seed=self.scenario.seed,
            big_bang=big_bang,
            universes=universes,
            config=self.scenario.as_dict(),
            provider=narration.get("provider"),
            model=narration.get("model"),
            narration=narration,
        )
        return cosmos


__all__ = ["Cosmogenesis"]
