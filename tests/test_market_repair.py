import copy,json,unittest
from pathlib import Path
from turf_lab.market_repair import predict,fit
from turf_lab.individual_history_check import normalize_history,reconcile

class Repair(unittest.TestCase):
 def test_market_baseline_and_sports_baseline(self):
  self.assertEqual(predict([2,4],[.2,.8],[1,0]),[2/3,1/3])
  self.assertAlmostEqual(predict([2,4],[.2,.8],[0,1])[0],.2)
 def test_bad_input(self):
  for odds,sport,w in [([2],[1],[1,0]),([2,3],[.2],[1,0]),([1,3],[.5,.5],[1,0]),([2,3],[float('nan'),.5],[1,0]),([2,3],[.5,.5],[-1,0])]:
   with self.assertRaises(ValueError):predict(odds,sport,w)
 def test_probabilities_and_order_invariance(self):
  odds=[2,5,80];sport=[.2,.3,.5];w=[.9,.3];p=predict(odds,sport,w)
  self.assertAlmostEqual(sum(p),1);self.assertGreater(p[0],p[2])
  self.assertEqual(p,list(reversed(predict(odds[::-1],sport[::-1],w))))
 def test_fit_rejects_test_data(self):
  protocol=json.loads(Path('config/market_repair_v1.json').read_text())
  with self.assertRaises(ValueError):fit([{'date':'2026-01-01'}],protocol)
 def test_fit_improves_known_signal_and_stays_bounded(self):
  protocol=json.loads(Path('config/market_repair_v1.json').read_text())
  rows=[{'date':'2025-01-01','odds':[2,4],'sport':[.8,.2],'winner_index':0 if i<80 else 1} for i in range(100)]
  model=fit(rows,protocol);p=predict([2,4],[.8,.2],model['weights'])
  self.assertGreater(p[0],.7);self.assertLess(p[0],.9);self.assertFalse(model['recommendations_allowed'])
 def raw(self,day,rank=None,status='PLACE',name='HORSE'):
  return {'raceDate':day,'racecourse':'VENUE','raceNumber':1,'discipline':'ATTELE',
    'raceRunParticipant':{'horseName':name,'place':{'runnerRank':rank,'arrivalStatus':status}}}
 def test_history_excludes_target_future_and_nonrunner(self):
  data={'runner':{'racesRun':[self.raw('2026-10-29',1),self.raw('2026-10-30',1),self.raw('2026-10-28',None,'NON_PARTANT'),self.raw('2026-10-18',1)]}}
  rows,_=normalize_history(data,{'nom':'HORSE'},'2026-10-29');self.assertEqual(len(rows),1);self.assertEqual(rows[0]['rank'],1)
 def test_wrong_horse_and_conflicting_duplicate_fail(self):
  with self.assertRaises(ValueError):normalize_history({'runner':{'racesRun':[self.raw('2026-10-18',1,name='OTHER')]}},{'nom':'HORSE'},'2026-10-29')
  with self.assertRaises(ValueError):normalize_history({'runner':{'racesRun':[self.raw('2026-10-18',1),self.raw('2026-10-18',2)]}},{'nom':'HORSE'},'2026-10-29')
 def test_dq_recovered_without_mutating_frozen_features(self):
  frame={'history':[],'features':[None,None,None,None,0]};old=copy.deepcopy(frame)
  payload={'runner':{'racesRun':[self.raw('2026-10-11',None,'DISQUALIFIE_POUR_ALLURE_IRREGULIERE')]}}
  result=reconcile({'nom':'HORSE','numPmu':3},frame,payload,'2026-10-29')
  self.assertEqual(result['status'],'MODEL_HISTORY_INCOMPLETE');self.assertEqual(result['supplemented_recent_features_for_research'][2],1)
  self.assertEqual(frame,old);self.assertFalse(result['recommendations_allowed'])
 def test_history_conflict_not_silently_merged(self):
  frame={'history':[{'date':'2026-10-18','venue':'VENUE','race_id':'2026-10-18_R1C1','rank':2,'dq':False}]}
  payload={'runner':{'racesRun':[self.raw('2026-10-18',1)]}}
  result=reconcile({'nom':'HORSE','numPmu':1},frame,payload,'2026-10-29')
  self.assertEqual(result['status'],'CONFLICT');self.assertIsNone(result['supplemented_recent_features_for_research'])

if __name__=='__main__':unittest.main()
