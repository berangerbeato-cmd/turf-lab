import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path
from tests.test_xgb_model import fixture
from turf_lab import xgb_rank as rank


class RankSelectionTests(unittest.TestCase):
    def test_temporal_and_overlap_guards(self):
        train=fixture()
        val=deepcopy(train)
        with self.assertRaises(ValueError):
            rank.chronological(train,val)
        for r in val:
            r['date']='2024-04-01'
        with self.assertRaises(ValueError):
            rank.chronological(train,val)
        for r in val:
            r['race_id']='future_'+r['race_id']
        rank.chronological(train,val)

    def test_temperature_normalization_and_ties(self):
        races=fixture()[:1]
        a=rank.predictions(races,[[0,1]],.5)[0]
        b=rank.predictions(races,[[0,1]],2)[0]
        self.assertGreater(a[2],b[2])
        self.assertAlmostEqual(sum(a.values()),1)
        self.assertEqual(a[3],0)
        with self.assertRaises(ValueError):
            rank.predictions(races,[[0,1]],0)
        trials=[{'name':'first','fold_log_losses':[1,3]},{'name':'second','fold_log_losses':[2,2]}]
        self.assertIs(rank.choose(trials),trials[0])


@unittest.skipUnless(importlib.util.find_spec('xgboost') and importlib.util.find_spec('numpy'),'optional XGBoost dependencies absent')
class RankTrainingTests(unittest.TestCase):
    def test_exact_groups_and_equal_race_weights(self):
        rows=fixture()
        data=rank.training_matrix(rows)
        self.assertEqual(list(data.get_uint_info('group_ptr')),[0,2,4,6,8])
        self.assertEqual(list(data.get_weight()),[1,1,1,1])
        self.assertEqual(list(data.get_label()),[1,0]*4)

    def test_both_objectives_and_result_blind_inference(self):
        p=json.loads(Path('config/xgboost_rank_v2_protocol.json').read_text())
        p['num_boost_round']=2
        rows=fixture()
        for choice in [p['candidates'][0],p['candidates'][2]]:
            model=rank.fit(rows,choice,p)
            values=rank.scores(rows,model)
            changed=deepcopy(rows)
            for r in changed:
                for h in r['runners']:
                    h.pop('won')
                    h['odds']=999
            self.assertEqual(rank.scores(changed,model),values)
