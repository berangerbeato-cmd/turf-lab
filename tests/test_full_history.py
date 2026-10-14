import copy
import importlib.util
import json
import unittest
from pathlib import Path
from scripts.retest_full_history import gate, learn, predict
from turf_lab.full_history_features import augment_continuous, prepare, seasonal
from turf_lab.full_history_evaluation import chronological, paired, score, matrix
from tests.test_xgb_model import fixture
from tests.test_opposition import race


class FullHistoryTests(unittest.TestCase):
    def test_missing_months_stop_full_retest(self):
        p=json.loads(Path('config/full_history_protocol.json').read_text())
        self.assertEqual(len(gate([],p)),57)
        row={'month':'2022-01','status':'COMPLETE','source_verified':False,'issues':[], 'coverage_fraction':1}
        self.assertIn('2022-01',gate([row],p))

    def test_chronological_overlap_rejected(self):
        a={'race_id':'a','date':'2024-01-01'};b={'race_id':'b','date':'2025-01-01'};c={'race_id':'c','date':'2026-01-01'}
        chronological([a],[b],[c])
        with self.assertRaises(ValueError):chronological([a],[b],[b])
        with self.assertRaises(ValueError):chronological([b],[a],[c])

    def test_elo_continues_across_new_year_and_excludes_today(self):
        rows=[race('2022-12-31'),race('2023-01-01')]
        out=augment_continuous(rows)
        self.assertGreater(out[1]['runners'][0]['opposition_features'][1],0)
        changed=copy.deepcopy(rows)
        for r in changed[1]['runners']:r['rank']=3-r['rank']
        out2=augment_continuous(changed)
        self.assertEqual([r['opposition_features'] for r in out[1]['runners']],
                         [r['opposition_features'] for r in out2[1]['runners']])

    def test_seasonal_interactions_preserve_missing(self):
        rows=fixture();rows[0]['runners'][0]['features'][0]=None
        out=seasonal(rows)
        self.assertEqual(len(out[0]['runners'][0]['features']),48)
        self.assertEqual(len(rows[0]['runners'][0]['features']),38)
        self.assertIsNone(out[0]['runners'][0]['features'][38])

    def test_full_feature_pipeline_ignores_future_outcomes(self):
        def record(day,winner):
            return {'date':day,'race_id':day+'_R1C1','venue':'TEST','country':'FRA','start_type':'AUTOSTART',
              'distance_m':2100,'scheduled_start_ms':0,'course':{},'participants':[
                {'numPmu':i,'nom':str(i),'nomMere':'M'+str(i),'nomPere':'P',
                 'ordreArrivee':1 if i==winner else 2,'statut':'PARTANT','age':5,'sexe':'HONGRES',
                 'driver':'D'+str(i),'entraineur':'T'+str(i),'deferre':'DEFERRE_POSTERIEURS'} for i in (1,2)]}
        records=[record('2022-12-31',1),record('2023-01-01',2),record('2023-01-02',1)]
        before=prepare(records);changed=copy.deepcopy(records)
        for r in changed[1:]:
            for p in r['participants']:p['ordreArrivee']=3-p['ordreArrivee']
        after=prepare(changed)
        self.assertEqual([p['features'] for p in before[1]['runners']], [p['features'] for p in after[1]['runners']])
        self.assertEqual(len(before[1]['runners'][0]['features']),38)


@unittest.skipUnless(importlib.util.find_spec('xgboost') and importlib.util.find_spec('numpy'), 'Numerical dependencies installed in evaluation job')
class NumericalPipelineTests(unittest.TestCase):
    def test_training_calibration_prediction_and_uncertainty(self):
        p=json.loads(Path('config/full_history_protocol.json').read_text());p.update(iterations=5,num_boost_round=2)
        tr=fixture();val=copy.deepcopy(tr);te=copy.deepcopy(tr)
        for rows,year in ((tr,'2022'),(val,'2025'),(te,'2026')):
            for i,r in enumerate(rows):
                r.update(date=f'{year}-01-{i+1:02d}',race_id=f'{year}_{i}',venue='TEST',start_type='AUTOSTART')
        chronological(tr,val,te)
        classic,trees,temps,alpha,vpred,_=learn(tr,val,p)
        pred,_=predict(te,classic,trees,temps,alpha)
        self.assertEqual(set(pred),{'classic','xgboost','xgboost_rank','ensemble','uniform'})
        self.assertEqual(score(te,pred['classic'])['overall']['races'],len(te))
        ci=paired(te,pred['classic'],pred['classic'],repetitions=50)
        self.assertEqual(ci['metrics']['log_loss']['interval_95'],[0.,0.])
        changed=copy.deepcopy(te)
        for r in changed:
            for runner in r['runners']:runner['won']=1-runner['won']
        self.assertEqual(predict(changed,classic,trees,temps,alpha)[0],pred)
        self.assertEqual(matrix(seasonal(tr),True).num_col(),48)

class RateLimitTests(unittest.TestCase):
    def test_http_429_stops_collection_without_retry(self):
        import tempfile
        from unittest.mock import patch
        from scripts.backfill_history import StopOnUnavailable
        from turf_lab.evidence import EvidenceStore
        with tempfile.TemporaryDirectory() as tmp:
            store=StopOnUnavailable(Path(tmp),max_requests=2,delay=0)
            def fail(self,url,key):
                self.manifest[key]={'status':429}
                return None
            with patch.object(EvidenceStore,'get',fail):
                with self.assertRaisesRegex(RuntimeError,'429'):
                    store.get('https://example.test','day')
