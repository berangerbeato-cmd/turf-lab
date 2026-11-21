"""Turf Lab V4, one experimental public-facing result.

This is a single validated-input PIPELINE, not yet a jointly trained model.
History Repair is required. No implicit fallback to V3 or real wagering.
"""
import copy
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from scripts.stage_ranking_shadow import frozen, predict
from turf_lab.evidence import dump

CFG = Path("config/v4_unified.json")


def moment(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Timezone required")
    return stamp


def distribution(raw, all_nums, active):
    result = {int(n): float(p) for n, p in raw.items()}
    if (set(result) != all_nums or any(not math.isfinite(p) or p < 0 or p > 1 for p in result.values())
            or abs(sum(result.values())-1) > 1e-8
            or any(result[n] != 0 for n in all_nums-active)):
        raise ValueError("Invalid distribution or starter field")
    return result


def prepare_features(source, repair):
    runners = copy.deepcopy(source["models"]["available_history_v3"]["runners"])
    by_num = {r["number"]: r for r in runners}
    audits = repair["runner_audit"]
    if len(audits) != len(by_num) or {a["number"] for a in audits} != set(by_num):
        raise ValueError("Individual history check did not cover entire field")
    uncertain = []
    for item in audits:
        row = by_num[item["number"]]
        state = item["status"]
        if state == "UPDATED":
            if row["features"][:5] != item["old_recent5"] or len(item["candidate_recent5"]) != 5:
                raise ValueError("Repair changes frozen original features")
            row["features"][:5] = item["candidate_recent5"]
        elif state == "UNCHANGED":
            if row["features"][:5] != item["old_recent5"] or row["features"][:5] != item["candidate_recent5"]:
                raise ValueError("False unchanged history")
        elif state == "NON_RUNNER":
            if not row["non_runner"]:
                raise ValueError("Runner incorrectly marked non-runner")
        else:
            uncertain.append({"number":item["number"],"reason":state})
    return runners, uncertain


def assemble(prediction_file, repair_file, pair_file=None, quote_file=None, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Naive time")
    prediction_file, repair_file = Path(prediction_file), Path(repair_file)
    pred = json.loads(prediction_file.read_text())
    repair = json.loads(repair_file.read_text())
    cfg = json.loads(CFG.read_text())
    if cfg["status"] != "RESEARCH_PAPER_ONLY" or cfg["recommendations_allowed"] is not False:
        raise ValueError("Unapproved V4 configuration")
    if pred["status"] != "PRESTART_RESEARCH" or pred["primary_model"] != "available_history_v3":
        raise ValueError("Require original frozen V3 snapshot")
    if (repair["race_id"] != pred["race_id"] or repair["candidate"] != cfg["history_repair_required"]
            or repair["source_prediction"] != prediction_file.as_posix()
            or repair["original_predicted_at"] != pred["predicted_at"]
            or repair["scheduled_start"] != pred["scheduled_start"]):
        raise ValueError("Missing or incorrect required History Repair")
    start, predicted = moment(pred["scheduled_start"]), moment(pred["predicted_at"])
    if predicted >= start:
        raise ValueError("Original sports snapshot was late")
    if repair["status"] not in ("PRESTART_HISTORY_REPAIR_SHADOW",
                                "RETROSPECTIVE_REPLAY_OF_ORIGINAL_PRESTART_EVIDENCE"):
        raise ValueError("Invalid history origin")
    if repair["status"] == "PRESTART_HISTORY_REPAIR_SHADOW":
        if not predicted <= moment(repair["shadow_calculated_at"]) < start:
            raise ValueError("Late history repair")
    raw = pred["models"]["available_history_v3"]
    if repair["frozen_v3_model_sha256"] != raw["model_sha256"]:
        raise ValueError("Frozen sports SHA mismatch")
    parts = pred["target_snapshot"]["participants"]
    numbers = {p["numPmu"] for p in parts}
    active = {p["numPmu"] for p in parts if p["statut"] == "PARTANT"}
    if len(active) < 6 or any(p["statut"] not in ("PARTANT","NON_PARTANT") for p in parts):
        raise ValueError("Unsupported field or fewer than six runners")
    original = distribution(raw["probabilities"], numbers, active)
    baseline = distribution(repair["v3_baseline"]["probabilities"], numbers, active)
    repaired = distribution(repair["research_candidate"]["probabilities"], numbers, active)
    if any(abs(original[n]-baseline[n]) > 1e-9 for n in numbers):
        raise ValueError("Frozen V3 baseline altered")
    patched, uncertain = prepare_features(pred, repair)
    ranking_model, hashes = frozen()
    selected = predict({"runners":patched,"probabilities":repaired},ranking_model)
    top5 = selected["5"]["stage_raw"]["selection"]
    if len(top5) != 5 or len(set(top5)) != 5 or not set(top5) <= active:
        raise ValueError("No valid Top 5")
    win = dict(repaired)
    basis = "REPAIRED_SPORT_UNCALIBRATED"
    value_state = "NO_VERIFIED_COTES"
    paper = []
    operator = None
    if pair_file is not None:
        if quote_file is None:
            raise ValueError("Missing odds file for corrected value")
        pair = json.loads(Path(pair_file).read_text())
        quotes = json.loads(Path(quote_file).read_text())
        if (pair["race_id"] != pred["race_id"] or quotes["race_id"] != pred["race_id"]
                or pair["history_model"] != repair["candidate"]
                or pair["history_source_status"] != repair["status"]
                or pair["v3_sha256"] != raw["model_sha256"]):
            raise ValueError("Unrelated market sidecar")
        if pair["status"] not in ("PRESTART_PAIRED_ON_DEMAND","RETROSPECTIVE_PAIRED_REPLAY"):
            raise ValueError("Unknown value-sidecar status")
        paired_at = moment(pair["paired_calculated_at"])
        if pair["status"] == "PRESTART_PAIRED_ON_DEMAND" and not predicted <= paired_at < start:
            raise ValueError("Value was not captured prestart")
        from turf_lab.value_history_pair import paired
        ref = json.loads((prediction_file.parent / "comparison.json").read_text())
        reproduced = paired(pred,repair,quotes,ref,now=paired_at)
        if reproduced["status"] != pair["status"]:
            raise ValueError("Value original timing not reproducible")
        previous = {r["number"]:r for r in pair["rows"]}
        checked = {r["number"]:r for r in reproduced["rows"]}
        if set(previous) != numbers or any(
            abs(previous[n]["history_plus_v2_probability"] -
                checked[n]["history_plus_v2_probability"]) > 1e-10 for n in numbers):
            raise ValueError("Frozen V2 pair changed")
        win = {n:checked[n]["history_plus_v2_probability"] for n in numbers}
        if any(not math.isfinite(v) or v <= 0 for n,v in win.items() if n in active):
            raise ValueError("Invalid corrected value")
        rank4 = sorted(active,key=lambda n:(-win[n],n))[:4]
        min_ev = cfg["simple_gagnant"]["minimum_indicative_ev"]
        for n in rank4:
            ev = checked[n]["history_plus_v2_indicative_ev"]
            if ev >= min_ev:
                paper.append({"number":n,"indicative_ev":ev})
        value_state = pair["status"]
        basis = "REPAIRED_SPORT_PLUS_FROZEN_V2_COTES_TRANSFER"
        operator = pair["operator"]
    winner = max(active,key=lambda n:(win[n],-n))
    names = {p["numPmu"]:p["nom"] for p in parts}
    historical = (now >= start or repair["status"] != "PRESTART_HISTORY_REPAIR_SHADOW"
                  or value_state == "RETROSPECTIVE_PAIRED_REPLAY")
    return {
        "version":cfg["version"],"race_id":pred["race_id"],
        "status":"HISTORY_INCOMPLETE_NO_BET" if uncertain else "RESEARCH_ONLY_NO_BET",
        "freshness":"RETROSPECTIVE" if historical else "PRESTART_RESEARCH",
        "recommendations_allowed":False,"decision":"NO BET",
        "gagnant":{"number":winner,"name":names[winner],"probability":win[winner],"basis":basis},
        "top5":{"numbers":top5,"names":[names[n] for n in top5],
                "method":"STAGE_V2_REPAIRED_FEATURES_UNVALIDATED"},
        "value":{"status":value_state,"operator":operator,
                 "paper_candidates_not_bets":paper,"min_ev":cfg["simple_gagnant"]["minimum_indicative_ev"]},
        "ze5":{"numbers":top5,"status":"PAPER_UNVALIDATED_OFFER_NOT_CONFIRMED",
               "recommended_stake_eur":None},
        "history_repair":{"required":True,"runners_updated":repair["runners_changed_recent5"],
                          "unresolved":uncertain,"quality":"INCOMPLETE" if uncertain else "CHECKED"},
        "evidence":{"sports":prediction_file.as_posix(),"repair":repair_file.as_posix(),
                    "market_pair":str(pair_file) if pair_file else None,
                    "v3_sha256":raw["model_sha256"],"ranking_sha256":hashes["stage"]},
        "limitations":["One interface, not a new jointly fitted model.",
                       "V2 Cotes and ranking are not calibrated on repaired features.",
                       "Historical uncertainty and missing odds are shown, never hidden.",
                       "Real-money betting policy remains suspended."]
    }


def record(prediction_file, repair_file, pair_file=None, quote_file=None, output=None, now=None):
    result = assemble(prediction_file,repair_file,pair_file,quote_file,now)
    path = Path(output) if output else Path(prediction_file).parent / "v4_unified.json"
    if path.exists() and json.loads(path.read_text()) != result:
        raise ValueError("V4 stored forecast is immutable")
    dump(path,result)
    return result
