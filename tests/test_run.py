"""Tests for findingtrace.run."""

import json
import tempfile
import unittest
from pathlib import Path

from findingtrace import DATA_DIR, run
from findingtrace.data import Corpus, Finding, Form
from findingtrace.extract import FIELDS

_NUMBERS = (
    "text_rows",
    "form_rows",
    "findings",
    "reports",
    "split_texts",
    "form_only_findings",
    "labelled",
    "labelled_random",
    "replicates",
    "facts",
    "facts_quoted_exactly",
)
_PER_FIELD = (
    "covered",
    "agree",
    "disagree",
    "disagree_reports",
    "disagree_rate",
    "disagree_rate_lo",
    "disagree_rate_hi",
    "form_varies",
)
_EVALUATE_COUNTS = ("extracted", "correct", "stated", "found", "flagged", "confirmed")
_QUALITY = ("precision", "recall", "flag_precision")


def expected_keys():
    keys = set(_NUMBERS) | set(_PER_FIELD) | set(_EVALUATE_COUNTS) | {"severity_text_vs_form"}
    for name in _QUALITY:
        keys.update((name, f"{name}_lo", f"{name}_hi"))
    return keys


def make_form(*, material=False, significant=False, repeat=False, questioned=False, requirements=""):
    return Form(material, significant, repeat, questioned, requirements, 1, ())


def make_finding(report_id, ref, text, form):
    return Finding(report_id, ref, 2024, text, form)


def make_corpus():
    agree_text = (
        "Material weakness in controls.\n"
        "Repeat finding: Yes\n"
        "Questioned costs: $1,000\n"
        "Compliance requirements: Reporting\n"
    )
    agree_form = make_form(material=True, repeat=True, questioned=True, requirements="L")
    return Corpus(
        (
            make_finding("R1", "1", agree_text, agree_form),
            make_finding("R2", "1", "Material weakness in controls.", make_form()),
            make_finding("R3", "1", "Material weakness in controls.", make_form(material=True)),
        ),
        5,
        7,
        1,
        2,
    )


ROWS = (
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


class SummarizeTest(unittest.TestCase):
    def test_keys_types_and_counts(self):
        metrics = run.summarize(make_corpus(), ROWS)
        self.assertEqual(set(metrics), expected_keys())
        for key in _NUMBERS:
            self.assertIsInstance(metrics[key], int)
        for key in ("covered", "agree", "disagree", "disagree_reports", "form_varies"):
            self.assertEqual(len(metrics[key]), len(FIELDS))
            self.assertTrue(all(isinstance(value, int) for value in metrics[key]))
        for key in ("disagree_rate", "disagree_rate_lo", "disagree_rate_hi"):
            self.assertEqual(len(metrics[key]), len(FIELDS))
            self.assertTrue(all(isinstance(value, float) for value in metrics[key]))
        for key in _EVALUATE_COUNTS:
            self.assertEqual(len(metrics[key]), len(FIELDS))
            self.assertTrue(all(isinstance(value, int) for value in metrics[key]))
        for name in _QUALITY:
            for key in (name, f"{name}_lo", f"{name}_hi"):
                self.assertEqual(len(metrics[key]), len(FIELDS))
                self.assertTrue(all(isinstance(value, float) for value in metrics[key]))

        self.assertEqual(metrics["findings"], 3)
        self.assertEqual(metrics["reports"], 3)
        self.assertEqual(metrics["facts"], sum(metrics["covered"]))
        self.assertEqual(metrics["facts_quoted_exactly"], metrics["facts"])
        self.assertEqual(metrics["labelled"], 3)
        self.assertEqual(metrics["labelled_random"], 2)
        self.assertEqual(metrics["replicates"], run.REPLICATES)
        self.assertEqual(metrics["covered"], [3, 1, 1, 1])
        self.assertEqual(metrics["agree"], [2, 1, 1, 1])
        self.assertEqual(metrics["disagree"], [1, 0, 0, 0])
        self.assertEqual(metrics["disagree_reports"], [1, 0, 0, 0])
        self.assertEqual(metrics["extracted"], [2, 1, 1, 1])
        self.assertEqual(metrics["correct"], [1, 1, 1, 1])
        self.assertEqual(metrics["stated"], [1, 1, 1, 1])
        self.assertEqual(metrics["found"], [1, 1, 1, 1])
        self.assertEqual(metrics["flagged"], [1, 0, 0, 0])
        self.assertEqual(metrics["confirmed"], [1, 0, 0, 0])
        self.assertEqual(metrics["precision"][0], 0.5)
        self.assertEqual(metrics["precision"][1], 1.0)
        self.assertEqual(len(metrics["severity_text_vs_form"]), 6)
        self.assertTrue(all(isinstance(value, int) for value in metrics["severity_text_vs_form"]))
        self.assertEqual(metrics["severity_text_vs_form"][0], 2)
        self.assertEqual(metrics["severity_text_vs_form"][2], 1)


@unittest.skipUnless(
    (DATA_DIR / "findings.csv").is_file()
    and (DATA_DIR / "findings_text.csv").is_file()
    and (DATA_DIR / "labels.json").is_file(),
    f"pinned data not found in {DATA_DIR}",
)
class MainTest(unittest.TestCase):
    def test_writes_sorted_indented_json_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "one" / "metrics.json"
            second = Path(folder) / "two" / "metrics.json"
            metrics = run.main(DATA_DIR, first)
            run.main(DATA_DIR, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            text = first.read_text(encoding="utf-8")
            self.assertTrue(text.endswith("\n"))
            parsed = json.loads(text)
            self.assertEqual(list(parsed), sorted(parsed))
            self.assertEqual(parsed, metrics)
            self.assertTrue(text.splitlines()[1].startswith(' "'))
