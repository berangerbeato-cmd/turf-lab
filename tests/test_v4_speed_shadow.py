"""Prestart V4 Speed is a real snapshot, cannot use target race outcomes."""
import copy
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch

from turf_lab.v4_speed_shadow import predict
from scripts.score_v4_speed_prospective import run as score_original

ROOT=Path("predictions_operational/2026-11-21/2026-11-21_R4C5_20261121T172911422587Z")
REPAIR=Path("reports/history_repair_shadow_v1/replays_nancy_alias_v1_1/2026-11-21_R4C5_20261121T172911422587Z.json")


def fixture(folder):
    raw=json.loads((ROOT/"prediction.json").read_text())
    shadow=json.loads(REPAIR.read_text())
    day="2026-11-22"
    race_id=day+"_R4C5"
    raw["race_id"]=race_id
    raw["scheduled_start"]="2026-11-22T15:00:00+00:00"
    raw["predicted_at"]="2026-11-22T14:00:00+00:00"
    raw["target_snapshot"]["race_id"]=race_id
    raw["target_snapshot"]["date"]=day
    shadow["race_id"]=race_id
    shadow["scheduled_start"]=raw["scheduled_start"]
    shadow["original_predicted_at"]=raw["predicted_at"]
    shadow["status"]="PRESTART_HISTORY_REPAIR_SHADOW"
    shadow["shadow_calculated_at"]="2026-11-22T14:05:00+00:00"
    p=folder/"prediction.json"
    h=folder/"history_repair_shadow_v1_1.json"
    shadow["source_prediction"]=p.as_posix()
    p.write_text(json.dumps(raw))
    h.write_text(json.dumps(shadow))
    prior=copy.deepcopy(raw["target_snapshot"])
    prior["date"]="2026-11-21"
    prior["race_id"]="2026-11-21_R4C5"
    for i,runner in enumerate(prior["participants"],1):
        runner["ordreArrivee"]=i
        runner["incident"]=None
        runner["reductionKilometrique"]=72000+i*1000
        runner["tempsObtenu"]=int((72000+i*1000)*2.7)
        runner["handicapDistance"]=2700
    return p,h,[prior]


class V4SpeedShadowTests(unittest.TestCase):
    def test_single_prestart_prospectively_captured_speed_output(self):
        with tempfile.TemporaryDirectory() as temp:
            p,h,history=fixture(Path(temp))
            output=predict(p,h,history,now=datetime(2026,11,22,14,10,tzinfo=timezone.utc))
            self.assertEqual(output["version"],"v4_speed_challenger_1")
            self.assertEqual(output["status"],"PRESTART_SHADOW_RESEARCH")
            self.assertFalse(output["recommendations_allowed"])
            self.assertEqual(output["decision"],"NO BET")
            self.assertEqual(len(output["top5"]),5)
            self.assertEqual(len(output["win_probabilities"]),14)
            self.assertAlmostEqual(sum(output["win_probabilities"].values()),1)
            self.assertEqual(len(output["speed_input_by_runner"]),14)
            self.assertTrue(all(row["context_residual"] is None
                            for row in output["speed_input_by_runner"].values()))

    def test_target_result_and_late_capture_forbidden(self):
        with tempfile.TemporaryDirectory() as temp:
            p,h,history=fixture(Path(temp))
            history[0]["date"]="2026-11-22"
            with self.assertRaisesRegex(ValueError,"Target or future"):
                predict(p,h,history,now=datetime(2026,11,22,14,10,tzinfo=timezone.utc))
            history[0]["date"]="2026-11-21"
            with self.assertRaisesRegex(ValueError,"before race departure"):
                predict(p,h,history,now=datetime(2026,11,22,15,1,tzinfo=timezone.utc))

    def test_no_cherrypicked_retro_replays_in_prospective_scorer(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("scripts.score_v4_speed_prospective.BASE",Path(temp)):
                with patch("scripts.score_v4_speed_prospective.History"):
                    outcome=score_original(Path(temp)/"score.json")
            self.assertEqual(outcome["captured"],0)
            self.assertEqual(outcome["verified_results"],0)
            self.assertEqual(outcome["means"],{})
            self.assertFalse(outcome["validation_ready"])


if __name__=="__main__":
    unittest.main()
