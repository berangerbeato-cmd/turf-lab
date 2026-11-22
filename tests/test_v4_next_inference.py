"""One user-facing V4 output contains five research components and no bet."""
import copy
import unittest
from unittest.mock import patch
from turf_lab.v4_next_inference import augment


def horse(n):
    return {"number":n,"horse_id":"HORSE"+str(n),
            "non_runner":False,"features":[.2]*47,"won":int(n==1)}


class OneV4IntegrationTests(unittest.TestCase):
    @staticmethod
    def fixture():
        rows=[horse(n) for n in range(1,7)]
        data={"race_id":"2026-12-01_R1C1",
              "target_snapshot":{"venue":"VINCENNES","start_type":"VOLTE",
                  "distance_m":2700,"participants":[{"numPmu":n} for n in range(1,7)]}}
        repair={"race_id":data["race_id"],"runner_audit":[
            {"number":n,"status":"UNCHANGED"} for n in range(1,7)]}
        report={"race_id":data["race_id"],"version":"turf_lab_v4_multifeature_1",
                "decision":"NO BET","recommendations_allowed":False,
                "gagnant":{"number":1,"probability":.4},
                "top5":{"numbers":[1,2,3,4,5]},
                "ze5":{"numbers":[1,2,3,4,5]},
                "limits":[]}
        sport={n:([.4,.25,.15,.1,.06,.04][n-1]) for n in range(1,7)}
        return report,data,repair,rows,sport

    def test_no_second_winner_and_no_DQ_double_count(self):
        report,orig,repair,rows,sport=self.fixture()
        models={"disqualification":{"weights":[0.]*13},
                "race_context":{"groups":{}},
                "odds_bands":{"bands":{k:{"log_factor":0.,"enabled":False}
                                       for k in ("1-4","4-8","8-20","20-50","50+")}},
                "quinte":{"shortlist_limit":6,"max_display_alternatives":3}}
        ranker={"mean":[0.]*47,"scale":[1.]*47,
                "coefficients":[[0.]*94 for _ in range(5)],"temperatures":[1.]*5}
        with patch("turf_lab.v4_next_inference.frozen",
                   return_value=(models,{"version":"v4_next_test"})):
            with patch("turf_lab.v4_next_inference.base_frozen",
                       return_value=({"ranking":ranker},{})):
                result=augment(report,orig,repair,rows,sport)
        self.assertEqual(result["gagnant"]["probability"],.4)
        self.assertEqual(result["gagnant"]["number"],1)
        self.assertEqual(result["decision"],"NO BET")
        self.assertEqual(result["ze5"]["stake_eur"],None)
        self.assertAlmostEqual(result["ze5"]["probability_unordered_paper"],1/6)
        self.assertEqual(len(result["research_improvements"]["disqualification"]["probability_by_runner"]),6)
        self.assertTrue(result["research_improvements"]["disqualification"]["not_multiplied_into_winner_twice"])
        self.assertEqual(result["research_improvements"]["history_repair_v2"]["status"],"CHECKED")

    def test_refuses_different_race(self):
        report,orig,repair,rows,sport=self.fixture()
        repair["race_id"]="OTHER_RACE"
        with self.assertRaisesRegex(ValueError,"Cross-race"):
            augment(report,orig,repair,rows,sport)

    def test_refuses_unapproved_betting(self):
        report,orig,repair,rows,sport=self.fixture()
        report["recommendations_allowed"]=True
        with self.assertRaisesRegex(ValueError,"suspension"):
            augment(report,orig,repair,rows,sport)


if __name__=="__main__":
    unittest.main()
