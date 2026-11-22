"""Strict prospective scorecard and deterministic selection regression tests."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.capture_history_repair_prospective import select
from scripts.score_history_repair_prospective import (
    BEGIN, CANDIDATE_VERSION, confidence_by_day, validate_sidecar, verified_top5
)


class ForwardScoreTests(unittest.TestCase):
    def test_first_two_races_by_time_with_no_odds_or_form_selection(self):
        now=datetime(2026,11,23,10,tzinfo=timezone.utc)
        race=lambda n,minutes:{"numOrdre":n,"heureDepart":int((now+timedelta(minutes=minutes)).timestamp()*1000),
                              "discipline":"ATTELE"}
        programme={"programme":{"reunions":[{"numOfficiel":1,"pays":{"code":"FRA"},
                         "courses":[race(4,95),race(3,65),race(2,30)]},
                     {"numOfficiel":2,"pays":{"code":"BEL"},"courses":[race(1,50)]}]}}
        selected=select(programme,now,0)
        self.assertEqual([(m["numOfficiel"],c["numOrdre"]) for m,c in selected],[(1,3),(1,4)])
        self.assertEqual(select(programme,now,10),[])

    def make_sidecar(self, root):
        folder=root/"predictions_operational/2026-11-23/race1"
        folder.mkdir(parents=True)
        forecast=folder/"prediction.json"
        start="2026-11-23T17:00:00+00:00"
        old="2026-11-23T16:00:00+00:00"
        probs={str(i):1/6 for i in range(1,7)}
        participants=[{"numPmu":n,"nom":f"H{n}","nomMere":"M","nomPere":"P",
                       "statut":"PARTANT"} for n in range(1,7)]
        original={
            "race_id":"2026-11-23_R1C3","status":"PRESTART_RESEARCH",
            "predicted_at":old,"scheduled_start":start,
            "target_snapshot":{"race_id":"2026-11-23_R1C3","participants":participants},
            "models":{"available_history_v3":{"model_sha256":"SHA","probabilities":probs}}
        }
        forecast.write_text(json.dumps(original))
        sidecar=folder/"history_repair_shadow_v1_1.json"
        report={
            "race_id":"2026-11-23_R1C3","status":"PRESTART_HISTORY_REPAIR_SHADOW",
            "candidate":CANDIDATE_VERSION,"recommendations_allowed":False,
            "is_independent_prospective_validation":True,
            "selection_rule":"SCHEDULED_FIRST_TWO_FRENCH_HARNESS_WITH_40MIN_LEAD",
            "scheduled_start":start,"original_predicted_at":old,
            "shadow_calculated_at":"2026-11-23T16:02:00+00:00",
            "source_prediction":str(forecast.relative_to(root)),
            "frozen_v3_model_sha256":"SHA","runners_changed_recent5":2,
            "v3_baseline":{"probabilities":probs},
            "research_candidate":{"probabilities":probs}
        }
        sidecar.write_text(json.dumps(report))
        return sidecar,report,original

    def test_sidecar_provenance_and_future_cutoff(self):
        with tempfile.TemporaryDirectory() as td:
            origin=Path.cwd()
            try:
                os.chdir(td)
                p,record,_=self.make_sidecar(Path("."))
                validate_sidecar(p)
                record["shadow_calculated_at"]="2026-11-23T17:01:00+00:00"
                p.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError,"not in the independent"):
                    validate_sidecar(p)
                record["shadow_calculated_at"]="2026-11-23T16:02:00+00:00"
                record["candidate"]="old-unversioned-candidate"
                p.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError,"version mismatch"):
                    validate_sidecar(p)
            finally:
                os.chdir(origin)

    def test_only_official_complete_results_and_matching_identities(self):
        start="2026-11-23T17:00:00+00:00"
        participants=[{"numPmu":n,"nom":f"H{n}","nomMere":"M","nomPere":"P",
                       "statut":"PARTANT"} for n in range(1,7)]
        source={"race_id":"2026-11-23_R1C3","scheduled_start":start,
                "target_snapshot":{"participants":participants}}
        run={**source,"date":"2026-11-23","scheduled_start_ms":int(datetime.fromisoformat(start).timestamp()*1000),
             "participants":[dict(p,ordreArrivee=n if n<=5 else None) for n,p in enumerate(participants,1)]}
        finish,status=verified_top5({"records":[run]},source)
        self.assertEqual(status,"VERIFIED_OFFICIAL")
        self.assertEqual(finish,[1,2,3,4,5])
        run["participants"][1]["statut"]="NON_PARTANT"
        self.assertEqual(verified_top5({"records":[run]},source)[1],"HORSE_IDENTITY_OR_STARTER_MISMATCH")

    def test_no_fictitious_confidence_interval_for_one_day(self):
        rows=[{"race_id":"2026-11-23_R1C3",
               "metrics":{"research_candidate":{"log_loss":1.0},
                          "v3_baseline":{"log_loss":1.2}}}]
        self.assertIsNone(confidence_by_day(rows,"log_loss"))


if __name__=="__main__":
    unittest.main()
