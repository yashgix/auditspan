"""Compare extracted facts with the auditor-filed SF-SAC flags."""

from .data import Finding, Form
from .extract import FIELDS, Fact, extract
from .requirements_v2 import requirements_v2
from .rules_v2_1 import extract_v2_1

OUTCOMES = ("silent", "agree", "disagree")
OUTCOMES_V2 = (*OUTCOMES, "a_vs_b", "uncheckable")
AB = {"A", "B"}

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


def requirements_verdict(value: str, form: Form) -> str:
    """SPEC-v2: letters the form lacks are not a disagreement when they are only A versus B, or the form says P."""
    filed = set(form.requirements)
    extra = set(value) - filed
    if not extra:
        return "agree"
    if extra <= AB and filed & AB:
        return "a_vs_b"
    if "P" in filed:
        return "uncheckable"
    return "disagree"


def verdict(field: str, value: str | bool, form: Form, version: str = "v1") -> str:
    if version != "v1" and field == "requirements":
        return requirements_verdict(value, form)
    return "agree" if agrees(field, value, form) else "disagree"


def outcome(fact: Fact | None, form: Form, version: str = "v1") -> str:
    if fact is None:
        return "silent"
    return verdict(fact.field, fact.value, form, version)


def _extract_v2(text: str) -> dict[str, Fact | None]:
    return {**extract(text), "requirements": requirements_v2(text)}


EXTRACT = {"v1": extract, "v2": _extract_v2, "v2.1": extract_v2_1}
VERSIONS = tuple(EXTRACT)


def compare(finding: Finding, version: str = "v1") -> dict[str, tuple[Fact | None, str]]:
    facts = EXTRACT[version](finding.text)
    return {field: (facts[field], outcome(facts[field], finding.form, version)) for field in FIELDS}
