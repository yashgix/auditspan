"""Tests for findingtrace.heldout."""

import hashlib
import unittest

from findingtrace.data import Finding, Form
from findingtrace.extract import requirements
from findingtrace.heldout import HELDOUT_DIR, load_heldout, score_extractor, stated


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


if __name__ == "__main__":
    unittest.main()
