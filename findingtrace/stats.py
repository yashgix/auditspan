"""Wilson intervals and a report-level bootstrap."""

from math import sqrt
from statistics import NormalDist

import numpy as np


def wilson(k: int, n: int) -> tuple[float, float, float]:
    if n == 0:
        return (0.0, 0.0, 1.0)
    z = NormalDist().inv_cdf(0.975)
    rate = float(k / n)
    denominator = 1.0 + z * z / n
    centre = (rate + z * z / (2.0 * n)) / denominator
    half = z * sqrt(rate * (1.0 - rate) / n + z * z / (4.0 * n * n)) / denominator
    return (rate, max(0.0, centre - half), min(1.0, centre + half))


def report_bootstrap(hits: np.ndarray, totals: np.ndarray, replicates: int, seed: int):
    hits = np.asarray(hits, dtype=float)
    totals = np.asarray(totals, dtype=float)
    n = hits.shape[0]
    rng = np.random.default_rng(seed)
    rates = np.empty((replicates, hits.shape[1]), dtype=float)
    for index in range(replicates):
        weights = np.bincount(rng.integers(0, n, n), minlength=n)
        rates[index] = weights @ hits / np.maximum(weights @ totals, 1)
    lo, hi = np.percentile(rates, [2.5, 97.5], axis=0)
    return lo, hi