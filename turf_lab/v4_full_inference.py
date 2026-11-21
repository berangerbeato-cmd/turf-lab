"""Genuine retrained V4 candidate inference, paper only and fail closed.

Separate fitted models are a single user-facing V4 pipeline:
 winner (42 corrected history features) -> conditional Top5 -> new market
 correction on same winner p. Legacy V3 is input evidence only, NOT its weights.
"""
import copy
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from turf_lab.evidence import dump
from turf_lab.market_repair import predict as correct_market
from turf_lab.operational_quotes import name as quote_name
from turf_lab.pilot import probabilities
from turf_lab.stage_ranking import greedy, strengths
from scripts.train_stage_ranking_v2 import features as get_features, transform

ROOT = Path("models/v4_full")
LOCK = ROOT/"frozen_before_test.json"


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def stamp(value):
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:
        raise ValueError("Timezone required")
    return t


def load():
    frozen=json.loads(LOCK.read_text())
    if (frozen["status"] != "FROZEN_BEFORE_REUSED_2026_TEST"
        or frozen["production_changed"] is not False
        or frozen["recommendations_allowed"] is not False):
        raise ValueError("V4 trained provenance is not research-only and locked")
    if sha("config/v4_full_training.json") != frozen["protocol_sha256"]:
        raise ValueError("V4 training policy modified")
    objects={}
    for name,filename in (("winner","winner.json"),("ranking","ranking.json"),("market","market.json")):
        path=ROOT/filename
        if sha(path)!=frozen["models_sha256"][filename]:
            raise ValueError("V4 retrained model hash mismatch: "+name)
        objects[name]=json.loads(path.read_text())
    if len(objects["ranking"]["coefficients"])!=5:
        raise ValueError("V4 top5 has incorrect conditional stage count")
    return objects,frozen


def repaired_frame(original, supplement):
    if supplement["candidate"] != "history_repair_shadow_v1_1_nancy_alias":
        raise ValueError("Wrong History Repair version")
    if (original["race_id"] != supplement["race_id"]
        or original["predicted_at"] != supplement["original_predicted_at"]
        or original["scheduled_start"] != supplement["scheduled_start"]):
        raise ValueError("History source race or time mismatch")
    if original["models"]["available_history_v3"]["model_sha256"] != supplement["frozen_v3_model_sha256"]:
        raise ValueError("History repair original sports SHA mismatch")
    if supplement["recommendations_allowed"] is not False:
        raise ValueError("History Repair switched to gambling")
    rows=copy.deepcopy(original["models"]["available_history_v3"]["runners"])
    by_num={p["number"]:p for p in rows}
    if len(supplement["runner_audit"]) != len(rows):
        raise ValueError("Missing individual horse audits")
    problems=[]
    for entry in supplement["runner_audit"]:
        n=entry["number"];status=entry["status"]
        if n not in by_num:
            raise ValueError("History audit horse identity mismatch")
        r=by_num[n]
        if status=="UPDATED":
            if r["features"][:5] != entry["old_recent5"] or len(entry["candidate_recent5"])!=5:
                raise ValueError("Historical five-start evidence mismatch")
            r["features"][:5] = entry["candidate_recent5"]
        elif status=="UNCHANGED":
            if r["features"][:5] != entry["old_recent5"] or r["features"][:5] != entry["candidate_recent5"]:
                raise ValueError("History claimed unchanged but values disagree")
        elif status=="NON_RUNNER":
            if not r["non_runner"]:
                raise ValueError("Wrong history non-runner")
        else:
            problems.append({"number":n,"reason":status})
    if len({a["number"] for a in supplement["runner_audit"]})!=len(rows):
        raise ValueError("Duplicate history audit number")
    return rows,problems


def verified_board(pred,quotes,at,now):
    if (quotes.get("race_id") != pred["race_id"]
        or quotes.get("verified") is not True
        or not quotes.get("source_evidence")
        or quotes.get("odds_format") != "DECIMAL_TOTAL_RETURN"):
        raise ValueError("No verified matching complete quote board")
    start=stamp(pred["scheduled_start"])
    qtime=stamp(quotes["observed_at"])
    if not (qtime < start and timedelta(0) <= start-qtime <= timedelta(minutes=15)):
        raise ValueError("No valid 15-minute prestart quote")
    parts=pred["target_snapshot"]["participants"]
    if any(p["statut"] != "PARTANT" for p in parts):
        raise ValueError("Unverified non-runner in market quote board")
    field={p["numPmu"]:quote_name(p["nom"]) for p in parts}
    odds={}
    for q in quotes["quotes"]:
        n=q["number"];c=q["decimal_odds"]
        if n not in field or n in odds or quote_name(q["name"])!=field[n]:
            raise ValueError("Odds name or starter field mismatch")
        if isinstance(c,bool) or not isinstance(c,(float,int)) or not math.isfinite(c) or c<=1:
            raise ValueError("Invalid odds")
        odds[n]=float(c)
    if set(odds)!=set(field) or sum(1/x for x in odds.values())<1-1e-9:
        raise ValueError("Incomplete odds or underround board")
    # Never label an odds calculation 'prestart' if computed after start.
    return odds,"PRESTART" if qtime<=at<start and at-qtime<=timedelta(minutes=5) else "RETROSPECTIVE"


def run(prediction_file,history_file,quotes_file=None,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Naive prediction timestamp")
    pred_path=Path(prediction_file)
    pred=json.loads(pred_path.read_text())
    repaired=json.loads(Path(history_file).read_text())
    if repaired["source_prediction"] != pred_path.as_posix():
        raise ValueError("Original history source path mismatch")
    start=stamp(pred["scheduled_start"])
    ptime=stamp(pred["predicted_at"])
    if ptime>=start or pred["status"] != "PRESTART_RESEARCH" or pred["primary_model"]!="available_history_v3":
        raise ValueError("No valid prior prestart prediction")
    if repaired["status"] not in ("PRESTART_HISTORY_REPAIR_SHADOW",
                                  "RETROSPECTIVE_REPLAY_OF_ORIGINAL_PRESTART_EVIDENCE"):
        raise ValueError("No acceptable history evidence")
    if repaired["status"]=="PRESTART_HISTORY_REPAIR_SHADOW":
        ht=stamp(repaired["shadow_calculated_at"])
        if not ptime <= ht < start:
            raise ValueError("Required history collected too late")
    objects,lock=load()
    rows,history_problems=repaired_frame(pred,repaired)
    field={r["number"] for r in rows}
    active={r["number"] for r in rows if not r["non_runner"]}
    if len(active)<6 or len(rows)!=len(field) or any(len(r["features"]) != 42 for r in rows):
        raise ValueError("V4 model requires six starters and exactly 42 features")
    win_model=objects["winner"]
    sport=probabilities({"runners":rows},win_model["model"])
    temperature=float(win_model["temperature"])
    p={n:val**(1/temperature) for n,val in sport.items()}
    z=sum(p.values())
    sport={n:val/z for n,val in p.items()}
    rk=objects["ranking"]
    matrix=transform(get_features({"runners":rows}),np.asarray(rk["mean"]),np.asarray(rk["scale"]))
    scores=np.asarray(rk["coefficients"])@matrix.T
    weights=strengths(scores,rk["temperatures"])
    active_order=[r["number"] for r in rows if not r["non_runner"]]
    top5=[active_order[i] for i in greedy(weights,5)]
    if len(set(top5))!=5 or not set(top5)<=active:
        raise ValueError("Invalid V4 Top5")
    quotes_state="NOT_AVAILABLE"
    win=sport
    odds=None
    if quotes_file is not None:
        quote=json.loads(Path(quotes_file).read_text())
        odds,quotes_state=verified_board(pred,quote,now,now)
        sorted_nums=sorted(odds)
        predicted=correct_market([odds[n] for n in sorted_nums],
                                  [sport[n] for n in sorted_nums],
                                  objects["market"]["weights"])
        win={n:v for n,v in zip(sorted_nums,predicted)}
    ranked=sorted(active,key=lambda n:(-win[n],n))
    top1=ranked[0]
    paper=[]
    if odds is not None:
        for n in ranked[:4]:
            ev=win[n]*odds[n]-1
            if ev>=.10:
                paper.append({"number":n,"indicative_ev":ev})
    names={p["numPmu"]:p["nom"] for p in pred["target_snapshot"]["participants"]}
    late=(now>=start or repaired["status"]!="PRESTART_HISTORY_REPAIR_SHADOW"
          or quotes_state=="RETROSPECTIVE")
    return {
       "version":"turf_lab_v4_full_retrained_candidate_1",
       "status":"RESEARCH_ONLY_NO_BET",
       "freshness":"RETROSPECTIVE" if late else "PRESTART_RESEARCH",
       "generated_at":now.isoformat() if not late else None,
       "race_id":pred["race_id"],
       "recommendations_allowed":False,
       "decision":"NO BET",
       "gagnant":{"number":top1,"name":names[top1],"probability":win[top1],
                  "basis":"V4_RETRAINED_WINNER" if odds is None else "V4_RETRAINED_MARKET_CORRECTION"},
       "top5":{"numbers":top5,"names":[names[n] for n in top5],
               "method":"V4_RETRAINED_FIVE_CONDITIONAL_STAGES"},
       "value":{"status":quotes_state,"paper_candidates_not_bets":paper,
                "minimum_indicative_ev":.10},
       "history_repair":{"required":True,"runners_updated":repaired["runners_changed_recent5"],
                         "unresolved":history_problems,
                         "quality":"INCOMPLETE" if history_problems else "CHECKED"},
       "model_sha256":lock["models_sha256"],
       "evidence":{"original":pred_path.as_posix(),"history":Path(history_file).as_posix(),
                   "quotes":str(quotes_file) if quotes_file else None},
       "limits":["New winner, ranking and market models trained together chronologically on 2022-2025.",
                 "Only a subset of historical runners had verifiable individual corrections.",
                 "2026 was reused for descriptive evaluation, not independent testing.",
                 "Real-money policy remains suspended: no advised SG or Z5 stakes."]
    }


def record(prediction_file,history_file,quotes_file=None,output=None,now=None):
    result=run(prediction_file,history_file,quotes_file,now)
    dest=Path(output) if output else Path(prediction_file).parent/"v4_full_retrained.json"
    if dest.exists() and json.loads(dest.read_text())!=result:
        raise ValueError("Immutable original V4 full forecast would be overwritten")
    dump(dest,result)
    return result
