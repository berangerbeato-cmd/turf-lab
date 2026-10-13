import unittest
from scripts.audit_connections import calibration_summary
from scripts.prepare_connections_shadow import authorized_month


class AuditTest(unittest.TestCase):
    def test_weighted_calibration(self):
        result = calibration_summary([{'count': 90, 'mean_probability': .1, 'win_frequency': .2},
                                      {'count': 10, 'mean_probability': .5, 'win_frequency': .5}])
        self.assertAlmostEqual(result['runner_weighted_ece'], .09)
        self.assertEqual(result['runner_count'], 100)

    def test_empty_calibration(self):
        with self.assertRaises(ValueError):
            calibration_summary([])

    def test_bounded_completed_history(self):
        p = {'collection_months': ['2026-09', '2026-10']}
        authorized_month('2026-09', p, '2026-10-13')
        for month in ['2026-08', '2026-10', '2026-11']:
            with self.assertRaises(ValueError):
                authorized_month(month, p, '2026-10-13')
