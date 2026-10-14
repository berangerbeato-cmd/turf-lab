import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from scripts import prospective_cohort as c
from tests.test_shadow_v5_score import fixture
from turf_lab.evidence import dump


class CohortTests(unittest.TestCase):
    def test_freeze_and_tamper(self):
        p,lock=c.verify()
        self.assertEqual(p['reference'],'v6')
        self.assertFalse(p['promotion'])
        with patch.object(c,'digest',return_value='changed'):
            with self.assertRaises(ValueError):
                c.verify()

    def test_sampling_fixed_unique_endpoints_and_sorted(self):
        items=[({'numOfficiel':1},{'numOrdre':i,'heureDepart':i}) for i in range(41)]
        selected=c.select(list(reversed(items)),20)
        self.assertEqual(len(selected),20)
        self.assertEqual(selected[0],items[0])
        self.assertEqual(selected[-1],items[-1])
        self.assertEqual(len({x[1]['numOrdre'] for x in selected}),20)
        self.assertEqual(c.select(items[:3],20),items[:3])

    def test_no_network_outside_dates(self):
        with patch.object(c,'datetime') as clock, patch.object(c,'EvidenceStore') as store:
            clock.now.return_value=datetime(2026,10,14,12,tzinfo=timezone.utc)
            c.main('capture')
            store.assert_not_called()
            clock.now.return_value=datetime(2027,10,15,12,tzinfo=timezone.utc)
            c.main('capture')
            store.assert_not_called()

    def test_paired_score_reused_without_result_refetch(self):
        p,_=c.verify()
        prediction,detail,runners=fixture()
        rid='2026-10-15_R1C1'
        prediction.update(race_id=rid,status='SHADOW_NO_BET',frozen={},scheduled_start='2026-10-15T12:00:00+00:00')
        prediction['models']={'v6':prediction['models']['v3'],'v7_speed':prediction['models']['combined']}
        old=Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                dump('predictions_cohort/2026-10-15/'+rid+'.json',prediction)
                dump('predictions_cohort/2026-10-15/plan.json',{'selection':[{}]})
                with patch.object(c,'EvidenceStore') as factory:
                    store=factory.return_value
                    store.requests=0
                    store.manifest_path='evidence/test/manifest.json'
                    store.race.side_effect=[detail,{'participants':runners}]
                    c.evaluate(datetime(2026,10,15,10,tzinfo=timezone.utc),p,{})
                    store.race.assert_not_called()
                    c.evaluate(datetime(2026,10,15,13,tzinfo=timezone.utc),p,{})
                    report=json.loads(Path('reports/cohort_status.json').read_text())
                    self.assertEqual(report['scored'],1)
                    self.assertEqual(set(report['metrics']),{'v6','v7_speed'})
                    self.assertEqual(store.race.call_count,2)
                    c.evaluate(datetime(2026,10,15,14,tzinfo=timezone.utc),p,{})
                    self.assertEqual(store.race.call_count,2)
            finally:
                os.chdir(old)
