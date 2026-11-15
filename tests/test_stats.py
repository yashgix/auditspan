"""Tests for findingtrace.stats."""

import unittest

import numpy as np

from findingtrace.stats import report_bootstrap, wilson


class WilsonTest(unittest.TestCase):
    def test_empty_sample(self):
        self.assertEqual(wilson(0, 0), (0.0, 0.0, 1.0))

    def test_no_hits(self):
        rate, lo, hi = wilson(0, 10)
        self.assertEqual(rate, 0.0)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)
        self.assertLess(hi, 1.0)

    def test_all_hits(self):
        rate, lo, hi = wilson(10, 10)
        self.assertEqual(rate, 1.0)
        self.assertGreater(lo, 0.0)
        self.assertLess(lo, 1.0)
        self.assertEqual(hi, 1.0)

    def test_known_half(self):
        rate, lo, hi = wilson(5, 10)
        self.assertEqual(rate, 0.5)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)

    def test_symmetry(self):
        low_rate, low_lo, low_hi = wilson(3, 10)
        high_rate, high_lo, high_hi = wilson(7, 10)
        self.assertAlmostEqual(low_rate + high_rate, 1.0)
        self.assertAlmostEqual(low_lo, 1.0 - high_hi, places=9)
        self.assertAlmostEqual(low_hi, 1.0 - high_lo, places=9)


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.hits = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        self.totals = np.ones_like(self.hits)

    def test_deterministic_and_shaped(self):
        first = report_bootstrap(self.hits, self.totals, 200, 7)
        second = report_bootstrap(self.hits, self.totals, 200, 7)
        self.assertEqual(first[0].shape, (2,))
        np.testing.assert_array_equal(first[0], second[0])
        np.testing.assert_array_equal(first[1], second[1])
        self.assertTrue(np.all(first[0] >= 0.0))
        self.assertTrue(np.all(first[1] <= 1.0))
        self.assertTrue(np.all(first[0] <= first[1]))

    def test_zero_total_column(self):
        hits = np.zeros((2, 1))
        totals = np.zeros((2, 1))
        lo, hi = report_bootstrap(hits, totals, 50, 1)
        np.testing.assert_array_equal(lo, np.zeros(1))
        np.testing.assert_array_equal(hi, np.zeros(1))
