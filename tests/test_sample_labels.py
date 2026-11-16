"""Tests for auditspan.sample and auditspan.labels."""

import unittest

from auditspan import DATA_DIR
from auditspan.data import Finding, Form
from auditspan.extract import FIELDS
from auditspan.labels import evaluate, load_labels
from auditspan.sample import PER_FIELD, RANDOM_SIZE, disagreement_keys, random_keys

LABELS_FILE = DATA_DIR / "labels.json"


def make_form(*, material=False, significant=False, repeat=False, questioned=False, requirements=""):
    return Form(material, significant, repeat, questioned, requirements, 1, ())


def make_finding(key, text, form):
    report_id, ref = key
    return Finding(report_id, ref, 2024, text, form)


def bulk_findings(count=120):
    text = (
        "Material weakness in controls.\n"
        "Repeat finding: Yes\n"
        "Questioned costs: $1,000\n"
        "Compliance requirements: Reporting\n"
    )
    form = make_form(significant=True, repeat=False, questioned=False, requirements="A")
    return tuple(make_finding((f"R{index:03}", "1"), text, form) for index in range(count))


class SampleTest(unittest.TestCase):
    def test_random_keys_are_deterministic_and_sorted(self):
        findings = bulk_findings()
        keys = random_keys(findings)
        self.assertEqual(keys, random_keys(tuple(reversed(findings))))
        self.assertEqual(len(keys), RANDOM_SIZE)
        self.assertEqual(len(set(keys)), RANDOM_SIZE)

    def test_disagreement_keys_are_disjoint_and_limited(self):
        findings = bulk_findings()
        keys = disagreement_keys(findings)
        taken = set(random_keys(findings))
        self.assertEqual(set(keys), set(FIELDS))
        for field in FIELDS:
            drawn = keys[field]
            self.assertLessEqual(len(drawn), PER_FIELD)
            self.assertEqual(len(drawn), len(set(drawn)))
            self.assertFalse(set(drawn) & taken)
            taken.update(drawn)
        self.assertEqual([len(keys[field]) for field in FIELDS], [PER_FIELD, 8, 0, 0])


class EvaluateTest(unittest.TestCase):
    def test_hand_checked_counts_and_null_labels(self):
        agree_text = (
            "Material weakness in controls.\n"
            "Repeat finding: Yes\n"
            "Questioned costs: $1,000\n"
            "Compliance requirements: Reporting\n"
        )
        agree_form = make_form(material=True, repeat=True, questioned=True, requirements="L")
        disagree_text = "Material weakness in controls."
        disagree_form = make_form()
        null_form = make_form(material=True)
        findings = (
            make_finding(("R1", "1"), agree_text, agree_form),
            make_finding(("R2", "1"), disagree_text, disagree_form),
            make_finding(("R3", "1"), disagree_text, null_form),
        )
        rows = (
            {
                "report_id": "R1",
                "ref": "1",
                "stratum": "random",
                "labels": {
                    "severity": "material_weakness",
                    "repeat": True,
                    "questioned_costs": True,
                    "requirements": "L",
                },
            },
            {
                "report_id": "R2",
                "ref": "1",
                "stratum": "severity",
                "labels": {"severity": "material_weakness"},
            },
            {"report_id": "R3", "ref": "1", "stratum": "random", "labels": {"severity": None}},
        )
        counts = evaluate(findings, rows)
        self.assertEqual(
            counts["severity"],
            {"extracted": 2, "correct": 1, "stated": 1, "found": 1, "flagged": 1, "confirmed": 1},
        )
        for field in ("repeat", "questioned_costs", "requirements"):
            with self.subTest(field=field):
                self.assertEqual(
                    counts[field],
                    {"extracted": 1, "correct": 1, "stated": 1, "found": 1, "flagged": 0, "confirmed": 0},
                )


@unittest.skipUnless(LABELS_FILE.is_file(), f"pinned labels not found at {LABELS_FILE}")
class LabelsFileTest(unittest.TestCase):
    def test_shape_and_strata(self):
        rows = load_labels()
        self.assertEqual(len(rows), 148)
        random_rows = [row for row in rows if row["stratum"] == "random"]
        self.assertEqual(len(random_rows), RANDOM_SIZE)
        for row in random_rows:
            self.assertEqual(set(row["labels"]), set(FIELDS))
        for field in FIELDS:
            field_rows = [row for row in rows if row["stratum"] == field]
            self.assertEqual(len(field_rows), PER_FIELD)
            for row in field_rows:
                self.assertEqual(set(row["labels"]), {field})
