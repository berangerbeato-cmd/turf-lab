import unittest
from itertools import combinations
from turf_lab.ranking_research import finish,weights,unordered,portfolio
class RankingTests(unittest.TestCase):
 def test_joint_mass_and_cost(self):
  p=dict(enumerate(weights([0]*6,1)))
  for k in (3,4,5):
   self.assertAlmostEqual(sum(unordered(p,s) for s in combinations(p,k)),1)
  x=portfolio(p,[[0,1,2],[0,1,3]],2)
  self.assertEqual(x['total_cost'],4)
  self.assertAlmostEqual(x['probability'],.1)
  self.assertAlmostEqual(x['break_even_total_return_per_winning_combination'],40)
 def test_duplicates_rejected(self):
  with self.assertRaises(ValueError):portfolio({i:1/6 for i in range(6)},[[0,1,2],[2,1,0]])
 def test_ties_and_dq(self):
  parts=[dict(numPmu=i,ordreArrivee=i,statut='PARTANT') for i in range(1,7)]
  self.assertEqual(finish(parts),[1,2,3,4,5])
  parts[0]['incident']='DISQUALIFIE'
  self.assertIsNone(finish(parts))
  parts[0].pop('incident');parts[1]['ordreArrivee']=1
  self.assertIsNone(finish(parts))
