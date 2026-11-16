"""Tests for auditspan.compare."""

import unittest

from auditspan.compare import (
    FORM_COLUMNS,
    OUTCOMES,
    OUTCOMES_V2,
    agrees,
    compare,
    form_value,
    outcome,
    requirements_verdict,
)
from auditspan.data import Finding, Form
from auditspan.extract import FIELDS, Fact


def make_form(
    *,
    material: bool = False,
    significant: bool = False,
    repeat: bool = False,
    questioned: bool = False,
    requirements: str = "",
) -> Form:
    return Form(
        material_weakness=material,
        significant_deficiency=significant,
        repeat=repeat,
        questioned_costs=questioned,
        requirements=requirements,
        awards=1,
        varies=(),
    )


def make_fact(field: str, value: str | bool) -> Fact:
    return Fact(field, value, 0, 1, "x")


class FormValueTest(unittest.TestCase):
    def test_severity_falls_back(self):
        self.assertEqual(form_value(make_form(), "severity"), "none")
        self.assertEqual(form_value(make_form(significant=True), "severity"), "significant_deficiency")
        self.assertEqual(form_value(make_form(material=True, significant=True), "severity"), "material_weakness")

    def test_other_fields_are_form_attributes(self):
        form = make_form(repeat=True, questioned=True, requirements="AB")
        self.assertIs(form_value(form, "repeat"), True)
        self.assertIs(form_value(form, "questioned_costs"), True)
        self.assertEqual(form_value(form, "requirements"), "AB")


class AgreesTest(unittest.TestCase):
    def test_requirements_is_one_way(self):
        form = make_form(requirements="AB")
        self.assertTrue(agrees("requirements", "A", form))
        self.assertTrue(agrees("requirements", "", form))
        self.assertFalse(agrees("requirements", "ABC", form))

    def test_other_fields_match_exactly(self):
        form = make_form(significant=True, repeat=True, requirements="L")
        self.assertTrue(agrees("severity", "significant_deficiency", form))
        self.assertFalse(agrees("severity", "material_weakness", form))
        self.assertTrue(agrees("repeat", True, form))
        self.assertFalse(agrees("repeat", False, form))
        self.assertTrue(agrees("questioned_costs", False, form))
        self.assertTrue(agrees("requirements", "L", form))


class OutcomeTest(unittest.TestCase):
    def test_silent(self):
        self.assertEqual(outcome(None, make_form()), "silent")

    def test_agree_and_disagree(self):
        form = make_form(material=True)
        self.assertEqual(outcome(make_fact("severity", "material_weakness"), form), "agree")
        self.assertEqual(outcome(make_fact("severity", "significant_deficiency"), form), "disagree")

    def test_requirements_use_agrees(self):
        form = make_form(requirements="AB")
        self.assertEqual(outcome(make_fact("requirements", "A"), form), "agree")
        self.assertEqual(outcome(make_fact("requirements", "AC"), form), "disagree")


class RequirementsVerdictTest(unittest.TestCase):
    def test_categories(self):
        cases = [
            ("A", "AB", "agree"),
            ("AB", "B", "a_vs_b"),
            ("B", "AE", "a_vs_b"),
            ("AB", "E", "disagree"),
            ("L", "P", "uncheckable"),
            ("AB", "BP", "a_vs_b"),
            ("N", "EL", "disagree"),
        ]
        for value, filed, expected in cases:
            with self.subTest(value=value, filed=filed):
                self.assertEqual(requirements_verdict(value, make_form(requirements=filed)), expected)

    def test_v2_changes_only_requirements(self):
        form = make_form(significant=True, requirements="B")
        self.assertEqual(outcome(make_fact("requirements", "AB"), form), "disagree")
        self.assertEqual(outcome(make_fact("requirements", "AB"), form, version="v2"), "a_vs_b")
        self.assertEqual(outcome(make_fact("severity", "material_weakness"), form, version="v2"), "disagree")

    def test_compare_v2_uses_v2_letters(self):
        text = "Compliance Requirement: Data Collection Form and Single Audit Reporting Package"
        finding = Finding("R", "1", 2024, text, make_form(requirements="N"))
        self.assertEqual(compare(finding)["requirements"][1], "disagree")
        self.assertEqual(compare(finding, version="v2")["requirements"], (None, "silent"))
        self.assertEqual(OUTCOMES_V2, ("silent", "agree", "disagree", "a_vs_b", "uncheckable"))


class CompareTest(unittest.TestCase):
    def test_order_and_agreement(self):
        text = (
            "Material weakness in controls.\n"
            "Repeat finding: Yes\n"
            "Questioned costs: $1,000\n"
            "Compliance requirements: Reporting\n"
        )
        form = make_form(material=True, repeat=True, questioned=True, requirements="L")
        result = compare(Finding("R", "1", 2024, text, form))
        self.assertEqual(tuple(result), FIELDS)
        for field in FIELDS:
            with self.subTest(field=field):
                fact, verdict = result[field]
                self.assertIsNotNone(fact)
                self.assertEqual(verdict, "agree")

    def test_empty_text_is_silent(self):
        result = compare(Finding("R", "1", 2024, "Nothing to see here.", make_form()))
        self.assertEqual(tuple(result), FIELDS)
        for fact, verdict in result.values():
            self.assertIsNone(fact)
            self.assertEqual(verdict, "silent")


class ConstantsTest(unittest.TestCase):
    def test_outcomes_and_form_columns(self):
        self.assertEqual(OUTCOMES, ("silent", "agree", "disagree"))
        self.assertEqual(
            FORM_COLUMNS,
            {
                "severity": ("is_material_weakness", "is_significant_deficiency"),
                "repeat": ("is_repeat_finding",),
                "questioned_costs": ("is_questioned_costs",),
                "requirements": ("type_requirement",),
            },
        )
