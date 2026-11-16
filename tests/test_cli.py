"""Tests for the auditspan command line."""

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from auditspan.__main__ import CSV_COLUMNS, main

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

TEXT_R1 = """Material weakness in controls.
Repeat finding: Yes
Questioned costs: $1,000
Compliance requirements: Reporting
"""
TEXT_R2 = """Material weakness in controls.
Repeat finding: No
Questioned costs: None
Compliance requirements: Allowable Costs
"""


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator=chr(10))
        writer.writerow(header)
        writer.writerows(rows)


def write_data(folder: Path) -> None:
    write_csv(
        folder / "findings_text.csv",
        TEXT_HEADER,
        [
            ["R1", "2024", "1", TEXT_R1],
            ["R2", "2024", "1", TEXT_R2],
        ],
    )
    write_csv(
        folder / "findings.csv",
        FORM_HEADER,
        [
            ["R1", "1", "Y", "N", "N", "N", "A"],
            ["R2", "1", "N", "Y", "Y", "Y", "B"],
        ],
    )


class CliTest(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._temporary.name)
        write_data(self.data_dir)

    def tearDown(self):
        self._temporary.cleanup()

    def _run(self, argv):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(argv)
        return status, output.getvalue()

    def test_show_prints_json(self):
        status, output = self._run(["--data", str(self.data_dir), "show", "R1", "1"])
        self.assertEqual(status, 0)
        payload = json.loads(output)
        self.assertEqual(payload["report_id"], "R1")
        self.assertEqual(payload["ref"], "1")
        self.assertEqual(set(payload), {"report_id", "ref", "facts", "form", "outcome"})
        self.assertEqual(payload["facts"]["severity"]["value"], "material_weakness")
        self.assertEqual(payload["facts"]["severity"]["quote"], "Material weakness")
        self.assertIs(payload["facts"]["repeat"]["value"], True)
        self.assertFalse(payload["form"]["repeat"])
        self.assertEqual(payload["outcome"]["repeat"], "disagree")
        self.assertEqual(payload["outcome"]["severity"], "agree")

    def test_show_unknown_finding_exits(self):
        with self.assertRaises(SystemExit):
            self._run(["--data", str(self.data_dir), "show", "R9", "1"])

    def test_disagreements_field_filter(self):
        status, output = self._run(["--data", str(self.data_dir), "disagreements", "--field", "severity"])
        self.assertEqual(status, 0)
        reader = csv.DictReader(io.StringIO(output))
        self.assertEqual(reader.fieldnames, list(CSV_COLUMNS))
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["report_id"], "R2")
        self.assertEqual(rows[0]["form_value"], "significant_deficiency")

    def test_disagreements_out_and_boolean_format(self):
        path = self.data_dir / "nested" / "disagreements.csv"
        status, output = self._run(["--data", str(self.data_dir), "disagreements", "--out", str(path)])
        self.assertEqual(status, 0)
        self.assertEqual(output, "")
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [(row["report_id"], row["field"]) for row in rows],
            [
                ("R1", "repeat"),
                ("R1", "questioned_costs"),
                ("R1", "requirements"),
                ("R2", "severity"),
                ("R2", "repeat"),
                ("R2", "questioned_costs"),
            ],
        )
        self.assertEqual(rows[0]["text_value"], "true")
        self.assertEqual(rows[0]["form_value"], "false")
        self.assertEqual(rows[0]["quote"], "Repeat finding: Yes")

    def test_data_option_after_subcommand(self):
        status, output = self._run(["show", "R1", "1", "--data", str(self.data_dir)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output)["report_id"], "R1")


if __name__ == "__main__":
    unittest.main()
