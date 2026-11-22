"""Ten unbiased daily harness-race slots, planned once, no replacement.

A sample slot may remain failed/missed; a later popular or winning race cannot
silently replace it. Those failures remain visible in daily_summary.json.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

from scripts.capture_history_repair_prospective import (
    MAX_PER_DAY,MAX_PER_RUN,SELECTION_RULE,select,plan_for_day,
    next_planned,daily_summary)
from scripts.score_history_repair_prospective import validate_sidecar


def programme(now,reverse=False):
    races=[{"numOrdre":i,"heureDepart":int((now+timedelta(minutes=60+i*12)).timestamp()*1000),
            "discipline":"ATTELE"} for i in range(1,14)]
    if reverse:races.reverse()
    return {"programme":{"reunions":[
        {"numOfficiel":1,"pays":{"code":"FRA"},"courses":races},
        {"numOfficiel":2,"pays":{"code":"BEL"},"courses":[
            {"numOrdre":1,"heureDepart":int((now+timedelta(minutes=65)).timestamp()*1000),
             "discipline":"ATTELE"}]}]}}


class TenDailyCohort(unittest.TestCase):
    def test_one_frozen_10_race_selection_across_runs(self):
        now=datetime(2026,11,23,6,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"2026-11-23"
            p=plan_for_day(folder,programme(now),now)
            self.assertEqual(MAX_PER_DAY,10)
            self.assertEqual(MAX_PER_RUN,4)
            self.assertEqual(len(p["selected"]),10)
            self.assertEqual(p["selection_rule"],SELECTION_RULE)
            self.assertEqual([r["course"] for r in p["selected"]],list(range(1,11)))
            self.assertEqual(len(next_planned(folder,p,now)),4)
            first=p["selected"][0]
            dest=folder/"R1C1"
            dest.mkdir()
            (dest/"attempt.json").write_text(json.dumps(
                {"race_id":first["race_id"],"status":"ERROR","reason":"PMU unavailable"}))
            others=next_planned(folder,p,now)
            self.assertEqual([r["course"] for r in others],[2,3,4,5])
            # Even if programme order changes and a new early race appears,
            # daily selection is frozen. Failures cannot be replaced.
            altered=programme(now,reverse=True)
            altered["programme"]["reunions"][0]["courses"].append(
                {"numOrdre":99,"heureDepart":int((now+timedelta(minutes=65)).timestamp()*1000),
                 "discipline":"ATTELE"})
            r=plan_for_day(folder,altered,now+timedelta(hours=3))
            self.assertEqual(r,p)
            self.assertEqual(daily_summary(folder,p)["failed_or_late"],1)
            self.assertEqual(daily_summary(folder,p)["attempted"],1)

    def test_cutoff_and_country_and_quota(self):
        now=datetime(2026,11,23,6,tzinfo=timezone.utc)
        chosen=select(programme(now),now,0)
        self.assertEqual(len(chosen),4)
        self.assertTrue(all(meeting["pays"]["code"]=="FRA" for meeting,course in chosen))
        self.assertEqual([c["numOrdre"] for m,c in chosen],[1,2,3,4])
        self.assertEqual(len(select(programme(now),now,9)),1)
        self.assertEqual(select(programme(now),now,10),[])
        self.assertEqual(len(select(programme(now),now,0,max_per_run=10)),10)

    def test_new_prestart_sidecar_requires_immutable_daily_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            oldcwd=Path.cwd()
            try:
                os.chdir(temp)
                root=Path("reports/history_repair_shadow_v1/prospective_forecasts/2026-11-23")
                race=root/"R1C3"
                race.mkdir(parents=True)
                at="2026-11-23T16:00:00+00:00"
                start="2026-11-23T17:00:00+00:00"
                p=str(race/"prediction.json")
                participants=[{"numPmu":n,"nom":"H"+str(n),"nomMere":"M",
                               "nomPere":"P","statut":"PARTANT"} for n in range(1,7)]
                prob={str(n):1/6 for n in range(1,7)}
                original={"race_id":"2026-11-23_R1C3","status":"PRESTART_RESEARCH",
                    "scheduled_start":start,"predicted_at":at,
                    "target_snapshot":{"race_id":"2026-11-23_R1C3","participants":participants},
                    "models":{"available_history_v3":{
                        "model_sha256":"SHA","probabilities":prob}}}
                Path(p).write_text(json.dumps(original))
                selected=[{"race_id":"2026-11-23_R1C3","reunion":1,"course":3,
                           "selection_index":1,"start_ms":int(datetime.fromisoformat(start).timestamp()*1000)}]
                plan={"version":"prospective_10_per_day_v1","date":"2026-11-23",
                      "created_at_utc":"2026-11-23T06:00:00+00:00",
                      "selection_rule":SELECTION_RULE,"daily_target":10,
                      "selected":selected}
                (root/"selection_plan.json").write_text(json.dumps(plan))
                sidecar={"race_id":original["race_id"],"status":"PRESTART_HISTORY_REPAIR_SHADOW",
                    "candidate":"history_repair_shadow_v1_1_nancy_alias",
                    "recommendations_allowed":False,
                    "is_independent_prospective_validation":True,
                    "selection_rule":SELECTION_RULE,"selection_index":1,
                    "daily_cohort_plan":str(root/"selection_plan.json"),
                    "scheduled_start":start,"original_predicted_at":at,
                    "shadow_calculated_at":"2026-11-23T16:02:00+00:00",
                    "source_prediction":p,"frozen_v3_model_sha256":"SHA",
                    "v3_baseline":{"probabilities":prob},
                    "research_candidate":{"probabilities":prob}}
                location=race/"history_repair_shadow_v1_1.json"
                location.write_text(json.dumps(sidecar))
                validate_sidecar(location)
                (root/"selection_plan.json").unlink()
                with self.assertRaises((ValueError,OSError)):
                    validate_sidecar(location)
            finally:
                os.chdir(oldcwd)


if __name__=="__main__":
    unittest.main()
