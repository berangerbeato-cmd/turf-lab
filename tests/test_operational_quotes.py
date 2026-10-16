import copy, unittest
from turf_lab.operational_quotes import compare

class Quotes(unittest.TestCase):
 def setUp(self):
  self.p={'race_id':'2020-01-01_R1C1','scheduled_start':'2020-01-01T15:00:00Z','predicted_at':'2020-01-01T12:00:00Z','primary_model':'v6','target_snapshot':{'participants':[{'numPmu':1,'nom':'CHEVAL','statut':'PARTANT'}]},'models':{'v6':{'probabilities':{'1':.25},'version':'frozen'}}}
  self.q={'race_id':self.p['race_id'],'operator':'fixture','source_evidence':'test','verified':True,'observed_at':'2020-01-01T13:00:00Z','odds_format':'DECIMAL_TOTAL_RETURN','quotes':[{'number':1,'name':'CHEVAL','decimal_odds':5}]}
 def test_ev(self):
  r=compare(self.p,self.q);self.assertEqual(r['rows'][0]['models']['v6']['ev'],.25);self.assertEqual(r['status'],'RETROSPECTIVE_QUOTE_COMPARISON')
 def test_mismatch(self):
  self.q['quotes'][0]['name']='AUTRE'
  with self.assertRaises(ValueError):compare(self.p,self.q)
 def test_late(self):
  self.q['observed_at']='2020-01-01T15:00:00Z'
  with self.assertRaises(ValueError):compare(self.p,self.q)
 def test_duplicate(self):
  self.q['quotes']*=2
  with self.assertRaises(ValueError):compare(self.p,self.q)
 def test_nonrunner(self):
  self.p['target_snapshot']['participants'][0]['statut']='NON_PARTANT'
  with self.assertRaises(ValueError):compare(self.p,self.q)
