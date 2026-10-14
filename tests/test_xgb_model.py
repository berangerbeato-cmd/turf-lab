import importlib.util
import json
import math
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from turf_lab import xgb_model as x
from turf_lab.pilot import metrics as original_metrics, probabilities


def fixture():
    return [{'race_id':str(i),'date':'2024-03-02','runners':[
        {'number':1,'non_runner':False,'won':True,'features':[1.,None]+[0.]*36},
        {'number':2,'non_runner':False,'won':False,'features':[0.,None]+[0.]*36},
        {'number':3,'non_runner':True,'won':False,'features':[999.]*38}]} for i in range(4)]


class XGBProbabilityTests(unittest.TestCase):
    def test_normalization_shift_and_nonrunner(self):
        race=fixture()[0]
        a=x.from_margins(race,[1000.,1001.])
        b=x.from_margins(race,[0.,1.])
        self.assertEqual(a,b)
        self.assertEqual(a[3],0)
        self.assertAlmostEqual(sum(a.values()),1)
        with self.assertRaises(ValueError):
            x.from_margins(race,[float('nan'),0])

    def test_metrics_reproduce_existing_and_reject_invalid(self):
        races=fixture()
        model={'kind':'uniform'}
        predictions=[probabilities(r,model) for r in races]
        self.assertEqual(x.metrics(races,predictions),original_metrics(races,model))
        self.assertEqual(x.paired(races,predictions,predictions)['delta_log_loss'],0)
        predictions[0][1]=float('nan')
        with self.assertRaises(ValueError):
            x.metrics(races,predictions)


@unittest.skipUnless(importlib.util.find_spec('xgboost') and importlib.util.find_spec('numpy'),'optional XGBoost dependencies absent')
class XGBTrainingTests(unittest.TestCase):
    def test_weights_dimensions_and_label_guard(self):
        races=fixture()
        data=x.matrix(races,True)
        self.assertEqual(data.num_col(),38)
        self.assertEqual(data.num_row(),8)
        self.assertAlmostEqual(float(sum(data.get_weight())),4)
        races[0]['runners'][1]['won']=True
        with self.assertRaises(ValueError):
            x.matrix(races,True)

    def test_saved_model_and_inference_ignore_results(self):
        import xgboost as xgb
        p=json.loads(Path('config/xgboost_v1_protocol.json').read_text())
        p['num_boost_round']=2
        rows=fixture()
        model=x.fit(rows,p)
        expected=x.predict(rows,model)
        changed=deepcopy(rows)
        for race in changed:
            for runner in race['runners']:
                runner.pop('won')
                runner.update(rank=999,odds=100000,tempsObtenu=0)
        self.assertEqual(x.predict(changed,model),expected)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'model.json'
            model.save_model(path)
            loaded=xgb.Booster();loaded.load_model(path)
            self.assertEqual(x.predict(rows,loaded),expected)
