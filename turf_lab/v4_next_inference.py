"""All five V4 research improvements IN THE SAME user-facing output.

The 47-feature V4 winning probabilities remain the single source of betting
probabilities until extra adjustments pass independent forward validation.
All other improvements are exposed as clearly marked paper diagnostics:
history V2, separate DQ risk, conditional-context alternative, odds-band
calibration alternative, coherent no-order Quinté subset likelihood.
"""
import json
from pathlib import Path

from turf_lab.history_repair_v2 import verify_prestart_sidecar
from turf_lab.v4_full_inference import sha
from turf_lab.v4_next_research import (predict_dq,apply_context,
                                       adjust_market_bands,quinte_unordered)
from turf_lab.v4_multifeature_inference import frozen as base_frozen

ROOT=Path("models/v4_next_bundle")
PROTOCOL=Path("config/v4_next_bundle.json")


def frozen():
    lock=json.loads((ROOT/"frozen_before_test.json").read_text())
    if (lock.get("status")!="FROZEN_BEFORE_REUSED_TEST"
            or lock.get("recommendations_allowed") is not False
            or lock.get("main_v4_unchanged") is not True):
        raise ValueError("Research bundle training is not frozen")
    if sha(PROTOCOL)!=lock["protocol_sha256"]:
        raise ValueError("Changed five-part protocol")
    if sha("models/v4_multifeature/frozen_before_test.json")!=lock["base_lock_sha256"]:
        raise ValueError("Fitted 47-feature V4 model changed")
    models={}
    for name in ("disqualification","race_context","odds_bands","quinte"):
        path=ROOT/(name+".json")
        if sha(path)!=lock["models_sha256"][path.name]:
            raise ValueError("New V4 component model file was altered: "+name)
        models[name]=json.loads(path.read_text())
    if models["quinte"]["model_sha256"]!=base_frozen()[1]["three_new_models_sha256"]["ranking.json"]:
        raise ValueError("Quinté and V4 position-specific model are not the same")
    return models,lock


def augment(report, original, repair, rows, sports, calibrated=None, odds=None):
    """Add the five parts to ONE previously calculated original V4 report.

    No separate winner prediction or extra real-money betting recommendations.
    """
    models,lock=frozen()
    if report.get("version")!="turf_lab_v4_multifeature_1":
        raise ValueError("Wrong base V4 version for five-part update")
    if report["race_id"]!=original["race_id"]!=repair["race_id"]:
        raise ValueError("Cross-race add-on forbidden")
    if report.get("decision")!="NO BET" or report.get("recommendations_allowed") is not False:
        raise ValueError("Old risk suspension must be preserved")
    if len(rows)!=len(original["target_snapshot"]["participants"]):
        raise ValueError("V4 contextual source horse field changed")
    if any(len(r["features"])!=47 for r in rows):
        raise ValueError("V4 add-on requires 47 recent verified feature inputs")
    names={r["number"]:r["horse_id"] for r in rows}
    if len(names)!=len(rows) or set(sports)!=set(names):
        raise ValueError("V4 add-on probability field mismatch")
    dq= predict_dq([{"race_id":report["race_id"],"runners":rows}],
                   models["disqualification"])[report["race_id"]]
    # Calibrated conditional winner proxy is NOT automatically multiplied by
    # (1 - pDQ). Existing winner already has DQ history in its features.
    context_p,key=apply_context(
        sports,original["target_snapshot"]["venue"],
        original["target_snapshot"]["start_type"],
        original["target_snapshot"]["distance_m"],models["race_context"])
    ranker=base_frozen()[0]["ranking"]
    q=quinte_unordered({"runners":rows},ranker,
        limit=models["quinte"]["shortlist_limit"],
        alternatives=models["quinte"]["max_display_alternatives"])
    # Research market bias is never silently substituted for the frozen
    # risk-weighted V4 probabilities in the public gagnant/value slots.
    market_result={"status":"NO_VERIFIED_QUOTES","paper_only":True}
    if calibrated is not None:
        if odds is None or set(calibrated)!=set(odds):
            raise ValueError("Cannot study odds band without complete price field")
        paper=adjust_market_bands(calibrated,odds,models["odds_bands"])
        market_result={
            "status":"RESEARCH_COMPARISON_NOT_APPROVED",
            "paper_only":True,
            "under_over_correction_by_price_band":True,
            "hypothetical_top1":max(paper,key=lambda n:(paper[n],-n)),
            "paper_adjusted_probability_by_runner":{str(n):v for n,v in paper.items()},
            "do_not_use_for_real_bet":True}
    safe={
        "version":lock["version"],
        "history_repair_v2":verify_prestart_sidecar(repair,original),
        "disqualification":{
            "status":"FITTED_INDEPENDENT_2022_2024",
            "probability_by_runner":{str(n):v for n,v in dq.items()},
            "not_multiplied_into_winner_twice":True,
            "calibration_not_verified_prospectively":True},
        "race_specialization":{
            "status":"SHRUNK_TEMPERATURE_RESEARCH_ONLY",
            "selected_group":key,
            "research_probability_by_runner":{str(n):v for n,v in context_p.items()},
            "main_winner_unchanged":True},
        "odds_bias":market_result,
        "quinte_unordered":{
            **q,
            "not_a_real_bet":True,
            "no_executable_ZEturf_price":True},
        "limitations":[
            "History Repair V2 never overwrites a contested personal record",
            "DQ is a separately calibrated risk, not a second penalty on win chances",
            "Context and odds band corrections need independent prestart validation",
            "Quinté probability comes from one coherent 5-position joint model",
            "No ZEturf ROI or permissible betting stake established"]}
    report["research_improvements"]=safe
    report["ze5"]={
        "numbers":q["selection"],
        "probability_unordered_paper":q["joint_probability_unordered"],
        "ranking_selection":report["top5"]["numbers"],
        "status":"UNVALIDATED_JOINT_PROBABILITY_NO_BET",
        "stake_eur":None}
    report["limits"].append("Five new research components integrated with unchanged validated-status V4 sporting probabilities.")
    return report
