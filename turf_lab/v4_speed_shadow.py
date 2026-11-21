"""Forward-only V4 Speed shadow, invisible to the one public V4 interface.

Build the old V7 corrected-kilometre-time feature from verified official
*previous* starts collected as of the prediction, then apply the newly fitted
43-feature winner and five-stage ranking weights. No replacement of frozen V4.
No target results, no market prices, no simulated live ZEturf value.
"""
import json
import math
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
from scripts.train_v4_full import rank_top5
from turf_lab.evidence import dump
from turf_lab.pilot import probabilities
from turf_lab.v4_full_inference import repaired_frame, stamp, sha
from turf_lab.v4_speed_data import dated_speed_features, append_speed


ROOT=Path("models/v4_speed")
POLICY=Path("config/v4_speed_ablation.json")


def frozen():
    lock=json.loads((ROOT/"frozen_before_test.json").read_text())
    if (lock.get("status")!="FROZEN_BEFORE_REUSED_TEST" or
            lock.get("recommendations_allowed") is not False or
            lock.get("production_changed") is not False):
        raise ValueError("V4 Speed is not a locked research candidate")
    if sha(POLICY)!=lock["config_sha256"]:
        raise ValueError("Speed ablation policy changed")
    cfg=json.loads(POLICY.read_text())
    if sha(cfg["speed_policy_file"])!=lock["old_speed_protocol_sha256"]:
        raise ValueError("Old contextual speed policy changed")
    if sha("models/v4_full/frozen_before_test.json")!=lock["frozen_v4_sha256"]:
        raise ValueError("Original full V4 lock changed")
    models={}
    for name in ("winner","ranking"):
        p=ROOT/(name+".json")
        if sha(p)!=lock["three_new_model_hashes"][p.name]:
            raise ValueError("Speed shadow model weights changed: "+name)
        models[name]=json.loads(p.read_text())
    if models["winner"]["features"]!=43:
        raise ValueError("Speed challenger needs exactly 43 features")
    return models,lock,cfg


def predict(original_file, history_repair_file, history_records, now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Naive shadow timestamp")
    original_file=Path(original_file)
    history_repair_file=Path(history_repair_file)
    pred=json.loads(original_file.read_text())
    repair=json.loads(history_repair_file.read_text())
    if repair["source_prediction"] != original_file.as_posix():
        raise ValueError("History Repair sidecar points at another snapshot")
    start=stamp(pred["scheduled_start"])
    if not stamp(pred["predicted_at"])<now<start:
        raise ValueError("V4 Speed capture was not before race departure")
    if (repair["status"]!="PRESTART_HISTORY_REPAIR_SHADOW" or
            not stamp(repair["shadow_calculated_at"]) <= now):
        raise ValueError("History Repair was not a valid prestart capture")
    if not history_records or len({r["race_id"] for r in history_records})!=len(history_records):
        raise ValueError("Missing or duplicate official prior-race context")
    day=pred["race_id"][:10]
    if any(r["date"]>=day for r in history_records):
        raise ValueError("Target or future results introduced into speed history")
    repaired,uncertain=repaired_frame(pred,repair)
    target=pred["target_snapshot"]
    if target["race_id"]!=pred["race_id"] or target["date"]!=day:
        raise ValueError("Target race mismatch")
    nums={r["number"]:r["horse_id"] for r in repaired}
    from turf_lab.month_history import identity
    live={p["numPmu"]:identity(p) for p in target["participants"]}
    if nums!=live:
        raise ValueError("Target runner pedigree mismatch")
    objects,lock,cfg=frozen()
    context=json.loads(Path(cfg["speed_policy_file"]).read_text())
    all_records=list(history_records)+[target]
    timed,diagnostic=dated_speed_features(all_records,context)
    enriched,cov=append_speed([{"race_id":pred["race_id"],"runners":repaired}],
                              {pred["race_id"]:timed[pred["race_id"]]})
    x=enriched[0]
    winner=objects["winner"]
    sport=probabilities(x,winner["model"])
    t=float(winner["temperature"])
    if not math.isfinite(t) or t<=0:
        raise ValueError("Bad retrained speed calibration")
    scaled={n:max(0,v)**(1/t) for n,v in sport.items()}
    total=sum(scaled.values())
    p={n:v/total for n,v in scaled.items()}
    ranked=sorted((n for n in p if p[n]>0),key=lambda n:(-p[n],n))
    top5=rank_top5(x,objects["ranking"])
    if len(ranked)<6 or len(set(top5))!=5:
        raise ValueError("Invalid prestart speed field")
    return {
        "version":lock["version"],
        "status":"PRESTART_SHADOW_RESEARCH",
        "source":"DETERMINISTIC_SCHEDULED_COHORT_ONLY",
        "generated_at":now.isoformat(),
        "race_id":pred["race_id"],
        "scheduled_start":pred["scheduled_start"],
        "research_only":True,"recommendations_allowed":False,"decision":"NO BET",
        "top1":ranked[0],"top5":top5,
        "win_probabilities":{str(k):v for k,v in p.items()},
        "speed_in_target_field":cov,
        "speed_input_by_runner":{
            str(n):{"context_residual":entry[1],"prior_races_used":entry[2]}
            for n,entry in sorted(timed[pred["race_id"]].items())
        },
        "speed_protocol_sha256":lock["old_speed_protocol_sha256"],
        "history_repair_unresolved":uncertain,
        "history_records_before_target":len(history_records),
        "prior_history_last_day":max(r["date"] for r in history_records),
        "speed_model_hashes":lock["three_new_model_hashes"],
        "reference_models_unchanged":True,
        "evidence":{"source_prediction":original_file.as_posix(),
                    "history_repair":history_repair_file.as_posix()},
        "limits":["No future or target outcomes used in this forecast.",
                  "Historical speed completeness and parity require independent checks.",
                  "This is an unpromoted research shadow, not the user-facing V4.",
                  "No ZEturf value or real-money wager is implied."]
    }


def record(original_file,history_repair_file,history_records,output=None,now=None):
    report=predict(original_file,history_repair_file,history_records,now)
    dest=Path(output) if output else Path(original_file).parent/"v4_speed_shadow.json"
    if dest.exists() and json.loads(dest.read_text())!=report:
        raise ValueError("Immutable original prestart speed shadow would be changed")
    dump(dest,report)
    return report
