"""Tests for page.py."""

import unittest
from pathlib import Path

import page


class PageTest(unittest.TestCase):
    def test_committed_page_matches_results(self):
        self.assertEqual(Path(page.ROOT, "docs", "index.html").read_text(encoding="utf-8"), page.build())

    def test_headline_numbers(self):
        built = page.build()
        for text in ("68.4%", "54/79", "9/79", "54/59", "47/50"):
            self.assertIn(text, built)
