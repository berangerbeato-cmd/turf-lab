"""V4 extras are captured without ever changing the SHA-locked V3 source."""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch

from scripts.capture_v4_context import enrich_recent_money,capture_from_original
from turf_lab.available_history_operational import verify_active
from turf_lab.month_history import identity


class ImmutableV3V4CaptureTests(unittest.TestCase):
    def test_frozen_V3_source_still_authenticates(self):
        policy,temp=verify_active()
        self.assertEqual(policy["primary_model"],"available_history_v3")
        self.assertGreater(temp,.5)

    def test_money_comes_from_official_previous_record_only(self):
        day="2040-01-01";target="2040-01-02";rid=day+"_R1C1"
        p={"numPmu":1,"nom":"TEST HORSE","nomMere":"M","nomPere":"F",
           "statut":"PARTANT","ordreArrivee":1}
        old={"date":day,"race_id":rid,"participants":[dict(p)]}
        source={"date":day,"race_id":rid,"participants":[dict(p,gainsParticipant={"gainsCarriere":1200})]}
        class MockHistory:
            entries={}
            def day(self,date):
                return {"records":[source]}
        with patch("scripts.capture_v4_context.History",return_value=MockHistory()):
            records,audit=enrich_recent_money([old],target)
        self.assertEqual(records[0]["participants"][0]["gainsParticipant"]["gainsCarriere"],1200)
        self.assertNotIn("gainsParticipant",old["participants"][0])
        self.assertEqual(audit["money_rows"],1)

    def test_original_prediction_snapshot_remains_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            now=datetime.now(timezone.utc)
            future=(now+timedelta(days=2)).date().isoformat()
            prior=(now-timedelta(days=1)).date().isoformat()
            rid=future+"_R1C1"
            rawp={"numPmu":1,"nom":"Test Horse","nomMere":"M","nomPere":"F",
                  "statut":"PARTANT","ordreArrivee":None}
            old={"race_id":prior+"_R1C1","date":prior,
                 "participants":[dict(rawp,ordreArrivee=1)]}
            history=[old]
            hsha=hashlib.sha256(json.dumps(history,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            original={"race_id":rid,"status":"PRESTART_RESEARCH",
                      "scheduled_start":(now+timedelta(days=2,hours=1)).isoformat(),
                      "predicted_at":now.isoformat(),"history_sha256":hsha,
                      "models":{"available_history_v3":{"runners":[{
                          "number":1,"horse_id":identity(rawp),"non_runner":False,
                          "features":[0]*42}]}},
                      "target_snapshot":{"race_id":rid,"date":future,
                                         "participants":[rawp]}}
            p=root/"prediction.json"
            raw=json.dumps(original)
            p.write_text(raw)
            speed={"target_field":{"1":{"context_residual":None,"prior_races_used":0,
                                        "horse_id":identity(rawp)}}}
            aux={"race_id":rid,"target_date":future,
                 "version":"v4_integrated_class_form_reliability_1",
                 "captured_at":now.isoformat()}
            with patch("scripts.predict_operational.load_history",return_value=(history,{})):
                with patch("scripts.capture_v4_context.prestart_target_context",return_value=speed):
                    with patch("scripts.capture_v4_context.enrich_recent_money",
                               return_value=(history,{"money_rows":0})):
                        with patch("scripts.capture_v4_context.live_context",return_value=aux):
                            result=capture_from_original(p)
            self.assertEqual(result["status"],"V4_PRESTART_47_FEATURE_CONTEXT_CAPTURED")
            self.assertEqual(p.read_text(),raw)
            self.assertTrue((root/"v4_speed_context.json").exists())
            self.assertTrue((root/"v4_aux_context.json").exists())
            with self.assertRaisesRegex(ValueError,"existing original"):
                # Prevent edited or duplicated prestart context.
                with patch("scripts.predict_operational.load_history",return_value=(history,{})):
                    with patch("scripts.capture_v4_context.prestart_target_context",return_value=speed):
                        with patch("scripts.capture_v4_context.enrich_recent_money",
                                   return_value=(history,{"money_rows":0})):
                            with patch("scripts.capture_v4_context.live_context",return_value=aux):
                                capture_from_original(p)


if __name__=="__main__":
    unittest.main()
