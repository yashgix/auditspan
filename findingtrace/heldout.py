"""Score the v1 and v2 requirements extractors on the blind hold-out labelled by an independent model."""

import json
from collections import Counter
from pathlib import Path

from .compare import AB, requirements_verdict
from .data import Finding
from .extract import requirements
from .requirements_v2 import requirements_v2
from .stats import wilson

HELDOUT_DIR = Path(__file__).resolve().parent.parent / "study" / "heldout"
LABEL_FILE = "labels-codex.jsonl"
EXTRACTORS = {"v1": requirements, "v2": requirements_v2}
# "label_title" matches how data/labels.json defines a stated requirement. "all" adds body sentences.
SCOPES = {"label_title": ("label", "title"), "all": ("label", "title", "prose")}


def load_heldout(folder: str | Path = HELDOUT_DIR) -> list[dict]:
    with (Path(folder) / LABEL_FILE).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def stated(label: dict, scope: str, drop_p: bool = False) -> str:
    """The label's letters if stated within the scope, else ''. drop_p ignores P (Other), which no rule emits."""
    if label["letters"] == "none" or label["where"] not in SCOPES[scope]:
        return ""
    letters = label["letters"]
    return letters.replace("P", "") if drop_p else letters


def _rate(k: int, n: int) -> dict:
    rate, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(rate, 6), "lo": round(lo, 6), "hi": round(hi, 6)}


def _only_a_vs_b(value: str, label: str) -> bool:
    return bool(value) and bool(label) and value != label and set(value) ^ set(label) <= AB


def score_extractor(pairs: list[tuple[Finding, dict]], extractor) -> dict:
    values = [(finding, label, fact.value if (fact := extractor(finding.text)) else "") for finding, label in pairs]
    extracted = [(finding, value, stated(label, "all")) for finding, label, value in values if value]
    result = {
        "extracted": len(extracted),
        "precision": _rate(sum(value == truth for _, value, truth in extracted), len(extracted)),
        "false_positive": sum(not truth for _, _, truth in extracted),
        "a_vs_b_only": sum(_only_a_vs_b(value, truth) for _, value, truth in extracted),
        "form": dict(Counter(requirements_verdict(value, finding.form) for finding, value, _ in extracted)),
    }
    for scope in SCOPES:
        for drop_p in (False, True):
            name = f"recall_{scope}" + ("_without_p" if drop_p else "")
            hits = [value == want for _, label, value in values if (want := stated(label, scope, drop_p))]
            result[name] = _rate(sum(hits), len(hits))
    return result


def score(findings, labels: list[dict]) -> dict:
    by_key = {f"{finding.report_id} {finding.ref}": finding for finding in findings}
    pairs = [(by_key[label["id"]], label) for label in labels]
    result = {name: score_extractor(pairs, extractor) for name, extractor in EXTRACTORS.items()}
    result["findings"] = len(pairs)
    result["labels_where"] = dict(Counter(label["where"] for label in labels))
    result["labels_with_p"] = sum("P" in label["letters"] for label in labels)
    result["labels_vs_form"] = dict(
        Counter(requirements_verdict(label["letters"], f.form) for f, label in pairs if label["letters"] != "none")
    )
    return result
