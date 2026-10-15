import unittest
from scripts.calibrate_market_tickets import fit_calibration,apply_calibration

class CalibrationTests(unittest.TestCase):
    def test_future_rows_rejected(self):
        with self.assertRaises(ValueError):fit_calibration([{'date':'2026-01-01','probability':.5,'observed_hit':1}])
    def test_overconfidence_reduced_and_monotonic(self):
        rows=[{'date':'2025-01-01','probability':.8,'observed_hit':int(i%2==0)} for i in range(100)]
        c=fit_calibration(rows)
        self.assertLess(abs(apply_calibration(.8,c)-.5),.02)
        self.assertLessEqual(apply_calibration(.2,c),apply_calibration(.8,c))
