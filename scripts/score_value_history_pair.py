"""Score ORIGINAL on-demand full-board V2 pairs, without recalculating forecasts.

Selection is user-supplied (not random) and does not establish bookmaker ROI.
No retrospective replay may enter prospective evaluation.
"""
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from turf_lab.evidence import dump
from turf_lab.history_sync import History
from turf_lab.month_history import identity

ROOT = Path("predictions_operational")
OUT = Path("reports/value_history_pair_v1/on_demand_prospective_scores.json")
VERSION = "history_repair_shadow_v1_1_nancy_alias"


def aware(value):
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:
        raise ValueError("Timezone required")
    return t


def validate(path):
    report=json.loads(Path(path).read_text())
    if report.get("status")!="PRESTART_PAIRED_ON_DEMAND":
        raise ValueError("Not an original prestart paired forecast")
    if report.get("recommendations_allowed") is not False or report.get("history_model") != VERSION:
        raise ValueError("Unknown or unapproved experimental version")
    if report.get("v2_coefficients_retrained") is not False:
        raise ValueError("V2 weights were changed")
    start=aware(report["scheduled_start"])
    if not (aware(report["observed_at"]) <= aware(report["paired_calculated_at"]) < start):
        raise ValueError("Paired capture was late")
    folder=Path(path).parent
    source=json.loads((folder/"prediction.json").read_text())
    sidecar=json.loads((folder/"history_repair_shadow_v1_1.json").read_text())
    quotes=json.loads((folder/"quotes.json").read_text())
    comparison=json.loads((folder/"comparison.json").read_text())
    if (source["race_id"] != report["race_id"] or quotes["race_id"] != report["race_id"] or
        sidecar["race_id"] != report["race_id"] or comparison["race_id"] != report["race_id"]):
        raise ValueError("Source race mismatch")
    if sidecar["status"] != "PRESTART_HISTORY_REPAIR_SHADOW" or
            aware(sidecar["shadow_calculated_at"]) >= start:
        raise ValueError("History sidecar was not actually captured before start")
    if comparison["value_shadow"]["status"] != "PRESTART_SHADOW" or aware(comparison["calculated_at"]) >= start:
        raise ValueError("Original V2 comparison not prestart")
    if quotes["operator"]!=report["operator"] or quotes["observed_at"]!=report["observed_at"]:
        raise ValueError("Quote mismatch")
    pmap={int(n):float(p) for n,p in sidecar["v3_baseline"]["probabilities"].items()}
    candidates={int(n):float(p) for n,p in sidecar["research_candidate"]["probabilities"].items()}
    old={r["number"]:r for r in comparison["value_shadow"]["rows"]}
    rows={r["number"]:r for r in report["rows"]}
    if set(rows)!=set(pmap) or set(rows)!=set(candidates) or set(rows)!=set(old):
        raise ValueError("Runner sets mismatch")
    for n,r in rows.items():
        if abs(r["v3_sport_probability"]-pmap[n])>1e-9 or abs(r["history_sport_probability"]-candidates[n])>1e-9:
            raise ValueError("Sports forecast mutated after start")
        if abs(r["v3_plus_v2_probability"]-old[n]["probability"])>1e-10:
            raise ValueError("V2 baseline changed from original")
    return report,source


def outcome(day_records, frozen):
    rid=frozen["race_id"]
    actual=next((r for r in day_records["records"] if r["race_id"]==rid),None)
    if actual is None:
        return None,"AWAITING_OFFICIAL_RESULT"
    if actual["scheduled_start_ms"] != int(aware(frozen["scheduled_start"]).timestamp()*1000):
        return None,"START_TIME_CHANGED"
    before={p["numPmu"]:(identity(p),p["statut"]) for p in frozen["target_snapshot"]["participants"]}
    after={p["numPmu"]:(identity(p),p["statut"]) for p in actual["participants"]}
    if before!=after:
        return None,"STARTER_LIST_OR_IDENTITY_CHANGED"
    winners=[p["numPmu"] for p in actual["participants"] if p.get("ordreArrivee")==1]
    if len(winners)!=1:
        return None,"NO_UNIQUE_WINNER"
    return winners[0],"VERIFIED_OFFICIAL"


def metrics(pair,winner):
    rows=pair["rows"]
    definitions={
        "market_normalized":"market_probability",
        "v3_plus_v2":"v3_plus_v2_probability",
        "history_plus_v2":"history_plus_v2_probability"
    }
    result={}
    for label,key in definitions.items():
        p={r["number"]:r[key] for r in rows}
        if winner not in p or len(p)!=len(rows) or sum(p.values()) < 0.999999 or sum(p.values())>1.000001:
            raise ValueError("Invalid paired distribution")
        result[label]={
            "log_loss":-math.log(max(1e-15,p[winner])),
            "brier":sum((pr-int(n==winner))**2 for n,pr in p.items()),
            "top1_correct":int(max(p,key=p.get)==winner),
            "winner_probability":p[winner]
        }
    return result


def run(destination=OUT):
    history=History()
    cache={}
    eligible=defaultdict(list);excluded=[]
    for path in sorted(ROOT.glob("*/*/value_history_pair_v1.json")):
        try:
            pair,source=validate(path)
            eligible[pair["race_id"]].append((pair["paired_calculated_at"],str(path),pair,source))
        except (ValueError,TypeError,KeyError,OSError) as e:
            excluded.append({"path":str(path),"reason":str(e)})
    chosen=[min(variants,key=lambda x:x[0]) for variants in eligible.values()]
    scored=[];pending=[]
    for _,name,pair,source in sorted(chosen):
        day=pair["race_id"][:10]
        if day not in cache:
            try:
                cache[day]=history.day(day)
            except (ValueError,OSError,KeyError,TypeError) as e:
                cache[day]={"records":[],"reason":str(e)}
        winner,reason=outcome(cache[day],source)
        row={"race_id":pair["race_id"],"source_pair":name,
             "operator":pair["operator"],"outcome":reason}
        if winner is None:
            pending.append(row)
        else:
            row["winner"]=winner
            row["metrics"]=metrics(pair,winner)
            scored.append(row)
    labels=("market_normalized","v3_plus_v2","history_plus_v2")
    means={k:{
        m:mean(row["metrics"][k][m] for row in scored)
        for m in ("log_loss","brier","top1_correct")
    } for k in labels} if scored else {}
    result={"status":"USER_SELECTED_PRESTART_BOARDS_ONLY","operator_scope":"User provided quotes, not automatic ZEturf coverage",
            "selection_bias":"ON_DEMAND_NONRANDOM",
            "is_independent_statistical_validation":False,
            "recommendations_allowed":False,"roi":None,
            "roi_reason":"Historical screenshot odds are not an independently verified fixed accepted price or paid dividend.",
            "eligible_pairs":len(chosen),"scored_races":len(scored),"pending_races":len(pending),
            "means":means,"scores":scored,"pending":pending,"invalid":excluded}
    dump(destination,result)
    return result


if __name__=="__main__":
    print(json.dumps({k:v for k,v in run().items() if k in ("eligible_pairs","scored_races","pending_races","means")},indent=2))
