import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from auditspan.compare import agrees, compare, form_value, outcome
from auditspan.data import Finding, Form, load, make_form
from auditspan.extract import FIELDS, extract, questioned_costs, repeat, requirements, severity
from auditspan.labels import evaluate
from auditspan.stats import report_bootstrap, wilson

TEXT_COLUMNS = ["report_id", "auditee_uei", "audit_year", "fac_accepted_date", "finding_ref_number",
                "contains_chart_or_table", "finding_text"]  # fmt: skip
FORM_COLUMNS = ["report_id", "auditee_uei", "audit_year", "fac_accepted_date", "award_reference", "reference_number",
                "is_material_weakness", "is_modified_opinion", "is_other_findings", "is_other_matters",
                "prior_finding_ref_numbers", "is_questioned_costs", "is_repeat_finding", "is_significant_deficiency",
                "type_requirement"]  # fmt: skip


def form(mw=False, sd=False, rep=False, qc=False, req=""):
    return Form(mw, sd, rep, qc, req, 1, ())


def form_row(report, ref, mw="N", sd="N", rep="N", qc="N", req="L"):
    return {"report_id": report, "auditee_uei": "U", "audit_year": "2024", "fac_accepted_date": "2025-08-01",
            "award_reference": "AWARD-0001", "reference_number": ref, "is_material_weakness": mw,
            "is_modified_opinion": "N", "is_other_findings": "N", "is_other_matters": "N",
            "prior_finding_ref_numbers": "N/A", "is_questioned_costs": qc, "is_repeat_finding": rep,
            "is_significant_deficiency": sd, "type_requirement": req}  # fmt: skip


def value(fact):
    return fact and fact.value


def span(text, fact):
    return fact.start, fact.end, text[fact.start : fact.end] == fact.quote


class Severity(unittest.TestCase):
    def test_labelled_heading(self):
        text = "Finding 2024-001\nType of Finding: Material Weakness in Internal Control over Compliance\n"
        fact = severity(text)
        self.assertEqual((fact.field, fact.value, fact.quote), ("severity", "material_weakness", "Material Weakness"))
        self.assertEqual(span(text, fact), (34, 51, True))

    def test_unticked_box_is_skipped(self):
        text = "[X] Compliance Finding [ ] Significant Deficiency [X] Material Weakness"
        self.assertEqual(value(severity(text)), "material_weakness")
        self.assertEqual(value(severity("☐ Material Weakness ☒ Significant Deficiency")),
                         "significant_deficiency")  # fmt: skip

    def test_negation_is_skipped(self):
        text = "We do not consider this to be a material weakness. We consider it a significant deficiency."
        self.assertEqual(value(severity(text)), "significant_deficiency")

    def test_or_pairs_and_definitions_are_skipped(self):
        self.assertIsNone(severity("Deficiencies that are a significant deficiency or a material weakness are listed."))
        self.assertIsNone(severity("A significant deficiency is a deficiency in internal control that is less severe."))
        self.assertIsNone(severity("The AICPA defines significant deficiencies and material weaknesses."))
        self.assertIsNone(severity("Type of finding: Noncompliance and other matters."))

    def test_financial_reporting_scope_is_skipped(self):
        text = "This is a material weakness over financial reporting. A significant deficiency over compliance."
        self.assertEqual(value(severity(text)), "significant_deficiency")


class Repeat(unittest.TestCase):
    def test_label_value_on_the_same_line(self):
        text = "Effect: none.\nRepeat Finding: No\nRecommendation: x"
        fact = repeat(text)
        self.assertEqual((fact.value, fact.quote), (False, "Repeat Finding: No"))
        self.assertEqual(span(text, fact), (14, 32, True))

    def test_label_value_on_the_next_non_empty_line(self):
        text = "Repeat Finding:\n\n  Yes, 2023-001\nRecommendation"
        fact = repeat(text)
        self.assertEqual((fact.value, fact.start, fact.quote), (True, 0, "Repeat Finding:\n\n  Yes, 2023-001"))

    def test_label_variants(self):
        cases = {
            "Repeat Finding from Prior Year(s): No": False,
            "Repeat Finding from Prior Year: Yes, finding 2023-002.": True,
            "Identification as a repeat finding, if applicable – Not a repeat finding": False,
            "Identification of whether the audit finding is a repeat of a finding in the immediately prior audit and "
            "if so, the applicable prior year finding number: No.": False,
            "Prior Year Finding Number: 2022-003": True,
            "Prior-year finding: N/A": False,
        }
        for text, expected in cases.items():
            self.assertEqual(value(repeat(text)), expected, text)

    def test_not_in_the_first_sentence_means_no(self):
        self.assertFalse(value(repeat("Repeat Finding: A similar finding was not reported in the prior year audit.")))
        text = "Repeat Finding: This is a repeat finding. See 2023-016. The Organization did not have time to fix it."
        self.assertTrue(value(repeat(text)))

    def test_sentences_when_no_label_answers(self):
        self.assertFalse(value(repeat("Context: x. This is not a repeat finding. Cause: y.")))
        fact = repeat("Cause: y. This finding is a repeat of 2023-004 from the prior year.")
        self.assertEqual((fact.value, fact.quote), (True, "This finding is a repeat"))
        self.assertTrue(value(repeat("Status: Repeat finding of 2022-001.")))
        self.assertIsNone(repeat("Repeat finding: To be determined by the agency"))
        text = "Repeat Finding: " + "x " * 80 + "\nThis is a repeat finding."
        fact = repeat(text)
        self.assertEqual((fact.value, fact.quote), (True, "This is a repeat"))


class QuestionedCosts(unittest.TestCase):
    def test_none_and_zero(self):
        for text in ("Questioned Costs: None", "Questioned costs – N/A", "Questioned Costs: $0",
                     "Known Questioned Costs: Not applicable.", "Questioned Cost: 0"):  # fmt: skip
            self.assertFalse(value(questioned_costs(text)), text)
            self.assertIsNotNone(questioned_costs(text), text)

    def test_amounts(self):
        text = "Criteria: x\nQuestioned Costs: $3,703 which includes salaries of $2,874.\nContext: y"
        fact = questioned_costs(text)
        self.assertEqual(
            (fact.value, fact.quote), (True, "Questioned Costs: $3,703 which includes salaries of $2,874.")
        )
        self.assertTrue(value(questioned_costs("Questioned costs:\n$0.50")))
        self.assertTrue(value(questioned_costs("Questioned Costs:\n\nKnown – $48,929")))

    def test_threshold_and_unknown_values_are_skipped(self):
        self.assertIsNone(questioned_costs("Known Questioned Costs: Amount is below threshold of $25,000."))
        self.assertIsNone(questioned_costs("Questioned Costs: Unknown"))
        text = "Questioned costs: Known questioned costs are under $25,000.\nThere were no questioned costs identified."
        fact = questioned_costs(text)
        self.assertEqual((fact.value, fact.quote), (False, "There were no questioned costs"))

    def test_label_must_start_a_line(self):
        self.assertIsNone(questioned_costs("See the schedule of findings and questioned costs: $5,000."))


class Requirements(unittest.TestCase):
    def test_labelled_line(self):
        text = "ALN 21.027\nCompliance Requirement: Procurement and Suspension and Debarment\nCriteria"
        fact = requirements(text)
        self.assertEqual(
            (fact.value, fact.quote), ("I", "Compliance Requirement: Procurement and Suspension and Debarment")
        )
        self.assertEqual(span(text, fact)[2], True)

    def test_dash_parts_describe_the_first(self):
        cases = {
            "Compliance Requirement: Special Tests and Provisions – Reporting PIC": "N",
            "Compliance Requirement: N – Special Tests and Provisions": "N",
            "Compliance Requirement:\tAllowable Costs/Cost Principles – Time and Effort Reporting": "B",
            "Compliance Requirement – Reporting": "L",
        }
        for text, expected in cases.items():
            self.assertEqual(value(requirements(text)), expected, text)

    def test_several_letters_in_letters_order(self):
        text = "Compliance Requirements: Eligibility; Activities Allowed or Unallowed, Allowable Costs/Cost Principles"
        self.assertEqual(value(requirements(text)), "ABE")
        self.assertEqual(value(requirements("Compliance requirement affected: Cash Management and Reporting")), "CL")

    def test_next_line_and_unmapped_values(self):
        self.assertEqual(value(requirements("Compliance Requirement\nSubrecipient Monitoring\n")), "M")
        self.assertIsNone(requirements("Compliance Requirement: Audit requirement 2 CFR part 200"))
        self.assertIsNone(requirements("The reporting compliance requirement was not met."))


class Compare(unittest.TestCase):
    def test_form_values_and_agreement(self):
        self.assertEqual(form_value(form(mw=True, sd=True), "severity"), "material_weakness")
        self.assertEqual(form_value(form(sd=True), "severity"), "significant_deficiency")
        self.assertEqual(form_value(form(), "severity"), "none")
        self.assertEqual(form_value(form(req="AB"), "requirements"), "AB")
        self.assertTrue(agrees("requirements", "B", form(req="AB")))
        self.assertFalse(agrees("requirements", "AB", form(req="B")))
        self.assertFalse(agrees("severity", "significant_deficiency", form(mw=True)))
        self.assertTrue(agrees("repeat", False, form()))

    def test_compare_outcomes(self):
        text = "Type of Finding: Significant Deficiency\nRepeat Finding: Yes\nQuestioned Costs: None\n"
        finding = Finding("R", "2024-001", 2024, text, form(sd=True, qc=True, req="L"))
        result = compare(finding)
        self.assertEqual(list(result), list(FIELDS))
        self.assertEqual([result[f][1] for f in FIELDS], ["agree", "disagree", "disagree", "silent"])
        self.assertEqual(outcome(None, finding.form), "silent")
        self.assertEqual(extract(text)["repeat"].quote, "Repeat Finding: Yes")


class Data(unittest.TestCase):
    def test_make_form(self):
        rows = [form_row("R", "2024-001", mw="Y", req="AB"), form_row("R", "2024-001", req="BH")]
        f = make_form(rows)
        self.assertEqual((f.material_weakness, f.significant_deficiency, f.requirements, f.awards),
                         (True, False, "ABH", 2))  # fmt: skip
        self.assertEqual(f.varies, ("is_material_weakness", "type_requirement"))

    def test_load_skips_split_texts_and_counts_form_only(self):
        texts = [("R1", "2024-001", "Repeat Finding: No"), ("R1", "2024-002", "part one"), ("R1", "2024-002", "two"),
                 ("R2", "2024-001", "Questioned Costs: $10"), ("R3", "2024-009", "no form rows")]  # fmt: skip
        forms = [form_row("R1", "2024-001"), form_row("R1", "2024-002"), form_row("R2", "2024-001", qc="Y"),
                 form_row("R2", "2024-001", qc="N"), form_row("R4", "2024-001")]  # fmt: skip
        with tempfile.TemporaryDirectory() as tmp:
            with open(Path(tmp) / "findings_text.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, TEXT_COLUMNS, lineterminator="\n")
                writer.writeheader()
                for report, ref, text in texts:
                    writer.writerow({"report_id": report, "auditee_uei": "U", "audit_year": "2024",
                                     "fac_accepted_date": "2025-08-01", "finding_ref_number": ref,
                                     "contains_chart_or_table": "N", "finding_text": text})  # fmt: skip
            with open(Path(tmp) / "findings.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, FORM_COLUMNS, lineterminator="\n")
                writer.writeheader()
                writer.writerows(forms)
            corpus = load(tmp)
        self.assertEqual([f.key for f in corpus.findings], [("R1", "2024-001"), ("R2", "2024-001")])
        self.assertEqual((corpus.text_rows, corpus.form_rows, corpus.split_texts, corpus.form_only), (5, 5, 1, 1))
        second = corpus.findings[1]
        self.assertEqual((second.audit_year, second.form.questioned_costs, second.form.awards), (2024, True, 2))
        self.assertEqual(second.form.varies, ("is_questioned_costs",))


class Stats(unittest.TestCase):
    def test_wilson(self):
        rate, lo, hi = wilson(58, 59)
        self.assertAlmostEqual(rate, 58 / 59)
        self.assertAlmostEqual(lo, 0.9100427, places=6)
        self.assertAlmostEqual(hi, 0.9970022, places=6)
        self.assertEqual(wilson(0, 0), (0.0, 0.0, 1.0))
        self.assertAlmostEqual(wilson(54, 54)[2], 1.0)

    def test_report_bootstrap(self):
        hits = np.array([[1.0, 0.0], [0.0, 2.0], [1.0, 1.0]])
        totals = np.array([[2.0, 4.0], [2.0, 4.0], [2.0, 4.0]])
        lo, hi = report_bootstrap(hits, totals, 500, 7)
        again = report_bootstrap(hits, totals, 500, 7)
        np.testing.assert_array_equal(lo, again[0])
        self.assertEqual(lo.shape, (2,))
        self.assertTrue(np.all(lo <= hits.sum(0) / totals.sum(0)) and np.all(hits.sum(0) / totals.sum(0) <= hi))
        lo, hi = report_bootstrap(np.ones((4, 1)), np.full((4, 1), 2.0), 100, 1)
        self.assertEqual((float(lo[0]), float(hi[0])), (0.5, 0.5))


class Labels(unittest.TestCase):
    def test_evaluate_counts_strata_and_null_labels(self):
        a = Finding("A", "1", 2024, "Repeat Finding: No\nQuestioned Costs: $50", form(rep=True))
        b = Finding("B", "1", 2024, "Repeat Finding: Yes", form(rep=True))
        c = Finding("C", "1", 2024, "nothing stated", form())
        rows = [
            {"report_id": "A", "ref": "1", "stratum": "random",
             "labels": {"severity": None, "repeat": False, "questioned_costs": None, "requirements": None}},
            {"report_id": "B", "ref": "1", "stratum": "random",
             "labels": {"severity": None, "repeat": True, "questioned_costs": None, "requirements": "L"}},
            {"report_id": "C", "ref": "1", "stratum": "random",
             "labels": {"severity": None, "repeat": None, "questioned_costs": True, "requirements": None}},
            {"report_id": "A", "ref": "1", "stratum": "repeat", "labels": {"repeat": None}},
        ]  # fmt: skip
        counts = evaluate([a, b, c], rows)
        self.assertEqual(counts["repeat"], {"extracted": 2, "correct": 2, "stated": 2, "found": 2, "flagged": 2,
                                            "confirmed": 1})  # fmt: skip
        self.assertEqual(counts["questioned_costs"], {"extracted": 1, "correct": 0, "stated": 1, "found": 0,
                                                      "flagged": 1, "confirmed": 0})  # fmt: skip
        self.assertEqual(counts["requirements"]["stated"], 1)
        self.assertEqual(counts["severity"], dict.fromkeys(counts["severity"], 0))
