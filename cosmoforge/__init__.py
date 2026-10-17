"""Cosmoforge — an AI worldview simulation framework.

The pipeline:

    Big Bang  ->  parallel universes  ->  planets  ->  random events  ->  prose

Universes sample their own physical constants; those constants drive
habitability, fate and how many worlds a branch supports. Events are drawn from
weighted lore tables and can causally promote a planet's biosphere. Any stage
can be narrated by a rule engine or by any registered model provider. The
finished cosmos renders as a self-contained interactive HTML mind map.
"""

from .models import (
    BigBang,
    Cosmos,
    Epoch,
    Event,
    MapNode,
    Planet,
    Universe,
)
from .narrate import LLMNarrator, Narrator, RuleNarrator, make_narrator
from .providers import (
    Provider,
    available as available_providers,
    register as register_provider,
    resolve as resolve_provider,
    resolve_many as resolve_providers,
)
from .render import build_tree, to_html, to_markdown, tree_to_html
from .scenario import Scenario
from .serve import make_server, serve
from .simulation import Cosmogenesis

__version__ = "0.1.0"

__all__ = [
    # domain
    "BigBang",
    "Cosmos",
    "Epoch",
    "Event",
    "MapNode",
    "Planet",
    "Universe",
    # engine
    "Cosmogenesis",
    "Scenario",
    # narration
    "Narrator",
    "RuleNarrator",
    "LLMNarrator",
    "make_narrator",
    # providers
    "Provider",
    "available_providers",
    "register_provider",
    "resolve_provider",
    "resolve_providers",
    # rendering
    "to_html",
    "tree_to_html",
    "to_markdown",
    "build_tree",
    # live server
    "serve",
    "make_server",
    "__version__",
]
