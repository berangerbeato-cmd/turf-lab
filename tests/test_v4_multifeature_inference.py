"""All requested improvements must really appear in the one V4 output."""
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch

from tests.test_v4_speed_shadow import fixture
from turf_lab.v4_speed_data import prestart_target_context
from turf_lab.v4_multi_features import live_context
from turf_lab.v4_multifeature_inference import run,frozen


def case(temp):
    root=Path(temp)
    p,h,history=fixture(root)
    pred=json.loads(p.read_text())
    target=pred["target_snapshot"]
    speed=prestart_target_context(history,target,
                   observed_at=datetime(2026,11,22,14,7,tzinfo=timezone.utc))
    speed_path=root/"v4_speed_context.json"
    speed_path.write_text(json.dumps(speed))
    f43={"race_id":pred["race_id"],"date":pred["race_id"][:10],
         "runners":[dict(r,features=list(r["features"])+[
             speed["target_field"][str(r["number"])]["context_residual"]
         ]) for r in pred["models"]["available_history_v3"]["runners"]]}
    extra=live_context(history,target,f43)
    extra["captured_at"]="2026-11-22T14:08:00+00:00"
    extra_path=root/"v4_aux_context.json"
    extra_path.write_text(json.dumps(extra))
    return p,h,speed_path,extra_path


class V4AllInOneInferenceTests(unittest.TestCase):
    def test_all_new_weights_frozen_and_three_component_training(self):
        models,lock=frozen()
        self.assertEqual(models["winner"]["features"],47)
        self.assertEqual(len(models["ranking"]["coefficients"]),5)
        self.assertEqual(len(models["market"]["weights"]),3)
        self.assertTrue(lock["all_four_added_features_trained"])
        self.assertFalse(lock["recommendations_allowed"])

    def test_live_single_v4_four_signals_no_price(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=case(tmp)
            r=run(*paths,now=datetime(2026,11,22,14,10,tzinfo=timezone.utc))
            self.assertEqual(r["version"],"turf_lab_v4_multifeature_1")
            self.assertEqual(r["model"],"TURF_LAB_V4")
            self.assertEqual(r["context_speed"]["dimension"],47)
            self.assertEqual(r["decision"],"NO BET")
            self.assertFalse(r["recommendations_allowed"])
            self.assertEqual(len(r["top5"]["numbers"]),5)
            self.assertIn("relative_class_and_gains",r)
            self.assertIn("weighted_recent_form",r)
            self.assertIn("reliability_R",r)
            self.assertTrue(r["reliability_R"]["market_R_gate_fitted"])
            self.assertEqual(r["value"]["status"],"NO_VERIFIED_PRESTART_QUOTES")

    def test_missing_extra_context_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p,h,s,e=case(tmp)
            e.unlink()
            with self.assertRaises(FileNotFoundError):
                run(p,h,s,e,now=datetime(2026,11,22,14,10,tzinfo=timezone.utc))

    def test_future_gain_and_untrusted_earnings_cannot_enter(self):
        with tempfile.TemporaryDirectory() as tmp:
            p,h,s,e=case(tmp)
            data=json.loads(e.read_text())
            data["contains_target_outcome"]=True
            e.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"history provenance"):
                run(p,h,s,e,now=datetime(2026,11,22,14,10,tzinfo=timezone.utc))
            data["contains_target_outcome"]=False
            one=next(iter(data["per_runner"]))
            data["per_runner"][one]["class_is_verified_euros"]=True
            e.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"source claimed"):
                run(p,h,s,e,now=datetime(2026,11,22,14,10,tzinfo=timezone.utc))

    def test_historical_repair_and_aux_must_be_prestart(self):
        with tempfile.TemporaryDirectory() as tmp:
            p,h,s,e=case(tmp)
            data=json.loads(e.read_text())
            data["captured_at"]="2026-11-22T15:01:00+00:00"
            e.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"prestart"):
                run(p,h,s,e,now=datetime(2026,11,22,14,10,tzinfo=timezone.utc))


if __name__=="__main__":
    unittest.main()
