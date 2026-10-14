import json
import unittest
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from pathlib import Path
from tests.test_shadow_v5_score import fixture
from scripts.capture_pmu_quotes import validate,window


class QuoteTests(unittest.TestCase):
    def sample(self):
        p=json.loads(Path('config/pmu_quotes_today.json').read_text())
        prediction,_,parts=fixture()
        prediction['models']={'v6':prediction['models']['combined']}
        now=datetime(2026,10,14,11,45,tzinfo=timezone.utc)
        for r in parts:
            r.pop('ordreArrivee')
            r['dernierRapportDirect']={'typePari':'SIMPLE_GAGNANT','typeRapport':'DIRECT',
                'numPmu1':r['numPmu'],'rapport':3.3,'dateRapport':(now-timedelta(minutes=6)).timestamp()*1000}
        return prediction,{},parts,now,p

    def test_valid_timestamped_pair(self):
        args=self.sample()
        old=deepcopy(args[0])
        result=validate(*args)
        self.assertEqual(result['minutes_before_start'],15)
        self.assertEqual(result['quotes'][0]['quote_age_seconds'],360)
        self.assertEqual(result['quotes'][0]['v6_probability'],.7)
        self.assertEqual(args[0],old)

    def test_stale_future_wrong_market_and_field(self):
        for kind in ('stale','future','market','field','result'):
            prediction,detail,parts,now,p=self.sample()
            q=parts[0]['dernierRapportDirect']
            if kind=='stale':q['dateRapport']=(now-timedelta(minutes=11)).timestamp()*1000
            if kind=='future':q['dateRapport']=(now+timedelta(seconds=1)).timestamp()*1000
            if kind=='market':q['typePari']='SIMPLE_PLACE'
            if kind=='field':parts[0]['driver']='CHANGED'
            if kind=='result':detail['arriveeDefinitive']=True
            with self.assertRaises(ValueError):
                validate(prediction,detail,parts,now,p)

    def test_departure_window(self):
        prediction,detail,parts,now,p=self.sample()
        start=datetime.fromisoformat(prediction['scheduled_start'])
        self.assertTrue(window(now,start,p))
        self.assertFalse(window(start,start,p))
        self.assertFalse(window(start-timedelta(minutes=21),start,p))
        with self.assertRaises(ValueError):
            validate(prediction,detail,parts,start,p)
