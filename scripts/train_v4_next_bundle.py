"""One-batch V4 development: history V2, DQ risk, race context, odds-bands, ZE5.

All research candidates are fitted/defined BEFORE 2026 evaluation. The 47
feature source and all prior V4 weights are immutable, no betting promotion.
2026 was already inspected by old experiments. The only truly independent
validation must be later original prestart snapshots.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

from scripts.train_available_history_v3 import sources
from scripts.train_market_repair import dataset as market_dataset
from scripts.train_v4_full import read,save,sha
from turf_lab.available_history_research import available_features
from turf_lab.full_history_evaluation import chronological,temper,score
from turf_lab.pilot import active,probabilities
from turf_lab.ranking_research import finish
from turf_lab.v4_retrain_data import reconcile,v4_rows,load_paired_cohort
from turf_lab.v4_speed_data import raw_pace_records,dated_speed_features,append_speed
from turf_lab.v4_multi_features import bring_historical_money,derive,attach
from turf_lab.v4_multifeature_inference import frozen
from turf_lab.v4_reliability_market import probs as market_probs
from turf_lab.v4_next_research import (
    fit_dq,predict_dq,dq_metrics,fit_context_temperatures,apply_context,
    market_band_fit,adjust_market_bands,quinte_unordered)
from turf_lab.history_repair_v2 import reconcile_v2
from turf_lab.evidence import dump

ROOT=Path("reports/v4_next_bundle")
MODELS=Path("models/v4_next_bundle")
PROTOCOL=Path("config/v4_next_bundle.json")


def mean_ll(rows,ps):
    if not rows:raise ValueError("Empty score input")
    values=[]
    hit=0
    for row,p in zip(rows,ps):
        winner=next(r["number"] for r in active(row) if r["won"])
        values.append(-math.log(max(1e-15,p[winner])))
        if max(p,key=lambda n:(p[n],-n))==winner:hit+=1
    return {"races":len(rows),"log_loss":mean(values),"top1":hit/len(rows)}


def main():
    if (MODELS/"frozen_before_test.json").exists() or (ROOT/"evaluation.json").exists():
        raise ValueError("V4 next bundle frozen: refuse post-hoc re-fitting")
    cfg=read(PROTOCOL)
    if cfg["status"]!="RESEARCH_NO_BET" or cfg["recommendations_allowed"] is not False:
        raise ValueError("Unauthorized training scope")
    models,base_lock=frozen()
    original_eval=read("reports/v4_multifeature/evaluation.json")
    if base_lock["three_new_models_sha256"]!={
        name:sha(Path("models/v4_multifeature")/name) for name in
        ("winner.json","ranking.json","market.json")}:
        raise ValueError("Active V4 weights unexpectedly changed")
    manifest=read("reports/full_history/datasets/manifest.json")
    frames={}
    for split,source in manifest["splits"].items():
        if sha(source["file"])!=source["sha256"]:raise ValueError("Historical training SHA mismatch")
        with gzip.open(source["file"],"rt") as f:
            frames[split]=[json.loads(s) for s in f]
        if len(frames[split])!=source["races"]:
            raise ValueError("Historical training split count mismatch")
    chronological(frames["train"],frames["validation"],frames["test"])
    print("Verified archived targets",sum(len(v) for v in frames.values()),flush=True)
    records,source_shas=sources()
    official={r["race_id"]:r for r in records}
    if len(official)!=len(records):raise ValueError("Duplicate authoritative official race")
    allframes=sum(frames.values(),[])
    prepared,history_audit=available_features(records,allframes,
                  read("config/v4_full_training.json")["dq_prior_strength"])
    cohorts,eligible,history_lock=load_paired_cohort()
    history_v2=reconcile_v2(prepared,cohorts)
    save(ROOT/"history_repair_v2_audit.json",history_v2)
    print("History Repair V2 reconciled",history_v2["summary"],flush=True)
    prepared,repair_stats,patches=reconcile(prepared,cohorts,eligible)
    if repair_stats["runners_repaired"]!=original_eval["coverage"].get("archive_repair",365):
        # Previous V4 audit records 365, avoid assuming extra repair was gained.
        if repair_stats["runners_repaired"]!=365:
            raise ValueError("Existing frozen V4 repair sample was changed")
    r42=v4_rows(prepared)
    timing=raw_pace_records(records)
    residual,coverage=dated_speed_features(timing,read("config/speed_v7_protocol.json"))
    r43,_=append_speed(r42,residual)
    money=bring_historical_money(records)
    extras,_=derive(r43,money)
    enriched,_=attach(r43,extras)
    byid={r["race_id"]:r for r in enriched}
    if len(byid)!=len(enriched):raise ValueError("Duplicate V4 fit frame")
    groups={name:[byid[r["race_id"]] for r in original]
            for name,original in frames.items()}
    if sum(len(v) for v in groups.values())!=len(enriched):
        raise ValueError("New bundle source differs from archived active V4")
    fit=groups["train"]
    cal=[r for r in groups["validation"] if r["date"]<"2025-07-01"]
    v_market=[r for r in groups["validation"] if r["date"]>="2025-07-01"]
    if not fit or not cal or not v_market:raise ValueError("Invalid chronological training partition")
    print("V4 source frames restored",len(fit),len(cal),len(v_market),flush=True)

    # Model 1: independent fitted horse DQ probability, not an arbitrary
    # multiplier on winning probability which already includes DQ history.
    dq_model=fit_dq(fit,official,ridge=cfg["dq_ridge"])
    save(MODELS/"disqualification.json",dq_model)
    print("DQ model fitted",dq_model["fit_runners"],flush=True)

    # Model 2: shrink regularized context-specific probability temperatures.
    winner=models["winner"]
    p_cal=temper(cal,[probabilities(r,winner["model"]) for r in cal],
                 winner["temperature"])
    context=fit_context_temperatures(cal,p_cal,
              minimum=cfg["context_min_races"],prior=cfg["context_shrink_races"])
    save(MODELS/"race_context.json",context)
    print("Context group temperatures fitted",len(context["groups"]),flush=True)

    # Model 3: odds-bin correction trained only in Jul-Oct 2025;
    # validation is Nov-Dec, 2026 is reused descriptive test.
    price_policy=read("config/value_correction_v2.json")
    original_quotes,excluded,_=market_dataset("validation",price_policy)
    vmarket_by={r["race_id"]:r for r in v_market}
    pmarket={r["race_id"]:p for r,p in zip(v_market,temper(
        v_market,[probabilities(r,winner["model"]) for r in v_market],
        winner["temperature"]))}
    prepared_market=[]
    for item in original_quotes:
        rid=item["race_id"]
        if rid not in pmarket:continue
        row=vmarket_by[rid]
        nums=item["numbers"]
        R={h["number"]:h["features"][-1] for h in row["runners"]}
        predicted=market_probs(item["odds"],[pmarket[rid][n] for n in nums],
                               [R[n] for n in nums],models["market"]["weights"])
        prepared_market.append((item,{n:p for n,p in zip(nums,predicted)}))
    mfit=[(r,p) for r,p in prepared_market if r["date"]<="2025-10-31"]
    mval=[(r,p) for r,p in prepared_market if r["date"]>="2025-11-01"]
    if len(mfit)<250 or len(mval)<80:raise ValueError("Insufficient separated odds calibration windows")
    bands=market_band_fit([r for r,p in mfit],[p for r,p in mfit],
                          prior=cfg["market_band_prior"])
    bands["fit_start"]="2025-07-01";bands["fit_end"]="2025-10-31"
    bands["validation_start"]="2025-11-01";bands["validation_end"]="2025-12-31"
    save(MODELS/"odds_bands.json",bands)
    print("Odds calibration bands fitted",bands["bands"],flush=True)

    # Quinté comes from the exact same frozen ranking model; no new trained
    # weights required, but joint-probability calibration is not yet verified.
    quinte_cfg={"method":"FROZEN_V4_FIVE_CONDITIONAL_UNORDERED_DP",
                "shortlist_limit":cfg["quinte_shortlist_limit"],
                "max_display_alternatives":cfg["quinte_alternatives"],
                "model_sha256":base_lock["three_new_models_sha256"]["ranking.json"],
                "status":"RESEARCH_ONLY_NOT_MARKET_CALIBRATED",
                "no_real_stake_recommendation":True}
    save(MODELS/"quinte.json",quinte_cfg)

    # LOCK BEFORE 2026 REUSED TEST.
    lock={"status":"FROZEN_BEFORE_REUSED_TEST",
          "version":cfg["version"],
          "main_v4_unchanged":True,"recommendations_allowed":False,
          "base_lock_sha256":sha("models/v4_multifeature/frozen_before_test.json"),
          "protocol_sha256":sha(PROTOCOL),
          "training_code_sha256":sha("scripts/train_v4_next_bundle.py"),
          "research_core_sha256":sha("turf_lab/v4_next_research.py"),
          "history_v2_sha256":sha("turf_lab/history_repair_v2.py"),
          "chronological_splits":cfg["windows"],
          "dataset_sha256":{s:v["sha256"] for s,v in manifest["splits"].items()},
          "source_manifest_shas":source_shas,
          "models_sha256":{x:sha(MODELS/x) for x in ("disqualification.json","race_context.json",
                                                    "odds_bands.json","quinte.json")},
          "prospective_independent_samples_at_lock":0,
          "test_2026_already_inspected":True,
          "not_an_evidence_of_ZEturf_ROI":True}
    save(MODELS/"frozen_before_test.json",lock)
    print("Four components and History Repair V2 LOCKED before 2026 analysis",flush=True)

    test=groups["test"]
    p_test=temper(test,[probabilities(r,winner["model"]) for r in test],
                  winner["temperature"])
    scored_context=[]
    used_groups={}
    for row,p in zip(test,p_test):
        corrected,g=apply_context(p,row["venue"],row["start_type"],row["distance_m"],context)
        used_groups[g or "NONE"]=used_groups.get(g or "NONE",0)+1
        scored_context.append(corrected)
    old_winner=mean_ll(test,p_test)
    new_context=mean_ll(test,scored_context)
    dq_eval=dq_metrics(test,official,dq_model)
    # Compare DQ with constant prior estimated ONLY on training cohort.
    dq_truth=[];dq_baseline=[]
    for race in test:
        by={p["numPmu"]:p for p in official[race["race_id"]]["participants"]}
        from turf_lab.v4_next_research import dq_label
        for horse in active(race):
            y=dq_label(by[horse["number"]])
            if y is None:continue
            dq_truth.append(y)
            dq_baseline.append((dq_model["observed_dq_rate"]-y)**2)
    dq_eval["constant_prior_brier"]=mean(dq_baseline)
    vchecks=[]
    for row,p in mval:
        odds={n:v for n,v in zip(row["numbers"],row["odds"])}
        pp=adjust_market_bands(p,odds,bands)
        win=row["numbers"][row["winner_index"]]
        vchecks.append((-math.log(max(1e-15,p[win])),
                        -math.log(max(1e-15,pp[win]))))
    market_validation={"races":len(vchecks),
                       "base_logloss":mean(x[0] for x in vchecks),
                       "band_logloss":mean(x[1] for x in vchecks),
                       "market_model_was_previously_fitted_on_2025H2":True}
    # Reused 2026 market snapshots (NOT actual executable ZEturf prices).
    test_quotes,excluded_test,_=market_dataset("test",price_policy)
    p_test_by={r["race_id"]:p for r,p in zip(test,p_test)}
    test_by={r["race_id"]:r for r in test}
    market_test=[]
    for quote in test_quotes:
        rid=quote["race_id"]
        if rid not in p_test_by:raise ValueError("Missing market test race")
        nums=quote["numbers"];R={h["number"]:h["features"][-1] for h in test_by[rid]["runners"]}
        cur=market_probs(quote["odds"],[p_test_by[rid][n] for n in nums],
                         [R[n] for n in nums],models["market"]["weights"])
        base={n:p for n,p in zip(nums,cur)}
        odds=dict(zip(nums,quote["odds"]))
        adjusted=adjust_market_bands(base,odds,bands)
        win=nums[quote["winner_index"]]
        market_test.append((-math.log(max(1e-15,base[win])),
                           -math.log(max(1e-15,adjusted[win]))))
    # Fixed, not outcome-selected sample of 2026 test races for expensive ZE5.
    sample=sorted(test,key=lambda r:hashlib.sha256(
             (cfg["quinte_fixed_sampling_seed"]+r["race_id"]).encode()).hexdigest())
    sample=sample[:cfg["quinte_reused_test_races"]]
    quinte_results=[]
    for race in sample:
        truth=finish(official[race["race_id"]]["participants"])
        if truth is None:continue
        q=quinte_unordered(race,models["ranking"],limit=cfg["quinte_shortlist_limit"])
        quinte_results.append({"p":q["joint_probability_unordered"],
                              "hit":int(set(q["selection"])==set(truth)),
                              "greedy_hit":int(set(q["greedy_selection"])==set(truth)),
                              "greedy_p":q["greedy_unordered_probability"]})
    if not quinte_results:raise ValueError("No verifiable ZE5 sample")
    ze5={"races":len(quinte_results),
         "expected_exact":sum(r["p"] for r in quinte_results),
         "actual_exact":sum(r["hit"] for r in quinte_results),
         "greedy_expected":sum(r["greedy_p"] for r in quinte_results),
         "greedy_actual":sum(r["greedy_hit"] for r in quinte_results),
         "mean_probability":mean(r["p"] for r in quinte_results),
         "joint_calibration_validated":False,
         "no_actual_ZEturf_payouts":True}
    report={"version":cfg["version"],"status":"EXPLORATORY_ALL_FIVE_COMPONENTS",
            "public_model_unchanged":"TURF_LAB_V4_47_FEATURE",
            "source_history_v2":history_v2["summary"],
            "disqualification":dq_eval,
            "context":{"unchanged":old_winner,"specialized":new_context,"applied":used_groups,
                       "trained_on_2025H1_already_used_for_main_temperature":True},
            "odds_bands":{"2025_Nov_Dec_validation":market_validation,
                          "2026_reused_test":{
                             "races":len(market_test),
                             "base_logloss":mean(x[0] for x in market_test),
                             "band_logloss":mean(x[1] for x in market_test)}},
            "ze5":ze5,
            "baseline_model_lock":lock["base_lock_sha256"],
            "locked_before_test":True,"recommendations_allowed":False,
            "provenance":["2026 has already been inspected in multiple V4 iterations",
                          "DQ model fitted on pre-2025 only",
                          "Context fitted on 2025 H1 previously used in main winner calibration",
                          "Odds-bin baseline itself was fitted with 2025 H2 so its calibration test is not virgin",
                          "No real-money strategy or payout validation yet"],
            "decision":"DO_NOT_PROMOTE_ANY_PROBABILITY_ADJUSTMENT_AUTOMATICALLY"}
    save(ROOT/"evaluation.json",report)
    lines=["# Turf Lab V4 : cinq chantiers lancés ensemble","",
      "Une seule V4 active 47 variables, avec un paquet de recherche gelé et audité.",
      "1. History Repair V2 : provenance renforcée et quarantaine des fenêtres historiques non équivalentes ; aucune correction non vérifiée injectée.",
      f"2. DQ : modèle réellement ajusté sur {dq_model['fit_runners']} partants datés 2022-2024 ; Brier 2026 {dq_eval['brier']:.5f}, référence constante {dq_eval['constant_prior_brier']:.5f}.",
      f"3. Contexte : {len(context['groups'])} groupes régularisés ; log loss 2026 {old_winner['log_loss']:.5f} → {new_context['log_loss']:.5f}, premier gagnant {old_winner['top1']:.2%} → {new_context['top1']:.2%}.",
      f"4. Tranches de cotes : calibration 2025 Nov-Dec {market_validation['base_logloss']:.5f} → {market_validation['band_logloss']:.5f} (marché de base déjà ajusté sur 2025), 2026 {mean(x[0] for x in market_test):.5f} → {mean(x[1] for x in market_test):.5f}.",
      f"5. Z5 sans ordre : {ze5['races']} arrivées 2026 réexaminées ; réussites attendues {ze5['expected_exact']:.2f}, obtenues {ze5['actual_exact']}, non validé comme probabilité de pari.",
      "",
      "**Aucune variante n'est automatiquement déclarée meilleure ou promue** : évaluation 2026 réutilisée, calibration par cotes historique non indépendante, aucune rentabilité réelle confirmée.",
      "**Le moteur unique V4 continue d'utiliser ses 47 coefficients figés.** Le nouveau rapport peut exposer séparément DQ/risque et probabilité théorique du Z5 ; les ajustements favoris/outsiders et contexte exigent une validation temporelle indépendante.",
      "**Aucune recommandation de mise.**"]
    (ROOT/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"dq_brier":dq_eval["brier"],"context_old_ll":old_winner["log_loss"],
                      "context_new_ll":new_context["log_loss"],
                      "2026_market_n":len(market_test),
                      "ze5_expected":ze5["expected_exact"],"ze5_actual":ze5["actual_exact"]},
                     indent=2),flush=True)


if __name__=="__main__":
    try:main()
    except Exception as e:
        dump(ROOT/"failure.json",{"type":type(e).__name__,"reason":str(e),
                                  "production_changed":False,
                                  "recommendations_allowed":False})
        raise
