"""Build docs/index.html from docs/index.template.html and the numbers in results/ and data/."""

import argparse
import html
import json
import re
from pathlib import Path

from demo import HELDOUT_ROWS, SEVERITY_VALUES, _first_confirmed, _interval, _pct
from findingtrace import DATA_DIR
from findingtrace.compare import form_value
from findingtrace.data import load
from findingtrace.extract import FIELDS
from findingtrace.labels import load_labels

ROOT = Path(__file__).resolve().parent
FIELD_NAMES = dict(zip(FIELDS, ("severity", "repeat", "questioned costs", "requirements"), strict=True))
SEVERITY_LABELS = [value.replace("_", " ") for value in SEVERITY_VALUES]


def _load(results: Path, name: str) -> dict:
    return json.loads((results / name).read_text(encoding="utf-8"))


def _wilson(rate: dict) -> str:
    interval = _interval(rate["lo"], rate["hi"])
    return f"<b>{_pct(rate['rate'])}</b> <span class=muted>{interval}</span> ({rate['k']}/{rate['n']})"


def _table(head: list[str], rows: list[list[str]]) -> str:
    cells = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{cells}</tr></thead><tbody>{body}</tbody></table></div>'


HELDOUT_HEAD = ["rules", "extracted", "precision", "false positives", "recall, label or title",
                "recall, label or title, P ignored", "recall, all statements"]  # fmt: skip


def _heldout_cells(title: str, s: dict) -> list[str]:
    return [title, str(s["extracted"]), _wilson(s["precision"]), str(s["false_positive"]),
            _wilson(s["recall_label_title"]), _wilson(s["recall_label_title_without_p"]),
            _wilson(s["recall_all"])]  # fmt: skip


def heldout_table(heldout: dict) -> str:
    return _table(HELDOUT_HEAD, [_heldout_cells(title, heldout[key]) for key, title in HELDOUT_ROWS.items()])


def second_model_table(heldout: dict) -> str:
    return _table(
        HELDOUT_HEAD, [_heldout_cells("v2 (frozen) against the second-model labels", heldout["second_model"]["v2"])]
    )


def bars(heldout: dict) -> str:
    out = []
    for key, title in HELDOUT_ROWS.items():
        rate = heldout[key]["recall_label_title"]
        out.append(
            f'<div class="b"><span class="name">{title}</span>'
            f'<span class="track"><span class="fill" style="width:{100 * rate["rate"]:.1f}%"></span></span>'
            f'<span class="v"><b>{_pct(rate["rate"])}</b> ({rate["k"]}/{rate["n"]})</span></div>'
        )
    return "".join(out)


def field_table(metrics: dict, v2: dict, v2_1: dict) -> str:
    rows = []
    for index, field in enumerate(FIELDS):
        m = {"v1": metrics, "v2": v2, "v2.1": v2_1}
        versions = ("v1",) if field != "requirements" else ("v1", "v2", "v2.1")
        for version in versions:
            d = m[version]
            interval = _interval(d["disagree_rate_lo"][index], d["disagree_rate_hi"][index])
            rows.append([FIELD_NAMES[field], version, str(d["covered"][index]), str(d["agree"][index]),
                         str(d["disagree"][index]), f"{_pct(d['disagree_rate'][index])} {interval}",
                         str(d["disagree_reports"][index])])  # fmt: skip
    head = ["field", "rules", "covered", "agree", "disagree", "disagree rate", "reports"]
    return _table(head, rows)


def severity_table(metrics: dict) -> str:
    cells = metrics["severity_text_vs_form"]
    rows = [[f"text: {label}", *map(str, cells[i * 3 : i * 3 + 3])] for i, label in enumerate(SEVERITY_LABELS)]
    return _table(["", "form: material weakness", "form: significant deficiency", "form: none"], rows)


def example(data_dir: Path) -> str:
    findings = {finding.key: finding for finding in load(data_dir).findings}
    finding, fact = _first_confirmed(findings, load_labels(data_dir), ("severity",), "v1")["severity"]
    text_value = html.escape(fact.value.replace("_", " "))
    filed = html.escape(form_value(finding.form, "severity").replace("_", " "))
    key = html.escape(f"{finding.report_id} {finding.ref}")
    return (
        f"<p class=small>Finding <code>{key}</code>. The text says <code>{html.escape(fact.quote)}</code> "
        f"(characters {fact.start} to {fact.end}), so the tool extracts <b>{text_value}</b>. "
        f"The auditor filed <b>{filed}</b> on the form.</p>"
    )


def values(results: Path, data_dir: Path) -> dict[str, str]:
    metrics, v2, v2_1, heldout = (
        _load(results, n) for n in ("metrics.json", "metrics_v2.json", "metrics_v2_1.json", "heldout.json")
    )
    r = FIELDS.index("requirements")
    where = heldout["labels_where"]
    return {
        "findings": f"{metrics['findings']:,}", "reports": f"{metrics['reports']:,}",
        "facts": f"{metrics['facts']:,}", "quoted": f"{metrics['facts_quoted_exactly']:,}",
        "blind_n": str(heldout["findings"]), "drawn": str(heldout["drawn"]),
        "v1_recall": _pct(heldout["v1"]["recall_label_title"]["rate"]),
        "v1_recall_frac": f"{heldout['v1']['recall_label_title']['k']}/{heldout['v1']['recall_label_title']['n']}",
        "v2_recall": _pct(heldout["v2"]["recall_label_title"]["rate"]),
        "v2_recall_frac": f"{heldout['v2']['recall_label_title']['k']}/{heldout['v2']['recall_label_title']['n']}",
        "v2_precision": _pct(heldout["v2"]["precision"]["rate"]),
        "v2_precision_frac": f"{heldout['v2']['precision']['k']}/{heldout['v2']['precision']['n']}",
        "v2_false_positive": str(heldout["v2"]["false_positive"]),
        "v21_false_positive": str(heldout["v2.1"]["false_positive"]),
        "in_sample_frac": f"{v2['correct'][r]}/{v2['stated'][r]}",
        "v2_a_vs_b": str(v2["a_vs_b"][r]), "v2_uncheckable": str(v2["uncheckable"][r]),
        "codex_label": str(where["label"]), "codex_title": str(where["title"]),
        "codex_prose": str(where["prose"]), "codex_none": str(where["none"]),
        "heldout_table": heldout_table(heldout), "bars": bars(heldout),
        "second_model_table": second_model_table(heldout),
        "second_changed": str(heldout["second_model"]["labels_changed"]),
        "field_table": field_table(metrics, v2, v2_1), "severity_table": severity_table(metrics),
        "example": example(data_dir),
    }  # fmt: skip


def build(results: Path = ROOT / "results", data_dir: Path = DATA_DIR) -> str:
    page = (ROOT / "docs" / "index.template.html").read_text(encoding="utf-8")
    for key, value in values(results, data_dir).items():
        page = page.replace("{{" + key + "}}", value)
    left = re.findall(r"\{\{\w+\}\}", page)
    if left:
        raise ValueError(f"unfilled placeholders: {left}")
    return page


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "docs" / "index.html"))
    args = parser.parse_args(argv)
    Path(args.out).write_text(build(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
