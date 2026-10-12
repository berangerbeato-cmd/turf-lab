import copy
import unittest
from turf_lab.shadow import score

class ShadowTests(unittest.TestCase):
    def fixture(self):
        pred={'predicted_at':'2026-10-12T09:00:00Z','scheduled_start':'2026-10-12T10:00:00Z','runners':[{'number':1,'horse_id':'A','status':'PARTANT','probability':.8},{'number':2,'horse_id':'B','status':'PARTANT','probability':.2}]}
        detail={'arriveeDefinitive':True,'ordreArrivee':[[1],[2]]}
        parts=[{'numPmu':1,'idCheval':'A','statut':'PARTANT','ordreArrivee':1},{'numPmu':2,'idCheval':'B','statut':'PARTANT','ordreArrivee':None,'incident':'DISQUALIFIE'}]
        return pred,detail,parts
    def test_correct_scoring_and_dq(self):
        p,d,r=self.fixture();out=score(p,d,r);self.assertEqual(out['status'],'SCORED');self.assertAlmostEqual(out['brier_multiclass'],.08)
    def test_changed_field_never_renormalized_after_result(self):
        p,d,r=self.fixture();r[1]['statut']='NON_PARTANT';original=copy.deepcopy(p)
        self.assertEqual(score(p,d,r)['status'],'QUARANTINE');self.assertEqual(p,original)
    def test_no_provisional_or_ambiguous_winner(self):
        p,d,r=self.fixture();d['arriveeDefinitive']=False;self.assertEqual(score(p,d,r)['status'],'PENDING')
        d['arriveeDefinitive']=True;d['ordreArrivee']=[[1,2]];self.assertEqual(score(p,d,r)['status'],'QUARANTINE')
    def test_late_prediction_rejected(self):
        p,d,r=self.fixture();p['predicted_at']='2026-10-12T11:00:00Z';self.assertEqual(score(p,d,r)['status'],'QUARANTINE')
