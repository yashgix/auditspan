"""Drawing the fixed random and disagreement samples."""

import random
from collections.abc import Iterable

from .compare import compare
from .data import Finding
from .extract import FIELDS

SEED = 20261114
RANDOM_SIZE = 100
PER_FIELD = 12


def random_keys(findings: Iterable[Finding]) -> list[tuple[str, str]]:
    return random.Random(SEED).sample(sorted(finding.key for finding in findings), RANDOM_SIZE)


def disagreement_keys(findings: Iterable[Finding]) -> dict[str, list[tuple[str, str]]]:
    items = tuple(findings)
    taken = set(random_keys(items))
    compared = {finding.key: compare(finding) for finding in items}
    keys: dict[str, list[tuple[str, str]]] = {}
    for index, field in enumerate(FIELDS):
        pool = sorted(key for key, results in compared.items() if results[field][1] == "disagree" and key not in taken)
        drawn = random.Random(SEED + 1 + index).sample(pool, min(PER_FIELD, len(pool)))
        taken.update(drawn)
        keys[field] = drawn
    return keys
