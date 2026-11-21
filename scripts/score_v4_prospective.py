"""Strict original-prestart V4 shadow scores vs frozen V3 on same races.

No outcomes ever used for inference. No odds/ROI without independently
verified accepted prices. Only the predeclared deterministic cohort counts.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from collections import defaultdict

from scripts.score_history_repair_prospective import validate_sidecar, verified_top5
from turf_lab.evidence import dump
from turf_lab.history_sync import History

ROOT = Path("reports/history_repair_shadow_v1/prospective_forecasts")
OUT = Path("reports/v4/prospective_scores.json")
BEGIN = datetime.fromisoformat("2026-11-22T00:00:00+01:00")


def validate(path):
    path = Path(path)
    v4 = json.loads(path.read_text())
    original = path.parent / "prediction.json"
    repair_path = path.parent / "history_repair_shadow_v1_1.json"
    repair,pred = validate_sidecar(repair_path)
    if v4.get("version") != "turf_lab_v4_research_1" or v4["race_id"] != pred["race_id"]:
        raise ValueError("V4 identity or version mismatch")
    if v4.get("freshness") != "PRESTART_RESEARCH" or v4.get("recommendations_allowed") is not False:
        raise ValueError("V4 snapshot was not safely captured prestart")
    if v4.get("decision") != "NO BET" or v4.get("value",{}).get("status") != "NO_VERIFIED_COTES":
        raise ValueError("Cohort V4 has unexpected odds or betting status")
    start = datetime.fromisoformat(pred["scheduled_start"])
    moment = datetime.fromisoformat(v4["generated_at"])
    if (moment.tzinfo is None or moment < BEGIN or not
            datetime.fromisoformat(repair["shadow_calculated_at"]) <= moment < start):
        raise ValueError("V4 generated late or before its inputs")
    if v4["evidence"]["sports"] != original.as_posix() or v4["evidence"]["repair"] != repair_path.as_posix():
        raise ValueError("V4 evidence pointers changed")
    originals={int(n):p for n,p in pred["models"]["available_history_v3"]["probabilities"].items()}
    challenger={int(n):p for n,p in repair["research_candidate"]["probabilities"].items()}
    active={p["numPmu"] for p in pred["target_snapshot"]["participants"] if p["statut"]=="PARTANT"}
    if (set(originals)!=set(challenger) or abs(sum(challenger.values())-1)>1e-9 or
            set(v4["top5"]["numbers"])-active or len(set(v4["top5"]["numbers"]))!=5):
        raise ValueError("V4 forecast uses inconsistent runner field")
    winner = max(active,key=lambda n:(challenger[n],-n))
    if (v4["gagnant"]["number"] != winner or
            abs(v4["gagnant"]["probability"]-challenger[winner])>1e-10 or
            v4["gagnant"]["basis"] != "REPAIRED_SPORT_UNCALIBRATED"):
        raise ValueError("V4 winner was changed from archived repaired sports distribution")
    return v4,pred,originals,challenger


def metrics(p, selection, finish):
    winner=finish[0]
    top5=list(selection)
    return {
        "log_loss":-math.log(max(1e-15,p[winner])),
        "brier":sum((v-int(n==winner))**2 for n,v in p.items()),
        "top1_correct":int(max(p,key=lambda n:(p[n],-n))==winner),
        "top5_overlap":len(set(top5)&set(finish[:5])),
        "top5_exact":int(set(top5)==set(finish[:5]))
    }


def run(output=OUT):
    forecasts = sorted(ROOT.glob("*/*/v4_unified.json"))
    history=History()
    cache={}
    scores=[];pending=[];invalid=[]
    for path in forecasts:
        try:
            v4,pred,v3,changed=validate(path)
            day=pred["race_id"][:10]
            if day not in cache:
                try:
                    cache[day]=history.day(day)
                except (ValueError,KeyError,OSError,TypeError) as e:
                    cache[day]={"records":[],"error":str(e)}
            finish,status=verified_top5(cache[day],pred)
            rec={"race_id":v4["race_id"],"status":status,
                 "source_v4":str(path),
                 "history_uncertainty":len(v4["history_repair"]["unresolved"])}
            if finish is None:
                pending.append(rec)
            else:
                v3_top5=sorted((n for n,p in v3.items() if p>0),
                               key=lambda n:(-v3[n],n))[:5]
                rec["metrics"]={
                    "frozen_v3":metrics(v3,v3_top5,finish),
                    "unified_v4_research":metrics(changed,v4["top5"]["numbers"],finish)
                }
                scores.append(rec)
        except (ValueError,KeyError,OSError,TypeError) as e:
            invalid.append({"source":str(path),"reason":str(e)})
    keys=("log_loss","brier","top1_correct","top5_overlap","top5_exact")
    means={
        label:{k:mean(x["metrics"][label][k] for x in scores) for k in keys}
        for label in ("frozen_v3","unified_v4_research")
    } if scores else {}
    return_value={
        "status":"FORWARD_ONLY_V4_VS_V3",
        "model_version":"turf_lab_v4_research_1",
        "selection":"Only deterministic scheduled originally archived prestart captures",
        "no_real_money_recommendations":True,
        "prospective_captures":len(forecasts),
        "verified_results":len(scores),
        "pending_results":len(pending),
        "invalid_captures":len(invalid),
        "races_with_unresolved_history":sum(x["history_uncertainty"]>0 for x in scores),
        "min_races_before_review":200,
        "validation_ready":len(scores)>=200,
        "means":means,
        "paired_scores":scores,
        "pending":pending,"invalid":invalid,
        "roi":None,
        "caveats":[
            "V4 is a composite of frozen existing models, not a newly fitted and calibrated joint model.",
            "V4 stage top five was never fitted with the new history-repaired features.",
            "Odds and real ZEturf settlement are outside this deterministic no-market cohort.",
            "Do not use this study to recommend or place bets."
        ]
    }
    dump(output,return_value)
    return return_value


if __name__=="__main__":
    result=run()
    print(json.dumps({key:result[key] for key in
                      ("prospective_captures","verified_results","pending_results",
                       "invalid_captures","means")},indent=2))
