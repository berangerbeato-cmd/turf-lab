"""Independent forward-only scorecard for History Repair Shadow V1.1.

Read archived PRESTART sidecars as written. Never recompute model predictions
after knowing race outcomes, never substitute retrospectively generated replays.
"""
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from turf_lab.evidence import dump
from turf_lab.history_sync import History
from turf_lab.month_history import identity
# Deliberately stdlib-only: daily settlement must not depend on inference code.
CANDIDATE_VERSION = "history_repair_shadow_v1_1_nancy_alias"


def score(sidecar, finish):
    winner = finish[0]
    result = {}
    for version in ("v3_baseline", "research_candidate"):
        p = {int(n): float(v) for n, v in sidecar[version]["probabilities"].items()}
        order = sorted(p, key=lambda n: (-p[n], n))
        result[version] = {
            "winner_probability": p[winner],
            "log_loss": -math.log(max(1e-15, p[winner])),
            "brier": sum((v-int(n==winner))**2 for n,v in p.items()),
            "top1_correct": int(order[0]==winner),
            "top4_overlap": len(set(order[:4]) & set(finish[:4])),
            "top5_overlap": len(set(order[:5]) & set(finish[:5])),
            "top4_exact": int(set(order[:4]) == set(finish[:4])),
            "top5_exact": int(set(order[:5]) == set(finish[:5])),
        }
    return result


OUT = Path("reports/history_repair_shadow_v1/prospective_scores.json")
BEGIN = datetime.fromisoformat("2026-11-22T00:00:00+01:00")
MIN_RACES_FOR_REVIEW = 200
MIN_DAYS_FOR_INTERVALS = 10
METRICS = ("log_loss", "brier", "top1_correct", "top4_overlap",
           "top5_overlap", "top4_exact", "top5_exact")


def validate_sidecar(path):
    sidecar = json.loads(Path(path).read_text())
    if sidecar.get("status") != "PRESTART_HISTORY_REPAIR_SHADOW":
        raise ValueError("Not a real prestart sidecar")
    if sidecar.get("candidate") != CANDIDATE_VERSION:
        raise ValueError("Shadow model version mismatch")
    if sidecar.get("recommendations_allowed") is not False:
        raise ValueError("Not an isolated paper-only forecast")
    if (sidecar.get("is_independent_prospective_validation") is not True
            or sidecar.get("selection_rule") != "SCHEDULED_FIRST_TWO_FRENCH_HARNESS_WITH_40MIN_LEAD"):
        raise ValueError("Not a predeclared deterministic cohort capture")
    start = datetime.fromisoformat(sidecar["scheduled_start"])
    forecasted = datetime.fromisoformat(sidecar["shadow_calculated_at"])
    originally = datetime.fromisoformat(sidecar["original_predicted_at"])
    if any(s.tzinfo is None for s in (start, forecasted, originally)):
        raise ValueError("Naive timestamps forbidden")
    if forecasted < BEGIN or not (originally <= forecasted < start):
        raise ValueError("Shadow not in the independent prospective window")
    source = Path(sidecar["source_prediction"])
    if source.is_absolute() or source.parent != Path(path).parent:
        raise ValueError("Original forecast must be co-located with sidecar")
    frozen = json.loads(source.read_text())
    if frozen.get("race_id") != sidecar["race_id"] or frozen.get("status") != "PRESTART_RESEARCH":
        raise ValueError("Original forecast mismatch")
    if frozen.get("predicted_at") != sidecar["original_predicted_at"]:
        raise ValueError("Original prediction timestamp mismatch")
    if frozen.get("scheduled_start") != sidecar["scheduled_start"]:
        raise ValueError("Original scheduled start mismatch")
    active = frozen["models"]["available_history_v3"]
    if active["model_sha256"] != sidecar["frozen_v3_model_sha256"]:
        raise ValueError("Frozen V3 model mismatch")
    if sidecar["race_id"] != frozen["target_snapshot"]["race_id"]:
        raise ValueError("Target race mismatch")
    active_nums = {p["numPmu"] for p in frozen["target_snapshot"]["participants"]
                   if p["statut"] == "PARTANT"}
    all_nums = {p["numPmu"] for p in frozen["target_snapshot"]["participants"]}
    for key in ("v3_baseline", "research_candidate"):
        probs = {int(n): float(p) for n, p in sidecar[key]["probabilities"].items()}
        if set(probs) != all_nums or any(not math.isfinite(x) or x < 0 or x > 1 for x in probs.values()):
            raise ValueError("Invalid predicted probabilities")
        if abs(sum(probs.values()) - 1) > 1e-8 or any(probs[n] != 0 for n in all_nums-active_nums):
            raise ValueError("Probabilities not normalized over active field")
    base = {int(n):p for n,p in active["probabilities"].items()}
    prior = {int(n):p for n,p in sidecar["v3_baseline"]["probabilities"].items()}
    if any(abs(base[n]-prior[n]) > 1e-9 for n in all_nums):
        raise ValueError("Sidecar V3 baseline was changed")
    return sidecar, frozen


def verified_top5(history, prediction):
    source = prediction["target_snapshot"]
    rid = prediction["race_id"]
    record = next((r for r in history["records"] if r["race_id"] == rid), None)
    if record is None:
        return None, "AWAITING_VERIFIED_RESULT"
    if int(record["scheduled_start_ms"]) != int(datetime.fromisoformat(
            prediction["scheduled_start"]).timestamp()*1000):
        return None, "RACE_START_MISMATCH"
    old = {p["numPmu"]: p for p in source["participants"]}
    new = {p["numPmu"]: p for p in record["participants"]}
    if set(old) != set(new):
        return None, "FIELD_MISMATCH"
    for n in old:
        if old[n]["statut"] != new[n]["statut"] or identity(old[n]) != identity(new[n]):
            return None, "HORSE_IDENTITY_OR_STARTER_MISMATCH"
    selected = {}
    for n, runner in new.items():
        rank = runner.get("ordreArrivee")
        if isinstance(rank, int) and 1 <= rank <= 5:
            if rank in selected:
                return None, "DUPLICATE_FINISH"
            selected[rank] = n
    if set(selected) != {1,2,3,4,5}:
        return None, "NO_UNIQUE_OFFICIAL_TOP5"
    return [selected[i] for i in range(1,6)], "VERIFIED_OFFICIAL"


def confidence_by_day(rows, metric, repeats=600):
    days = defaultdict(list)
    for r in rows:
        v = (r["metrics"]["research_candidate"][metric] -
             r["metrics"]["v3_baseline"][metric])
        days[r["race_id"][:10]].append(v)
    if len(days) < MIN_DAYS_FOR_INTERVALS:
        return None
    rng = random.Random(20261122)
    keys = sorted(days)
    samples = []
    for _ in range(repeats):
        sample = [x for _ in keys for x in days[rng.choice(keys)]]
        samples.append(mean(sample))
    samples.sort()
    return [samples[int(repeats*.025)], samples[int(repeats*.975)-1]]


def run(source_paths=None, dest=OUT):
    if source_paths is None:
        # Validation must NOT mix user-selected races with the deterministic
        # scheduled sample. On-demand captures remain separately archived.
        source_paths = sorted(
            Path("reports/history_repair_shadow_v1/prospective_forecasts").glob(
                "*/*/history_repair_shadow_v1_1.json")
        )
    accepted = defaultdict(list)
    exclusions = []
    for p in source_paths:
        try:
            s, forecast = validate_sidecar(p)
            accepted[s["race_id"]].append((s["shadow_calculated_at"], str(p), s, forecast))
        except (OSError, ValueError, KeyError, TypeError) as e:
            exclusions.append({"file": str(p), "reason": str(e)})
    chosen = [sorted(v, key=lambda row: row[0])[0] for v in accepted.values()]
    cache = {}
    history = History()
    scored, pending = [], []
    for _, filename, sidecar, frozen in sorted(chosen):
        day = sidecar["race_id"][:10]
        if day not in cache:
            try:
                cache[day] = history.day(day)
            except (KeyError, TypeError, OSError, ValueError) as e:
                cache[day] = {"records": [], "error": str(e)}
        result, status = verified_top5(cache[day], frozen)
        rec = {"race_id": sidecar["race_id"], "sidecar": filename,
               "model": CANDIDATE_VERSION, "status": status,
               "runner_changes": sidecar["runners_changed_recent5"]}
        if result is None:
            pending.append(rec)
        else:
            rec.update({"finish_top5": result, "metrics": score(sidecar, result)})
            scored.append(rec)
    averages = {version:{m:mean(x["metrics"][version][m] for x in scored)
                  for m in METRICS} for version in ("v3_baseline","research_candidate")} if scored else {}
    differences = {m:{"candidate_minus_v3":mean(
       x["metrics"]["research_candidate"][m]-x["metrics"]["v3_baseline"][m] for x in scored),
       "clustered_95pct_ci":confidence_by_day(scored, m)} for m in METRICS} if scored else {}
    report = {"status":"PROSPECTIVE_SCORECARD",
              "version":CANDIDATE_VERSION, "recommendations_allowed":False,
              "prospective_start":"2026-11-22T00:00:00+01:00",
              "selection_cohort":"Deterministic scheduled first-two-races, no user-selected forecasts",
              "eligible_forecasts":len(chosen), "verified_results":len(scored),
              "pending_or_excluded_outcomes":len(pending),
              "candidate_changes":sum(x["runner_changes"]>0 for x in scored+pending),
              "validation_minimum_races":MIN_RACES_FOR_REVIEW,
              "validation_ready":len(scored)>=MIN_RACES_FOR_REVIEW,
              "means":averages, "paired_differences":differences,
              "scored":scored, "awaiting_outcomes":pending,
              "invalid_forecasts":exclusions,
              "limitations":[
                "Only predeclared scheduled cohort sidecars and independent verified race outcomes; no on-demand cherry-picking.",
                "This is a paired sample; formal promotion requires new independent test and reviewed gate.",
                "No historical PMU prices reused as executable bets; no ROI or automatic bets.",
                "Never replace the frozen original prediction with a retrospective replay."
              ]}
    dump(dest, report)
    return report


if __name__ == "__main__":
    import pprint
    report = run()
    pprint.pp({k:report[k] for k in (
        "eligible_forecasts","verified_results","pending_or_excluded_outcomes",
        "validation_ready","means","paired_differences")})
