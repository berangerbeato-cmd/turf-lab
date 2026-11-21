"""Paired, paper-only comparison of the SAME frozen V2 market correction
on (1) frozen sports V3 and (2) History Repair V1.1 probabilities.

The hybrid weights were FIT ON V3, not fitted or recalibrated on repaired V1.1.
The V1.1+V2 result is a transfer experiment, NOT a validated value signal.
"""
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from turf_lab.market_repair import predict
from turf_lab.operational_quotes import name

CORRECTION_FILE = Path("models/value_correction_v2/hybrid.json")
CORRECTION_LOCK = Path("models/value_correction_v2/frozen_before_test.json")
ACTIVE_FILE = Path("config/active_model.json")
CORRECTION_NAME = "value_correction_v2"
HISTORY_NAME = "history_repair_shadow_v1_1_nancy_alias"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp(value):
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("Naive timestamp not allowed")
    return t


def probabilities(values, numbers):
    p = {int(k): float(v) for k,v in values.items()}
    if set(p) != set(numbers) or any(not math.isfinite(v) or v <= 0 for v in p.values()):
        raise ValueError("Both sports probabilities must cover the full active field")
    if abs(sum(p.values())-1.0) > 1e-8:
        raise ValueError("Sports probabilities do not normalize")
    return p


def paired(prediction, sidecar, quotes, reference, *, now=None):
    """Run once at live quote time, or replay already archived prestart inputs.

    A late or newly computed history sidecar can only yield RETROSPECTIVE.
    Existing frozen V2's dated PRESTART comparison must be reproduced exactly.
    """
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None:
        raise ValueError("Now must have timezone")
    rid = prediction["race_id"]
    if prediction["primary_model"] != "available_history_v3":
        raise ValueError("Original sports primary mismatch")
    if quotes["race_id"] != rid or sidecar["race_id"] != rid or reference["race_id"] != rid:
        raise ValueError("Cross-race quote or history substitution")
    if quotes.get("verified") is not True or not quotes.get("source_evidence") or not quotes.get("operator"):
        raise ValueError("Screenshot quote provenance missing")
    if quotes.get("odds_format") != "DECIMAL_TOTAL_RETURN":
        raise ValueError("Unsupported price basis")

    lock = json.loads(CORRECTION_LOCK.read_text())
    active = json.loads(ACTIVE_FILE.read_text())
    if digest(ACTIVE_FILE) != lock["active_policy_sha256"]:
        raise ValueError("Frozen V2 active policy changed")
    if digest(CORRECTION_FILE) != lock["model_hashes"]["hybrid"]:
        raise ValueError("Frozen V2 hybrid weights changed")
    sport = prediction["models"]["available_history_v3"]
    if sport["model_sha256"] != active["files_sha256"][active["model_file"]]:
        raise ValueError("Active V3 model hash mismatch")
    selected = json.loads(Path(active["selection_file"]).read_text())
    if sport.get("temperature") != selected["temperatures"][active["variant"]]:
        raise ValueError("Active sports calibration mismatch")
    if sidecar.get("candidate") != HISTORY_NAME or sidecar.get("recommendations_allowed") is not False:
        raise ValueError("Wrong experimental history version")
    if sidecar.get("frozen_v3_model_sha256") != sport["model_sha256"]:
        raise ValueError("History sidecar frozen baseline differs")
    if sidecar["original_predicted_at"] != prediction["predicted_at"]:
        raise ValueError("History prediction timestamp differs")
    if sidecar["scheduled_start"] != prediction["scheduled_start"]:
        raise ValueError("History target start differs")

    start = stamp(prediction["scheduled_start"])
    predicted = stamp(prediction["predicted_at"])
    quote_at = stamp(quotes["observed_at"])
    reference_at = stamp(reference["calculated_at"])
    if not (predicted < start and quote_at < start and reference_at < start):
        raise ValueError("Original model or odds were not recorded before start")
    if not timedelta(0) <= start-quote_at <= timedelta(minutes=15):
        raise ValueError("Quote not within frozen V2 fifteen-minute window")
    if quote_at > reference_at or reference_at-quote_at > timedelta(minutes=5):
        raise ValueError("Reference V2 quote was not fresh when originally evaluated")
    ref = reference.get("value_shadow", {})
    if (ref.get("status") != "PRESTART_SHADOW" or ref.get("model") != CORRECTION_NAME
            or ref.get("model_sha256") != digest(CORRECTION_FILE)
            or ref.get("operator") != quotes["operator"]
            or ref.get("observed_at") != quotes["observed_at"]):
        raise ValueError("Missing original genuine prestart V2 comparison")

    participants = prediction["target_snapshot"]["participants"]
    if any(p["statut"] != "PARTANT" for p in participants):
        raise ValueError("Nonrunner or unsupported status")
    names = {p["numPmu"]:name(p["nom"]) for p in participants}
    nums = sorted(names)
    board = {}
    for q in quotes["quotes"]:
        n = q["number"]
        if n not in names or n in board or name(q["name"]) != names[n]:
            raise ValueError("Incomplete, duplicate or mismatched quote horse")
        c = q["decimal_odds"]
        if isinstance(c, bool) or not isinstance(c,(int,float)) or not math.isfinite(c) or c <= 1:
            raise ValueError("Invalid decimal quote")
        board[n] = float(c)
    if set(board) != set(nums):
        raise ValueError("The same complete odds board is mandatory")
    if sum(1.0/board[n] for n in nums) < 1 - 1e-9:
        raise ValueError("Underround quote board outside frozen V2 scope")

    base = probabilities(sport["probabilities"], nums)
    history_base = probabilities(sidecar["v3_baseline"]["probabilities"], nums)
    history_new = probabilities(sidecar["research_candidate"]["probabilities"], nums)
    if any(not math.isclose(base[n], history_base[n], rel_tol=0, abs_tol=1e-9) for n in nums):
        raise ValueError("V3 probabilities changed inside history sidecar")
    if sidecar.get("status") not in ("PRESTART_HISTORY_REPAIR_SHADOW",
                                    "RETROSPECTIVE_REPLAY_OF_ORIGINAL_PRESTART_EVIDENCE"):
        raise ValueError("Unknown history-sidecar provenance")
    original_source = sidecar.get("source_prediction")
    if not isinstance(original_source,str) or not original_source.endswith("/prediction.json"):
        raise ValueError("Source prediction provenance missing")

    odds = [board[n] for n in nums]
    weights = json.loads(CORRECTION_FILE.read_text())["weights"]
    old_hybrid = predict(odds, [base[n] for n in nums], weights)
    new_hybrid = predict(odds, [history_new[n] for n in nums], weights)
    normalized_market = [1.0/c / sum(1.0/x for x in odds) for c in odds]

    # This equality ensures the previous archived V3+V2 result was not
    # silently changed when connecting the new candidate.
    expected = {r["number"]:r for r in ref["rows"]}
    if set(expected) != set(nums) or any(
            not math.isclose(old_hybrid[i], expected[n]["probability"], abs_tol=1e-10, rel_tol=0)
            for i,n in enumerate(nums)):
        raise ValueError("Cannot reproduce original archived V2 correction")

    is_prestart = (
        sidecar["status"] == "PRESTART_HISTORY_REPAIR_SHADOW"
        and "shadow_calculated_at" in sidecar
        and predicted <= stamp(sidecar["shadow_calculated_at"]) < start
        and quote_at <= now < start
        and now-quote_at <= timedelta(minutes=5)
    )
    result = {
        "race_id":rid, "status":"PRESTART_PAIRED_ON_DEMAND" if is_prestart else "RETROSPECTIVE_PAIRED_REPLAY",
        "research_only":True, "recommendations_allowed":False, "selection":"USER_SUPPLIED_FULL_ODDS_BOARD",
        "independent_prospective_validation":False,
        "operator":quotes["operator"], "quote_source":quotes["source_evidence"],
        "observed_at":quotes["observed_at"], "original_v2_calculated_at":reference["calculated_at"],
        "paired_calculated_at":now.isoformat(), "scheduled_start":prediction["scheduled_start"],
        "history_model":HISTORY_NAME, "history_source_status":sidecar["status"],
        "history_runners_changed":sidecar["runners_changed_recent5"],
        "v3_sha256":sport["model_sha256"], "v2_sha256":digest(CORRECTION_FILE),
        "v2_coefficients_retrained":False, "v2_trained_with_repaired_history":False,
        "caveat":"V2 fitted on uncorrected V3, transferred without refit; no validated EV or ROI.",
        "rows":[{
            "number":n, "odds":board[n],
            "market_probability":normalized_market[i],
            "v3_sport_probability":base[n], "history_sport_probability":history_new[n],
            "v3_plus_v2_probability":old_hybrid[i],
            "history_plus_v2_probability":new_hybrid[i],
            "v3_plus_v2_indicative_ev":old_hybrid[i]*board[n]-1,
            "history_plus_v2_indicative_ev":new_hybrid[i]*board[n]-1,
            "delta_probability_pp":100*(new_hybrid[i]-old_hybrid[i])
        } for i,n in enumerate(nums)]
    }
    return result
