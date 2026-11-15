"""Loading the labelled sample and scoring extraction against it."""

import json
from collections.abc import Iterable, Mapping
from pathlib import Path

from . import DATA_DIR
from .compare import compare, verdict
from .data import Finding
from .extract import FIELDS

_COUNTS = ("extracted", "correct", "stated", "found", "flagged", "confirmed")


def load_labels(data_dir: str | Path = DATA_DIR) -> list[dict]:
    return json.loads((Path(data_dir) / "labels.json").read_text(encoding="utf-8"))["findings"]


def evaluate(findings: Iterable[Finding], rows: Iterable[Mapping], v2: bool = False) -> dict[str, dict[str, int]]:
    by_key = {finding.key: finding for finding in findings}
    counts = {field: dict.fromkeys(_COUNTS, 0) for field in FIELDS}
    for row in rows:
        finding = by_key.get((row["report_id"], row["ref"]))
        if finding is None:
            continue
        results = compare(finding, v2)
        labels = row["labels"]
        for field in labels:
            if field not in counts:
                continue
            fact, result = results[field]
            label = labels[field]
            if row["stratum"] == "random":
                if fact is not None:
                    counts[field]["extracted"] += 1
                if label is not None:
                    counts[field]["stated"] += 1
                correct = label is not None and fact is not None and fact.value == label
                if correct:
                    counts[field]["correct"] += 1
                    counts[field]["found"] += 1
            if result == "disagree":
                counts[field]["flagged"] += 1
                if label is not None and verdict(field, label, finding.form, v2) == "disagree":
                    counts[field]["confirmed"] += 1
    return counts
