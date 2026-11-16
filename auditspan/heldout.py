"""Score each version's requirements extractor on the blind hold-out labelled by an independent model."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from .compare import AB, requirements_verdict
from .data import Finding
from .extract import requirements
from .requirements_v2 import requirements_v2
from .rules_v2_1 import requirements_v2_1
from .stats import wilson

HELDOUT_DIR = Path(__file__).resolve().parent.parent / "study" / "heldout"
LABEL_FILE = "labels-codex.jsonl"
DEV_FILE = "dev-ids.jsonl"
# A second, non-blind label set for 30 disputed findings (study/adjudication/README.md). Never the headline.
ADJUDICATION_DIR = HELDOUT_DIR.parent / "adjudication"
DECISIONS_FILE = "decisions.jsonl"
# v2.1 was written after reviewing hold-out errors, so its hold-out scores are not blind.
EXTRACTORS = {"v1": requirements, "v2": requirements_v2, "v2.1": requirements_v2_1}
# "label_title" matches how data/labels.json defines a stated requirement. "all" adds body sentences.
SCOPES = {"label_title": ("label", "title"), "all": ("label", "title", "prose")}


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def load_heldout(folder: str | Path = HELDOUT_DIR) -> list[dict]:
    return _read_jsonl(Path(folder) / LABEL_FILE)


def load_dev_ids(folder: str | Path = HELDOUT_DIR) -> set[str]:
    return {f"{row['report_id']} {row['ref']}" for row in _read_jsonl(Path(folder) / DEV_FILE)}


def load_decisions(folder: str | Path = ADJUDICATION_DIR) -> list[dict]:
    return _read_jsonl(Path(folder) / DECISIONS_FILE)


def adjudicate(labels: list[dict], decisions: list[dict]) -> list[dict]:
    """The labels with each decision's resulting letters and location applied."""
    result = {row["id"]: row["result"] for row in decisions}
    return [label | result[label["id"]] if label["id"] in result else label for label in labels]


def text_hash(finding: Finding) -> str:
    return hashlib.sha256(finding.text.encode("utf-8")).hexdigest()


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


def score(findings, labels: list[dict], dev_ids: set[str], decisions: list[dict] | None = None) -> dict:
    """Findings whose text equals a development finding's text are left out, since that text was seen."""
    by_key = {f"{finding.report_id} {finding.ref}": finding for finding in findings}
    seen = {text_hash(by_key[key]) for key in dev_ids}
    pairs = [(by_key[label["id"]], label) for label in labels]
    duplicates = [label["id"] for finding, label in pairs if text_hash(finding) in seen]
    pairs = [(finding, label) for finding, label in pairs if label["id"] not in duplicates]
    result = {name: score_extractor(pairs, extractor) for name, extractor in EXTRACTORS.items()}
    result["drawn"] = len(labels)
    result["findings"] = len(pairs)
    result["duplicate_text_left_out"] = duplicates
    result["labels_where"] = dict(Counter(label["where"] for _, label in pairs))
    result["labels_with_p"] = sum("P" in label["letters"] for _, label in pairs)
    result["labels_vs_form"] = dict(
        Counter(requirements_verdict(label["letters"], f.form) for f, label in pairs if label["letters"] != "none")
    )
    if decisions:
        adjusted = adjudicate([label for _, label in pairs], decisions)
        second = list(zip([finding for finding, _ in pairs], adjusted, strict=True))
        changed = sum(a != b for (_, a), b in zip(pairs, adjusted, strict=True))
        result["second_model"] = {"v2": score_extractor(second, requirements_v2), "labels_changed": changed}
    return result
