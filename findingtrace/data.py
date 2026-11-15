"""Loading and aggregating the pinned FAC subset."""

import csv
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from . import DATA_DIR


@dataclass(frozen=True)
class Form:
    """The SF-SAC flags for one finding, aggregated across its awards."""

    material_weakness: bool
    significant_deficiency: bool
    repeat: bool
    questioned_costs: bool
    requirements: str
    awards: int
    varies: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    """One finding with its free text and filed form flags."""

    report_id: str
    ref: str
    audit_year: int
    text: str
    form: Form

    @property
    def key(self) -> tuple[str, str]:
        return self.report_id, self.ref


@dataclass(frozen=True)
class Corpus:
    """All usable findings plus row and exclusion counts."""

    findings: tuple[Finding, ...]
    text_rows: int
    form_rows: int
    split_texts: int
    form_only: int


_FLAG_COLUMNS = (
    ("material_weakness", "is_material_weakness"),
    ("significant_deficiency", "is_significant_deficiency"),
    ("repeat", "is_repeat_finding"),
    ("questioned_costs", "is_questioned_costs"),
)
_VARY_COLUMNS = tuple(column for _, column in _FLAG_COLUMNS) + ("type_requirement",)


def make_form(rows: Iterable[Mapping[str, str]]) -> Form:
    """Aggregate one finding's form rows (one per award) into a Form."""
    rows = tuple(rows)

    def any_yes(column: str) -> bool:
        return any(row.get(column) == "Y" for row in rows)

    requirements = "".join(
        sorted({letter for row in rows for letter in (row.get("type_requirement") or "") if letter.isalpha()})
    )
    varies = tuple(column for column in _VARY_COLUMNS if len({row.get(column, "") for row in rows}) > 1)
    return Form(
        material_weakness=any_yes("is_material_weakness"),
        significant_deficiency=any_yes("is_significant_deficiency"),
        repeat=any_yes("is_repeat_finding"),
        questioned_costs=any_yes("is_questioned_costs"),
        requirements=requirements,
        awards=len(rows),
        varies=varies,
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load(data_dir: str | Path = DATA_DIR) -> Corpus:
    """Read the text and form CSVs and keep findings with a single text row and a form."""
    csv.field_size_limit(sys.maxsize)
    folder = Path(data_dir)
    text_data = _read_rows(folder / "findings_text.csv")
    form_data = _read_rows(folder / "findings.csv")

    texts_by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in text_data:
        key = (row["report_id"], row["finding_ref_number"])
        texts_by_key.setdefault(key, []).append(row)

    forms_by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in form_data:
        key = (row["report_id"], row["reference_number"])
        forms_by_key.setdefault(key, []).append(row)

    findings = []
    for key, rows in texts_by_key.items():
        if len(rows) == 1 and key in forms_by_key:
            row = rows[0]
            findings.append(
                Finding(
                    report_id=row["report_id"],
                    ref=row["finding_ref_number"],
                    audit_year=int(row["audit_year"]),
                    text=row["finding_text"],
                    form=make_form(forms_by_key[key]),
                )
            )

    split_texts = sum(1 for rows in texts_by_key.values() if len(rows) > 1)
    form_only = sum(1 for key in forms_by_key if key not in texts_by_key)
    return Corpus(tuple(findings), len(text_data), len(form_data), split_texts, form_only)
