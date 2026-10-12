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
        self.assertFalse(valid_programme({'programme': None}))
        self.assertFalse(valid_programme({'programme': []}))
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

    def test_quality_quarantine_and_cached_rebuild(self):
        class Store:
            requests = 0
            def programme(self, day):
                return {'reunions': [{'numOfficiel':1,'pays':{'code':'FRA'},'hippodrome':{'libelleCourt':'TEST'},
                    'courses':[{'numOrdre':1,'discipline':'ATTELE','nombreDeclaresPartants':1}]}]} if day.endswith(('-01','-02')) else {'reunions':[]}
            def race(self, day, rn, cn, endpoint):
                if endpoint:
                    return {'participants':[{'numPmu':1,'idCheval':'A','ordreArrivee':1}]}
                return {'ordreArrivee':[[1 if day.endswith('-01') else 2]], 'arriveeDefinitive':True}
        with tempfile.TemporaryDirectory() as tmp:
            first=collect('2024-01',Store(),Path(tmp))
            second=collect('2024-01',Store(),Path(tmp))
            self.assertEqual(first,second)
            self.assertEqual(len(first['partitions']),1)
            self.assertEqual(len(first['quarantine']),1)
            self.assertEqual(first['quarantine'][0]['issues'][0]['issue'],'winner_disagreement')
