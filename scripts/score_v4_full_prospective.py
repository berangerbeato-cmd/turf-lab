"""Forward-only paired V4 retrained versus frozen V3 sporting evaluation.

Only immutable sidecars produced by the originally scheduled deterministic
cohort count. No historical Reims replays or user-selected races can enter.
"""
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from scripts.score_history_repair_prospective import validate_sidecar, verified_top5
from turf_lab.evidence import dump
from turf_lab.history_sync import History

BASE = Path("reports/history_repair_shadow_v1/prospective_forecasts")
OUT = Path("reports/v4_full/prospective_scores.json")
BEGINS = datetime.fromisoformat("2026-11-22T00:00:00+01:00")
METRICS = ("log_loss","brier","top1_correct","top5_overlap","top5_exact")


def read_valid(path):
    path=Path(path)
    saved=json.loads(path.read_text())
    shadow,pred=validate_sidecar(path.parent/"history_repair_shadow_v1_1.json")
    if not shadow.get("is_independent_prospective_validation",False):
        raise ValueError("On-demand or retrospectively chosen race")
    if saved.get("version") != "turf_lab_v4_full_retrained_candidate_1":
        raise ValueError("Not the freshly trained full V4")
    if (saved.get("freshness")!="PRESTART_RESEARCH" or
            saved.get("decision")!="NO BET" or saved.get("recommendations_allowed") is not False):
        raise ValueError("V4 not genuinely paper-only and prestart")
    generated=datetime.fromisoformat(saved["generated_at"])
    start=datetime.fromisoformat(pred["scheduled_start"])
    before=datetime.fromisoformat(shadow["shadow_calculated_at"])
    if (generated.tzinfo is None or generated < BEGINS or not before <= generated < start):
        raise ValueError("Late, missing or misordered V4 prediction")
    if (saved["race_id"]!=pred["race_id"] or
            saved["evidence"]["original"]!=(path.parent/"prediction.json").as_posix() or
            saved["evidence"]["history"]!=(path.parent/"history_repair_shadow_v1_1.json").as_posix() or
            saved["evidence"]["quotes"] is not None):
        raise ValueError("Cross-race or market-influenced scheduled V4")
    # Reproduction is a *verification* of original immutable snapshot, never
    # a new prediction after the outcome has become known.
    from turf_lab.v4_full_inference import run
    reproduced=run(path.parent/"prediction.json",path.parent/"history_repair_shadow_v1_1.json",
                   now=generated)
    if (reproduced["gagnant"]!=saved["gagnant"] or
            reproduced["top5"]!=saved["top5"] or
            reproduced["model_sha256"]!=saved["model_sha256"]):
        raise ValueError("Original V4 coefficients/outputs are not reproducible")
    return saved,pred


def values(probs, top5, finish):
    winner=finish[0]
    if winner not in probs:
        raise ValueError("Winner missing from model")
    return {
        "log_loss":-math.log(max(1e-15,probs[winner])),
        "brier":sum((p-int(n==winner))**2 for n,p in probs.items()),
        "top1_correct":int(max(probs,key=lambda n:(probs[n],-n))==winner),
        "top5_overlap":len(set(top5)&set(finish[:5])),
        "top5_exact":int(set(top5)==set(finish[:5])),
    }


def interval(rows,metric,n=500):
    grouped=defaultdict(list)
    for r in rows:
        v=r["metrics"]["v4_retrained"][metric]-r["metrics"]["frozen_v3"][metric]
        grouped[r["race_id"][:10]].append(v)
    if len(grouped)<10:
        return None
    keys=sorted(grouped);rng=random.Random(20261122)
    out=[]
    for _ in range(n):
        vals=[v for _ in keys for v in grouped[rng.choice(keys)]]
        out.append(mean(vals))
    out.sort()
    return [out[int(n*.025)],out[int(n*.975)-1]]


def main(output=OUT):
    history=History();cache={}
    scored=[];pending=[];invalid=[]
    candidates=sorted(BASE.glob("*/*/v4_full_retrained.json"))
    used=set()
    for path in candidates:
        try:
            original,pred=read_valid(path)
            rid=original["race_id"]
            if rid in used:
                raise ValueError("Duplicate race in V4 planned sample")
            used.add(rid)
            day=rid[:10]
            if day not in cache:
                try:
                    cache[day]=history.day(day)
                except (OSError,ValueError,TypeError,KeyError) as e:
                    cache[day]={"records":[],"error":str(e)}
            finish,status=verified_top5(cache[day],pred)
            details={"race_id":rid,"source_v4":str(path),"outcome_status":status,
                     "history_anomalies":len(original["history_repair"]["unresolved"])}
            if finish is None:
                pending.append(details)
                continue
            # Full V4 output includes winner only. Read a verified RECOMPUTATION
            # of the distribution from the frozen model; never from results.
            from turf_lab.v4_full_inference import load,repaired_frame
            from turf_lab.pilot import probabilities
            weights,_=load()
            sidecar=json.loads((path.parent/"history_repair_shadow_v1_1.json").read_text())
            patched,_=repaired_frame(pred,sidecar)
            sport=probabilities({"runners":patched},weights["winner"]["model"])
            temp=float(weights["winner"]["temperature"])
            p={n:v**(1/temp) for n,v in sport.items()}
            total=sum(p.values());p={n:v/total for n,v in p.items()}
            v3={int(k):v for k,v in pred["models"]["available_history_v3"]["probabilities"].items()}
            top3=sorted((n for n in v3 if v3[n]>0),key=lambda n:(-v3[n],n))[:5]
            details["metrics"]={
                "frozen_v3":values(v3,top3,finish),
                "v4_retrained":values(p,original["top5"]["numbers"],finish),
            }
            scored.append(details)
        except (OSError,ValueError,TypeError,KeyError) as e:
            invalid.append({"source":str(path),"reason":str(e)})
    summary={
        "status":"INDEPENDENT_PRESTART_V4_FULL_VS_V3",
        "model":"turf_lab_v4_full_retrained_candidate_1",
        "planned_selection":"Predeclared deterministic two upcoming French harness races per capture window",
        "recommendations_allowed":False,
        "captured":len(candidates),"scored":len(scored),"pending":len(pending),"invalid":len(invalid),
        "minimum_verification_races":200,"validation_ready":len(scored)>=200,
        "mean":{k:{m:mean(r["metrics"][k][m] for r in scored) for m in METRICS}
                for k in ("frozen_v3","v4_retrained")} if scored else {},
        "paired_v4_minus_v3":{m:{"difference":mean(r["metrics"]["v4_retrained"][m]-
                                                r["metrics"]["frozen_v3"][m] for r in scored),
                                  "day_bootstrap_95":interval(scored,m)}
                              for m in METRICS} if scored else {},
        "verified_races":scored,"pending_races":pending,"invalid_races":invalid,
        "roi":None,
        "limits":["This cohort has NO ZEturf prices, hence does not validate the market correction or expected value.",
                  "2026 test used during development was already inspected; only genuinely later prestart samples count.",
                  "Promotion is not automatic and real betting remains suspended."]
    }
    dump(output,summary)
    print(json.dumps({k:summary[k] for k in ("captured","scored","pending","invalid","mean")},
                     indent=2))
    return summary


if __name__=="__main__":
    main()
