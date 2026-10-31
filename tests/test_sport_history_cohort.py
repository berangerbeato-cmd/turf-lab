import copy
import unittest
from datetime import datetime, timezone
from turf_lab.sport_history_cohort import select, repair
from turf_lab.pilot import features

class Cohort(unittest.TestCase):
    def setUp(self):
        self.baseline={'runners':[{'number':1,'name':'HORSE','horse_id':'a','features':[None,None,None,None,0.0],'history':[]}]}
        self.frame={'race_id':'2025-03-10_R1C1','date':'2025-03-10','runners':[{'number':1,'horse_id':'a','non_runner':False,'features':[None,None,None,None,0.0,99.0],'won':1}]}
        self.payload={'participants':[{'numPmu':1,'nomCheval':'HORSE','coursesCourues':[{'date':int(datetime(2025,3,1,tzinfo=timezone.utc).timestamp()*1000),'hippodrome':'LAVAL','nomPrix':'Prix A','discipline':'ATTELE','participants':[{'itsHim':True,'nomCheval':'HORSE','place':{'place':1,'statusArrivee':'PLACE'}}]}]}]}
    def test_repair_does_not_mutate_or_change_other_inputs(self):
        before=copy.deepcopy(self.frame)
        out,stats=repair(self.frame,self.baseline,self.payload)
        self.assertEqual(self.frame,before)
        self.assertEqual(out['runners'][0]['features'][:3],[1,1,0])
        self.assertEqual(out['runners'][0]['features'][5],99)
        self.assertEqual(stats['added_starts'],1)
    def test_future_and_same_day_rejected(self):
        for day in (10,11):
            self.payload['participants'][0]['coursesCourues'][0]['date']=int(datetime(2025,3,day,tzinfo=timezone.utc).timestamp()*1000)
            with self.assertRaises(ValueError):repair(self.frame,self.baseline,self.payload)
    def test_identity_and_missing_runner_rejected(self):
        self.payload['participants'][0]['nomCheval']='OTHER'
        with self.assertRaises(ValueError):repair(self.frame,self.baseline,self.payload)
        with self.assertRaises(ValueError):repair(self.frame,self.baseline,{'participants':[]})
    def test_conflicting_history_rejected(self):
        prior={'date':'2025-03-01','venue':'LAVAL','rank':None,'status':'DISQUALIFIE','dq':True}
        self.baseline['runners'][0]['history']=[prior]
        values=features([prior],self.frame['date'])
        self.baseline['runners'][0]['features']=values
        self.frame['runners'][0]['features'][:5]=values
        with self.assertRaises(ValueError):repair(self.frame,self.baseline,self.payload)
    def test_sampling_independent_of_outcome_and_input_order(self):
        p={'version':'x','races_per_month':3,'train':['2024-01-01','2024-12-31'],'validation':['2025-01-01','2025-12-31'],'test':['2026-01-01','2026-12-31']}
        rows=[{'race_id':str(i),'date':'2024-03-01','won':i%2} for i in range(30)]
        expected=[r['race_id'] for r in select(rows,p)]
        changed=[dict(r,won=1-r['won']) for r in reversed(rows)]
        self.assertEqual(expected,[r['race_id'] for r in select(changed,p)])
    def test_archived_feature_mismatch_rejected(self):
        self.frame['runners'][0]['features'][0]=.5
        with self.assertRaises(ValueError):repair(self.frame,self.baseline,self.payload)

    def test_imprecise_nonplaced_keeps_known_rank(self):
        prior={'date':'2025-03-01','venue':'LAVAL','rank':10,'status':'','dq':False}
        self.baseline['runners'][0]['history']=[prior]
        values=features([prior],self.frame['date'])
        self.baseline['runners'][0]['features']=values
        self.frame['runners'][0]['features'][:5]=values
        self.payload['participants'][0]['coursesCourues'][0]['participants'][0]['place'].update(place=None,statusArrivee='NON_PLACE')
        out,stats=repair(self.frame,self.baseline,self.payload)
        self.assertEqual(out['runners'][0]['features'],self.frame['runners'][0]['features'])
        self.assertEqual(stats['added_starts'],0)
        prior['rank']=1
        values=features([prior],self.frame['date'])
        self.baseline['runners'][0]['features']=values
        self.frame['runners'][0]['features'][:5]=values
        with self.assertRaises(ValueError):repair(self.frame,self.baseline,self.payload)

if __name__=='__main__':unittest.main()
