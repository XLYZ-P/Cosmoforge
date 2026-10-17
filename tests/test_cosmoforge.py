"""Tests for the Cosmoforge generators and renderers."""
from __future__ import annotations

import json
import unittest

from cosmoforge import (
    Cosmogenesis,
    RuleNarrator,
    Scenario,
    available_providers,
    build_tree,
    resolve_provider,
    to_html,
    to_markdown,
)
from cosmoforge.events import generate_events
from cosmoforge.genesis import (
    build_big_bang,
    destiny_from_laws,
    habitability_from_laws,
    sample_laws,
    spawn_universes,
)
from cosmoforge.providers import ChatMessage, FallbackProvider, MockProvider
from cosmoforge.providers.mock import MockProvider as _Mock


class GenesisTest(unittest.TestCase):
    def test_laws_have_all_keys(self):
        import random

        laws = sample_laws(random.Random(1), 0.2)
        self.assertEqual(
            set(laws), {"gravity", "strong_force", "dark_energy", "entropy", "dimensions"}
        )

    def test_baseline_laws_are_habitable(self):
        baseline = {
            "gravity": 1.0, "strong_force": 1.0, "dark_energy": 1.0,
            "entropy": 1.0, "dimensions": 3.0,
        }
        from cosmoforge.models import DESTINIES

        self.assertGreater(habitability_from_laws(baseline), 0.9)
        self.assertIn(destiny_from_laws(baseline), DESTINIES)

    def test_extreme_cosmology_gets_extreme_destiny(self):
        self.assertEqual(destiny_from_laws({"dark_energy": 2.0}), "big_rip")
        self.assertEqual(
            destiny_from_laws({"gravity": 1.9, "dark_energy": 0.5}), "big_bounce"
        )
        self.assertEqual(destiny_from_laws({"strong_force": 0.2}), "vacuum_decay")

    def test_spawn_respects_count_and_branching(self):
        import random

        universes = spawn_universes(
            random.Random(4), count=3, branching=1.0, max_generation=1, base_seed=4
        )
        self.assertEqual(len(universes), 6)  # 3 roots + 3 forced children
        self.assertEqual({u.generation for u in universes}, {0, 1})

    def test_big_bang_has_epochs(self):
        big_bang = build_big_bang(7)
        self.assertGreaterEqual(len(big_bang.epochs), 8)
        self.assertEqual(big_bang.epochs[0].name, "Planck epoch")


class EngineTest(unittest.TestCase):
    def test_deterministic_for_same_seed(self):
        scenario = Scenario.demo().with_overrides(universes=3, seed=99, branching=0.5)
        first = Cosmogenesis(scenario).run().as_dict()
        second = Cosmogenesis(scenario).run().as_dict()
        self.assertEqual(first, second)

    def test_structural_expectations(self):
        scenario = Scenario.demo().with_overrides(
            universes=4, seed=11, planets_per_universe=(2, 4),
            branching=0.0, max_generation=0,
        )
        cosmos = Cosmogenesis(scenario).run()
        self.assertEqual(len(cosmos.universes), 4)
        valid_biospheres = {
            "sterile", "prebiotic", "microbial", "multicellular", "complex", "sapient",
        }
        for universe in cosmos.universes:
            self.assertEqual(set(universe.laws), {
                "gravity", "strong_force", "dark_energy", "entropy", "dimensions",
            })
            self.assertTrue(universe.narrative)
            for planet in universe.planets:
                self.assertGreaterEqual(planet.habitability, 0.0)
                self.assertLessEqual(planet.habitability, 1.0)
                self.assertIn(planet.biosphere, valid_biospheres)
                self.assertEqual(planet.universe_id, universe.id)

    def test_events_are_sorted_and_distinct(self):
        scenario = Scenario.demo().with_overrides(universes=2, seed=3)
        cosmos = Cosmogenesis(scenario).run()
        for universe in cosmos.universes:
            kinds = [e.kind for e in universe.events]
            self.assertEqual(len(kinds), len(set(kinds)))
            ages = [e.age_gyr for e in universe.events]
            self.assertEqual(ages, sorted(ages))

    def test_llm_narrator_falls_back_and_still_works(self):
        from cosmoforge import LLMNarrator

        scenario = Scenario.demo().with_overrides(universes=2, seed=5, narrator="llm")
        narrator = LLMNarrator(_Mock(), fallback=True)
        cosmos = Cosmogenesis(scenario, narrator=narrator).run()
        stats = cosmos.narration
        self.assertEqual(stats["narrator"], "llm")
        self.assertGreater(stats["ok"], 0)
        self.assertTrue(all(u.narrative for u in cosmos.universes))


class EventsTest(unittest.TestCase):
    def test_generation_respects_habitability_gate(self):
        import random

        rng = random.Random(2)
        events = generate_events(
            rng, "planet", count=10, universe_age_gyr=13.8, habitability=0.0
        )
        kinds = {e.kind for e in events}
        self.assertNotIn("abiogenesis", kinds)  # needs habitability >= 0.35

    def test_generation_caps_at_available_kinds(self):
        import random

        rng = random.Random(8)
        events = generate_events(
            rng, "universe", count=999, universe_age_gyr=13.8, habitability=1.0
        )
        self.assertLessEqual(len(events), 10)


class ProviderTest(unittest.TestCase):
    def test_registry_has_major_vendors(self):
        names = {row["provider"] for row in available_providers()}
        for expected in ("openai", "anthropic", "google", "ollama", "deepseek", "mock"):
            self.assertIn(expected, names)

    def test_alias_resolution(self):
        self.assertEqual(resolve_provider("claude").name, "anthropic")
        self.assertEqual(resolve_provider("gemini").name, "google")
        self.assertEqual(resolve_provider("offline").name, "mock")

    def test_unknown_provider_raises(self):
        with self.assertRaises(KeyError):
            resolve_provider("definitely-not-a-provider")

    def test_mock_provider_returns_json_narrative(self):
        provider = MockProvider()
        response = provider.complete([ChatMessage("user", "describe a universe")])
        payload = json.loads(response.text)
        self.assertIn("narrative", payload)
        self.assertEqual(provider.name, "mock")

    def test_fallback_chain_uses_first_configured(self):
        chain = FallbackProvider([MockProvider(), MockProvider()])
        response = chain.complete([ChatMessage("user", "hello")])
        self.assertEqual(response.provider, "mock")

    def test_config_dict_builds_provider(self):
        provider = resolve_provider(
            {"provider": "deepseek", "model": "deepseek-chat", "api_key": "x"}
        )
        self.assertEqual(provider.name, "deepseek")
        self.assertEqual(provider.base_url, "https://api.deepseek.com/v1")
        self.assertTrue(provider.configured)


class RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scenario = Scenario.demo().with_overrides(universes=3, seed=21)
        cls.cosmos = Cosmogenesis(scenario).run()

    def test_build_tree_shape(self):
        tree = build_tree(self.cosmos)
        self.assertEqual(tree.kind, "root")
        kinds = [child.kind for child in tree.children]
        self.assertEqual(kinds[0], "bigbang")
        self.assertEqual(kinds.count("universe"), len(self.cosmos.universes))

    def test_html_is_self_contained(self):
        html = to_html(self.cosmos)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertNotIn("__DATA__", html)   # placeholder was replaced
        self.assertNotIn("__TITLE__", html)
        self.assertIn(self.cosmos.universes[0].name, html)
        self.assertNotIn("<script src=", html)   # no external scripts
        self.assertNotIn("href=\"http", html)     # no external stylesheets

    def test_html_survives_a_script_breakout(self):
        cosmos = Cosmogenesis(Scenario.demo().with_overrides(universes=1, seed=2)).run()
        cosmos.name = "Cosmos </script><script>alert(1)</script>"
        html = to_html(cosmos)
        self.assertNotIn("</script><script>alert(1)", html)

    def test_markdown_has_sections(self):
        md = to_markdown(self.cosmos)
        for heading in ("# ", "## Big Bang", "## Universes"):
            self.assertIn(heading, md)

    def test_html_has_timeline_and_zoom_and_numeric_ages(self):
        html = to_html(self.cosmos)
        self.assertIn('id="timeline"', html)
        self.assertIn('id="zoom"', html)
        self.assertIn("renderTimeline", html)
        self.assertIn('"live": false', html)   # plain file: no live buttons
        # numeric ages are required for the timeline axis
        self.assertIn('"age_gyr"', html)
        self.assertIn('"age_years"', html)

    def test_html_has_touch_motion_and_streaming(self):
        html = to_html(self.cosmos)
        for token in (
            "pointerdown",
            "touch-action:none",
            "playTimeline",
            "/api/expand/stream",
            "evolveOnce",
            "动态演化",
            "regenerateFromSeed",
            "archive-modal",
            "nodePop",
            "#viewport.smooth",
        ):
            self.assertIn(token, html)

    def test_tree_to_html_can_enable_live(self):
        from cosmoforge.render import build_tree, tree_to_html

        html = tree_to_html(build_tree(self.cosmos), "X", live=True)
        self.assertIn('"live": true', html)
        self.assertIn("window.COSMOS_BOOTSTRAP", html)
        self.assertIn("/api/expand", html)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
