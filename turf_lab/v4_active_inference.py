"""The single active Turf Lab V4 interface: 43 history features incl. old V7 pace.

The three V4 Speed weights were fitted and SHA-frozen before promotion.
This module *uses* those weights (winner, 5 conditional positions, market),
not any old 42-feature V4 model. Missing timed history is explicitly encoded
as None (a value the fitted model learned); missing whole speed evidence BLOCKS.
Mandatory History Repair and original prestart data; never place a bet.
"""
import json
import math
from datetime import datetime,timezone
from pathlib import Path

from turf_lab.evidence import dump
from turf_lab.month_history import identity
from turf_lab.pilot import probabilities
from turf_lab.market_repair import predict as market_probabilities
from turf_lab.v4_full_inference import repaired_frame,verified_board,stamp,sha
from turf_lab.v4_speed_shadow import frozen as speed_frozen
from scripts.train_v4_full import rank_top5

REGISTRY=Path("config/v4_active.json")
MARKET=Path("models/v4_speed/market.json")


def load_active():
    registry=json.loads(REGISTRY.read_text())
    if (registry.get("active_user_model")!="TURF_LAB_V4" or
            registry.get("model_family")!="v4_speed_challenger_1" or
            registry.get("context_file")!="v4_speed_context.json" or
            registry.get("recommendations_allowed") is not False or
            registry.get("real_money_betting") is not False):
        raise ValueError("Active V4 promotion policy is missing or unsafe")
    weights,lock,cfg=speed_frozen()
    if (sha(MARKET)!=lock["three_new_model_hashes"]["market.json"] or
            lock["version"]!=registry["model_family"]):
        raise ValueError("Recalibrated V4 market coefficients are not locked")
    market=json.loads(MARKET.read_text())
    if len(market["weights"])!=2:
        raise ValueError("V4 market model has wrong coefficient count")
    return weights,market,lock,registry


def frame(original,repair,context,original_path,now):
    """Verify all 43rd features were calculated and captured BEFORE start."""
    start=stamp(original["scheduled_start"])
    pred_time=stamp(original["predicted_at"])
    context_time=stamp(context["captured_at"])
    repair_time=stamp(repair["shadow_calculated_at"])
    if not pred_time<=context_time<start or not pred_time<=repair_time<start:
        raise ValueError("V4 needs valid prestart sport/history/speed evidence")
    if now<max(context_time,repair_time) or now>=start:
        raise ValueError("New V4 prediction cannot be recorded after departure")
    if repair.get("status")!="PRESTART_HISTORY_REPAIR_SHADOW":
        raise ValueError("Mandatory History Repair was not made prestart")
    if repair["source_prediction"]!=Path(original_path).as_posix():
        raise ValueError("History Repair source does not match original forecast")
    if (context.get("version")!="v4_speed_prior_only_context_v1" or
            context.get("source")!="VERIFIED_PMU_PRIOR_RACE_RESULTS_ONLY" or
            context.get("contains_target_outcome") is not False or
            context.get("race_id")!=original["race_id"] or
            context.get("target_date")!=original["race_id"][:10]):
        raise ValueError("V4 speed context is not a verified prior-only snapshot")
    if context.get("prior_races",0)<1 or context.get("last_prior_day","9999")>=context["target_date"]:
        raise ValueError("V4 speed included future or unavailable history")
    if (not isinstance(context.get("prior_history_sha256"),str)
            or len(context["prior_history_sha256"])!=64):
        raise ValueError("V4 previous-races source checksum missing")
    if context.get("target_participants")!=len(original["target_snapshot"]["participants"]):
        raise ValueError("The speed horse field changed")
    runners,unresolved=repaired_frame(original,repair)
    participants=original["target_snapshot"]["participants"]
    names={p["numPmu"]:p["nom"] for p in participants}
    known={p["numPmu"]:identity(p) for p in participants}
    by_num={r["number"]:r for r in runners}
    raw=context["target_field"]
    if set(map(str,known))!=set(raw) or len(known)!=len(by_num):
        raise ValueError("Speed feature field differs from current starters")
    features=[]
    active=set()
    for r in runners:
        n=r["number"]
        obj=raw[str(n)]
        count=obj.get("prior_races_used")
        val=obj.get("context_residual")
        if (r["horse_id"]!=known[n] or obj["horse_id"]!=known[n]
                or not isinstance(count,int) or isinstance(count,bool) or not 0<=count<=5
                or (count==0)!=(val is None)
                or (val is not None and
                    (isinstance(val,bool) or not isinstance(val,(int,float)) or not math.isfinite(val)))):
            raise ValueError("V4 speed runner identity/number/value mismatch")
        if len(r["features"])!=42:
            raise ValueError("Wrong frozen V4 base feature dimension")
        features.append(dict(r,features=list(r["features"])+[val]))
        if not r["non_runner"]:
            active.add(n)
    if len(active)<6:
        raise ValueError("V4 needs at least six active horses")
    return features,unresolved,active,names


def run(prediction_file,repair_file,context_file,quotes_file=None,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Timezone-aware V4 prediction required")
    prediction_file=Path(prediction_file)
    repair_file=Path(repair_file)
    context_file=Path(context_file)
    if not context_file.exists():
        raise ValueError("Mandatory prestart contextual speed is missing")
    original=json.loads(prediction_file.read_text())
    repair=json.loads(repair_file.read_text())
    context=json.loads(context_file.read_text())
    if (original.get("status")!="PRESTART_RESEARCH" or
            original.get("primary_model")!="available_history_v3" or
            original.get("recommendations_allowed") is not False):
        raise ValueError("Original prestart frozen sports evidence invalid")
    models,market,lock,registry=load_active()
    if context.get("speed_protocol_sha256")!=lock["old_speed_protocol_sha256"]:
        raise ValueError("Prestart chrono protocol differs from training")
    runners,unresolved,active,names=frame(original,repair,context,prediction_file,now)
    sport=probabilities({"runners":runners},models["winner"]["model"])
    temperature=float(models["winner"]["temperature"])
    if not math.isfinite(temperature) or temperature<=0:
        raise ValueError("V4 winner calibration invalid")
    transformed={n:max(0,p)**(1/temperature) for n,p in sport.items()}
    denom=sum(transformed.values())
    win={n:p/denom for n,p in transformed.items()}
    if (set(win)!={r["number"] for r in runners}
            or abs(sum(win.values())-1)>1e-8):
        raise ValueError("V4 sport distribution invalid")
    top5=rank_top5({"runners":runners},models["ranking"])
    if len(top5)!=5 or len(set(top5))!=5 or not set(top5)<=active:
        raise ValueError("V4 43-feature Top5 is invalid")
    price_state="NO_VERIFIED_PRESTART_QUOTES"
    operator=None
    odds=None
    if quotes_file is not None:
        quotes=json.loads(Path(quotes_file).read_text())
        odds,price_state=verified_board(original,quotes,now,now)
        if price_state!="PRESTART":
            raise ValueError("V4 market correction requires a fresh prestart quote board")
        order=sorted(odds)
        updated=market_probabilities(
            [odds[n] for n in order],[win[n] for n in order],market["weights"])
        win={n:p for n,p in zip(order,updated)}
        operator=quotes["operator"]
    top1=sorted(active,key=lambda n:(-win[n],n))[0]
    paper=[]
    if odds is not None:
        for n in sorted(active,key=lambda n:(-win[n],n))[:4]:
            ev=win[n]*odds[n]-1
            if ev>=.10:
                paper.append({"number":n,"indicative_ev":ev})
    coverage=sum(r["features"][-1] is not None for r in runners if not r["non_runner"])
    return {
      "version":"turf_lab_v4_integrated_speed_1",
      "model":"TURF_LAB_V4",
      "status":"RESEARCH_NO_BET" if not unresolved else "HISTORY_INCOMPLETE_NO_BET",
      "freshness":"PRESTART_RESEARCH",
      "generated_at":now.isoformat(),
      "race_id":original["race_id"],
      "recommendations_allowed":False,
      "decision":"NO BET",
      "gagnant":{"number":top1,"name":names[top1],"probability":win[top1],
                 "basis":"V4_43F_SPORT" if odds is None else "V4_43F_RETRAINED_COTES"},
      "top5":{"numbers":top5,"names":[names[n] for n in top5],
              "method":"V4_43F_FIVE_CONDITIONAL_RANK_MODELS"},
      "value":{"status":price_state,"operator":operator,
               "paper_candidates_not_bets":paper,"minimum_indicative_ev":.10},
      "ze5":{"numbers":top5,"status":"PAPER_UNVALIDATED","stake_eur":None},
      "history_repair":{"required":True,
                        "runners_updated":repair["runners_changed_recent5"],
                        "unresolved":unresolved},
      "context_speed":{"required":True,"dimension":43,
                       "coverage":coverage,"active":len(active),
                       "missing_context_count":len(active)-coverage,
                       "policy_sha256":lock["old_speed_protocol_sha256"]},
      "model_sha256":lock["three_new_model_hashes"],
      "evidence":{"original":prediction_file.as_posix(),
                  "history_repair":repair_file.as_posix(),
                  "speed_context":context_file.as_posix(),
                  "original_prior_history_sha256":context["prior_history_sha256"],
                  "quotes":str(quotes_file) if quotes_file else None},
      "limitations":["V4 Speed weights are integrated but independent forward value/ROI not yet established.",
                     "An entirely absent speed snapshot blocks V4; individual missing timed starts are modeled as missing.",
                     "Real-money wagers and advised stakes remain suspended."]
    }


def record(prediction_file,repair_file,context_file,quotes_file=None,output=None,now=None):
    result=run(prediction_file,repair_file,context_file,quotes_file,now)
    if now is None:
        finished=datetime.now(timezone.utc)
        if finished>=stamp(json.loads(Path(prediction_file).read_text())["scheduled_start"]):
            raise ValueError("V4 with contextual speed completed after start")
        result["generated_at"]=finished.isoformat()
    dest=Path(output) if output else Path(prediction_file).parent/"v4_integrated.json"
    if dest.exists() and json.loads(dest.read_text())!=result:
        raise ValueError("Original V4 snapshot cannot be overwritten")
    dump(dest,result)
    return result
