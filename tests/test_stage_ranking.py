import unittest
from itertools import combinations,permutations
import numpy as np
from turf_lab.stage_ranking import strengths,ordered,unordered,greedy,fit_choice

class StageRankingTests(unittest.TestCase):
    def test_distribution(self):
        w=strengths(np.random.default_rng(42).normal(size=(5,6)),[1]*5)
        for k in (3,4,5):
            self.assertAlmostEqual(sum(unordered(w,s) for s in combinations(range(6),k)),1)
            s=list(range(k))
            self.assertAlmostEqual(unordered(w,s),sum(ordered(w,o) for o in permutations(s)))
    def test_uniform(self):
        from math import comb
        w=np.ones((5,7))
        self.assertAlmostEqual(unordered(w,[0,1,2]),1/comb(7,3))
        self.assertEqual(greedy(w,5),[0,1,2,3,4])
    def test_stage_sensitivity(self):
        w=np.ones((5,6));w[1,2]=50
        self.assertGreater(ordered(w,[0,2,1]),ordered(w,[0,1,2]))
    def test_fit_signal(self):
        w,_=fit_choice(np.array([[1.],[-1.]]*20),[2]*20,[0]*20)
        self.assertGreater(w[0],0)
    def test_duplicate(self):
        with self.assertRaises(ValueError):unordered(np.ones((5,6)),[0,0,1])
    def test_calibration_preserves_selection_and_mass(self):
        scores=np.random.default_rng(7).normal(size=(5,6))
        raw=strengths(scores,[1]*5)
        calibrated=strengths(scores,[.5,2,3,.8,1.4])
        self.assertEqual(greedy(raw,5),greedy(calibrated,5))
        self.assertAlmostEqual(sum(unordered(calibrated,s) for s in combinations(range(6),5)),1)
    def test_shared_scores_match_existing_pl(self):
        from turf_lab.rank45 import ordered_probability
        p={0:.4,1:.2,2:.15,3:.1,4:.08,5:.07}
        w=np.tile(list(p.values()),(5,1))
        self.assertAlmostEqual(ordered(w,[2,0,4,1,3]),ordered_probability(p,[2,0,4,1,3]))
