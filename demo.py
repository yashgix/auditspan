"""Render the generated results block and a summary."""

import argparse
import json
from pathlib import Path

from findingtrace import DATA_DIR
from findingtrace.compare import compare, form_value, verdict
from findingtrace.data import load
from findingtrace.extract import FIELDS
from findingtrace.labels import load_labels

START = "<!-- results:start -->"
END = "<!-- results:end -->"
DEFAULT_RESULTS = "results"
FIELD_LABELS = {
    "severity": "severity",
    "repeat": "repeat",
    "questioned_costs": "questioned costs",
    "requirements": "requirements",
}
SEVERITY_VALUES = ("material_weakness", "significant_deficiency")
FORM_VALUES = ("material_weakness", "significant_deficiency", "none")


def _text(value: str | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def _interval(lo: float, hi: float) -> str:
    return f"[{_pct(lo)}, {_pct(hi)}]"


def _corpus_line(metrics: dict) -> str:
    return (
        f"Corpus: {metrics['findings']} findings in {metrics['reports']} reports; "
        f"{metrics['text_rows']} text rows, {metrics['form_rows']} form rows; "
        f"{metrics['split_texts']} split texts and {metrics['form_only_findings']} form-only findings left out; "
        f"{metrics['facts']} cited facts, {metrics['facts_quoted_exactly']} of them an exact copy of their source "
        "span (this checks the copying, not that each quote supports its fact)."
    )


def _comparison_line(metrics: dict, field: str) -> str:
    index = FIELDS.index(field)
    rate = metrics["disagree_rate"][index]
    interval = _interval(metrics["disagree_rate_lo"][index], metrics["disagree_rate_hi"][index])
    return (
        f"- {FIELD_LABELS[field]}: {metrics['covered'][index]} covered, {metrics['agree'][index]} agree, "
        f"{metrics['disagree'][index]} disagree ({_pct(rate)} {interval}); "
        f"{metrics['disagree_reports'][index]} reports; {metrics['form_varies'][index]} form rows differ."
    )


def _score(metrics: dict, name: str, index: int, numerator: str, denominator: str) -> str:
    interval = _interval(metrics[f"{name}_lo"][index], metrics[f"{name}_hi"][index])
    return f"{_pct(metrics[name][index])} {interval} ({metrics[numerator][index]}/{metrics[denominator][index]})"


def _quality_line(metrics: dict, field: str) -> str:
    index = FIELDS.index(field)
    return (
        f"- {FIELD_LABELS[field]}: precision {_score(metrics, 'precision', index, 'correct', 'extracted')}; "
        f"recall {_score(metrics, 'recall', index, 'found', 'stated')}; "
        f"confirmed flags {_score(metrics, 'flag_precision', index, 'confirmed', 'flagged')}."
    )


def _severity_lines(metrics: dict) -> list[str]:
    cells = metrics["severity_text_vs_form"]
    lines = [
        "| text / form | material weakness | significant deficiency | none |",
        "| --- | --- | --- | --- |",
    ]
    width = len(FORM_VALUES)
    for text_index, text in enumerate(SEVERITY_VALUES):
        values = [str(cells[text_index * width + form_index]) for form_index in range(width)]
        lines.append("| " + " | ".join([text.replace("_", " "), *values]) + " |")
    return lines


def _cell(value: str) -> str:
    return value.replace("|", "&#124;")


def _first_confirmed(findings: dict, rows: list[dict], fields: tuple, v2: bool) -> dict[str, tuple]:
    """The first labels.json row per field that is flagged and whose label also contradicts the form."""
    found = {}
    for row in rows:
        finding = findings.get((row["report_id"], row["ref"]))
        if finding is None:
            continue
        results = compare(finding, v2)
        for field in fields:
            label = row.get("labels", {}).get(field)
            if field in found or label is None:
                continue
            fact, result = results[field]
            if result == "disagree" and verdict(field, label, finding.form, v2) == "disagree":
                found[field] = (finding, fact)
    return found


def _row(field: str, finding, fact, *extra: str) -> str:
    cells = (
        FIELD_LABELS[field],
        f"{finding.report_id} {finding.ref}",
        _cell(_text(fact.value)),
        _cell(_text(form_value(finding.form, field))),
        _cell(" ".join(fact.quote.split())),
        *extra,
    )
    return "| " + " | ".join(cells) + " |"


def _v1_disagreement_lines(findings: dict, rows: list[dict]) -> list[str]:
    found = _first_confirmed(findings, rows, FIELDS, v2=False)
    lines = [
        "| field | finding | text value | form value | quote | v2 outcome |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for field in FIELDS:
        if field not in found:
            lines.append(f"| {FIELD_LABELS[field]} | none | - | - | - | - |")
            continue
        finding, fact = found[field]
        lines.append(_row(field, finding, fact, compare(finding, v2=True)[field][1]))
    return lines


def _v2_lines(metrics: dict, findings: dict, rows: list[dict]) -> list[str]:
    index = FIELDS.index("requirements")
    lines = [
        "### Version 2: requirements (SPEC-v2.md; the other fields are as in version 1)",
        _comparison_line(metrics, "requirements"),
        f"- requirements outcomes not counted as disagreements: {metrics['a_vs_b'][index]} differ only in A versus "
        f"B, {metrics['uncheckable'][index]} uncheckable (the form says P, Other).",
        "",
        "Labelled sample, version 2:",
        _quality_line(metrics, "requirements"),
        "",
        "| field | finding | text value | form value | quote |",
        "| --- | --- | --- | --- | --- |",
    ]
    found = _first_confirmed(findings, rows, ("requirements",), v2=True)
    if "requirements" in found:
        lines.append(_row("requirements", *found["requirements"]))
    else:
        lines.append("| requirements | none | - | - | - |")
    return lines


def render_block(metrics: dict, data_dir=DATA_DIR, metrics_v2: dict | None = None) -> str:
    findings = {finding.key: finding for finding in load(data_dir).findings}
    rows = load_labels(data_dir)
    lines = [
        _corpus_line(metrics),
        "",
        "### Text versus form, per field",
        *(_comparison_line(metrics, field) for field in FIELDS),
        "",
        "### Labelled sample",
        "Labels: labelled by Claude from the text, not by an auditor.",
        *(_quality_line(metrics, field) for field in FIELDS),
        "",
        "### Severity: text versus form",
        *_severity_lines(metrics),
        "",
        "### First confirmed disagreement per field",
        *_v1_disagreement_lines(findings, rows),
    ]
    if metrics_v2 is not None:
        lines += ["", *_v2_lines(metrics_v2, findings, rows)]
    return chr(10).join(lines)


def replace_block(document: str, block: str) -> str:
    start = document.find(START)
    if start < 0:
        raise ValueError("README results markers not found")
    end = document.find(END, start + len(START))
    if end < 0:
        raise ValueError("README results markers not found")
    separator = chr(10)
    return f"{document[:start]}{START}{separator}{block}{separator}{END}{document[end + len(END) :]}"


def _summary(metrics: dict) -> str:
    findings = metrics["findings"]
    reports = metrics["reports"]
    facts = metrics["facts"]
    disagreements = metrics["disagree"][0]
    return f"{findings} findings across {reports} reports; {facts} cited facts; {disagreements} severity disagreements."


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=DEFAULT_RESULTS)
    parser.add_argument("--readme")
    parser.add_argument("--out")
    parser.add_argument("--data", default=DATA_DIR)
    args = parser.parse_args(argv)
    metrics = json.loads((Path(args.results) / "metrics.json").read_text(encoding="utf-8"))
    if args.readme is None:
        print(_summary(metrics))
        return 0
    if args.out is None:
        parser.error("--out is required with --readme")
    document = Path(args.readme).read_text(encoding="utf-8")
    v2_path = Path(args.results) / "metrics_v2.json"
    metrics_v2 = json.loads(v2_path.read_text(encoding="utf-8")) if v2_path.is_file() else None
    block = render_block(metrics, args.data, metrics_v2)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(replace_block(document, block), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
