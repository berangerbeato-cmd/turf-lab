"""Full V4 inference loads newly fitted locked coefficients and fails closed."""
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch

from turf_lab.v4_full_inference import load, run, repaired_frame

ROOT=Path("predictions_operational/2026-11-21/2026-11-21_R4C5_20261121T172911422587Z")
HISTORY=Path("reports/history_repair_shadow_v1/replays_nancy_alias_v1_1/2026-11-21_R4C5_20261121T172911422587Z.json")


class V4FullInferenceTests(unittest.TestCase):
    def test_all_three_weights_are_new_and_locked(self):
        models,lock=load()
        self.assertEqual(set(models),{"winner","ranking","market"})
        self.assertEqual(len(models["winner"]["model"]["transform"]["mean"]),42)
        self.assertEqual(len(models["ranking"]["coefficients"]),5)
        self.assertEqual(len(models["market"]["weights"]),2)
        self.assertTrue(lock["old_v3_and_v2_preserved"])
        self.assertFalse(lock["recommendations_allowed"])

    def test_one_retrained_v4_report_with_market_and_top5(self):
        r=run(ROOT/"prediction.json",HISTORY,ROOT/"quotes.json",
              now=datetime(2026,11,21,19,0,tzinfo=timezone.utc))
        self.assertEqual(r["version"],"turf_lab_v4_full_retrained_candidate_1")
        self.assertEqual(r["gagnant"]["basis"],"V4_RETRAINED_MARKET_CORRECTION")
        self.assertEqual(r["freshness"],"RETROSPECTIVE")
        self.assertEqual(len(set(r["top5"]["numbers"])),5)
        self.assertGreater(len(r["history_repair"]["unresolved"]),0)
        self.assertEqual(r["decision"],"NO BET")
        self.assertFalse(r["recommendations_allowed"])

    def test_no_quote_is_not_fake_value(self):
        r=run(ROOT/"prediction.json",HISTORY,
              now=datetime(2026,11,21,19,0,tzinfo=timezone.utc))
        self.assertEqual(r["gagnant"]["basis"],"V4_RETRAINED_WINNER")
        self.assertEqual(r["value"]["status"],"NOT_AVAILABLE")
        self.assertEqual(r["value"]["paper_candidates_not_bets"],[])

    def test_no_history_repair_no_v4(self):
        with self.assertRaises(FileNotFoundError):
            run(ROOT/"prediction.json",Path("/tmp/no_history_repair_full_v4.json"))
        original=json.loads(HISTORY.read_text())
        original["candidate"]="history_v2_not_approved"
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"history.json"
            path.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError,"History Repair"):
                run(ROOT/"prediction.json",path)

    def test_late_or_wrong_individual_history_abstains(self):
        original=json.loads(HISTORY.read_text())
        original["status"]="PRESTART_HISTORY_REPAIR_SHADOW"
        original["shadow_calculated_at"]="2026-11-21T18:00:00+00:00"
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"late.json"
            path.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError,"too late"):
                run(ROOT/"prediction.json",path)

    def test_model_integrity_failure_is_not_silent(self):
        with patch("turf_lab.v4_full_inference.sha",return_value="bad-sha"):
            with self.assertRaisesRegex(ValueError,"training policy modified"):
                load()


if __name__=="__main__":
    unittest.main()
