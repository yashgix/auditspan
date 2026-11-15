"""Compare extracted facts with the auditor-filed SF-SAC flags."""

from .data import Finding, Form
from .extract import FIELDS, Fact, extract

OUTCOMES = ("silent", "agree", "disagree")

FORM_COLUMNS = {
    "severity": ("is_material_weakness", "is_significant_deficiency"),
    "repeat": ("is_repeat_finding",),
    "questioned_costs": ("is_questioned_costs",),
    "requirements": ("type_requirement",),
}


def form_value(form: Form, field: str) -> str | bool:
    if field == "severity":
        if form.material_weakness:
            return "material_weakness"
        if form.significant_deficiency:
            return "significant_deficiency"
        return "none"
    if field == "repeat":
        return form.repeat
    if field == "questioned_costs":
        return form.questioned_costs
    if field == "requirements":
        return form.requirements
    raise ValueError(f"unknown field: {field}")


def agrees(field: str, value: str | bool, form: Form) -> bool:
    if field == "requirements":
        return set(value) <= set(form.requirements)
    return value == form_value(form, field)


def outcome(fact: Fact | None, form: Form) -> str:
    if fact is None:
        return "silent"
    return "agree" if agrees(fact.field, fact.value, form) else "disagree"


def compare(finding: Finding) -> dict[str, tuple[Fact | None, str]]:
    facts = extract(finding.text)
    return {field: (facts[field], outcome(facts[field], finding.form)) for field in FIELDS}
