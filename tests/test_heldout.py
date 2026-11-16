"""Tests for auditspan.heldout."""

import hashlib
import unittest

from auditspan import DATA_DIR
from auditspan.data import Finding, Form, load
from auditspan.extract import requirements
from auditspan.heldout import (
    HELDOUT_DIR,
    adjudicate,
    load_decisions,
    load_dev_ids,
    load_heldout,
    score_extractor,
    stated,
    text_hash,
)


def finding(text, filed):
    return Finding("R", text[:8], 2024, text, Form(False, False, False, False, filed, 1, ()))


def label(letters, where):
    return {"id": "R x", "letters": letters, "where": where, "span": ""}


class StatedTest(unittest.TestCase):
    def test_scopes_and_p(self):
        self.assertEqual(stated(label("L", "prose"), "label_title"), "")
        self.assertEqual(stated(label("L", "prose"), "all"), "L")
        self.assertEqual(stated(label("IP", "label"), "all", drop_p=True), "I")
        self.assertEqual(stated(label("none", "none"), "all"), "")


class ScoreTest(unittest.TestCase):
    def test_counts(self):
        pairs = [
            (finding("Compliance requirement: Reporting", "L"), label("L", "label")),
            (finding("Compliance requirement: Allowable costs", "AB"), label("AB", "label")),
            (finding("Compliance requirement: Eligibility", "E"), label("none", "none")),
            (finding("Nothing here", "N"), label("N", "prose")),
        ]
        scores = score_extractor(pairs, requirements)
        self.assertEqual(scores["extracted"], 3)
        self.assertEqual((scores["precision"]["k"], scores["precision"]["n"]), (1, 3))
        self.assertEqual(scores["false_positive"], 1)
        self.assertEqual(scores["a_vs_b_only"], 1)
        self.assertEqual((scores["recall_label_title"]["k"], scores["recall_label_title"]["n"]), (1, 2))
        self.assertEqual((scores["recall_all"]["k"], scores["recall_all"]["n"]), (1, 3))
        self.assertEqual(scores["form"], {"agree": 3})


class FilesTest(unittest.TestCase):
    def test_files_match_their_checksums(self):
        for line in (HELDOUT_DIR / "SHA256SUMS").read_text().splitlines():
            digest, name = line.split()
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((HELDOUT_DIR / name).read_bytes()).hexdigest(), digest)

    def test_labels_follow_the_drawn_ids(self):
        ids = (HELDOUT_DIR / "ids.txt").read_text().split("\n")[:-1]
        self.assertEqual([row["id"] for row in load_heldout()], ids)
        self.assertEqual(len(ids), 150)

    def test_development_and_hold_out_are_disjoint_by_id_and_text(self):
        findings = {f"{f.report_id} {f.ref}": f for f in load(DATA_DIR).findings}
        dev, held = load_dev_ids(), [row["id"] for row in load_heldout()]
        self.assertFalse(dev & set(held))
        seen = {text_hash(findings[key]) for key in dev}
        overlap = [key for key in held if text_hash(findings[key]) in seen]
        self.assertEqual(overlap, ["2024-09-GSAFAC-0000384866 2024-001"])
        self.assertEqual(findings[overlap[0]].text, findings["2024-09-GSAFAC-0000385016 2024-001"].text)


if __name__ == "__main__":
    unittest.main()


class AdjudicationTest(unittest.TestCase):
    def test_applies_only_listed_ids(self):
        labels = [label("P", "title"), {"id": "R y", "letters": "L", "where": "label", "span": ""}]
        decisions = [{"id": "R x", "result": {"letters": "N", "where": "title"}}]
        out = adjudicate(labels, decisions)
        self.assertEqual((out[0]["letters"], out[0]["where"]), ("N", "title"))
        self.assertEqual(out[1], labels[1])

    def test_committed_decisions_match_the_codex_labels(self):
        codex = {row["id"]: row for row in load_heldout()}
        decisions = load_decisions()
        self.assertEqual(len(decisions), 30)
        for row in decisions:
            blind = codex[row["id"]]
            self.assertEqual(row["codex"], {"letters": blind["letters"], "where": blind["where"]})
            self.assertEqual(row["changed"], row["result"] != row["codex"])
        self.assertEqual([row["item"] for row in decisions if row["corrected_by_claude"]], [1, 4, 12])
