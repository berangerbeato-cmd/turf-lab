"""Compare original prestart FULL V4 vs V4+V7 speed shadow, same selected races.

No post-start recomputation of speed from history: only archived runner
context residual captured BEFORE START is allowed. The frozen 43-feature
winner and five-rank models are checked against the archived outputs.
This is a NON-market cohort: no ZEturf odds, no claimed ROI.
"""
import json
import math
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

from scripts.score_history_repair_prospective import validate_sidecar, verified_top5
from scripts.score_v4_full_prospective import values,read_valid as v4_valid
from turf_lab.evidence import dump
from turf_lab.history_sync import History
from turf_lab.pilot import probabilities

BASE=Path("reports/history_repair_shadow_v1/prospective_forecasts")
OUT=Path("reports/v4_speed/prospective_scores.json")
BEGIN=datetime.fromisoformat("2026-11-22T00:00:00+01:00")
METRICS=("log_loss","brier","top1_correct","top5_overlap","top5_exact")


def input_check(path):
    # Delayed scientific dependencies: the empty scorecard stays stdlib-only.
    from turf_lab.v4_full_inference import load as base_load,repaired_frame
    from turf_lab.v4_speed_shadow import frozen as speed_load
    from scripts.train_v4_full import rank_top5
    path=Path(path)
    saved=json.loads(path.read_text())
    prior,source=validate_sidecar(path.parent/"history_repair_shadow_v1_1.json")
    if (saved.get("version")!="v4_speed_challenger_1" or
            saved.get("status")!="PRESTART_SHADOW_RESEARCH" or
            saved.get("source")!="DETERMINISTIC_SCHEDULED_COHORT_ONLY" or
            saved.get("recommendations_allowed") is not False or
            saved.get("decision")!="NO BET"):
        raise ValueError("Invalid V4 Speed research provenance")
    at=datetime.fromisoformat(saved["generated_at"])
    start=datetime.fromisoformat(source["scheduled_start"])
    before=datetime.fromisoformat(prior["shadow_calculated_at"])
    if (at.tzinfo is None or at<BEGIN or not before<=at<start or
            saved["scheduled_start"]!=source["scheduled_start"] or
            saved["race_id"]!=source["race_id"]):
        raise ValueError("Speed prestart dates/target not valid")
    if (saved["evidence"]["source_prediction"]!=(path.parent/"prediction.json").as_posix()
         or saved["evidence"]["history_repair"]!=(path.parent/"history_repair_shadow_v1_1.json").as_posix()):
        raise ValueError("Archived speed input pointers changed")
    models,lock,cfg=speed_load()
    if (saved["speed_model_hashes"]!=lock["three_new_model_hashes"] or
            saved["speed_protocol_sha256"]!=lock["old_speed_protocol_sha256"]):
        raise ValueError("Speed models or feature policy changed")
    patched,uncertain=repaired_frame(source,prior)
    if saved["history_repair_unresolved"]!=uncertain:
        raise ValueError("Historical uncertainty changed")
    present={r["number"] for r in patched}
    vals={int(n):v for n,v in saved["speed_input_by_runner"].items()}
    if set(vals)!=present:
        raise ValueError("Missing original prestart speed for a runner")
    rows=[]
    for r in patched:
        inp=vals[r["number"]]
        z=inp["context_residual"]
        count=inp["prior_races_used"]
        if ((z is not None and (not isinstance(z,(int,float)) or not math.isfinite(z)))
                or isinstance(count,bool) or not isinstance(count,int) or not 0<=count<=5):
            raise ValueError("Invalid original runner speed value/count")
        if count==0 and z is not None or count>0 and z is None:
            raise ValueError("Speed field did not match historical count")
        rows.append(dict(r,features=list(r["features"])+[z]))
    fresh=probabilities({"runners":rows},models["winner"]["model"])
    temperature=models["winner"]["temperature"]
    scaled={n:max(0,v)**(1/temperature) for n,v in fresh.items()}
    z=sum(scaled.values())
    challenger={n:v/z for n,v in scaled.items()}
    stored={int(n):float(v) for n,v in saved["win_probabilities"].items()}
    if (set(challenger)!=set(stored) or
            any(abs(challenger[n]-stored[n])>1e-10 for n in stored)):
        raise ValueError("Original frozen 43-feature winning probabilities not reproducible")
    ranked=sorted((n for n in challenger if challenger[n]>0),key=lambda n:(-challenger[n],n))
    if (saved["top1"]!=ranked[0] or
            saved["top5"]!=rank_top5({"runners":rows},models["ranking"])):
        raise ValueError("Original conditional V4 Speed ranking not reproducible")
    # V4 was also written BEFORE the start, not computed from the known result.
    old,pred=v4_valid(path.parent/"v4_full_retrained.json")
    if old["race_id"]!=saved["race_id"]:
        raise ValueError("Cannot compare different target races")
    weights,_=base_load()
    frame,_=repaired_frame(pred,prior)
    baseline=probabilities({"runners":frame},weights["winner"]["model"])
    t=weights["winner"]["temperature"]
    p={n:v**(1/t) for n,v in baseline.items()}
    denominator=sum(p.values())
    baseline={n:v/denominator for n,v in p.items()}
    return saved,pred,challenger,baseline,old["top5"]["numbers"]


def bootstrap(rows,metric,reps=600):
    days=defaultdict(list)
    for row in rows:
        v=row["metrics"]["v4_speed"][metric]-row["metrics"]["v4_current"][metric]
        days[row["race_id"][:10]].append(v)
    if len(days)<10:
        return None
    keys=sorted(days)
    rng=random.Random(20261122)
    dist=[]
    for _ in range(reps):
        dist.append(mean(v for _ in keys for v in days[rng.choice(keys)]))
    dist.sort()
    return [dist[int(reps*.025)],dist[int(reps*.975)-1]]


def run(output=OUT):
    paths=sorted(BASE.glob("*/*/v4_speed_shadow.json"))
    cache={};history=History();scored=[];pending=[];rejected=[];ids=set()
    for path in paths:
        try:
            report,source,ch,base,old_top=input_check(path)
            if report["race_id"] in ids:
                raise ValueError("Duplicate selected race")
            ids.add(report["race_id"])
            day=report["race_id"][:10]
            if day not in cache:
                try:
                    cache[day]=history.day(day)
                except (ValueError,OSError,KeyError,TypeError) as e:
                    cache[day]={"records":[],"error":str(e)}
            finish,status=verified_top5(cache[day],source)
            item={"race_id":report["race_id"],"status":status,"input":str(path),
                  "speed_prior_coverage":report["speed_in_target_field"]["fraction"]}
            if finish is None:
                pending.append(item)
                continue
            item["metrics"]={
                "v4_current":values(base,old_top,finish),
                "v4_speed":values(ch,report["top5"],finish)
            }
            scored.append(item)
        except (ValueError,KeyError,TypeError,OSError) as e:
            rejected.append({"input":str(path),"reason":str(e)})
    avg={k:{name:mean(r["metrics"][k][name] for r in scored) for name in METRICS}
         for k in ("v4_current","v4_speed")} if scored else {}
    delta={name:{"v4_speed_minus_current":mean(r["metrics"]["v4_speed"][name]-
                                            r["metrics"]["v4_current"][name] for r in scored),
                 "day_bootstrap_95":bootstrap(scored,name)} for name in METRICS} if scored else {}
    summary={
        "version":"v4_speed_challenger_1",
        "status":"ORIGINAL_PRESTART_NONMARKET_V4_SPEED_VS_V4",
        "sampling_rule":"Only deterministic scheduled captures; never retro or user-selected race",
        "recommendations_allowed":False,
        "captured":len(paths),"verified_results":len(scored),"pending_results":len(pending),
        "invalid_original_captures":len(rejected),
        "minimum_races_before_review":200,"validation_ready":len(scored)>=200,
        "means":avg,"paired_differences":delta,
        "scored":scored,"pending":pending,"invalid":rejected,
        "roi":None,
        "limits":["PMU archived prices are not real ZEturf bets; this research cohort has no odds.",
                  "Race-level speed inputs must be captured before the race, not rebuilt after result.",
                  "No automatic candidate promotion to the one user-facing V4."]
    }
    dump(output,summary)
    print(json.dumps({k:summary[k] for k in
                      ("captured","verified_results","pending_results","invalid_original_captures",
                       "means")},indent=2))
    return summary


if __name__=="__main__":
    run()
