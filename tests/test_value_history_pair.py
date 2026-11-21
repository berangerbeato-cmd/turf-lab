"""Frozen V2 correction remains unmodified when paired with repaired V1.1."""
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from turf_lab.value_history_pair import paired

ROOT=Path("predictions_operational/2026-11-21/2026-11-21_R4C5_20261121T172911422587Z")
HISTORY=Path("reports/history_repair_shadow_v1/replays_nancy_alias_v1_1/2026-11-21_R4C5_20261121T172911422587Z.json")


class MarketHistoryPairTests(unittest.TestCase):
    def fixture(self):
        return tuple(json.loads(p.read_text()) for p in
                     (ROOT/"prediction.json",HISTORY,ROOT/"quotes.json",ROOT/"comparison.json"))

    def test_reims_legacy_v2_reproduction_and_no_posthoc_prospective(self):
        p,h,q,r=self.fixture()
        result=paired(p,h,q,r,now=datetime(2026,11,21,19,0,tzinfo=timezone.utc))
        self.assertEqual(result["status"],"RETROSPECTIVE_PAIRED_REPLAY")
        self.assertEqual(len(result["rows"]),14)
        self.assertFalse(result["recommendations_allowed"])
        self.assertFalse(result["v2_coefficients_retrained"])
        self.assertTrue(all(abs(x["v3_plus_v2_indicative_ev"] - (x["v3_plus_v2_probability"]*x["odds"]-1)) < 1e-12 for x in result["rows"]))
        self.assertAlmostEqual(sum(x["v3_plus_v2_probability"] for x in result["rows"]),1)
        self.assertAlmostEqual(sum(x["history_plus_v2_probability"] for x in result["rows"]),1)
        self.assertTrue(all(x["v3_plus_v2_indicative_ev"] < 0 for x in result["rows"]))

    def test_complete_same_snapshot_required(self):
        p,h,q,r=self.fixture()
        q["quotes"].pop()
        with self.assertRaisesRegex(ValueError, "complete"):
            paired(p,h,q,r)
        p,h,q,r=self.fixture()
        q["quotes"][1]["name"]="WRONG HORSE"
        with self.assertRaisesRegex(ValueError, "mismatched"):
            paired(p,h,q,r)
        p,h,q,r=self.fixture()
        q["quotes"][0]["decimal_odds"] *= 2
        with self.assertRaisesRegex(ValueError, "reproduce"):
            paired(p,h,q,r)

    def test_mismatch_and_attempted_history_revision_blocked(self):
        p,h,q,r=self.fixture()
        h["v3_baseline"]["probabilities"]["1"] += 0.005
        h["v3_baseline"]["probabilities"]["2"] -= 0.005
        with self.assertRaisesRegex(ValueError, "changed"):
            paired(p,h,q,r)
        p,h,q,r=self.fixture()
        h["candidate"]="unfrozen_retrained_v2"
        with self.assertRaisesRegex(ValueError, "history version"):
            paired(p,h,q,r)

    def test_prospective_replay_requires_actual_before_departure(self):
        p,h,q,r=self.fixture()
        now=datetime.now(timezone.utc)
        p["predicted_at"]=(now-timedelta(minutes=3)).isoformat()
        p["scheduled_start"]=(now+timedelta(minutes=6)).isoformat()
        h["original_predicted_at"]=p["predicted_at"]
        h["scheduled_start"]=p["scheduled_start"]
        h["status"]="PRESTART_HISTORY_REPAIR_SHADOW"
        h["shadow_calculated_at"]=(now-timedelta(seconds=30)).isoformat()
        q["observed_at"]=(now-timedelta(minutes=2)).isoformat()
        r["calculated_at"]=(now-timedelta(minutes=1)).isoformat()
        r["value_shadow"]["observed_at"]=q["observed_at"]
        self.assertEqual(paired(p,h,q,r,now=now)["status"],"PRESTART_PAIRED_ON_DEMAND")
        h["shadow_calculated_at"]=(now+timedelta(seconds=1)).isoformat()
        self.assertEqual(paired(p,h,q,r,now=now)["status"],"RETROSPECTIVE_PAIRED_REPLAY")

    def test_stale_original_market_or_late_reference_forbidden(self):
        p,h,q,r=self.fixture()
        q["observed_at"]="2026-11-21T17:00:00+00:00"
        r["value_shadow"]["observed_at"]=q["observed_at"]
        with self.assertRaisesRegex(ValueError, "fifteen-minute"):
            paired(p,h,q,r)
        p,h,q,r=self.fixture()
        r["calculated_at"]="2026-11-21T18:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "before start"):
            paired(p,h,q,r)


if __name__=="__main__":
    unittest.main()
