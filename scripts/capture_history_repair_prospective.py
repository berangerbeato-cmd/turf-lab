"""Bounded, deterministic, market-independent prospective cohort for V3 vs history repair.

Only upcoming French harness races. Never writes the live operational latest.json,
never recommends or places a wager, never learns from same-day results.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.predict_operational import classic_frame, load_history
from scripts.run_prediction_request import record_history_repair_shadow
from scripts.shadow_connections import live_record
from turf_lab.available_history_operational import compute as compute_v3, verify_active
from turf_lab.evidence import EvidenceStore, dump, races
from turf_lab.individual_history_check import check_all

ROOT = Path("reports/history_repair_shadow_v1/prospective_forecasts")
START = "2026-11-22"
END = "2027-03-22"
# Ten FIXED race slots per day, sampled without looking at form/odds.
# Four at most per workflow avoids a burst of per-horse PMU requests.
MAX_PER_RUN = 4
MAX_PER_DAY = 10
LEAD_MINUTES = 40
SELECTION_RULE = "SCHEDULED_FIRST_TEN_FRENCH_HARNESS_WITH_40MIN_LEAD_V2"
PLAN_FILE = "selection_plan.json"


def select(programme, now, already, max_per_run=MAX_PER_RUN, max_per_day=MAX_PER_DAY):
    if already >= max_per_day:
        return []
    # Fixed, prediction-blind rule; races with too little lead are ineligible.
    # Rejections do NOT cause cherry-picked replacement.
    cutoff = now + timedelta(minutes=LEAD_MINUTES)
    candidates = sorted(
        ((m,c) for m,c in races(programme)
         if datetime.fromtimestamp(c["heureDepart"]/1000, timezone.utc) >= cutoff),
        key=lambda mc: (mc[1]["heureDepart"],mc[0]["numOfficiel"],mc[1]["numOrdre"])
    )
    return candidates[:min(max_per_run, max_per_day-already)]

def plan_for_day(folder, programme, now):
    """Choose ALL ten daily race IDs before any forecast/outcome inspection.

    No failed, late, disqualified or unpopular horse/race is replaced by a
    later race. The plan is persisted across scheduled GitHub executions.
    """
    path=folder/PLAN_FILE
    if path.exists():
        plan=json.loads(path.read_text())
        if (plan.get("date")!=folder.name or plan.get("selection_rule")!=SELECTION_RULE
                or plan.get("daily_target")!=MAX_PER_DAY):
            raise ValueError("Frozen daily cohort selection has changed")
        items=plan.get("selected",[])
        if len(items)>MAX_PER_DAY or len({r["race_id"] for r in items})!=len(items):
            raise ValueError("Duplicate or excessive selected daily races")
        return plan
    chosen=select(programme,now,0,max_per_run=MAX_PER_DAY,max_per_day=MAX_PER_DAY)
    selected=[{"race_id":f"{folder.name}_R{meeting['numOfficiel']}C{course['numOrdre']}",
               "reunion":meeting["numOfficiel"],"course":course["numOrdre"],
               "start_ms":course["heureDepart"],"selection_index":i+1}
              for i,(meeting,course) in enumerate(chosen)]
    plan={"version":"prospective_10_per_day_v1","date":folder.name,
          "created_at_utc":now.isoformat(),"selection_rule":SELECTION_RULE,
          "daily_target":MAX_PER_DAY,"per_execution_max":MAX_PER_RUN,
          "lead_minutes":LEAD_MINUTES,"selected":selected,
          "no_replacements_after_error":True,"no_outcome_or_odds_filter":True,
          "recommendations_allowed":False}
    dump(path,plan)
    return plan


def next_planned(folder, plan, now, maximum=MAX_PER_RUN):
    """Only untouched planned IDs, still at least 40 minutes prestart."""
    pending=[]
    for item in plan["selected"]:
        name=f"R{item['reunion']}C{item['course']}"
        dest=folder/name
        if (dest/"attempt.json").exists() or (dest/"prediction.json").exists():
            continue
        pending.append(item)
    return pending[:maximum]


def daily_summary(folder, plan):
    outcomes=[]
    for item in plan["selected"]:
        dest=folder/f"R{item['reunion']}C{item['course']}"
        attempt=dest/"attempt.json"
        evidence=dest/"v4_integrated.json"
        data=json.loads(attempt.read_text()) if attempt.exists() else None
        outcomes.append({"race_id":item["race_id"],
                         "attempt_status":data.get("status") if data else "NOT_ATTEMPTED",
                         "prestart_v4_saved":evidence.exists(),
                         "record_path":str(evidence) if evidence.exists() else None})
    report={"version":"prospective_10_per_day_v1","date":plan["date"],
            "daily_target":MAX_PER_DAY,"selected":len(outcomes),
            "attempted":sum(o["attempt_status"]!="NOT_ATTEMPTED" for o in outcomes),
            "v4_prestart_captured":sum(o["prestart_v4_saved"] for o in outcomes),
            "failed_or_late":sum(o["attempt_status"] in ("ERROR","MISSED_PRESTART","V4_UNAVAILABLE")
                                 for o in outcomes),
            "no_substitutions":True,"outcomes":outcomes,
            "recommendations_allowed":False}
    dump(folder/"daily_summary.json",report)
    return report


def capture():
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo("Europe/Paris")).date()
    day = today.isoformat()
    if not START <= day <= END:
        print("Outside registered independent cohort")
        return {"date":day,"status":"OUTSIDE_WINDOW","saved":[]}
    folder = ROOT/day
    discovery = EvidenceStore(folder/"discovery",max_requests=1+MAX_PER_RUN)
    programme = discovery.programme(day)
    if not programme:
        raise ValueError("No race programme")
    # The first invocation freezes all ten IDs for this day. Subsequent
    # invocations process the SAME chosen slots, never fresh substitutes.
    plan=plan_for_day(folder,programme,datetime.now(timezone.utc))
    pairs={(f"{day}_R{m['numOfficiel']}C{c['numOrdre']}"):(m,c)
           for m,c in races(programme)}
    picks=next_planned(folder,plan,datetime.now(timezone.utc))
    state={"date":day,"selected_races":[],"saved":[],"skipped":[],"status":"PAPER_ONLY",
           "cohort_version":"history_repair_shadow_v1_1_nancy_alias",
           "daily_target":MAX_PER_DAY,"per_execution_limit":MAX_PER_RUN,
           "selection_rule":SELECTION_RULE,
           "selection":"Ten fixed first French harness races selected daily before odds/results, 40 min prestart, max four attempted per execution; no failed-race replacement"}
    if not picks:
        state["daily_summary"]=daily_summary(folder,plan)
        dump(folder/"capture_status.json",state)
        return state

    history, coverage = load_history(today, day)
    exclusions=json.loads(Path("config/full_history_protocol.json").read_text())
    filtered=[r for r in history if r["date"][:7] not in exclusions["excluded_months"]
              and r["race_id"] not in exclusions["excluded_races"]]
    policy, _ = verify_active()
    history_sha=hashlib.sha256(json.dumps(filtered,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    for item in picks:
        rn,cn=item["reunion"],item["course"]
        rid=item["race_id"]
        state["selected_races"].append(rid)
        dest=folder/f"R{rn}C{cn}"
        dest.mkdir(parents=True,exist_ok=True)
        if rid not in pairs:
            dump(dest/"attempt.json",{"race_id":rid,"status":"ERROR",
                 "reason":"Originally selected race absent from predeclared programme",
                 "recommendations_allowed":False})
            state["skipped"].append({"race_id":rid,"reason":"PLAN_RACE_NOT_FOUND"})
            continue
        meeting,course=pairs[rid]
        if course["heureDepart"]!=item["start_ms"]:
            dump(dest/"attempt.json",{"race_id":rid,"status":"ERROR",
                 "reason":"Frozen start time differs from current programme",
                 "recommendations_allowed":False})
            state["skipped"].append({"race_id":rid,"reason":"START_TIME_CHANGED"})
            continue
        now_race=datetime.now(timezone.utc)
        if datetime.fromtimestamp(item["start_ms"]/1000,timezone.utc)<now_race+timedelta(minutes=LEAD_MINUTES):
            dump(dest/"attempt.json",{"race_id":rid,"status":"MISSED_PRESTART",
                 "attempted_at":now_race.isoformat(),
                 "reason":"Less than 40 minutes before originally scheduled departure; no replacement",
                 "recommendations_allowed":False})
            state["skipped"].append({"race_id":rid,"reason":"MISSED_PRESTART_NO_REPLACEMENT"})
            continue
        try:
            raw=discovery.race(day,rn,cn,"participants")
            target=live_record(day,meeting,course,(raw or {}).get("participants"),datetime.now(timezone.utc))
            if sum(p["statut"]=="PARTANT" for p in target["participants"]) < 6:
                raise ValueError("Fewer than six active runners")
            records=filtered+[target]
            classic=classic_frame(records,rid)
            v3, _=compute_v3(records,classic)
            v3["model_sha256"]=policy["files_sha256"][policy["model_file"]]
            captured=datetime.now(timezone.utc)
            # The historical audit depends only on the original *prestart*
            # runner fields, and cannot introduce the race's future outcome.
            original={"race_id":rid,"status":"PRESTART_RESEARCH",
                      "primary_model":"available_history_v3",
                      "recommendations_allowed":False,
                      "predicted_at":captured.isoformat(),
                      "scheduled_start":datetime.fromtimestamp(course["heureDepart"]/1000,timezone.utc).isoformat(),
                      "target_snapshot":target,
                      "models":{"available_history_v3":v3,"v6":{"runners":classic["runners"]}},
                      "history_through":coverage["last_collected_day"],
                      "history_sha256":history_sha,
                      "research_only":True,
                      "original_operational_latest_modified":False}
            # Capture supplemental horse histories before making any repaired inference.
            check=check_all(target,original["models"],dest/"individual_history_evidence")
            original["individual_history_check"]=check
            if datetime.now(timezone.utc).timestamp()*1000>=course["heureDepart"]:
                raise ValueError("Race started during research calculation")
            dump(dest/"prediction.json",original)
            status={"request_id":"prospective-cohort-"+rid}
            record_history_repair_shadow(dest/"prediction.json",status)
            if status.get("history_repair_shadow_status")!="PRESTART_RECORDED":
                raise ValueError(status.get("history_repair_shadow_reason","No prestart sidecar"))
            # This forecast is from the predeclared non-selective scheduled cohort,
            # unlike user-selected on-demand sidecars.
            sidecar_path=dest/"history_repair_shadow_v1_1.json"
            sidecar=json.loads(sidecar_path.read_text())
            sidecar["is_independent_prospective_validation"]=True
            sidecar["selection_rule"]=SELECTION_RULE
            sidecar["daily_cohort_plan"]=str(folder/PLAN_FILE)
            sidecar["selection_index"]=item["selection_index"]
            dump(sidecar_path,sidecar)
            # ONE integrated V4: obtain the 43rd chrono feature from the
            # already verified prestart history, then use all trained weights.
            # Do not silently return to the former 42-feature V4.
            try:
                from turf_lab.v4_speed_data import prestart_target_context
                from turf_lab.v4_multi_features import live_context
                from turf_lab.v4_multifeature_inference import record as record_v4
                speed_context = prestart_target_context(filtered,target)
                speed_context["captured_at"] = datetime.now(timezone.utc).isoformat()
                speed_file = dest/"v4_speed_context.json"
                if datetime.fromisoformat(speed_context["captured_at"]).timestamp()*1000 >= course["heureDepart"]:
                    raise ValueError("V4 chrono computed too late")
                dump(speed_file,speed_context)
                base43={"race_id":rid,"date":day,"runners":[
                    dict(r,features=list(r["features"])+[
                        speed_context["target_field"][str(r["number"])]["context_residual"]
                    ]) for r in v3["runners"]]}
                from scripts.capture_v4_context import enrich_recent_money
                money_filtered,money_diag=enrich_recent_money(filtered,day)
                aux=live_context(money_filtered,target,base43)
                aux["money_enrichment_audit"]=money_diag
                if datetime.fromisoformat(aux["captured_at"]).timestamp()*1000 >= course["heureDepart"]:
                    raise ValueError("V4 monetary class/form/R evidence completed after departure")
                aux_file=dest/"v4_aux_context.json"
                dump(aux_file,aux)
                result = record_v4(dest/"prediction.json", sidecar_path,speed_file,aux_file)
                if result["freshness"] != "PRESTART_RESEARCH":
                    raise ValueError("New integrated V4 finished after departure")
                state.setdefault("v4_integrated_saved",[]).append(rid)
            except (ValueError,KeyError,TypeError,OSError,RuntimeError) as error:
                state.setdefault("v4_integrated_unavailable",[]).append(
                    {"race_id":rid,"reason":type(error).__name__+": "+str(error)})
            if rid in state.get("v4_integrated_saved",[]):
                attempt_status="V4_CAPTURED"
            else:
                attempt_status="V4_UNAVAILABLE"
            dump(dest/"attempt.json",{"race_id":rid,"status":attempt_status,
                 "original_prestart_saved":True,
                 "v4_prestart_saved":attempt_status=="V4_CAPTURED",
                 "attempted_at":datetime.now(timezone.utc).isoformat(),
                 "selection_index":item["selection_index"],
                 "recommendations_allowed":False})
            state["saved"].append(rid)
        except (ValueError,KeyError,TypeError,RuntimeError,OSError) as error:
            state["skipped"].append({"race_id":rid,"reason":str(error)})
            dump(dest/"attempt.json",{"race_id":rid,"status":"ERROR",
                 "attempted_at":datetime.now(timezone.utc).isoformat(),
                 "reason":type(error).__name__+": "+str(error),
                 "selection_index":item["selection_index"],
                 "recommendations_allowed":False})
        print(rid,"archived" if rid in state["saved"] else "skipped",flush=True)
    state["daily_summary"]=daily_summary(folder,plan)
    dump(folder/"capture_status.json",state)
    return state


if __name__=="__main__":
    print(json.dumps(capture(),ensure_ascii=False,indent=2))
