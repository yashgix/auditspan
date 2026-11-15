"""Experiment metrics for findingtrace."""

import json
from pathlib import Path

import numpy as np

from . import DATA_DIR, heldout
from .compare import FORM_COLUMNS, OUTCOMES, OUTCOMES_V2, compare, form_value
from .data import Corpus, load
from .extract import FIELDS
from .labels import evaluate, load_labels
from .sample import SEED
from .stats import report_bootstrap, wilson

REPLICATES = 2000
SEVERITY_CELLS = tuple(
    f"{text}__{form}"
    for text in ("material_weakness", "significant_deficiency")
    for form in ("material_weakness", "significant_deficiency", "none")
)
_EVALUATE_COUNTS = ("extracted", "correct", "stated", "found", "flagged", "confirmed")
_QUALITY = (
    ("precision", "correct", "extracted"),
    ("recall", "found", "stated"),
    ("flag_precision", "confirmed", "flagged"),
)


def _round6(value: float) -> float:
    return round(float(value), 6)


def _rate(part: int, whole: int) -> float:
    return part / whole if whole else 0.0


def summarize(corpus: Corpus, rows, version: str = "v1") -> dict:
    """Compute all experiment metrics for one corpus and label set (v2 and later add the SPEC-v2 outcome counts)."""
    rows = tuple(rows)
    findings = corpus.findings
    report_ids = sorted({finding.report_id for finding in findings})
    report_index = {report_id: index for index, report_id in enumerate(report_ids)}
    covered_matrix = np.zeros((len(report_ids), len(FIELDS)), dtype=int)
    disagree_matrix = np.zeros_like(covered_matrix)
    covered = [0] * len(FIELDS)
    agree = [0] * len(FIELDS)
    disagree = [0] * len(FIELDS)
    form_varies = [0] * len(FIELDS)
    other = {name: [0] * len(FIELDS) for name in OUTCOMES_V2 if name not in OUTCOMES}
    severity_counts = dict.fromkeys(SEVERITY_CELLS, 0)
    facts = 0
    quoted = 0

    for finding in findings:
        results = compare(finding, version)
        row = report_index[finding.report_id]
        for column, field in enumerate(FIELDS):
            fact, verdict = results[field]
            if fact is not None:
                covered[column] += 1
                covered_matrix[row, column] += 1
                facts += 1
                if fact.quote == finding.text[fact.start : fact.end] and fact.quote.strip():
                    quoted += 1
            if verdict == "agree":
                agree[column] += 1
            elif verdict == "disagree":
                disagree[column] += 1
                disagree_matrix[row, column] += 1
            elif verdict in other:
                other[verdict][column] += 1
            if any(name in finding.form.varies for name in FORM_COLUMNS[field]):
                form_varies[column] += 1
        severity_fact = results["severity"][0]
        if severity_fact is not None:
            cell = f"{severity_fact.value}__{form_value(finding.form, 'severity')}"
            if cell in severity_counts:
                severity_counts[cell] += 1

    lower, upper = report_bootstrap(disagree_matrix, covered_matrix, REPLICATES, SEED)
    metrics = {
        "text_rows": int(corpus.text_rows),
        "form_rows": int(corpus.form_rows),
        "findings": len(findings),
        "reports": len(report_ids),
        "split_texts": int(corpus.split_texts),
        "form_only_findings": int(corpus.form_only),
        "labelled": len(rows),
        "labelled_random": sum(1 for row in rows if row.get("stratum") == "random"),
        "replicates": REPLICATES,
        "facts": facts,
        "facts_quoted_exactly": quoted,
        "covered": [int(value) for value in covered],
        "agree": [int(value) for value in agree],
        "disagree": [int(value) for value in disagree],
        "disagree_reports": [int((disagree_matrix[:, column] > 0).sum()) for column in range(len(FIELDS))],
        "disagree_rate": [_round6(_rate(disagree[index], covered[index])) for index in range(len(FIELDS))],
        "disagree_rate_lo": [_round6(value) for value in lower],
        "disagree_rate_hi": [_round6(value) for value in upper],
        "form_varies": [int(value) for value in form_varies],
    }

    if version != "v1":
        metrics.update(other)

    evaluation = evaluate(findings, rows, version)
    for count in _EVALUATE_COUNTS:
        metrics[count] = [int(evaluation[field][count]) for field in FIELDS]
    for name, numerator, denominator in _QUALITY:
        intervals = [wilson(evaluation[field][numerator], evaluation[field][denominator]) for field in FIELDS]
        metrics[name] = [_round6(value[0]) for value in intervals]
        metrics[f"{name}_lo"] = [_round6(value[1]) for value in intervals]
        metrics[f"{name}_hi"] = [_round6(value[2]) for value in intervals]
    metrics["severity_text_vs_form"] = [int(severity_counts[cell]) for cell in SEVERITY_CELLS]
    return metrics


def _write(metrics: dict, out) -> dict:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    return metrics


def main(data_dir=DATA_DIR, out="results/metrics.json", version: str = "v1") -> dict:
    """Load the pinned data, compute the metrics, and write them as JSON."""
    return _write(summarize(load(data_dir), load_labels(data_dir), version), out)


def main_heldout(data_dir=DATA_DIR, heldout_dir=heldout.HELDOUT_DIR, out="results/heldout.json") -> dict:
    """Score each version's requirements on the blind hold-out and write them as JSON."""
    labels, dev_ids = heldout.load_heldout(heldout_dir), heldout.load_dev_ids(heldout_dir)
    return _write(heldout.score(load(data_dir).findings, labels, dev_ids), out)
