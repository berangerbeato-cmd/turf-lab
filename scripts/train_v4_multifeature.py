"""One-shot retraining of ALL requested V4 improvements, winner/top5/market.

47 features = 43 frozen V4 Speed + as-of previous career gains relative +
relative previous finish/prize class proxy + weighted five-start form + R.

Strictly before-target past data for all new predictors. Historic raw career
gains were retrieved retrospectively; their original publication at racing
time is NOT independently proven. Separate 2025 fit and calibration periods,
test only after model SHA locks, 2026 previously inspected exploration.
"""
import gzip,json
from pathlib import Path

from scripts.train_available_history_v3 import sources
from scripts.train_market_repair import dataset as market_dataset,evaluate as evaluate_old_market
from scripts.train_v4_full import (read,save,sha,add_truth,fit_ranker,rank_top5,
                                   simple_top5_stats)
from turf_lab.available_history_research import available_features,calibrate_temperature
from turf_lab.fast_logit import fit as fit_sport
from turf_lab.full_history_evaluation import chronological,score,paired,temper
from turf_lab.pilot import probabilities
from turf_lab.ranking_research import finish
from turf_lab.v4_retrain_data import reconcile,v4_rows,load_paired_cohort
from turf_lab.v4_speed_data import raw_pace_records,dated_speed_features,append_speed
from turf_lab.v4_multi_features import bring_historical_money,derive,attach
from turf_lab.v4_reliability_market import fit as fit_R_market,evaluate as evaluate_R_market
from turf_lab.evidence import dump

ROOT=Path("reports/v4_multifeature")
MODELS=Path("models/v4_multifeature")
POLICY=Path("config/v4_multifeature_training.json")


def main():
    if (MODELS/"frozen_before_test.json").exists() or (ROOT/"evaluation.json").exists():
        raise ValueError("Joint V4 with R already fitted. Never rechoose based on 2026 test")
    p=read(POLICY)
    if p["status"]!="RESEARCH_ONLY_NO_BET" or p["recommendations_allowed"] is not False:
        raise ValueError("V4 joint training policy not allowed")
    old_speed=read("reports/v4_speed/evaluation.json")
    old_lock=read(p["frozen_previous"])
    if old_lock["status"]!="FROZEN_BEFORE_REUSED_TEST" or any(
            sha(Path("models/v4_speed")/filename)!=expected
            for filename,expected in old_lock["three_new_model_hashes"].items()):
        raise ValueError("Old 43-feature V4 baseline is no longer frozen")
    manifest=read("reports/full_history/datasets/manifest.json")
    frames={}
    for split,meta in manifest["splits"].items():
        if sha(meta["file"])!=meta["sha256"]:
            raise ValueError("Training corpus SHA mismatch")
        with gzip.open(meta["file"],"rt") as fd:
            frames[split]=[json.loads(line) for line in fd]
        if len(frames[split])!=meta["races"]:
            raise ValueError("Training corpus race count mismatch")
    chronological(frames["train"],frames["validation"],frames["test"])
    records,raw_manifests=sources()
    historic,base_audit=available_features(records,sum(frames.values(),[]),
                        read("config/v4_full_training.json")["dq_prior_strength"])
    cohorts,eligible,repair_lock=load_paired_cohort()
    reconciled,repair_counts,repair_changes=reconcile(historic,cohorts,eligible)
    if repair_counts["runners_repaired"]!=old_speed["history_repaired_runners"]:
        raise ValueError("Reconstructed 43-feature V4 historical repair count changed")
    originals=v4_rows(reconciled)
    timing=raw_pace_records(records)
    chrono,chrono_audit=dated_speed_features(timing,read("config/speed_v7_protocol.json"))
    base43,chrono_coverage=append_speed(originals,chrono)
    by43={r["race_id"]:r for r in base43}
    for group,meta in frames.items():
        for item in meta:
            if item["race_id"] not in by43:
                raise ValueError("Old training split or individual race missing")
    money_records=bring_historical_money(records)
    auxiliary,extra_audit=derive(base43,money_records)
    combined,attach_audit=attach(base43,auxiliary)
    by_combined={r["race_id"]:r for r in combined}
    if len(by_combined)!=len(combined):
        raise ValueError("Duplicate transformed V4 race")
    groups={
        name:[by_combined[x["race_id"]] for x in rows]
        for name,rows in frames.items()
    }
    # Explicitly fail if any of the four new signals was accidentally omitted.
    if (not combined or any(len(h["features"])!=p["model_features"]
            for r in combined for h in r["runners"])):
        raise ValueError("Missing joint V4 47-feature train frame")
    counts={}
    for split,rs in groups.items():
        horses=[r for race in rs for r in race["runners"] if not r["non_runner"]]
        counts[split]={
            "races":len(rs),"active_runners":len(horses),
            "valid_previous_gains":sum(r["features"][-4] is not None for r in horses),
            "valid_weighted_form":sum(r["features"][-2] is not None for r in horses),
            "with_context_speed":sum(r["features"][42] is not None for r in horses),
            "R_mean":sum(r["features"][-1] for r in horses)/len(horses)}
    if not counts["train"]["valid_previous_gains"] or not counts["train"]["valid_weighted_form"]:
        raise ValueError("Money/form signal has no training evidence")
    save(ROOT/"feature_audit.json",{
        "status":"AS_OF_HISTORY_RESEARCH_NOT_MONEY_PRESTART_PROVEN",
        "cohort":counts,"repair":repair_counts,
        "retrospective_gain_snapshots_caveat":p["original_historical_gain_snapshots"],
        "historic_raw_manifest_shas":raw_manifests,
        "speed_source":chrono_audit,"extra_features":extra_audit,
        "source_hashes":{
            "feature_code":sha("turf_lab/v4_multi_features.py"),
            "speed_code":sha("turf_lab/context_speed.py"),
            "gain_audit":sha("reports/v4_multifeature/gains_temporal_audit.json")},
        "all_features":p["additions"]})
    print("JOINT_FEATURES_BUILT",json.dumps(counts),flush=True)

    train=groups["train"]
    early=[r for r in groups["validation"] if r["date"]<"2025-07-01"]
    late=[r for r in groups["validation"] if r["date"]>="2025-07-01"]
    if not all((train,early,late)):
        raise ValueError("Chronological calibration groups not available")

    winner=fit_sport(train,p["winner_l2"],p["winner_iterations"],
                     p["winner_learning_rate"])
    temp=calibrate_temperature(early,[probabilities(r,winner) for r in early])
    save(MODELS/"winner.json",{
        "model":winner,"temperature":temp,
        "features":47,"fit_races":len(train),
        "calibration_races":len(early),
        "added_features":p["additions"]})
    print("JOINT_V4_WINNER_TRAINED",len(train),temp,flush=True)

    truths={r["race_id"]:finish(r["participants"]) for r in records}
    toptrain=add_truth(train,truths)
    topcal=add_truth(early,truths)
    ranking=fit_ranker(toptrain,topcal,{"ranking_ridge":p["ranking_ridge"]})
    save(MODELS/"ranking.json",ranking)
    print("JOINT_V4_TOP5_TRAINED",len(toptrain),flush=True)

    price_policy=read("config/value_correction_v2.json")
    prices_train,train_exclusions,train_sha=market_dataset("validation",price_policy)
    late_prob={r["race_id"]:prediction for r,prediction in zip(
        late,temper(late,[probabilities(r,winner) for r in late],temp))}
    bylate={r["race_id"]:r for r in late}
    train_prices=[]
    for quote in prices_train:
        if quote["date"]<"2025-07-01":continue
        rid=quote["race_id"]
        if rid not in bylate:
            raise ValueError("Missing joint V4 sport R for reference PMU quote")
        per={x["number"]:x["features"][-1] for x in bylate[rid]["runners"]}
        row=dict(quote,sport=[late_prob[rid][n] for n in quote["numbers"]],
                 reliability=[per[n] for n in quote["numbers"]])
        train_prices.append(row)
    if len(train_prices)<p["minimum_market_rows"]:
        raise ValueError("Insufficient independent 2025 H2 market/R fit cases")
    frozen_old_market=read("models/v4_speed/market.json")
    fitted_market=fit_R_market(train_prices,p,frozen_old_market["weights"])
    save(MODELS/"market.json",fitted_market)
    print("JOINT_V4_MARKET_AND_R_TRAINED",len(train_prices),fitted_market["weights"],flush=True)

    # All 3 model hashes are frozen BEFORE any 2026 scores are calculated.
    lock={
        "version":p["version"],"status":"FROZEN_BEFORE_REUSED_2026_EVALUATION",
        "all_four_added_features_trained":True,
        "prior_speed_lock_sha256":sha("models/v4_speed/frozen_before_test.json"),
        "protocol_sha256":sha(POLICY),
        "training_code_sha256":sha("scripts/train_v4_multifeature.py"),
        "four_feature_source_sha256":sha("turf_lab/v4_multi_features.py"),
        "reliability_market_code_sha256":sha("turf_lab/v4_reliability_market.py"),
        "old_speed_sha256":sha("config/speed_v7_protocol.json"),
        "dataset_hashes":{k:v["sha256"] for k,v in manifest["splits"].items()},
        "original_source_sha256":raw_manifests,
        "three_new_models_sha256":{
            fname:sha(MODELS/fname)
            for fname in ("winner.json","ranking.json","market.json")},
        "all_sources_dated_before_target":True,
        "retrospective_gain_asof_proven":False,
        "no_retrained_weights_used_from_previous_V4":True,
        "test_is_previously_inspected":True,
        "production_switched":False,
        "recommendations_allowed":False,
        "limits":p["limits"]}
    save(MODELS/"frozen_before_test.json",lock)
    print("JOINT_47_FEATURE_V4_FROZEN_BEFORE_2026",flush=True)

    test=groups["test"]
    baseline_rows=[by43[r["race_id"]] for r in frames["test"]]
    base_winner=read("models/v4_speed/winner.json")
    base_prob=temper(baseline_rows,[probabilities(r,base_winner["model"]) for r in baseline_rows],base_winner["temperature"])
    previous=score(baseline_rows,base_prob)["overall"]
    if abs(previous["log_loss"]-old_speed["winner"]["v4_speed"]["log_loss"])>1e-9:
        raise ValueError("Existing V4 baseline performance is not reproducible")
    new_prob=temper(test,[probabilities(r,winner) for r in test],temp)
    sporting=score(test,new_prob)["overall"]
    paired_results=paired(test,base_prob,new_prob,repetitions=500)

    exact_new=add_truth(test,truths)
    exact_old=add_truth(baseline_rows,truths)
    old_ranking=read("models/v4_speed/ranking.json")
    new_rank=simple_top5_stats(exact_new,[rank_top5(r,ranking) for r in exact_new])
    old_rank=simple_top5_stats(exact_old,[rank_top5(r,old_ranking) for r in exact_old])
    if old_rank["top5_exact_count"]!=old_speed["top5"]["v4_speed"]["top5_exact_count"]:
        raise ValueError("Baseline V4 Top5 was not reproduced")
    historic_prices,discarded_test,_=market_dataset("test",price_policy)
    if len(historic_prices)!=old_speed["market"]["v4_speed"]["races"]:
        raise ValueError("Not the same market test races")
    p_old={r["race_id"]:q for r,q in zip(baseline_rows,base_prob)}
    p_new={r["race_id"]:q for r,q in zip(test,new_prob)}
    t_new={r["race_id"]:r for r in test}
    old_price=[];new_price=[]
    for original in historic_prices:
        rid=original["race_id"]
        if rid not in p_old or rid not in p_new:
            raise ValueError("Lost PMU reference quote race")
        old_price.append(dict(original,sport=[p_old[rid][n] for n in original["numbers"]]))
        reliability={r["number"]:r["features"][-1] for r in t_new[rid]["runners"]}
        new_price.append(dict(original,
            sport=[p_new[rid][n] for n in original["numbers"]],
            reliability=[reliability[n] for n in original["numbers"]]))
    former,_=evaluate_old_market(old_price,read("models/v4_speed/market.json")["weights"])
    if abs(former["log_loss"]-old_speed["market"]["v4_speed"]["log_loss"])>1e-9:
        raise ValueError("Historic V4 Speed market evaluation cannot be reproduced")
    updated=evaluate_R_market(new_price,fitted_market["weights"])
    report={
        "version":p["version"],"status":"COMPLETE_ALL_FEATURES_EXPLORATORY_2026",
        "features":47,"sources":{"gain_asof_proven":False,
                                 "gain_previous_race_only":True,
                                 "one_model_promotion_deferred_to_integrity_tests":True},
        "train_races":len(train),"ranking_train_races":len(toptrain),
        "ranking_calibration_races":len(topcal),
        "market_training_races":len(train_prices),
        "test_races":len(test),"rank_test_races":len(exact_new),
        "coverage":counts,
        "winner":{"v4_speed_reference":previous,
                  "v4_joint_all_features":sporting,
                  "paired_weekly":paired_results},
        "top5":{"v4_speed_reference":old_rank,
                "v4_joint_all_features":new_rank},
        "market":{"v4_speed_reference":{
                     k:former[k] for k in ("races","log_loss","brier","top1","positive_ev_diagnostic")},
                  "v4_joint_all_features":updated},
        "new_market_coefficients":fitted_market["weights"],
        "money_feature_is_historical_lagged_not_proven_prestart":True,
        "test_not_independent":True,
        "recommendations_allowed":False,"roi":None,
        "training_frozen_before_test":str(MODELS/"frozen_before_test.json"),
        "limitations":p["limits"]
    }
    save(ROOT/"evaluation.json",report)
    lines=["# Une V4, toutes les anciennes idées intégrées d'un coup","",
           "**47 variables** : 43 actuelles, derniers gains antérieurs relatifs (montants PMU datés, publication historiquement non certifiée), classe relative des résultats passés, forme 35/25/18/12/10 et indice R.",
           "**Gagnant, 5 positions Top5 et modèle de cotes conditionnel à R tous réentraînés.**","",
           "## Étude exploratoire 2026 : les années 2025/2026 avaient déjà été inspectées",
           "| Mesure | V4 chrono 43 variables | V4 complète 47 variables |",
           "|---|---:|---:|",
           f"| Gagnant log loss ↓ | {previous['log_loss']:.6f} | {sporting['log_loss']:.6f} |",
           f"| Gagnant Brier ↓ | {previous['brier_multiclass']:.6f} | {sporting['brier_multiclass']:.6f} |",
           f"| Premier gagnant | {previous['top1_accuracy']:.2%} | {sporting['top1_accuracy']:.2%} |",
           f"| Top5 exact | {old_rank['top5_exact_count']}/{len(exact_old)} | {new_rank['top5_exact_count']}/{len(exact_new)} |",
           f"| Cotes PMU log loss ↓ | {former['log_loss']:.6f} | {updated['log_loss']:.6f} |",
           "",
           f"Couverture gain antérieur train : {counts['train']['valid_previous_gains']}/{counts['train']['active_runners']}.",
           f"Couverture forme pondérée train : {counts['train']['valid_weighted_form']}/{counts['train']['active_runners']}.",
           "L'ancien indice R est remplacé par une mesure explicite de complétude des données, dont l'effet sur le marché est APPRIS sur les cotes 2025 H2.",
           "L'audit des gains confirme une progression chronologique généralement cohérente, mais les archives sont rétrospectives : la publication initiale n'est pas prouvée.",
           "Aucune correction de valeur positive/ROI n'est attestée avec de véritables cotes ZEturf exécutables. Politique NO BET maintenue."]
    (ROOT/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"winner_baseline":previous["log_loss"],"winner_all":sporting["log_loss"],
       "top5_baseline":old_rank["top5_exact_count"],"top5_all":new_rank["top5_exact_count"],
       "market_baseline":former["log_loss"],"market_all":updated["log_loss"],
       "gain_train":counts["train"]["valid_previous_gains"]},indent=2),flush=True)
    return report


if __name__=="__main__":
    try:main()
    except Exception as e:
        dump(ROOT/"failure.json",{"stage":"FAILED","reason":type(e).__name__+": "+str(e),
                                  "recommendations_allowed":False})
        raise
