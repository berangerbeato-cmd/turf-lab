import tempfile
import unittest
from pathlib import Path
from scripts.collect_month import collect, month_days, valid_programme

class MonthTests(unittest.TestCase):
    def test_full_calendar(self):
        self.assertEqual(len(month_days('2024-02')), 29)
        self.assertEqual(month_days('2024-01')[-1], '2024-01-31')

    def test_empty_response_not_zero_race_day(self):
        self.assertFalse(valid_programme({}))
        self.assertFalse(valid_programme(None))
        self.assertTrue(valid_programme({'programme': {'reunions': []}}))

    def test_missing_programme_is_recorded(self):
        class Store:
            requests = 0
            def programme(self, day):
                return None if day.endswith('-02') else {'reunions': []}
        with tempfile.TemporaryDirectory() as tmp:
            report = collect('2024-01', Store(), Path(tmp))
            self.assertEqual(report['status'], 'COLLECTED_WITH_GAPS')
            self.assertEqual(len(report['days']), 31)
            self.assertEqual(report['days'][1]['status'], 'PROGRAMME_UNAVAILABLE')

    def test_budget_pause_retains_checkpoint(self):
        class Store:
            requests = 1
            def programme(self, day):
                raise RuntimeError('Bounded audit request budget reached; rerun')
        with tempfile.TemporaryDirectory() as tmp:
            report = collect('2024-01', Store(), Path(tmp))
            self.assertEqual(report['status'], 'PAUSED_REQUEST_BUDGET')
            self.assertTrue((Path(tmp)/'manifest.json').exists())
