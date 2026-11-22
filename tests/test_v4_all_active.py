"""Validate signed DQ integration, without double-counting or manual odds."""
import unittest
from unittest.mock import patch
from turf_lab.v4_active_final import residual_dq,sport_v4,quotes_v4,quintet_v4
from tests.test_v4_next_inference import OneV4IntegrationTests


class V4AllActiveRules(unittest.TestCase):
    def test_signed_DQ_correction_is_normalized_and_not_hardcoded(self):
        p={1:.45,2:.35,3:.20}
        q={1:.05,2:.20,3:.40}
        same=residual_dq(p,q,0.)
        self.assertEqual(same,p)
        plus=residual_dq(p,q,.5)
        minus=residual_dq(p,q,-.5)
        self.assertGreater(plus[1],p[1])
        self.assertLess(minus[1],p[1])
        self.assertAlmostEqual(sum(plus.values()),1.)
        self.assertAlmostEqual(sum(minus.values()),1.)
        with self.assertRaisesRegex(ValueError,"DQ residual"):
            residual_dq(p,{1:.05,2:.20},.5)
        with self.assertRaisesRegex(ValueError,"Invalid sport"):
            residual_dq(p,{1:.05,2:.20,3:1.},.5)

    def test_history_v2_and_DQ_AND_context_all_affect_single_winner(self):
        report,orig,repair,rows,sports=OneV4IntegrationTests.fixture()
        models={
          "disqualification":{"weights":[0.]*13},
          "race_context":{"groups":{"VOLTE|middle":{
                 "temperature":1.10,"races":300}}},
          "odds_bands":{"bands":{}},
          "quinte":{"shortlist_limit":6,"max_display_alternatives":3}}
        with patch("turf_lab.v4_active_final.activated",
                    return_value=({"coefficient":.3},models,{"version":"test_locked"})):
            p,diag=sport_v4(orig,repair,rows,sports)
        self.assertNotEqual(p,sports)
        self.assertAlmostEqual(sum(p.values()),1.)
        self.assertTrue(diag["disqualification"]["applied_to_winner"])
        self.assertEqual(diag["race_context"]["selected_group"],"VOLTE|middle")
        self.assertEqual(diag["history_repair_v2"]["status"],"CHECKED")
        self.assertFalse(diag["real_money_betting_allowed"])

    def test_price_band_is_used_in_final_calculation(self):
        ps={1:.55,2:.25,3:.20}
        odds={1:2.5,2:8.5,3:21}
        bands={"bands":{
           "1-4":{"log_factor":-.13},"4-8":{"log_factor":.04},
           "8-20":{"log_factor":.16},"20-50":{"log_factor":-.2},
           "50+":{"log_factor":0.}}}
        with patch("turf_lab.v4_active_final.activated",
                   return_value=({"coefficient":.3},{"odds_bands":bands},
                                 {"version":"test_locked"})):
            market=quotes_v4(ps,odds)
        self.assertNotEqual(market,ps)
        self.assertAlmostEqual(sum(market.values()),1.)
        self.assertLess(market[1],ps[1])

    def test_joint_Quinte_replaces_stage_greedy_if_needed(self):
        report,orig,repair,rows,sports=OneV4IntegrationTests.fixture()
        ranker={"mean":[0.]*47,"scale":[1.]*47,
                "coefficients":[[0.]*94 for _ in range(5)],"temperatures":[1.]*5}
        models={"quinte":{"shortlist_limit":6,"max_display_alternatives":3}}
        with patch("turf_lab.v4_active_final.activated",
                    return_value=({"coefficient":.3},models,{"version":"test_locked"})):
            q=quintet_v4(rows,ranker)
        self.assertAlmostEqual(q["joint_probability_unordered"],1/6)
        self.assertEqual(len(q["selection"]),5)
        self.assertIsNone(q["recommended_stake_eur"])


if __name__=="__main__":
    unittest.main()
