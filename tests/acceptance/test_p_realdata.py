import contextlib
import csv
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import auditspan
from auditspan import run
from auditspan.__main__ import main as cli
from auditspan.compare import compare
from auditspan.data import load
from auditspan.extract import FIELDS
from auditspan.labels import evaluate, load_labels
from auditspan.sample import disagreement_keys, random_keys

REPO = Path(auditspan.__file__).resolve().parent.parent
PER_FIELD = ("covered", "agree", "disagree", "disagree_reports", "disagree_rate", "disagree_rate_lo",
             "disagree_rate_hi", "form_varies", "extracted", "correct", "stated", "found", "flagged", "confirmed",
             "precision", "precision_lo", "precision_hi", "recall", "recall_lo", "recall_hi", "flag_precision",
             "flag_precision_lo", "flag_precision_hi")  # fmt: skip
SCALARS = ("text_rows", "form_rows", "findings", "reports", "split_texts", "form_only_findings", "labelled",
           "labelled_random", "replicates", "facts", "facts_quoted_exactly")  # fmt: skip
OUTCOMES = {
    "severity": {"silent": 3564, "agree": 2683, "disagree": 24},
    "repeat": {"silent": 3797, "agree": 2452, "disagree": 22},
    "questioned_costs": {"silent": 2797, "agree": 3437, "disagree": 37},
    "requirements": {"silent": 5423, "agree": 823, "disagree": 25},
}
COUNTS = {
    "severity": {"extracted": 59, "correct": 58, "stated": 59, "found": 58, "flagged": 13, "confirmed": 7},
    "repeat": {"extracted": 40, "correct": 39, "stated": 49, "found": 39, "flagged": 13, "confirmed": 11},
    "questioned_costs": {"extracted": 54, "correct": 54, "stated": 65, "found": 54, "flagged": 12, "confirmed": 11},
    "requirements": {"extracted": 14, "correct": 13, "stated": 50, "found": 13, "flagged": 13, "confirmed": 10},
}


def fact_tuple(fact):
    return fact and (fact.value, fact.start, fact.end, fact.quote)


class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load()
        cls.by_key = {f.key: f for f in cls.corpus.findings}
        cls.results = {f.key: compare(f) for f in cls.corpus.findings}

    def test_data_matches_the_manifest(self):
        manifest = json.loads((auditspan.DATA_DIR / "MANIFEST.json").read_text())
        self.assertEqual(sorted(manifest["files"]), ["findings.csv", "findings_text.csv", "labels.json"])
        for name, entry in manifest["files"].items():
            digest = hashlib.sha256((auditspan.DATA_DIR / name).read_bytes()).hexdigest()
            self.assertEqual(digest, entry["sha256"], name)

    def test_fetch_verify_needs_no_network(self):
        out = subprocess.run([sys.executable, str(REPO / "tools" / "fetch_data.py"), "--verify"], capture_output=True,
                             text=True, timeout=120)  # fmt: skip
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("3 files match", out.stdout)

    def test_corpus_counts(self):
        c = self.corpus
        self.assertEqual((c.text_rows, c.form_rows, c.split_texts, c.form_only), (8772, 21183, 151, 396))
        self.assertEqual(len(c.findings), 6271)
        self.assertEqual(len({f.report_id for f in c.findings}), 3293)

    def test_findings_keep_text_file_order(self):
        first, last = self.corpus.findings[0], self.corpus.findings[-1]
        self.assertEqual(first.key, ("2017-06-GSAFAC-0000375278", "2017-001"))
        self.assertEqual(last.key, ("2025-06-GSAFAC-0000392542", "2025-001"))
        self.assertEqual(first.audit_year, 2017)
        with open(auditspan.DATA_DIR / "findings_text.csv", newline="", encoding="utf-8") as f:
            csv.field_size_limit(sys.maxsize)
            row = next(csv.DictReader(f))
        self.assertEqual(first.text, row["finding_text"])

    def test_form_is_aggregated_over_award_rows(self):
        f = self.by_key["2023-06-GSAFAC-0000381422", "2023-053"].form
        self.assertEqual((f.awards, f.repeat, f.requirements, f.varies), (10, True, "M", ("is_repeat_finding",)))
        f = self.by_key["2023-06-GSAFAC-0000377095", "2023-006"].form
        self.assertEqual((f.requirements, f.varies, f.significant_deficiency), ("ABHN", ("type_requirement",), True))
        self.assertEqual(sum(bool(f.form.varies) for f in self.corpus.findings), 76)

    def test_known_facts(self):
        r = self.results["2024-12-GSAFAC-0000383372", "2024-004"]
        self.assertEqual(fact_tuple(r["severity"][0]), ("material_weakness", 1806, 1823, "Material Weakness"))
        self.assertEqual(
            fact_tuple(r["questioned_costs"][0]), (True, 2129, 2164, "Questioned Costs: \n\nKnown – $48,929")
        )
        self.assertEqual(fact_tuple(r["repeat"][0]), (False, 2166, 2185, "Repeat Finding: No."))
        self.assertIsNone(r["requirements"][0])
        r = self.results["2024-06-GSAFAC-0000376191", "2024-008"]
        self.assertEqual(r["requirements"][0].value, "ABM")
        self.assertEqual([r[f][1] for f in FIELDS], ["agree", "silent", "disagree", "agree"])

    def test_known_disagreements(self):
        r = self.results["2024-12-GSAFAC-0000380500", "2024-003"]["repeat"]
        self.assertEqual((fact_tuple(r[0]), r[1]), ((False, 1009, 1048, "Identification of a repeat finding: No."),
                                                    "disagree"))  # fmt: skip
        r = self.results["2024-12-GSAFAC-0000381878", "2024-006"]["requirements"]
        self.assertEqual((r[0].value, r[1]), ("AB", "disagree"))
        r = self.results["2025-06-GSAFAC-0000392695", "2025-001"]["severity"]
        self.assertEqual((r[0].value, r[0].start, r[1]), ("significant_deficiency", 1191, "disagree"))

    def test_outcome_counts(self):
        for field, expected in OUTCOMES.items():
            counts = {k: sum(r[field][1] == k for r in self.results.values()) for k in expected}
            self.assertEqual(counts, expected, field)

    def test_every_quote_is_its_exact_span(self):
        n = 0
        for f in self.corpus.findings:
            for fact, _ in self.results[f.key].values():
                if fact:
                    n += 1
                    self.assertEqual(f.text[fact.start : fact.end], fact.quote)
                    self.assertTrue(fact.quote.strip())
        self.assertEqual(n, 9503)

    def test_labelled_sample_is_the_seeded_draw(self):
        rows = load_labels()
        strata = {}
        for r in rows:
            strata.setdefault(r["stratum"], []).append((r["report_id"], r["ref"]))
        self.assertEqual(strata["random"], random_keys(self.corpus.findings))
        drawn = disagreement_keys(self.corpus.findings)
        self.assertEqual(list(drawn), list(FIELDS))
        for field in FIELDS:
            self.assertEqual(strata[field], drawn[field], field)

    def test_labels_file(self):
        doc = json.loads((auditspan.DATA_DIR / "labels.json").read_text(encoding="utf-8"))
        self.assertIn("not an auditor", doc["labeller"])
        self.assertEqual(len(doc["findings"]), 148)
        for r in doc["findings"]:
            self.assertIn((r["report_id"], r["ref"]), self.by_key)
            expected = list(FIELDS) if r["stratum"] == "random" else [r["stratum"]]
            self.assertEqual(list(r["labels"]), expected)

    def test_evaluate_counts(self):
        self.assertEqual(evaluate(self.corpus.findings, load_labels()), COUNTS)


class CommandLine(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli(list(argv))
        return out.getvalue()

    def test_disagreements_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d.csv"
            self.run_cli("disagreements", "--out", str(path))
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        self.assertEqual(rows[0], ["report_id", "ref", "field", "text_value", "form_value", "start", "end", "quote"])
        self.assertEqual(len(rows) - 1, 108)
        self.assertEqual(
            rows[1][:7], ["2021-06-GSAFAC-0000395398", "2021-005", "requirements", "AB", "E", "178", "297"]
        )
        repeat = [r for r in rows[1:] if r[:3] == ["2024-12-GSAFAC-0000380500", "2024-003", "repeat"]]
        self.assertEqual(repeat[0][3:], ["false", "true", "1009", "1048", "Identification of a repeat finding: No."])

    def test_disagreements_for_one_field_on_stdout(self):
        rows = list(csv.reader(io.StringIO(self.run_cli("disagreements", "--field", "severity"))))
        self.assertEqual(len(rows) - 1, 24)
        self.assertEqual({r[2] for r in rows[1:]}, {"severity"})

    def test_show(self):
        shown = json.loads(self.run_cli("show", "2024-12-GSAFAC-0000380500", "2024-003"))
        self.assertEqual(shown["facts"]["repeat"], {"field": "repeat", "value": False, "start": 1009, "end": 1048,
                                                     "quote": "Identification of a repeat finding: No."})  # fmt: skip
        self.assertIsNone(shown["facts"]["severity"])
        self.assertEqual(shown["form"], {"severity": "significant_deficiency", "repeat": True,
                                         "questioned_costs": False, "requirements": "B"})  # fmt: skip
        self.assertEqual(shown["outcome"]["repeat"], "disagree")
        with self.assertRaises(SystemExit) as caught, contextlib.redirect_stderr(io.StringIO()):
            self.run_cli("show", "2024-12-GSAFAC-0000000000", "2024-001")
        self.assertNotIn(caught.exception.code, (0, None))


class Experiment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "results" / "metrics.json"
        run.main(auditspan.DATA_DIR, cls.out)
        cls.text = cls.out.read_text()
        cls.m = json.loads(cls.text)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_metric_names_and_shapes(self):
        self.assertEqual(set(self.m), {*SCALARS, *PER_FIELD, "severity_text_vs_form"})
        self.assertEqual(len(self.m), 35)
        for k in PER_FIELD:
            self.assertEqual(len(self.m[k]), 4, k)
        for k in SCALARS:
            self.assertIsInstance(self.m[k], int, k)

    def test_main_writes_identical_sorted_numbers(self):
        again = Path(self.tmp.name) / "again.json"
        run.main(auditspan.DATA_DIR, again)
        self.assertEqual(again.read_text(), self.text)
        self.assertEqual(self.text, json.dumps(self.m, sort_keys=True, indent=1) + "\n")

    def test_scalars(self):
        expected = {"text_rows": 8772, "form_rows": 21183, "findings": 6271, "reports": 3293, "split_texts": 151,
                    "form_only_findings": 396, "labelled": 148, "labelled_random": 100, "replicates": 2000,
                    "facts": 9503, "facts_quoted_exactly": 9503}  # fmt: skip
        self.assertEqual({k: self.m[k] for k in SCALARS}, expected)

    def test_corpus_metrics(self):
        m = self.m
        self.assertEqual(m["covered"], [2707, 2474, 3474, 848])
        self.assertEqual(m["disagree"], [24, 22, 37, 25])
        self.assertEqual(m["disagree_reports"], [22, 19, 32, 20])
        self.assertEqual(m["disagree_rate"], [0.008866, 0.008892, 0.010651, 0.029481])
        self.assertEqual(m["form_varies"], [9, 26, 17, 33])
        self.assertEqual(m["severity_text_vs_form"], [1243, 5, 2, 12, 1440, 5])

    def test_report_bootstrap_intervals(self):
        self.assertEqual(self.m["disagree_rate_lo"], [0.005223, 0.004969, 0.006883, 0.017491])
        self.assertEqual(self.m["disagree_rate_hi"], [0.012848, 0.013883, 0.0147, 0.044329])

    def test_label_metrics(self):
        m = self.m
        for k in ("extracted", "correct", "stated", "found", "flagged", "confirmed"):
            self.assertEqual(m[k], [COUNTS[f][k] for f in FIELDS], k)
        self.assertEqual(m["precision"], [0.983051, 0.975, 1.0, 0.928571])
        self.assertEqual(m["precision_lo"], [0.910043, 0.871186, 0.933586, 0.685313])
        self.assertEqual(m["recall"], [0.983051, 0.795918, 0.830769, 0.26])
        self.assertEqual(m["recall_hi"], [0.997002, 0.885182, 0.902788, 0.395532])
        self.assertEqual(m["flag_precision"], [0.538462, 0.846154, 0.916667, 0.769231])
        self.assertEqual(m["flag_precision_lo"], [0.291438, 0.577654, 0.64612, 0.497436])

    def test_experiment_script(self):
        out = Path(self.tmp.name) / "script.json"
        done = subprocess.run([sys.executable, str(REPO / "experiment.py"), "--out", str(out)], capture_output=True,
                              text=True, cwd=self.tmp.name, timeout=300)  # fmt: skip
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(out.read_text(), self.text)

    def test_demo_renders_the_readme_block(self):
        readme, rendered = Path(self.tmp.name) / "README.md", Path(self.tmp.name) / "rendered.md"
        readme.write_text("# Title\n\nKeep this.\n\n<!-- results:start -->\nstale\n<!-- results:end -->\n\nAnd this.\n")
        args = ["--readme", str(readme), "--out", str(rendered), "--results", str(self.out.parent)]
        done = subprocess.run(
            [sys.executable, str(REPO / "demo.py"), *args], capture_output=True, text=True, timeout=300
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        text = rendered.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Title\n\nKeep this.\n\n<!-- results:start -->\n"))
        self.assertTrue(text.endswith("<!-- results:end -->\n\nAnd this.\n"))
        self.assertNotIn("stale", text)
        block = text.split("<!-- results:start -->")[1].split("<!-- results:end -->")[0]
        for value in ("6271", "3293", "2707", "1440"):
            self.assertIn(value, block)
        self.assertIn("not by an auditor", block)
        for example in ("2025-06-GSAFAC-0000392695 2025-001", "2024-06-GSAFAC-0000377872 2024-003",
                        "2024-06-GSAFAC-0000376191 2024-008", "2024-12-GSAFAC-0000381878 2024-006"):  # fmt: skip
            self.assertIn(example, block)
        self.assertIn("Questioned Costs: $0", block)

    def test_demo_summary(self):
        done = subprocess.run([sys.executable, str(REPO / "demo.py"), "--results", str(self.out.parent)],
                              capture_output=True, text=True, timeout=300)  # fmt: skip
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(done.stdout.strip().splitlines()), 1)
        self.assertIn("6271", done.stdout)
