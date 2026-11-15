"""Tests for findingtrace.data."""

import csv
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from findingtrace import DATA_DIR
from findingtrace.data import Corpus, Finding, Form, load, make_form

TEXT_FILE = DATA_DIR / "findings_text.csv"
FORM_FILE = DATA_DIR / "findings.csv"

TEXT_HEADER = ["report_id", "audit_year", "finding_ref_number", "finding_text"]
FORM_HEADER = [
    "report_id",
    "reference_number",
    "is_material_weakness",
    "is_significant_deficiency",
    "is_repeat_finding",
    "is_questioned_costs",
    "type_requirement",
]


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _form_row(
    material: str = "N",
    significant: str = "N",
    repeat: str = "N",
    questioned: str = "N",
    requirements: str = "",
) -> dict[str, str]:
    return {
        "is_material_weakness": material,
        "is_significant_deficiency": significant,
        "is_repeat_finding": repeat,
        "is_questioned_costs": questioned,
        "type_requirement": requirements,
    }


class SyntheticLoadTest(unittest.TestCase):
    def test_load_matches_counts_and_aggregates_form(self):
        with tempfile.TemporaryDirectory() as folder:
            data_dir = Path(folder)
            write_csv(
                data_dir / "findings_text.csv",
                TEXT_HEADER,
                [
                    ["R1", "2024", "K1", "single text"],
                    ["R1", "2024", "K2", "split first"],
                    ["R1", "2024", "K2", "split second"],
                    ["R2", "2023", "K1", "no form"],
                ],
            )
            write_csv(
                data_dir / "findings.csv",
                FORM_HEADER,
                [
                    ["R1", "K1", "Y", "N", "N", "N", "B"],
                    ["R1", "K1", "N", "Y", "Y", "Y", "A"],
                    ["R1", "K2", "N", "N", "N", "N", "L"],
                    ["R3", "K1", "N", "N", "N", "N", ""],
                ],
            )
            corpus = load(folder)

        self.assertEqual(corpus.text_rows, 4)
        self.assertEqual(corpus.form_rows, 4)
        self.assertEqual(corpus.split_texts, 1)
        self.assertEqual(corpus.form_only, 1)
        self.assertEqual(len(corpus.findings), 1)

        finding = corpus.findings[0]
        self.assertEqual(finding.key, ("R1", "K1"))
        self.assertEqual(finding.audit_year, 2024)
        self.assertEqual(finding.text, "single text")
        self.assertTrue(finding.form.material_weakness)
        self.assertTrue(finding.form.significant_deficiency)
        self.assertTrue(finding.form.repeat)
        self.assertTrue(finding.form.questioned_costs)
        self.assertEqual(finding.form.requirements, "AB")
        self.assertEqual(finding.form.awards, 2)
        self.assertEqual(
            finding.form.varies,
            (
                "is_material_weakness",
                "is_significant_deficiency",
                "is_repeat_finding",
                "is_questioned_costs",
                "type_requirement",
            ),
        )


class MakeFormTest(unittest.TestCase):
    def test_union_and_varies(self):
        form = make_form(
            [
                _form_row("Y", "N", "N", "N", "B"),
                _form_row("N", "Y", "Y", "Y", "A"),
            ]
        )
        self.assertTrue(form.material_weakness)
        self.assertTrue(form.significant_deficiency)
        self.assertTrue(form.repeat)
        self.assertTrue(form.questioned_costs)
        self.assertEqual(form.requirements, "AB")
        self.assertEqual(form.awards, 2)
        self.assertEqual(
            form.varies,
            (
                "is_material_weakness",
                "is_significant_deficiency",
                "is_repeat_finding",
                "is_questioned_costs",
                "type_requirement",
            ),
        )

    def test_identical_rows_do_not_vary(self):
        form = make_form([_form_row(requirements="A"), _form_row(requirements="A")])
        self.assertEqual(form.requirements, "A")
        self.assertEqual(form.awards, 2)
        self.assertEqual(form.varies, ())
        self.assertFalse(form.material_weakness)


class DataclassTest(unittest.TestCase):
    def test_frozen_and_key(self):
        form = Form(False, False, False, False, "", 1, ())
        finding = Finding("R", "1", 2024, "text", form)
        corpus = Corpus((finding,), 1, 1, 0, 0)

        self.assertEqual(finding.key, ("R", "1"))
        with self.assertRaises(FrozenInstanceError):
            finding.ref = "2"
        with self.assertRaises(FrozenInstanceError):
            form.awards = 2
        with self.assertRaises(FrozenInstanceError):
            corpus.form_only = 1


@unittest.skipUnless(TEXT_FILE.is_file() and FORM_FILE.is_file(), f"pinned FAC data not found in {DATA_DIR}")
class RealDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = load()

    def test_manifest_row_counts(self):
        self.assertEqual(self.corpus.text_rows, 8772)
        self.assertEqual(self.corpus.form_rows, 21183)

    def test_findings_have_unique_keys_and_forms(self):
        keys = [finding.key for finding in self.corpus.findings]
        self.assertTrue(keys)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertLessEqual(len(keys), self.corpus.text_rows)
        self.assertGreaterEqual(self.corpus.split_texts, 0)
        self.assertGreaterEqual(self.corpus.form_only, 0)
        for finding in self.corpus.findings:
            self.assertGreaterEqual(finding.form.awards, 1)
            self.assertIsInstance(finding.audit_year, int)
            self.assertIsInstance(finding.text, str)
