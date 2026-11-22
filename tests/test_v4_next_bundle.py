"""All five new V4 research upgrades: invariants, chronology and coherent ZE5."""
import copy
import math
import unittest

from turf_lab.history_repair_v2 import reconcile_v2,verify_prestart_sidecar
from turf_lab.v4_next_research import (
  dq_label,dq_vector,fit_context_temperatures,apply_context,
  odds_band,market_band_fit,adjust_market_bands,quinte_unordered)
from turf_lab.stage_ranking import strengths,unordered
import numpy as np


def frame(day="2024-10-01",n=6):
    return {"race_id":day+"_R1C1","date":day,"venue":"VINCENNES",
            "start_type":"VOLTE","distance_m":2700,
            "runners":[{"number":i+1,"horse_id":"H"+str(i+1),
                        "features":[.2]*47,
                        "non_runner":False,"won":int(i==0)}
                       for i in range(n)]}


class SingleV4AllFiveTests(unittest.TestCase):
    def test_dq_distinguishes_disqualification_from_unplaced(self):
        self.assertEqual(dq_label({"statut":"PARTANT","incident":"DISQUALIFIE_ALLURES",
                                   "ordreArrivee":None}),1)
        self.assertEqual(dq_label({"statut":"PARTANT","incident":None,
                                   "ordreArrivee":9}),0)
        self.assertIsNone(dq_label({"statut":"PARTANT","incident":None,
                                    "ordreArrivee":None}))
        self.assertIsNone(dq_label({"statut":"NON_PARTANT","incident":"DISQUALIFIE",
                                    "ordreArrivee":None}))
        self.assertEqual(len(dq_vector(frame()["runners"][0])),13)

    def test_history_v2_quarantines_conflicting_windows(self):
        race=frame(n=6)
        for r in race["runners"]:r["available_recent"]=[0,0,0,0,.8]
        old=copy.deepcopy(race)
        revised=copy.deepcopy(race)
        for r in old["runners"]:r["features"][:5]=[0,0,0,0,.6]
        for r in revised["runners"]:r["features"][:5]=[0,0,0,0,1.]
        groups={"original":{race["race_id"]:old},
                "enriched":{race["race_id"]:revised}}
        original=copy.deepcopy(race)
        report=reconcile_v2([race],groups)
        self.assertEqual(report["summary"]["MULTI_SOURCE_CONFLICT_NO_PATCH"],6)
        self.assertEqual(report["new_corrections_claimed"],0)
        self.assertEqual(race,original)

    def test_coherent_quinte_exact_unordered_probability(self):
        r=frame(n=6)
        ranker={"mean":[0.]*47,"scale":[1.]*47,
                "coefficients":[[0.]*94 for _ in range(5)],
                "temperatures":[1.]*5}
        result=quinte_unordered(r,ranker,limit=6)
        self.assertEqual(result["candidates_examined"],6)
        self.assertAlmostEqual(result["joint_probability_unordered"],1/6,places=12)
        self.assertEqual(len(result["selection"]),5)
        self.assertFalse(result["joint_calibration_verified"])
        # All six possible five-of-six events are exhaustive and disjoint.
        w=np.ones((5,6))
        total=sum(unordered(w,subset) for subset in
                  ([j for j in range(6) if j!=i] for i in range(6)))
        self.assertAlmostEqual(total,1.,places=12)

    def test_odds_band_preserves_probability_simplex(self):
        ps={1:.5,2:.3,3:.2};odds={1:2.5,2:8.2,3:30.}
        rows=[]
        for j in range(300):
            rows.append({"date":"2025-10-01","numbers":[1,2,3],
                         "odds":[2.5,8.2,30.],
                         "winner_index":j%3})
        bands=market_band_fit(rows,[ps]*300)
        out=adjust_market_bands(ps,odds,bands)
        self.assertAlmostEqual(sum(out.values()),1.,places=12)
        self.assertEqual(set(out),set(ps))
        with self.assertRaisesRegex(ValueError,"Incomplete"):
            adjust_market_bands(ps,{1:2.5,2:8.2},bands)

    def test_race_specialization_uses_temperature_not_common_bonus(self):
        p={1:.7,2:.2,3:.1}
        m={"groups":{"VOLTE|middle":{"temperature":1.15,"races":200}}}
        out,group=apply_context(p,"VINCENNES","VOLTE",2700,m)
        self.assertEqual(group,"VOLTE|middle")
        self.assertLess(out[1],p[1])
        self.assertAlmostEqual(sum(out.values()),1.)
        unknown,group=apply_context(p,"VINCENNES","UNKNOWN",2700,m)
        self.assertEqual(unknown,p)
        self.assertIsNone(group)


if __name__=="__main__":
    unittest.main()
