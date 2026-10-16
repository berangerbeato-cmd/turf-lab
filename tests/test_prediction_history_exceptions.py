import unittest
from datetime import date
from turf_lab.live_history import check_prediction_history


class PredictionHistoryExceptions(unittest.TestCase):
    def test_only_known_old_gap_allowed(self):
        rows=[dict(date='2023-01-22',status='PARTIEL'),dict(date='2026-10-15',status='OK')]
        self.assertEqual(check_prediction_history(rows,date(2026,10,16),['2023-01-22']),['2023-01-22'])
        with self.assertRaises(ValueError): check_prediction_history(rows,date(2026,10,16),[])

    def test_yesterday_cannot_be_waived(self):
        for rows in ([],[dict(date='2026-10-15',status='PARTIEL')]):
            with self.assertRaises(ValueError): check_prediction_history(rows,date(2026,10,16),['2026-10-15'])
