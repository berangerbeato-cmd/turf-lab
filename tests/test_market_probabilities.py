import unittest
import numpy as np
from itertools import permutations
from turf_lab.market_probabilities import markets,value_bounds

class MarketTests(unittest.TestCase):
    def test_uniform_and_mass(self):
        m=markets(list(range(10)),[1]*10)
        for key,expected,total in [('win',.1,1),('place3',.3,3),('pair_place3',1/15,3),('pair_top4',2/15,6)]:
            self.assertTrue(np.allclose(m[key][1],expected))
            self.assertAlmostEqual(sum(m[key][1]),total)
        self.assertTrue(np.all(m['pair_place3'][1]<=m['pair_top4'][1]))

    def test_matches_independent_permutation_enumeration(self):
        w=np.array([1,2,3,4,5],dtype=float);w/=w.sum()
        expected_single=np.zeros(5);expected_pair=0
        for order in permutations(range(5),4):
            p=1.;remaining=1.
            for i in order:p*=w[i]/remaining;remaining-=w[i]
            for i in order[:3]:expected_single[i]+=p
            if 0 in order and 1 in order:expected_pair+=p
        m=markets(list(range(5)),w)
        self.assertTrue(np.allclose(m['place3'][1],expected_single))
        self.assertAlmostEqual(m['pair_top4'][1][0],expected_pair)
        self.assertFalse(np.isclose(m['pair_place3'][1][0],m['place3'][1][0]*m['place3'][1][1]))

    def test_bad_input_and_ev(self):
        for weights in ([1,1,1,1,0],[1,1,1,1,float('nan')]):
            with self.assertRaises(ValueError):markets(list(range(5)),weights)
        v=value_bounds(.6,1.5,2)
        self.assertAlmostEqual(v['ev_low'],-.1)
        self.assertAlmostEqual(v['ev_high'],.2)
        with self.assertRaises(ValueError):value_bounds(.6,2,1.5)
