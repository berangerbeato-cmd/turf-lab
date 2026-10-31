import unittest
from itertools import permutations,combinations
from turf_lab.rank45 import ordered_probability,unordered_probability,forecast
class Rank45Tests(unittest.TestCase):
 def test_normalized_joint_distributions(self):
  p={i:i+1 for i in range(6)}
  for k in (4,5):
   self.assertAlmostEqual(sum(ordered_probability(p,s) for s in permutations(p,k)),1)
   self.assertAlmostEqual(sum(unordered_probability(p,s) for s in combinations(p,k)),1)
 def test_uniform_and_order(self):
  p={i:1/6 for i in range(6)}
  self.assertAlmostEqual(unordered_probability(p,[0,1,2,3]),1/15)
  self.assertEqual(forecast({1:.1,2:.2,3:.3,4:.4},4)['order'],[4,3,2,1])
 def test_duplicates_rejected(self):
  with self.assertRaises(ValueError): unordered_probability({1:.5,2:.5},[1,1,2,2])
