"""Tests for findingtrace.rules_v2_1 (SPEC-v2 section 6)."""

import unittest

from findingtrace.extract import questioned_costs, repeat
from findingtrace.requirements_v2 import requirements_v2
from findingtrace.rules_v2_1 import extract_v2_1, requirements_v2_1


def value(fact):
    return fact and fact.value


class RepeatTest(unittest.TestCase):
    def test_explicit_yes_beats_a_later_not(self):
        text = "Repeat Finding: Yes, prior finding 2023-001 has not been corrected."
        self.assertFalse(value(repeat(text)))
        self.assertTrue(extract_v2_1(text)["repeat"].value)

    def test_other_answers_as_v1(self):
        for text, expected in (("Repeat Finding: No, this is not a repeat.", False), ("Repeat Finding: N/A", False),
                               ("Repeat Finding: See 2023-002", True)):  # fmt: skip
            with self.subTest(text=text):
                self.assertEqual(value(extract_v2_1(text)["repeat"]), expected)
                self.assertEqual(value(repeat(text)), expected)


class QuestionedCostsTest(unittest.TestCase):
    def test_none_of_an_amount_is_not_a_no(self):
        text = "Questioned costs: None of the $50,000 was allowable."
        self.assertFalse(value(questioned_costs(text)))
        self.assertTrue(extract_v2_1(text)["questioned_costs"].value)

    def test_plain_none_is_still_no(self):
        self.assertFalse(extract_v2_1("Questioned costs: None")["questioned_costs"].value)
        self.assertIsNone(extract_v2_1("Questioned costs: None of the costs were reviewed.")["questioned_costs"])


class RequirementsTest(unittest.TestCase):
    def test_title_scan_stops_at_a_body_heading(self):
        text = "Criteria:\nTitle 2, Code of Federal Regulations, Part 200, Subpart E, Cost Principles for\nawards\n"
        self.assertEqual(value(requirements_v2(text)), "B")
        self.assertIsNone(requirements_v2_1(text))

    def test_program_lines_are_skipped_not_a_stop(self):
        self.assertEqual(value(requirements_v2_1("Federal Program: Head Start\n2024-001 – Reporting\n")), "L")

    def test_audit_filing_is_not_reporting(self):
        for text in (
            "2024-001 – Reporting Deadline for Federal Single Audit – Noncompliance",
            "Finding 2023-004 – Late Audit Reporting",
        ):
            with self.subTest(text=text):
                self.assertEqual(value(requirements_v2(text)), "L")
                self.assertIsNone(requirements_v2_1(text))
        self.assertEqual(value(requirements_v2_1("2024-002 – Federal Financial Reporting")), "L")


if __name__ == "__main__":
    unittest.main()
