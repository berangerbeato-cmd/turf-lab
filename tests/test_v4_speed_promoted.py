"""Promotion tests: single V4 must use original 43-feature speed weights.

No backup to the 42-feature baseline. Original prestart histories and
identities must be valid; missing one horse's timed starts is allowed (None).
"""
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch

from tests.test_v4_speed_shadow import fixture
from turf_lab.v4_speed_data import prestart_target_context
from turf_lab.v4_active_inference import run,load_active


def make_case(root):
    p,h,history=fixture(root)
    target=json.loads(p.read_text())["target_snapshot"]
    speed=prestart_target_context(history,target,
              observed_at=datetime(2026,11,22,14,7,tzinfo=timezone.utc))
    path=root/"v4_speed_context.json"
    path.write_text(json.dumps(speed))
    return p,h,path


class ActiveV4SpeedTests(unittest.TestCase):
    def test_actual_retrained_speed_models_are_in_the_one_V4(self):
        models,market,lock,cfg=load_active()
        self.assertEqual(cfg["active_user_model"],"TURF_LAB_V4")
        self.assertEqual(models["winner"]["features"],43)
        self.assertEqual(len(models["ranking"]["coefficients"]),5)
        self.assertEqual(len(market["weights"]),2)
        self.assertFalse(cfg["recommendations_allowed"])
        self.assertFalse(cfg["real_money_betting"])

    def test_integrated_forecast_and_43rd_missing_feature(self):
        with tempfile.TemporaryDirectory() as temp:
            p,h,c=make_case(Path(temp))
            report=run(p,h,c,now=datetime(2026,11,22,14,10,tzinfo=timezone.utc))
            self.assertEqual(report["version"],"turf_lab_v4_integrated_speed_1")
            self.assertEqual(report["model"],"TURF_LAB_V4")
            self.assertEqual(report["freshness"],"PRESTART_RESEARCH")
            self.assertEqual(report["decision"],"NO BET")
            self.assertEqual(report["context_speed"]["dimension"],43)
            self.assertEqual(report["context_speed"]["coverage"],0)
            self.assertEqual(len(report["top5"]["numbers"]),5)
            self.assertEqual(report["value"]["status"],"NO_VERIFIED_PRESTART_QUOTES")
            self.assertEqual(report["value"]["paper_candidates_not_bets"],[])
            self.assertEqual(report["model_sha256"],load_active()[2]["three_new_model_hashes"])

    def test_no_speed_snapshot_means_blocked_not_42_feature_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            p,h,c=make_case(Path(temp))
            c.unlink()
            with self.assertRaisesRegex(ValueError,"Mandatory prestart contextual speed"):
                run(p,h,c)

    def test_unverified_horse_and_target_result_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p,h,c=make_case(Path(temp))
            current=json.loads(c.read_text())
            first=next(iter(current["target_field"]))
            current["target_field"][first]["horse_id"]="WRONG"
            c.write_text(json.dumps(current))
            with self.assertRaisesRegex(ValueError,"speed runner identity"):
                run(p,h,c,now=datetime(2026,11,22,14,10,tzinfo=timezone.utc))
            current["target_field"][first]["horse_id"]=json.loads(p.read_text())[
                "target_snapshot"]["participants"][int(first)-1]["idCheval"]
            current["contains_target_outcome"]=True
            c.write_text(json.dumps(current))
            with self.assertRaisesRegex(ValueError,"prior-only"):
                run(p,h,c,now=datetime(2026,11,22,14,10,tzinfo=timezone.utc))

    def test_late_speed_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p,h,c=make_case(Path(temp))
            meta=json.loads(c.read_text())
            meta["captured_at"]="2026-11-22T15:01:00+00:00"
            c.write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError,"prestart"):
                run(p,h,c,now=datetime(2026,11,22,14,10,tzinfo=timezone.utc))


if __name__=="__main__":
    unittest.main()
