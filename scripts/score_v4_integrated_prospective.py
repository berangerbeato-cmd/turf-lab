"""Official-result evaluation of the ONE integrated 43-feature V4.

Only original snapshots from the deterministic predeclared prospective cohort
count. Frozen model and original captured 43rd inputs can be recomputed to
verify they are truly the probabilities used before the target outcome.
"""
import json
import math
from datetime import datetime
from pathlib import Path
from statistics import mean

from scripts.score_history_repair_prospective import validate_sidecar,verified_top5
from turf_lab.history_sync import History
from turf_lab.evidence import dump

ROOT=Path("reports/history_repair_shadow_v1/prospective_forecasts")
OUT=Path("reports/v4_integrated/prospective_scores.json")
BEGIN=datetime.fromisoformat("2026-11-22T00:00:00+01:00")


def confirm(path):
    path=Path(path)
    saved=json.loads(path.read_text())
    sidecar,pred=validate_sidecar(path.parent/"history_repair_shadow_v1_1.json")
    if (saved.get("version")!="turf_lab_v4_multifeature_1"
            or saved.get("model")!="TURF_LAB_V4"
            or saved.get("freshness")!="PRESTART_RESEARCH"
            or saved.get("recommendations_allowed") is not False
            or saved.get("decision")!="NO BET"):
        raise ValueError("Unapproved V4 version or risk policy")
    generated=datetime.fromisoformat(saved["generated_at"])
    start=datetime.fromisoformat(pred["scheduled_start"])
    speed=json.loads((path.parent/"v4_speed_context.json").read_text())
    feature_time=datetime.fromisoformat(speed["captured_at"])
    repaired_time=datetime.fromisoformat(sidecar["shadow_calculated_at"])
    if (generated.tzinfo is None or generated<BEGIN
            or not feature_time<=generated<start
            or not repaired_time<=generated
            or saved["race_id"]!=pred["race_id"]):
        raise ValueError("Non-prospective V4 original snapshot")
    if (saved["evidence"]["original"]!=(path.parent/"prediction.json").as_posix()
            or saved["evidence"]["history_repair"]!=(path.parent/"history_repair_shadow_v1_1.json").as_posix()
            or saved["evidence"]["speed_context"]!=(path.parent/"v4_speed_context.json").as_posix()
            or saved["evidence"]["quotes"] is not None):
        raise ValueError("Unexpected V4 source, quote or mismatched race")
    aux_path=path.parent/"v4_aux_context.json"
    if (saved["evidence"].get("aux_context")!=aux_path.as_posix()
            or saved.get("reliability_R",{}).get("market_R_gate_fitted") is not True):
        raise ValueError("Missing original class/gain/form/R evidence")
    from turf_lab.v4_multifeature_inference import run,enhanced_frame,frozen
    reproduced=run(path.parent/"prediction.json",
                   path.parent/"history_repair_shadow_v1_1.json",
                   path.parent/"v4_speed_context.json",
                   aux_path,now=generated)
    for key in ("gagnant","top5","history_repair","context_speed","model_sha256",
                "relative_class_and_gains","weighted_recent_form","reliability_R"):
        if saved[key]!=reproduced[key]:
            raise ValueError("Original 47-feature V4 inputs or outputs not reproducible")
    objects,lock=frozen()
    aux=json.loads(aux_path.read_text())
    runners,_,active,_,indices=enhanced_frame(
        pred,sidecar,speed,aux,path.parent/"prediction.json",generated)
    from turf_lab.pilot import probabilities
    raw=probabilities({"runners":runners},objects["winner"]["model"])
    temp=objects["winner"]["temperature"]
    p={n:val**(1/temp) for n,val in raw.items()}
    total=sum(p.values())
    v4={n:val/total for n,val in p.items()}
    if abs(v4[saved["gagnant"]["number"]]-saved["gagnant"]["probability"])>1e-10:
        raise ValueError("Archived V4 winner was not from its frozen 43-feature model")
    v3={int(n):float(val) for n,val in pred["models"]["available_history_v3"]["probabilities"].items()}
    if set(v3)!=set(v4):
        raise ValueError("Frozen V3 field differs from V4")
    return saved,pred,v4,v3


def metrics(p,top5,finish):
    return {
      "log_loss":-math.log(max(1e-15,p[finish[0]])),
      "brier":sum((v-int(n==finish[0]))**2 for n,v in p.items()),
      "top1_correct":int(max(p,key=lambda n:(p[n],-n))==finish[0]),
      "top5_overlap":len(set(top5)&set(finish[:5])),
      "top5_exact":int(set(top5)==set(finish[:5]))
    }


def run(output=OUT):
    paths=sorted(ROOT.glob("*/*/v4_integrated.json"))
    history=History()
    scores=[];pending=[];invalid=[];already=set();cache={}
    for path in paths:
        try:
            saved,pred,p4,p3=confirm(path)
            rid=saved["race_id"]
            if rid in already:
                raise ValueError("Duplicate V4 race")
            already.add(rid)
            day=rid[:10]
            if day not in cache:
                try:cache[day]=history.day(day)
                except (ValueError,OSError,KeyError,TypeError) as e:
                    cache[day]={"records":[],"error":str(e)}
            order,status=verified_top5(cache[day],pred)
            item={"race_id":rid,"source":str(path),"outcome":status,
                  "prior_speed_coverage":saved["context_speed"]["coverage"]}
            if order is None:
                pending.append(item)
                continue
            v3_order=sorted((n for n in p3 if p3[n]>0),key=lambda n:(-p3[n],n))[:5]
            item["metrics"]={
               "v4_integrated":metrics(p4,saved["top5"]["numbers"],order),
               "v3_frozen":metrics(p3,v3_order,order)}
            scores.append(item)
        except (ValueError,OSError,KeyError,TypeError) as e:
            invalid.append({"source":str(path),"error":str(e)})
    fields=("log_loss","brier","top1_correct","top5_overlap","top5_exact")
    averages={label:{m:mean(r["metrics"][label][m] for r in scores) for m in fields}
              for label in ("v4_integrated","v3_frozen")} if scores else {}
    result={"version":"turf_lab_v4_multifeature_1",
            "status":"SINGLE_47_FEATURE_V4_PRESTART_COHORT",
            "research_only":True,"recommendations_allowed":False,
            "original_captures":len(paths),"verified_results":len(scores),
            "pending_results":len(pending),"invalid_inputs":len(invalid),
            "minimum_review_races":200,"validation_ready":len(scores)>=200,
            "mean":averages,"scored":scores,"pending":pending,"invalid":invalid,
            "roi":None,
            "limits":["2026 historical comparisons were non-independent; this cohort counts ONLY forecasts archived before actual race starts.",
                      "No ZEturf executable odds or betting settlement, so profitability cannot be claimed.",
                      "The speed and class/gains/form/R inputs are frozen before the race; the R market gate is not a certified bookmaker ROI."]}
    dump(output,result)
    print(json.dumps({k:result[k] for k in ("original_captures","verified_results","pending_results","invalid_inputs","mean")},indent=2))
    return result


if __name__=="__main__":
    run()
