"""The ONE Turf Lab V4 with all requested additions in ONE coherent inference.

Use newly retrained 47-feature winner, 5 conditional rankers and a 3-param
R-conditioned odds corrector. The 43-feature V4 reference remains archived.
No silent fallback to old models, no fabricated past career euros, no betting.
"""
import json
import math
from datetime import datetime,timezone
from pathlib import Path

from turf_lab.evidence import dump
from turf_lab.v4_active_inference import frame as verified_speed_frame
from turf_lab.v4_full_inference import stamp,verified_board,sha
from turf_lab.v4_multi_features import VERSION as FEATURES_VERSION,WEIGHTS
from turf_lab.v4_reliability_market import probs as market_probs
from turf_lab.pilot import probabilities
from scripts.train_v4_full import rank_top5

ROOT=Path("models/v4_multifeature")
POLICY=Path("config/v4_multifeature_training.json")


def frozen():
    lock=json.loads((ROOT/"frozen_before_test.json").read_text())
    if (lock["version"]!="turf_lab_v4_multifeature_1"
            or lock["status"]!="FROZEN_BEFORE_REUSED_2026_EVALUATION"
            or lock["recommendations_allowed"] is not False):
        raise ValueError("No approved 47 feature research lock")
    if sha(POLICY)!=lock["protocol_sha256"]:
        raise ValueError("Full V4 47 input/training policy changed")
    if sha("models/v4_speed/frozen_before_test.json")!=lock["prior_speed_lock_sha256"]:
        raise ValueError("Frozen prior 43-feature V4 source changed")
    if sha("turf_lab/v4_multi_features.py")!=lock["four_feature_source_sha256"]:
        raise ValueError("Class/form/R source code changed after training")
    if sha("turf_lab/v4_reliability_market.py")!=lock["reliability_market_code_sha256"]:
        raise ValueError("R-conditioned odds code changed after training")
    x={}
    for key in ("winner","ranking","market"):
        path=ROOT/(key+".json")
        if sha(path)!=lock["three_new_models_sha256"][path.name]:
            raise ValueError("47 feature "+key+" coefficients changed")
        x[key]=json.loads(path.read_text())
    if (x["winner"]["features"]!=47 or len(x["ranking"]["coefficients"])!=5
            or len(x["market"]["weights"])!=3):
        raise ValueError("Incomplete new jointly trained V4 components")
    return x,lock


def enhanced_frame(original,repair,speed,aux,source_path,now):
    rows,unresolved,active,names=verified_speed_frame(original,repair,speed,source_path,now)
    start=stamp(original["scheduled_start"])
    captured=stamp(aux["captured_at"])
    if not stamp(original["predicted_at"])<=captured<=now<start:
        raise ValueError("V4 extended inputs were not captured prestart")
    if (aux.get("version")!=FEATURES_VERSION
            or aux.get("race_id")!=original["race_id"]
            or aux.get("target_date")!=original["race_id"][:10]
            or aux.get("same_day_result_used") is not False
            or aux.get("contains_target_outcome") is not False
            or aux.get("last_prior_day","9999")>=aux["target_date"]
            or aux.get("prior_races",0)<1
            or aux.get("form_weights_newest_first")!=list(WEIGHTS)
            or aux.get("reliability_is_data_completeness_not_a_probability") is not True
            or len(aux.get("source_hash",""))!=64):
        raise ValueError("Extended career gains, class, form, R history provenance invalid")
    by={r["number"]:r for r in rows}
    raw=aux["per_runner"]
    if set(raw)!={str(n) for n in by}:
        raise ValueError("The class/gains/form/R starter list changed")
    enhanced=[]
    indices={}
    for row in rows:
        n=row["number"];details=raw[str(n)]
        if details["horse_id"]!=row["horse_id"] or len(row["features"])!=43:
            raise ValueError("Class/form/R feature horse identity/width mismatch")
        money=details["relative_career_gains_prior"]
        class_proxy=details["relative_class_proxy"]
        weighted=details["weighted_recent_form"]
        known=details["known_form_weight"]
        if not isinstance(known,(int,float)) or isinstance(known,bool) or not 0<=known<=1:
            raise ValueError("Invalid weighted form source completeness")
        for val in (money,class_proxy,weighted):
            if val is not None and (isinstance(val,bool)
                    or not isinstance(val,(int,float)) or not math.isfinite(val)):
                raise ValueError("Historical gain/class/weighted form nonfinite")
        if ((money is not None)!=details["gain_is_from_previous_dated_race"] or
                details["class_is_verified_euros"] is not False):
            raise ValueError("Career gain source claimed to be current/preverified euros")
        coverage=row["features"][4]
        if not isinstance(coverage,(int,float)) or not 0<=coverage<=1:
            raise ValueError("History Repair recent starts coverage invalid")
        R=.4*coverage+.3*known+.2*float(row["features"][42] is not None)+.1*float(money is not None)
        if not 0<=R<=1.00000001:
            raise ValueError("Reliability R data-completeness score invalid")
        features=list(row["features"])+[money,class_proxy,weighted,R]
        enhanced.append(dict(row,features=features))
        indices[n]={"relative_career_gains_prior":money,
                    "relative_class_proxy":class_proxy,
                    "weighted_recent_form":weighted,
                    "reliability_R":R}
    return enhanced,unresolved,active,names,indices


def run(prediction_file,repair_file,speed_file,aux_file,quotes_file=None,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Naive V4 prediction timestamp forbidden")
    prediction_file=Path(prediction_file)
    original=json.loads(prediction_file.read_text())
    repair=json.loads(Path(repair_file).read_text())
    speed=json.loads(Path(speed_file).read_text())
    aux=json.loads(Path(aux_file).read_text())
    if original["status"]!="PRESTART_RESEARCH" or original.get("recommendations_allowed") is not False:
        raise ValueError("Original frozen horse input invalid")
    models,lock=frozen()
    if speed.get("speed_protocol_sha256")!=lock["old_speed_sha256"]:
        raise ValueError("Speed source not the previously trained protocol")
    runners,unresolved,active,names,indices=enhanced_frame(
        original,repair,speed,aux,prediction_file,now)
    raw=probabilities({"runners":runners},models["winner"]["model"])
    temperature=models["winner"]["temperature"]
    if not math.isfinite(temperature) or temperature<=0:
        raise ValueError("Invalid retrained 47-feature calibration")
    vals={n:max(0,p)**(1/temperature) for n,p in raw.items()}
    denom=sum(vals.values())
    if denom<=0:
        raise ValueError("Null V4 win distribution")
    sports={n:v/denom for n,v in vals.items()}
    top5=rank_top5({"runners":runners},models["ranking"])
    if len(top5)!=5 or len(set(top5))!=5 or not set(top5)<=active:
        raise ValueError("Invalid 47-feature Top5")
    odds=None;state="NO_VERIFIED_PRESTART_QUOTES";operator=None
    winner=sports
    if quotes_file is not None:
        quotes=json.loads(Path(quotes_file).read_text())
        odds,state=verified_board(original,quotes,now,now)
        if state!="PRESTART":
            raise ValueError("No timely executable ZEturf odds reference")
        numbers=sorted(odds)
        corrected=market_probs([odds[n] for n in numbers],
                [sports[n] for n in numbers],
                [indices[n]["reliability_R"] for n in numbers],
                models["market"]["weights"])
        winner=dict(zip(numbers,corrected))
        operator=quotes["operator"]
    ranked=sorted(active,key=lambda n:(-winner[n],n))
    ev=[]
    if odds:
        for n in ranked[:4]:
            value=winner[n]*odds[n]-1
            if value>=.10:
                ev.append({"number":n,"indicative_ev":value})
    return {
      "version":"turf_lab_v4_multifeature_1",
      "model":"TURF_LAB_V4",
      "status":"HISTORY_INCOMPLETE_NO_BET" if unresolved else "RESEARCH_NO_BET",
      "freshness":"PRESTART_RESEARCH",
      "generated_at":now.isoformat(),
      "race_id":original["race_id"],
      "decision":"NO BET","recommendations_allowed":False,
      "gagnant":{"number":ranked[0],"name":names[ranked[0]],
                 "probability":winner[ranked[0]],
                 "basis":"V4_47F_WINNER" if odds is None else "V4_47F_R_CALIBRATED_MARKET"},
      "top5":{"numbers":top5,"names":[names[n] for n in top5],
              "method":"V4_47F_RETRAINED_5_STAGE"},
      "value":{"status":state,"operator":operator,
               "paper_candidates_not_bets":ev,
               "minimum_indicative_ev":.10},
      "ze5":{"numbers":top5,"status":"RESEARCH_ONLY_NO_STAKE","stake_eur":None},
      "relative_class_and_gains":{"historical_money_is_prior_only":True,
                "historical_money_original_capture_proven":False,
                "runners_with_prior_career_gains":sum(v["relative_career_gains_prior"] is not None for
                                                     n,v in indices.items() if n in active)},
      "weighted_recent_form":{"weights":list(WEIGHTS),
                              "runners_with_data":sum(v["weighted_recent_form"] is not None for
                                                       n,v in indices.items() if n in active)},
      "reliability_R":{"index_is_completeness_not_win_probability":True,
                       "per_runner":{str(n):v["reliability_R"] for n,v in indices.items()},
                       "market_R_gate_fitted":True},
      "history_repair":{"required":True,"unresolved":unresolved,
                        "runners_updated":repair["runners_changed_recent5"]},
      "context_speed":{"required":True,"dimension":47,
                       "coverage":sum(r["features"][42] is not None for r in runners if not r["non_runner"])},
      "model_sha256":lock["three_new_models_sha256"],
      "evidence":{"original":prediction_file.as_posix(),"history_repair":str(repair_file),
                  "speed_context":str(speed_file),"aux_context":str(aux_file),
                  "quotes":str(quotes_file) if quotes_file else None},
      "limits":["All four feature additions are active; previous 43-feature V4 remains frozen as reference.",
                "Historical career euros were retrieved retrospectively; use only lagged older race snapshots.",
                "2026 historical testing already seen; no independent prospective validation or real ROI.",
                "Real-money betting policy remains suspended."]
    }


def record(prediction_file,repair_file,speed_file,aux_file,quotes_file=None,output=None,now=None):
    outcome=run(prediction_file,repair_file,speed_file,aux_file,quotes_file,now)
    if now is None:
        finish=datetime.now(timezone.utc)
        start=stamp(json.loads(Path(prediction_file).read_text())["scheduled_start"])
        if finish>=start:
            raise ValueError("V4 finished after departure; late output is not prestart")
        outcome["generated_at"]=finish.isoformat()
    output=Path(output) if output is not None else Path(prediction_file).parent/"v4_integrated.json"
    if output.exists() and json.loads(output.read_text())!=outcome:
        raise ValueError("Refusing to rewrite frozen prestart V4 forecast")
    dump(output,outcome)
    return outcome
