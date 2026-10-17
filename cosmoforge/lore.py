"""Static lore tables: cosmic epochs, event templates, name pools.

Everything here is deterministic data. The generators in :mod:`cosmoforge.events`
and friends only sample from these tables, so the same seed always rebuilds the
same cosmos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .models import Epoch

# ---------------------------------------------------------------------------
# Big Bang epochs (cosmic time in years, temperature in kelvin)
# ---------------------------------------------------------------------------

EPOCHS: Tuple[Epoch, ...] = (
    Epoch(
        "Planck epoch", 3.2e-51, 1.4e32,
        "Gravity and the other forces are one. Spacetime is a quantum foam "
        "with no stable geometry; time itself is not yet meaningful.",
    ),
    Epoch(
        "Grand unification", 1.0e-49, 1.0e29,
        "Gravity decouples from the unified force. A first arrow of time "
        "appears as the young cosmos begins to cool.",
    ),
    Epoch(
        "Inflation", 3.2e-44, 1.0e27,
        "Space expands by a factor of 10^26 in a fraction of a second. "
        "Quantum fluctuations are stretched into the seeds of every galaxy "
        "that will ever exist.",
    ),
    Epoch(
        "Electroweak epoch", 1.6e-38, 1.0e15,
        "The strong force separates. Particles acquire mass through the "
        "Higgs field as symmetry breaks.",
    ),
    Epoch(
        "Quark epoch", 1.2e-36, 1.0e12,
        "Quarks, leptons and gluons move freely. Matter and antimatter "
        "annihilate in a faintly lopsided contest.",
    ),
    Epoch(
        "Hadron epoch", 3.2e-26, 1.0e10,
        "Quarks bind into protons and neutrons. The surviving matter/antimatter "
        "asymmetry freezes in at roughly one baryon per billion photons.",
    ),
    Epoch(
        "Lepton epoch", 3.2e-16, 1.0e9,
        "Neutrinos decouple and stream away. Electrons and positrons annihilate, "
        "leaving the lepton budget that will feed the first atoms.",
    ),
    Epoch(
        "Nucleosynthesis", 5.7e-9, 1.0e8,
        "Primordial fusion forges hydrogen, helium and a trace of lithium. "
        "The elemental recipe of the cosmos is set within minutes.",
    ),
    Epoch(
        "Recombination", 3.8e-4, 3.0e3,
        "Electrons finally bind to nuclei. The fog clears, photons stream free, "
        "and the cosmic microwave background is released.",
    ),
    Epoch(
        "Dark ages", 1.0e-2, 60.0,
        "Neutral hydrogen fills a lightless, cooling cosmos. Gravity quietly "
        "assembles the first filaments of structure.",
    ),
    Epoch(
        "Reionization", 5.0e-1, 30.0,
        "The first stars ignite, then die, reionizing the intergalactic medium. "
        "The universe becomes visible to itself.",
    ),
)

# ---------------------------------------------------------------------------
# Random event templates
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventTemplate:
    """Blueprint sampled by the event generator."""

    kind: str
    title: str
    description: str
    severity: float
    weight: float
    scope: str
    min_habitability: float = 0.0
    max_age_gyr: float = 1e9
    unlock_biosphere: str = ""     # sets planet.biosphere if currently lower
    tags: Tuple[str, ...] = ()


UNIVERSE_EVENTS: Tuple[EventTemplate, ...] = (
    EventTemplate(
        "false_vacuum", "False-vacuum bubble",
        "A region of the cosmos tunnels into a truer vacuum and expands at "
        "light speed, rewriting the constants inside its wall.",
        1.0, 0.5, "universe", tags=("cataclysm", "exotic"),
    ),
    EventTemplate(
        "cosmic_string", "Cosmic string network",
        "One-dimensional topological defects from the early universe stretch "
        "across intergalactic space, seeding gravitationally lensed filaments.",
        0.6, 0.8, "universe", tags=("structure", "exotic"),
    ),
    EventTemplate(
        "domain_wall", "Domain-wall turbulence",
        "Mismatched vacuum patches collide along domain walls, injecting "
        "enormous energy into the cosmic horizon.",
        0.7, 0.6, "universe", tags=("cataclysm", "exotic"),
    ),
    EventTemplate(
        "primordial_bh", "Primordial black holes",
        "Density peaks from the inflationary era collapse directly into black "
        "holes, populating the dark matter halo with hidden singularities.",
        0.5, 1.0, "universe", tags=("structure",),
    ),
    EventTemplate(
        "baryon_anomaly", "Baryon-asymmetry anomaly",
        "An unusually strong matter/antimatter imbalance leaves a dense, "
        "metal-rich medium where the first stars burn fast and die young.",
        0.4, 0.9, "universe", tags=("chemistry",),
    ),
    EventTemplate(
        "dark_energy_surge", "Dark-energy surge",
        "Vacuum energy briefly dominates, accelerating expansion and isolating "
        "young galaxies beyond one another's reach.",
        0.8, 0.9, "universe", tags=("expansion",),
    ),
    EventTemplate(
        "structure_collapse", "Large-scale structure collapse",
        "A rare overdensity pulls a supercluster into a single gravitationally "
        "bound cathedral of galaxies.",
        0.5, 1.0, "universe", tags=("structure",),
    ),
    EventTemplate(
        "gamma_ray_burst", "Hypernova gamma-ray burst",
        "A rotating super-massive star dies as a hypernova, raking nearby "
        "systems with sterilizing radiation.",
        0.7, 1.1, "universe", tags=("radiation",),
    ),
    EventTemplate(
        "galactic_merger", "Galactic merger cascade",
        "Two spiral galaxies collide and merge, quenching star formation and "
        "relocating entire planetary systems.",
        0.5, 1.2, "universe", tags=("structure",),
    ),
    EventTemplate(
        "phase_transition", "Symmetry-breaking phase transition",
        "A late phase transition changes the vacuum expectation values, "
        "nudging chemistry across the entire branch.",
        0.6, 0.7, "universe", tags=("exotic",),
    ),
)

PLANET_EVENTS: Tuple[EventTemplate, ...] = (
    EventTemplate(
        "late_bombardment", "Late heavy bombardment",
        "A rain of leftover planetesimals reshapes the crust and delivers "
        "water and organics in equal measure.",
        0.7, 1.2, "planet", max_age_gyr=1.5, tags=("impact",),
    ),
    EventTemplate(
        "impact_winter", "Impact winter",
        "A body the size of a small moon strikes, throwing enough dust into "
        "the sky to darken the world for centuries.",
        0.8, 1.0, "planet", tags=("impact",),
    ),
    EventTemplate(
        "magnetic_collapse", "Magnetosphere collapse",
        "The core dynamo stalls and the magnetic shield fails, letting the "
        "stellar wind strip the atmosphere away.",
        0.7, 0.9, "planet", tags=("atmosphere",),
    ),
    EventTemplate(
        "runaway_greenhouse", "Runaway greenhouse",
        "Oceans evaporate, water vapour traps heat, and the planet tips into a "
        "permanent furnace state.",
        0.85, 0.9, "planet", tags=("climate",),
    ),
    EventTemplate(
        "snowball", "Snowball epoch",
        "Runaway ice albedo whitens the whole globe; photosynthesis retreats to "
        "a few volcanic refugia.",
        0.6, 1.0, "planet", tags=("climate",),
    ),
    EventTemplate(
        "supervolcano", "Supervolcanic province",
        "A flood-basalt province erupts for a million years, resetting the "
        "climate and enriching the crust in rare metals.",
        0.6, 1.1, "planet", tags=("geology",),
    ),
    EventTemplate(
        "abiogenesis", "First life",
        "Self-replicating chemistry appears in a warm coastal basin and begins "
        "to reshape the atmosphere.",
        0.5, 1.0, "planet", min_habitability=0.35,
        unlock_biosphere="microbial", tags=("life",),
    ),
    EventTemplate(
        "oxygenation", "Great oxygenation",
        "Photosynthesis floods the air with oxygen, poisoning much of the "
        "existing biosphere and enabling complex life.",
        0.5, 0.9, "planet", min_habitability=0.45,
        unlock_biosphere="multicellular", tags=("life", "atmosphere"),
    ),
    EventTemplate(
        "adaptive_radiation", "Adaptive radiation",
        "An empty niche opens and a single lineage explodes into a riot of new "
        "body plans in a geological eyeblink.",
        0.4, 1.0, "planet", min_habitability=0.55,
        unlock_biosphere="complex", tags=("life",),
    ),
    EventTemplate(
        "mass_extinction", "Mass extinction",
        "A compounding crisis erases the majority of species; the survivors "
        "inherit a hollow world.",
        0.8, 1.3, "planet", tags=("life", "cataclysm"),
    ),
    EventTemplate(
        "sapience", "Dawn of sapience",
        "A tool-using, storytelling species emerges and starts asking what the "
        "stars are.",
        0.6, 0.7, "planet", min_habitability=0.7,
        unlock_biosphere="sapient", tags=("life", "civilization"),
    ),
    EventTemplate(
        "civilization", "Civilization rises",
        "Cities, writing and industry appear. The planet acquires a biosphere "
        "that can notice it is being simulated.",
        0.6, 0.6, "planet", min_habitability=0.75,
        unlock_biosphere="sapient", tags=("civilization",),
    ),
    EventTemplate(
        "climate_collapse", "Climate collapse",
        "Runaway feedbacks unravel the biosphere's margin for error, forcing "
        "whatever lives here to adapt fast or vanish.",
        0.85, 1.0, "planet", min_habitability=0.4, tags=("climate", "life"),
    ),
    EventTemplate(
        "orbital_instability", "Orbital destabilization",
        "Resonances with a giant neighbour scatter the planet's orbit, "
        "swinging its climate between extremes.",
        0.6, 0.8, "planet", tags=("orbital",),
    ),
    EventTemplate(
        "stellar_flare", "Stellar superflare",
        "The host star unloads a coronal mass ejection strong enough to strip "
        "an unprotected atmosphere.",
        0.7, 1.0, "planet", tags=("radiation",),
    ),
    EventTemplate(
        "rogue_capture", "Rogue-world capture",
        "A sunless wanderer drifts through the system, perturbing orbits and "
        "briefly heating the outer worlds.",
        0.5, 0.7, "planet", tags=("orbital", "exotic"),
    ),
    EventTemplate(
        "panspermia", "Panspermia vector",
        "A fragment of a neighbouring biosphere, flung free by an impact, "
        "arrives intact enough to seed new chemistry.",
        0.4, 0.6, "planet", min_habitability=0.3, tags=("life", "exotic"),
    ),
)

#: Sorted or not, the generator samples by weight and filters by scope.
EVENT_TEMPLATES: Dict[str, Tuple[EventTemplate, ...]] = {
    "universe": UNIVERSE_EVENTS,
    "planet": PLANET_EVENTS,
}

# ---------------------------------------------------------------------------
# Name generation pools
# ---------------------------------------------------------------------------

GREEK = (
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta",
    "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", "Rho",
    "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega",
)

UNIVERSE_SYLLABLES: Tuple[str, ...] = (
    "Ael", "Vor", "Kyr", "Nym", "Thes", "Ori", "Zan", "Ith", "Lum", "Ser",
    "Dra", "Ely", "Nova", "Quen", "Astr", "Vex", "Mor", "Sol", "Cyn", "Pyx",
    "Hal", "Umb", "Rho", "Ism", "Fen", "Gal", "Tir", "Oph", "Wren", "Ysol",
)
UNIVERSE_SUFFIXES: Tuple[str, ...] = (
    "ia", "os", "ar", "eth", "um", "yn", "is", "or", "ael", "une", "ax", "iel",
)

PLANET_PREFIXES: Tuple[str, ...] = (
    "Thal", "Er", "Gor", "Cy", "Ner", "Aur", "Vel", "Kess", "Mar", "Tyn",
    "Bel", "Osh", "Ryn", "Dal", "Ith", "Zar", "Mor", "Pell", "Syr", "Vael",
)
PLANET_SUFFIXES: Tuple[str, ...] = (
    "assa", "ion", "eth", "ora", "yn", "ix", "une", "ar", "is", "os",
    "terra", "wei", "kai", "mund", "heim", "vale",
)

GASES: Tuple[str, ...] = ("H2", "He", "CH4", "N2", "O2", "CO2", "Ne", "Ar", "H2O", "NH3")

BIOSPHERE_ORDER: Tuple[str, ...] = (
    "sterile", "prebiotic", "microbial", "multicellular", "complex", "sapient",
)

CIVILIZATION_STYLES: Tuple[str, ...] = (
    "crystal-lit", "steppe-borne", "orbital-ring", "deep-ocean", "hive",
    "scholar-caste", "nomadic", "theocratic", "mercantile", "post-biological",
)


def biosphere_rank(stage: str) -> int:
    try:
        return BIOSPHERE_ORDER.index(stage)
    except ValueError:
        return 0


__all__ = [
    "EPOCHS",
    "EventTemplate",
    "UNIVERSE_EVENTS",
    "PLANET_EVENTS",
    "EVENT_TEMPLATES",
    "GREEK",
    "UNIVERSE_SYLLABLES",
    "UNIVERSE_SUFFIXES",
    "PLANET_PREFIXES",
    "PLANET_SUFFIXES",
    "GASES",
    "BIOSPHERE_ORDER",
    "CIVILIZATION_STYLES",
    "biosphere_rank",
]
