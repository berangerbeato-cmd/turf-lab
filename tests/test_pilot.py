import copy
import unittest
from turf_lab.pilot import dated_history,features,fit,probabilities,metrics

class PilotTests(unittest.TestCase):
    def race(self):
        return {'runners':[{'number':1,'non_runner':False,'won':1,'features':[1,.5,0,2,1]}, {'number':2,'non_runner':False,'won':0,'features':[None]*4+[0]}, {'number':3,'non_runner':True,'won':0,'features':[1]*5}]}
    def test_non_runners_and_normalization(self):
        r=self.race();m=fit([r],1);p=probabilities(r,m)
        self.assertAlmostEqual(sum(p.values()),1);self.assertEqual(p[3],0)
        r['runners'][0]['non_runner']=True;p=probabilities(r,m);self.assertEqual(p[2],1)
    def test_target_and_odds_do_not_change_prediction(self):
        r=self.race();m=fit([r],1);p=probabilities(r,m)
        for x in r['runners']:x.update(won=0,rank=9,odds=999,incident='DISQUALIFIE')
        self.assertEqual(probabilities(r,m),p)
    def test_future_rejected(self):
        with self.assertRaises(ValueError):features([{'date':'2025-01-01'}],'2025-01-01')
        with self.assertRaises(ValueError):dated_history({'coursesCourues':[{'date':1735689600000}]},'2025-01-01')
    def test_metrics_multiclass(self):
        m=metrics([self.race()],{'kind':'uniform'})
        self.assertAlmostEqual(m['brier_multiclass'],.5);self.assertEqual(m['top1_accuracy'],1)
    def test_training_does_not_mutate(self):
        r=self.race();before=copy.deepcopy(r);fit([r],1);self.assertEqual(r,before)
    def test_dq_no_invented_rank(self):
        h={'nomCheval':'A','coursesCourues':[{'date':1704067200000,'discipline':'ATTELE','participants':[{'nomCheval':'A','itsHim':True,'place':{'statusArrivee':'DISQUALIFIE','place':None}}]}]}
        rows=dated_history(h,'2024-02-01');self.assertIsNone(rows[0]['rank']);self.assertEqual(features(rows,'2024-02-01')[2],1)
