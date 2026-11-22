"""SINGLE active Turf Lab V4: all five new components affect core outputs.

The 47 fitted features are unchanged. History Repair V2 checks the evidence
and quarantines conflicts. A fitted (possibly signed) DQ residual coefficient
corrects the 47f winning distribution *without blindly penalising DQ twice*.
Venue/start/distance temperature is APPLIED. When verified prices exist, the
R-conditioned market model AND the fitted odds-band correction are APPLIED.
The unordered conditional Top5 optimum is the actual single V4 Quinté/Top5
selection. Every calculation remains research-only; no advice to stake money.

The activation lock was fitted in pre-2026 data and points to the previously
immutable original 47f winner/ranker/market plus four new components.
"""
import json
import math
from pathlib import Path

from turf_lab.v4_full_inference import sha
from turf_lab.history_repair_v2 import verify_prestart_sidecar
from turf_lab.v4_next_research import (
    apply_context, predict_dq, adjust_market_bands, quinte_unordered)
from turf_lab.v4_next_inference import frozen as bundle_frozen

ROOT=Path("models/v4_active_activation")
LOCK=ROOT/"frozen_activation.json"
PARAMETERS=ROOT/"dq_residual.json"


def activated():
    frozen=json.loads(LOCK.read_text())
    if (frozen.get("status")!="ACTIVATED_SINGLE_V4_ALL_COMPONENTS"
            or frozen.get("recommendations_allowed") is not False
            or frozen.get("version")!="turf_lab_v4_fully_integrated_1"):
        raise ValueError("Complete V4 activation lock is absent or unsafe")
    if sha("models/v4_next_bundle/frozen_before_test.json")!=frozen["prior_bundle_lock_sha256"]:
        raise ValueError("Five-component source research bundle changed")
    if sha("models/v4_multifeature/frozen_before_test.json")!=frozen["v4_47f_lock_sha256"]:
        raise ValueError("Previous 47f V4 weights changed")
    if sha(PARAMETERS)!=frozen["dq_residual_sha256"]:
        raise ValueError("New DQ residual calibration changed")
    model=json.loads(PARAMETERS.read_text())
    if (model["training_period"]!=["2025-01-01","2025-06-30"]
            or model.get("method")!="AS_OF_LOG_DQ_SURVIVAL_RESIDUAL"
            or not -1<=model["coefficient"]<=1):
        raise ValueError("Invalid DQ weight or point-in-time fit")
    bundle,lock=bundle_frozen()
    return model,bundle,frozen


def residual_dq(sport,dq,coefficient):
    """A fitted residual log-survival tilt, NOT an arbitrary second DQ penalty."""
    if set(sport)!=set(dq) or not sport or not -1<=coefficient<=1:
        raise ValueError("Invalid DQ residual runner field or coefficient")
    weights={}
    for number,prior in sport.items():
        chance=dq[number]
        if (not math.isfinite(prior) or prior<0 or not math.isfinite(chance)
                or not 0<=chance<1):
            raise ValueError("Invalid sport or DQ probability")
        weights[number]=prior * math.exp(coefficient*math.log1p(-chance))
    total=sum(weights.values())
    if total<=0:
        raise ValueError("DQ integrated sports probability is empty")
    return {n:v/total for n,v in weights.items()}


def sport_v4(original,repair,runners,raw_sport):
    """Use History Repair V2 + DQ + context IN core winning distribution."""
    model,bundle,lock=activated()
    history_v2=verify_prestart_sidecar(repair,original)
    if history_v2["status"]=="QUARANTINED_UNCERTAINTY":
        # Do NOT invent a corrected performance or silently discard a runner.
        # The uncertainty is visible and stops any claim of a betting signal.
        pass
    active_rows=[r for r in runners if not r["non_runner"]]
    dq=predict_dq([{"race_id":original["race_id"],"runners":runners}],
                  bundle["disqualification"])[original["race_id"]]
    if set(dq)!={r["number"] for r in active_rows}:
        raise ValueError("DQ model runner field does not match active horses")
    context_p,key=apply_context(
        {n:raw_sport[n] for n in dq},
        original["target_snapshot"]["venue"],
        original["target_snapshot"]["start_type"],
        original["target_snapshot"]["distance_m"],bundle["race_context"])
    adjusted=residual_dq(context_p,dq,model["coefficient"])
    if abs(sum(adjusted.values())-1)>1e-9:
        raise ValueError("Integrated winner lost normalization")
    details={
        "history_repair_v2":history_v2,
        "disqualification":{
            "applied_to_winner":True,
            "model":"FROZEN_DQ_PRIOR47",
            "survival_residual_weight_fitted":model["coefficient"],
            "p_dq_by_runner":{str(n):v for n,v in dq.items()},
            "no_arbitrary_double_dq_multiplier":True},
        "race_context":{
            "applied_to_winner":True,
            "selected_group":key,
            "calibrated_probability_by_runner":{str(n):v for n,v in context_p.items()}},
        "market_odds_bands":{"applied_if_verified_quotes":True,
                             "applied_to_value_if_quotes":True},
        "activation_model_lock":lock["version"],
        "real_money_betting_allowed":False}
    return adjusted,details


def quotes_v4(base_market,odds):
    """Apply the odds-band bias to the final REAL V4 market probabilities."""
    model,bundle,lock=activated()
    result=adjust_market_bands(base_market,odds,bundle["odds_bands"])
    if set(result)!=set(odds) or abs(sum(result.values())-1)>1e-9:
        raise ValueError("V4 odds band adjustment failed")
    return result


def quintet_v4(runners,base_ranker):
    """Return one selected Top5: highest unordered conditional joint chance."""
    model,bundle,lock=activated()
    quinte=bundle["quinte"]
    result=quinte_unordered(
        {"runners":runners},base_ranker,
        limit=quinte["shortlist_limit"],
        alternatives=quinte["max_display_alternatives"])
    if (not 0<result["joint_probability_unordered"]<=1
            or result["recommended_stake_eur"] is not None):
        raise ValueError("Uncalibrated ordered/executable Quinté output")
    return result
