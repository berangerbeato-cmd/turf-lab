import json
import unittest
import os
import tempfile
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scripts.capture_pmu_cohort import authorized, due
from scripts import capture_pmu_cohort as collector
from tests.test_pmu_quotes import QuoteTests


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads(Path('config/pmu_quotes_cohort.json').read_text())
        self.now = datetime(2026,10,15,12,tzinfo=timezone.utc)
        self.start = self.now+timedelta(minutes=15)

    def test_fixed_dates_and_year(self):
        self.assertTrue(authorized(self.now,self.p))
        self.assertFalse(authorized(self.now.replace(day=14),self.p))
        self.assertFalse(authorized(self.now.replace(year=2027),self.p))
        self.assertFalse(authorized(self.now.replace(month=11),self.p))

    def test_minute_poll_survives_single_cron_launch(self):
        # One worker launched an hour early eventually reaches the capture window.
        ticks = [self.now-timedelta(minutes=60)+timedelta(minutes=i) for i in range(80)]
        available = [t for t in ticks if due(t,self.start,{},self.p)]
        self.assertEqual(len(available),16)
        self.assertFalse(due(self.start,self.start,{},self.p))

    def test_retry_budget_and_restart(self):
        self.assertTrue(due(self.now,self.start,{},self.p))
        self.assertFalse(due(self.now,self.start,{'status':'CAPTURED'},self.p))
        self.assertFalse(due(self.now,self.start,{'attempts':5},self.p))
        state={'attempts':1,'last_attempt':self.now.isoformat()}
        self.assertFalse(due(self.now+timedelta(seconds=60),self.start,state,self.p))
        self.assertTrue(due(self.now+timedelta(seconds=120),self.start,state,self.p))

    def test_capture_persist_restart_without_second_request(self):
        prediction,detail,parts,now,_ = QuoteTests().sample()
        # Keep fixture start/quotes coherent; authorize that date in test only.
        policy=dict(self.p, **{'from':'2026-10-14'})
        prediction.update(status='SHADOW_NO_BET',race_id='2026-10-14_R1C1',
                          predicted_at=(now-timedelta(hours=1)).isoformat(),frozen={'test':True})
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None): return now
        class Store:
            calls=0
            manifest_path='test-manifest.json'
            def __init__(self,*args,**kwargs): pass
            def race(self,*args):
                Store.calls+=1
                return {'participants':parts} if args[-1]=='participants' else detail
        previous=os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                folder=Path('predictions_cohort/2026-10-14');folder.mkdir(parents=True)
                source=folder/'2026-10-14_R1C1.json';source.write_text(json.dumps(prediction))
                (folder/'plan.json').write_text(json.dumps({'date':'2026-10-14','frozen':{'test':True},
                    'selection':[[{'numOfficiel':1},{'numOrdre':1}]]}))
                policy_path=Path('policy.json');policy_path.write_text(json.dumps(policy))
                with patch.object(collector,'POLICY',policy_path), patch.object(collector,'datetime',Clock), \
                     patch.object(collector,'verify',return_value=({}, {'test':True})), \
                     patch.object(collector,'EvidenceStore',Store),patch.object(collector,'digest',return_value='test'):
                    collector.main()
                    output=Path('quotes_pmu/cohort/2026-10-14/2026-10-14_R1C1.json')
                    first=output.read_bytes()
                    collector.main()
                    self.assertEqual(first,output.read_bytes())
                    self.assertEqual(Store.calls,2)
                    state=json.loads(Path('reports/pmu_cohort/2026-10-14/2026-10-14_R1C1.json').read_text())
                    self.assertEqual(state['status'],'CAPTURED')
            finally:
                os.chdir(previous)
