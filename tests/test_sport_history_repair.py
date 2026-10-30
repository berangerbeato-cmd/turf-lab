import copy,unittest
from turf_lab.sport_history_repair import repaired_frame,sensitivity
class Repair(unittest.TestCase):
 def setUp(self):
  self.m={'runners':[{'number':1,'non_runner':False,'features':[None,None,None,None,0,7]},{'number':2,'non_runner':True,'features':[0]*6}]}
  self.c={'runners':[{'number':1,'status':'MODEL_HISTORY_INCOMPLETE','supplemented_recent_features_for_research':[1,1,0,2,.2]}]}
 def test_only_recent_features_change(self):
  old=copy.deepcopy(self.m);f,changed=repaired_frame(self.m,self.c)
  self.assertEqual(changed,[1]);self.assertEqual(f['runners'][0]['features'],[1,1,0,2,.2,7]);self.assertEqual(self.m,old)
 def test_conflict_blocks(self):
  self.c['runners'][0]['status']='CONFLICT'
  with self.assertRaises(ValueError):repaired_frame(self.m,self.c)
 def test_missing_blocks(self):
  with self.assertRaises(ValueError):repaired_frame(self.m,{'runners':[]})
 def test_market_free_and_no_recommendation(self):
  model={'kind':'uniform'};r=sensitivity(self.m,self.c,model)
  self.assertFalse(r['market_informed']);self.assertFalse(r['recommendations_allowed']);self.assertEqual(r['probabilities'],{1:1.,2:0.})
