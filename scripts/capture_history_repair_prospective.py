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
MAX_PER_RUN = 2
MAX_PER_DAY = 4
LEAD_MINUTES = 40


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


def capture():
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo("Europe/Paris")).date()
    day = today.isoformat()
    if not START <= day <= END:
        print("Outside registered independent cohort")
        return {"date":day,"status":"OUTSIDE_WINDOW","saved":[]}
    folder = ROOT/day
    existing = {p.parent.name for p in folder.glob("*/prediction.json")}
    discovery = EvidenceStore(folder/"discovery",max_requests=1+MAX_PER_RUN)
    programme = discovery.programme(day)
    if not programme:
        raise ValueError("No race programme")
    # Selection is fixed BEFORE looking at outcomes, price, ability or expected value.
    picks = select(programme,datetime.now(timezone.utc),len(existing))
    state={"date":day,"selected_races":[],"saved":[],"skipped":[],"status":"PAPER_ONLY",
           "cohort_version":"history_repair_shadow_v1_1_nancy_alias",
           "selection":"First two French harness races >=40 min in future at each predeclared execution; max four per day"}
    if not picks:
        dump(folder/"capture_status.json",state)
        return state

    history, coverage = load_history(today, day)
    exclusions=json.loads(Path("config/full_history_protocol.json").read_text())
    filtered=[r for r in history if r["date"][:7] not in exclusions["excluded_months"]
              and r["race_id"] not in exclusions["excluded_races"]]
    policy, _ = verify_active()
    history_sha=hashlib.sha256(json.dumps(filtered,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    for meeting, course in picks:
        rn, cn = meeting["numOfficiel"],course["numOrdre"]
        rid=f"{day}_R{rn}C{cn}"
        state["selected_races"].append(rid)
        dest=folder/f"R{rn}C{cn}"
        if (dest/"prediction.json").exists():
            state["skipped"].append({"race_id":rid,"reason":"PREVIOUSLY_CAPTURED"})
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
            state["saved"].append(rid)
        except (ValueError,KeyError,TypeError,RuntimeError,OSError) as error:
            state["skipped"].append({"race_id":rid,"reason":str(error)})
        print(rid,"archived" if rid in state["saved"] else "skipped",flush=True)
    dump(folder/"capture_status.json",state)
    return state


if __name__=="__main__":
    print(json.dumps(capture(),ensure_ascii=False,indent=2))
