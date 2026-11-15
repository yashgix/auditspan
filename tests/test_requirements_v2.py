"""Tests for findingtrace.requirements_v2 (SPEC-v2)."""

import unittest

from findingtrace.extract import requirements
from findingtrace.requirements_v2 import letters_v2, requirements_v2


def value(text):
    fact = requirements_v2(text)
    if fact is not None:
        assert fact.quote == text[fact.start : fact.end]
    return fact and fact.value


class LettersTest(unittest.TestCase):
    def test_names(self):
        cases = {
            "Special Test and Provision – Federal Interest in Real Property": "N",
            "Allowable Activities and Costs": "AB",
            "Allowable Costs and Activities": "AB",
            "Eligibility and Allowable Activities/Costs": "ABE",
            "Activities Allowed or Unallowed": "A",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(letters_v2(text), expected)

    def test_explicit_codes_win(self):
        self.assertEqual(letters_v2("Special Tests and Provisions - Reporting (L.)"), "L")
        self.assertEqual(letters_v2("A-Allowable Costs - Significant Deficiency"), "A")
        self.assertEqual(letters_v2("N – Special Tests and Provisions"), "N")
        self.assertEqual(letters_v2("A-Allowable Costs", lead_code=False), "B")

    def test_phrases_that_are_not_requirements(self):
        for text in (
            "Data Collection Form and Single Audit Reporting Package",
            "SEFA Reporting",
            "Financial Statement Close and Reporting Process",
            "Internal Control over Financial Reporting",
            "Uniform Administrative Requirements, Cost Principles, and Audit Requirements",
        ):
            with self.subTest(text=text):
                self.assertEqual(letters_v2(text), "")
        self.assertEqual(letters_v2("Federal Financial Reporting"), "L")


# Four lines first, so a match must come from the label rule, not the title rule.
PROSE = "Criteria: a\nCondition: b\nCause: c\nEffect: d\n"


class LabelTest(unittest.TestCase):
    def test_v1_label_first(self):
        text = "2024-001 – Eligibility\nCompliance Requirement: Reporting\n"
        self.assertEqual(value(text), "L")

    def test_more_label_wordings(self):
        cases = {
            "Area:\tEligibility": "E",
            "Requirement: \t\tReporting": "L",
            "CONTROL CATEGORY: Equipment and Real Property Management, Subrecipient Monitoring": "FM",
            "Description: Procurement and Suspension and Debarment": "I",
            "Type of Finding: Compliance: Special Tests": "N",
            "Compliance: Reporting": "L",
            "Finding No. 2023-006 - Uniform Guidance Compliance Requirement Code: A-Allowable Costs": "A",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertIsNone(requirements(text))
                self.assertEqual(value(PROSE + text), expected)

    def test_mid_line_label_needs_a_separator(self):
        self.assertIsNone(value("Criteria: the reporting compliance requirement was not met."))


class TitleTest(unittest.TestCase):
    def test_title_line(self):
        cases = {
            "2024-004- Reporting\nFederal Agency: Treasury": "L",
            "Finding 2024-003: Material Weakness - Procurement, Suspension and Debarment": "I",
            "14.871 – Section 8 Housing Choice Vouchers\nE. Eligibility – Significant Deficiency": "E",
            "Reporting – Material Weakness in Internal Control over Compliance": "L",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(value(text), expected)

    def test_only_the_first_three_title_lines(self):
        self.assertIsNone(value("Program A\nProgram B\nProgram C\nReporting\n"))

    def test_skips_labelled_lines_and_prose(self):
        self.assertIsNone(value("Criteria: reports must be filed on time under the reporting rules."))
        self.assertIsNone(value("Federal Program: Child Nutrition Cluster - Eligibility"))
        self.assertIsNone(value("Item 2024-002 - " + "x" * 130 + " reporting"))
        self.assertEqual(value("Item 2024-002 - Reporting - " + "x" * 200), "L")


if __name__ == "__main__":
    unittest.main()
