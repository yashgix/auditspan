"""Tests for findingtrace.extract."""

import unittest
from dataclasses import FrozenInstanceError

from findingtrace import DATA_DIR
from findingtrace.data import load
from findingtrace.extract import (
    FIELDS,
    LETTERS_V2,
    MAX_VALUE,
    Fact,
    extract,
    questioned_costs,
    repeat,
    requirement_letters,
    requirements,
    severity,
)


class FactTest(unittest.TestCase):
    def test_frozen(self):
        fact = Fact("severity", "material_weakness", 0, 1, "M")
        with self.assertRaises(FrozenInstanceError):
            fact.value = "significant_deficiency"


class FactTestCase(unittest.TestCase):
    def assert_quote(self, text, fact):
        self.assertIsInstance(fact, Fact)
        self.assertEqual(fact.quote, text[fact.start : fact.end])
        self.assertTrue(fact.quote.strip())


class SeverityTest(FactTestCase):
    def test_singular_kinds(self):
        cases = [
            ("A material weakness was reported.", "material_weakness"),
            ("A significant deficiency was reported.", "significant_deficiency"),
        ]
        for text, value in cases:
            with self.subTest(value=value):
                fact = severity(text)
                self.assertEqual(fact.value, value)
                self.assertEqual(fact.field, "severity")
                self.assert_quote(text, fact)

    def test_first_valid_match(self):
        text = "A material weakness was found; a significant deficiency was also found."
        fact = severity(text)
        self.assertEqual(fact.value, "material_weakness")
        self.assertEqual(fact.quote, "material weakness")

    def test_plural_forms_do_not_match(self):
        self.assertIsNone(severity("Material weaknesses and significant deficiencies were noted."))

    def test_skips_unhelpful_mentions(self):
        cases = [
            "This is not a material weakness.",
            "\u2610 material weakness",
            "material weakness or significant deficiency",
            "A significant deficiency is a deficiency in internal control.",
            "A material weakness over financial reporting.",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertIsNone(severity(text))


class RepeatTest(FactTestCase):
    def test_labelled_yes(self):
        text = "Repeat finding? Yes - prior year."
        fact = repeat(text)
        self.assertIs(fact.value, True)
        self.assertEqual(fact.field, "repeat")
        self.assert_quote(text, fact)

    def test_labelled_no_forms(self):
        for answer in ("No", "N/A", "None", "New"):
            text = f"Repeat finding: {answer}"
            with self.subTest(answer=answer):
                fact = repeat(text)
                self.assertIs(fact.value, False)
                self.assert_quote(text, fact)

    def test_not_in_first_sentence_is_false(self):
        text = "Repeat finding: We did not identify a repeat."
        fact = repeat(text)
        self.assertIs(fact.value, False)

    def test_next_line_value(self):
        text = "Repeat finding:\n   Yes\n"
        fact = repeat(text)
        self.assertIs(fact.value, True)
        self.assertIn("Yes", fact.quote)
        self.assertIn("\n", fact.quote)
        self.assert_quote(text, fact)

    def test_too_long_value_is_skipped(self):
        text = "Repeat finding: " + "x" * (MAX_VALUE + 1)
        self.assertIsNone(repeat(text))

    def test_sentence_fallbacks(self):
        repeat_text = "The auditor said this finding is a repeat of 2024-001."
        fact = repeat(repeat_text)
        self.assertIs(fact.value, True)
        self.assertEqual(fact.quote, "this finding is a repeat")
        self.assert_quote(repeat_text, fact)

        not_repeat_text = "The auditor said this is not a repeat finding."
        fact = repeat(not_repeat_text)
        self.assertIs(fact.value, False)
        self.assertEqual(fact.quote, "not a repeat finding")
        self.assert_quote(not_repeat_text, fact)

    def test_unresolved_label_is_skipped(self):
        text = "Repeat finding: of 2022-007."
        self.assertIsNone(repeat(text))

    def test_sentence_fallback_keeps_exact_span(self):
        text = "Repeat finding of 2022-007."
        fact = repeat(text)
        self.assertIs(fact.value, True)
        self.assertEqual(fact.quote, "Repeat finding of 2022-007")
        self.assert_quote(text, fact)


class QuestionedCostsTest(FactTestCase):
    def test_no_cost_forms(self):
        for answer in ("None", "$0.00", "N/A", "Not applicable", "$ -"):
            text = f"Questioned costs: {answer}"
            with self.subTest(answer=answer):
                fact = questioned_costs(text)
                self.assertIs(fact.value, False)
                self.assert_quote(text, fact)

    def test_amount_with_commas(self):
        text = "Questioned costs: $12,345.67"
        fact = questioned_costs(text)
        self.assertIs(fact.value, True)
        self.assertEqual(fact.quote, text)

    def test_below_threshold_is_skipped(self):
        for answer in ("below the $25,000 threshold", "Less than $25,000"):
            text = f"Questioned costs: {answer}"
            with self.subTest(answer=answer):
                self.assertIsNone(questioned_costs(text))

    def test_next_line_amount(self):
        text = "Questioned costs:\n  $1,000\n"
        fact = questioned_costs(text)
        self.assertIs(fact.value, True)
        self.assertIn("$1,000", fact.quote)
        self.assert_quote(text, fact)

    def test_no_costs_sentence(self):
        for text in ("There were no questioned costs.", "No known questioned costs were identified."):
            fact = questioned_costs(text)
            self.assertIs(fact.value, False)
            self.assert_quote(text, fact)


class RequirementsTest(FactTestCase):
    def test_requirement_letters(self):
        cases = {
            "Allowable Costs \u2013 Time and Effort Reporting": "B",
            "Cash Management \u2013 Reporting": "C",
            "Activities Allowed and Allowable Costs": "AB",
            "Procurement and Suspension and Debarment": "I",
            "General": "",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(requirement_letters(value), expected)

    def test_label_and_dash_rule(self):
        text = "Compliance requirements: Allowable Costs \u2013 Time and Effort Reporting"
        fact = requirements(text)
        self.assertEqual(fact.value, "B")
        self.assert_quote(text, fact)

    def test_letters_sorted(self):
        text = "Compliance requirements: Activities Allowed and Allowable Costs"
        fact = requirements(text)
        self.assertEqual(fact.value, "AB")

    def test_next_line_value(self):
        text = "Compliance requirements:\n  Reporting\n"
        fact = requirements(text)
        self.assertEqual(fact.value, "L")
        self.assertIn("Reporting", fact.quote)
        self.assert_quote(text, fact)

    def test_unrecognised_value_is_none(self):
        self.assertIsNone(requirements("Compliance requirements: General"))


class RequirementsV2Test(unittest.TestCase):
    def test_singular_special_test_is_n(self):
        text = "Compliance Requirement: Special Test and Provision \u2013 Federal Interest in Real Property"
        self.assertEqual(requirements(text).value, "F")
        self.assertEqual(requirements(text, LETTERS_V2).value, "N")

    def test_reporting_package_is_not_reporting(self):
        text = "Compliance Requirement: Data Collection Form and Single Audit Reporting Package"
        self.assertEqual(requirements(text).value, "L")
        self.assertIsNone(requirements(text, LETTERS_V2))
        self.assertEqual(requirements("Compliance Requirement: Reporting", LETTERS_V2).value, "L")

    def test_extract_passes_letters_to_requirements_only(self):
        text = "Compliance Requirement: Special Test and Provisions"
        self.assertIsNone(extract(text)["requirements"])
        self.assertEqual(extract(text, LETTERS_V2)["requirements"].value, "N")


class ExtractTest(FactTestCase):
    def test_empty_prose(self):
        facts = extract("Nothing to see here.")
        self.assertEqual(tuple(facts), FIELDS)
        self.assertTrue(all(fact is None for fact in facts.values()))

    def test_all_fields(self):
        text = (
            "Material weakness in controls.\n"
            "Repeat finding: Yes\n"
            "Questioned costs: $1,000\n"
            "Compliance requirements: Reporting\n"
        )
        facts = extract(text)
        self.assertEqual(facts["severity"].value, "material_weakness")
        self.assertIs(facts["repeat"].value, True)
        self.assertIs(facts["questioned_costs"].value, True)
        self.assertEqual(facts["requirements"].value, "L")
        for field, fact in facts.items():
            with self.subTest(field=field):
                self.assertEqual(fact.field, field)
                self.assert_quote(text, fact)


@unittest.skipUnless(
    (DATA_DIR / "findings_text.csv").is_file() and (DATA_DIR / "findings.csv").is_file(),
    f"pinned FAC data not found in {DATA_DIR}",
)
class RealCorpusTest(unittest.TestCase):
    def test_facts_quote_source_text(self):
        corpus = load()
        for finding in corpus.findings:
            for field, fact in extract(finding.text).items():
                if fact is None:
                    continue
                self.assertEqual(fact.field, field)
                self.assertEqual(fact.quote, finding.text[fact.start : fact.end])
                self.assertTrue(fact.quote.strip())
