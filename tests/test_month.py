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

    def test_weekly_durable_checkpoint_boundaries(self):
        class Store:
            requests = 0
            def programme(self, day):
                return {'reunions': []}
        observed=[]
        with tempfile.TemporaryDirectory() as tmp:
            import json
            root=Path(tmp)
            def checkpoint():
                observed.append(len(json.loads((root/'manifest.json').read_text())['days']))
            collect('2024-01', Store(), root, checkpoint)
        self.assertEqual(observed,[7,14,21,28,31])

    def test_complete_cache_is_verified_without_network_or_checkpoint(self):
        import json,gzip,hashlib
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=b'{}';part=root/'race.gz';part.write_bytes(gzip.compress(raw))
            report={'month':'2024-01','status':'COLLECTED','days':[{'date':d,'status':'OK'} for d in month_days('2024-01')],
                    'partitions':[{'file':str(part),'race_id':'r','sha256':hashlib.sha256(raw).hexdigest()}]}
            (root/'manifest.json').write_text(json.dumps(report));store=Mock();checkpoint=Mock()
            self.assertEqual(collect('2024-01',store,root,checkpoint),report)
            store.programme.assert_not_called();checkpoint.assert_not_called()
            part.write_bytes(gzip.compress(b'corrupt'))
            with self.assertRaisesRegex(ValueError,'digest mismatch'):
                collect('2024-01',store,root,checkpoint)

    def test_checkpoint_rebases_again_after_concurrent_push(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from scripts.collect_month import git_checkpoint
        calls=[]; pushes=0
        def run(args,**kwargs):
            nonlocal pushes
            calls.append(args)
            if args[:2]==['git','diff']:return SimpleNamespace(returncode=1)
            if args[:2]==['git','push']:
                pushes+=1;return SimpleNamespace(returncode=1 if pushes==1 else 0)
            return SimpleNamespace(returncode=0)
        with patch('scripts.collect_month.subprocess.run',side_effect=run):
            git_checkpoint(Path('evidence'),Path('data'))
        self.assertEqual(pushes,2)
        self.assertEqual(sum(c[:2]==['git','pull'] for c in calls),2)
        self.assertFalse(any('--force' in c for c in calls))
