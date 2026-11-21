"""Capture all V4 extra input evidence OUTSIDE the immutable V3 code.

V3's code SHA is frozen: never change scripts/predict_operational.py to add
V4 features. Re-open the same strictly prior verified race records, check
original history hash, add lagged PMU money from SHA-verified old partitions
or existing verified date overlays, and write pace+class/form/R sidecars.
"""
import gzip
import hashlib
import json
from datetime import datetime,timezone,timedelta,date
from pathlib import Path
from zoneinfo import ZoneInfo

from turf_lab.evidence import dump
from turf_lab.history_sync import History,read_gzip
from turf_lab.month_history import identity
from turf_lab.v4_speed_data import prestart_target_context
from turf_lab.v4_multi_features import live_context

def enrich_recent_money(records,target_day):
    """Only previous 365 days have usable non-stale career money snapshots.

    Missing or unverifiable *money* is excluded; no current-race earnings,
    no inferred euro earnings, no result rewrite.
    """
    hist=History()
    cutoff=(date.fromisoformat(target_day)-timedelta(days=365)).isoformat()
    overlay_cache={}
    enriched=[]
    stats={"recent_races":0,"money_rows":0,"missing_money_sources":0}
    for r in records:
        copied=dict(r,participants=[dict(p) for p in r["participants"]])
        if not cutoff<=r["date"]<target_day:
            enriched.append(copied)
            continue
        stats["recent_races"]+=1
        origin=None
        entry=hist.entries.get(r["race_id"])
        if entry is not None:
            origin=read_gzip(entry["file"],entry["sha256"])
        else:
            # New dated recovery overlays have no monthly partition yet.
            day=r["date"]
            if day not in overlay_cache:
                file=Path("data/history_updates")/(day+".json.gz")
                if file.exists():
                    overlay=json.loads(gzip.decompress(file.read_bytes()))
                    if overlay["date"]!=day:
                        raise ValueError("Overlay money date disagrees with filename")
                    overlay_cache[day]={x["race_id"]:x for x in overlay["records"]}
                else:
                    # Recent-history evidence was already accepted by History.day;
                    # retrieve it from the same trusted source, not the internet.
                    state=hist.day(day)
                    overlay_cache[day]={x["race_id"]:x for x in state["records"]}
            origin=overlay_cache[day].get(r["race_id"])
        if origin is None:
            stats["missing_money_sources"]+=1
            enriched.append(copied)
            continue
        if origin["race_id"]!=r["race_id"] or origin["date"]!=r["date"]:
            raise ValueError("Historic career-gains source race/date mismatch")
        by={p["numPmu"]:p for p in origin["participants"]}
        before={p["numPmu"]:p for p in r["participants"]}
        if len(by)!=len(origin["participants"]) or set(before)!=set(by):
            raise ValueError("Historic PMU careers participant mismatch")
        for p in copied["participants"]:
            prior=by[p["numPmu"]]
            if prior["statut"]!=p["statut"] or identity(prior)!=identity(p):
                raise ValueError("Historic career-money horse pedigree mismatch")
            money=prior.get("gainsParticipant")
            if money is not None:
                p["gainsParticipant"]=money
                stats["money_rows"]+=1
        enriched.append(copied)
    return enriched,stats


def capture_from_original(prediction_file):
    original_file=Path(prediction_file)
    predicted=json.loads(original_file.read_text())
    start=datetime.fromisoformat(predicted["scheduled_start"])
    if start.tzinfo is None or datetime.now(timezone.utc)>=start:
        raise ValueError("Historical feature capture must finish before target start")
    if predicted["status"]!="PRESTART_RESEARCH":
        raise ValueError("No original verified V3 prestart snapshot")
    day=predicted["race_id"][:10]
    today=datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Paris")).date()
    if day!=today.isoformat() and day<(today.isoformat()):
        raise ValueError("V4 historical feature capture cannot backdate old races")
    # Read-only replay of immutable V3 historical loader. No frozen code edit.
    from scripts.predict_operational import load_history
    history,coverage=load_history(today,day)
    expected=predicted["history_sha256"]
    actual=hashlib.sha256(json.dumps(history,sort_keys=True,
                         ensure_ascii=False).encode()).hexdigest()
    if actual!=expected:
        raise ValueError("V4 underlying official history changed since frozen V3 forecast")
    protocol=json.loads(Path("config/full_history_protocol.json").read_text())
    prior=[r for r in history if r["date"][:7] not in protocol["excluded_months"]
           and r["race_id"] not in protocol["excluded_races"]]
    target=predicted["target_snapshot"]
    speed=prestart_target_context(prior,target)
    if datetime.now(timezone.utc)>=start:
        raise ValueError("V4 prestart speed scan finished late")
    speed["captured_at"]=datetime.now(timezone.utc).isoformat()
    # Deliberately do not write sidecars until BOTH have passed.
    runner_rows=[dict(r,features=list(r["features"])+[
        speed["target_field"][str(r["number"])]["context_residual"]])
        for r in predicted["models"]["available_history_v3"]["runners"]]
    money_prior,diag=enrich_recent_money(prior,day)
    aux=live_context(money_prior,target,
             {"race_id":predicted["race_id"],"date":day,"runners":runner_rows})
    finished=datetime.now(timezone.utc)
    if finished>=start:
        raise ValueError("V4 auxiliary money/class/form/R collection completed after race start")
    aux["captured_at"]=finished.isoformat()
    aux["official_history_sha256"]=actual
    aux["money_enrichment_audit"]=diag
    speed_path=original_file.parent/"v4_speed_context.json"
    aux_path=original_file.parent/"v4_aux_context.json"
    if speed_path.exists() or aux_path.exists():
        raise ValueError("Refusing to overwrite an existing original feature capture")
    dump(speed_path,speed)
    dump(aux_path,aux)
    return {"race_id":predicted["race_id"],"speed_file":str(speed_path),
            "aux_file":str(aux_path),"money_evidence":diag,
            "captured_at":finished.isoformat(),
            "status":"V4_PRESTART_47_FEATURE_CONTEXT_CAPTURED"}
