"""Small sampling helpers shared by the generators."""
from __future__ import annotations

import random
from typing import Sequence, TypeVar

from .models import clamp

T = TypeVar("T")


def weighted_choice(rng: random.Random, items: Sequence[T], weights: Sequence[float]) -> T:
    """Pick one item with probability proportional to its weight."""
    total = float(sum(weights))
    if total <= 0:
        return rng.choice(list(items))
    target = rng.random() * total
    upto = 0.0
    for item, weight in zip(items, weights):
        upto += float(weight)
        if upto >= target:
            return item
    return items[-1]


def sample_range(rng: random.Random, bounds: Sequence[int]) -> int:
    """Inclusive integer sample from a (low, high) pair or a scalar."""
    if isinstance(bounds, int):
        return bounds
    low, high = int(bounds[0]), int(bounds[-1])
    if high < low:
        low, high = high, low
    return rng.randint(low, high)


def gaussian_clamped(
    rng: random.Random, mu: float, sigma: float, low: float, high: float
) -> float:
    return clamp(rng.gauss(mu, sigma), low, high)


def log_uniform(rng: random.Random, low: float, high: float) -> float:
    import math

    return math.exp(rng.uniform(math.log(low), math.log(high)))


__all__ = ["weighted_choice", "sample_range", "gaussian_clamped", "log_uniform"]
