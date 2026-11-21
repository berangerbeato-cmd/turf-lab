"""Turf Lab V4: FULL retraining of winner, conditional Top5 and market weights.

Chronological, frozen source, no network, no unchanged V3 weight reuse:
  Fit sports and five conditional ranks: 2022-03 .. 2024-12.
  Calibrate on 2025-01 .. 2025-06.
  Fit fresh market correction on 2025-07 .. 2025-12.
  Inspect 2026 as a *reused exploratory* test, NOT independent validation.
  Forward prestart cohort is the only virgin validation.

History Repair: import every verified individual-history supplement in the
existing immutable 618-race cohort WHEN it exactly reconciles with the
existing unlimited-5 base. Preserve all known starts and quarantine mismatches.
All other training rows are archive-only, explicitly tracked. Never invent
missing 2022-2024 individual histories.
"""
import gzip
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.train_available_history_v3 import sources
from scripts.train_market_repair import dataset as market_dataset
from scripts.train_market_repair import evaluate as evaluate_market
from scripts.train_stage_ranking_v2 import features as stage_features, transform
from turf_lab.available_history_research import available_features, calibrate_temperature
from turf_lab.fast_logit import fit as fit_sport
from turf_lab.full_history_evaluation import chronological, paired, score, temper
from turf_lab.market_repair import fit as fit_market
from turf_lab.pilot import active, probabilities
from turf_lab.ranking_research import finish
from turf_lab.stage_ranking import fit_choice, temperature as stage_temperature
from turf_lab.stage_ranking import greedy, strengths
from turf_lab.v4_retrain_data import load_paired_cohort, reconcile, v4_rows
from turf_lab.evidence import dump

ROOT = Path("reports/v4_full")
MODEL = Path("models/v4_full")
CONFIG = Path("config/v4_full_training.json")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, data):
    path = Path(path)
    if path.exists():
        if json.loads(path.read_text()) != data:
            raise ValueError("Immutable output conflict: "+str(path))
        return
    dump(path,data)


def status(stage, **details):
    dump(ROOT/"status.json",{"stage":stage,"models_retrained":stage in
         ("FROZEN_BEFORE_2026_TEST","COMPLETED_EXPLORATORY"),
         "recommendations_allowed":False,"production_changed":False,
         **details})
    print(stage,json.dumps(details),flush=True)


def matrix_for(row, mean,scale):
    return transform(stage_features(row),mean,scale)


def fit_ranker(rows, calibration, config):
    print("Training FIVE conditional finish-order models",flush=True)
    train_x = [stage_features(r) for r in rows]
    combined = np.concatenate(train_x)
    mean = np.nanmean(combined,axis=0)
    mean = np.nan_to_num(mean)
    scale = np.nanstd(combined,axis=0)
    scale = np.where(np.isfinite(scale) & (scale > 1e-8), scale, 1)
    train_x = [transform(x,mean,scale) for x in train_x]
    coef=[]; fits=[]
    for position in range(5):
        matrices=[];sizes=[]; winners=[]
        for row,x in zip(rows,train_x):
            ranks=row["true_top5_index"]
            keep=[i for i in range(len(x)) if i not in ranks[:position]]
            matrices.append(x[keep])
            sizes.append(len(keep))
            winners.append(keep.index(ranks[position]))
        result, fit_stats = fit_choice(np.concatenate(matrices),sizes,winners,config["ranking_ridge"])
        coef.append(result);fits.append(fit_stats)
        print("Position",position+1,"fitted",flush=True)
    weights=np.asarray(coef)
    cal_x=[weights@matrix_for(r,mean,scale).T for r in calibration]
    true=[r["true_top5_index"] for r in calibration]
    temps=[stage_temperature(cal_x,true,j) for j in range(5)]
    return {"mean":mean.tolist(),"scale":scale.tolist(),"coefficients":weights.tolist(),
            "temperatures":temps,"fit_status":fits,
            "train_races_with_exact_top5":len(rows),
            "calibration_races_with_exact_top5":len(calibration),
            "kind":"five_conditional_linear_softmax_models",
            "independent_new_training":True}


def rank_top5(row,model):
    matrix = matrix_for(row,np.array(model["mean"]),np.array(model["scale"]))
    raw = np.asarray(model["coefficients"])@matrix.T
    weight = strengths(raw, model["temperatures"])
    selected = greedy(weight,5)
    return [active(row)[i]["number"] for i in selected]


def add_truth(rows,truths):
    kept=[]
    for row in rows:
        order=truths.get(row["race_id"])
        if order is None:
            continue
        nums=[p["number"] for p in active(row)]
        if any(n not in nums for n in order):
            raise ValueError("Top5 truth cannot be joined by runner number")
        enriched=dict(row,true_top5_index=[nums.index(n) for n in order])
        kept.append(enriched)
    return kept


def read_original_v3_test():
    original={}
    with gzip.open("reports/available_history_v3/test_predictions.jsonl.gz","rt") as f:
        for line in f:
            x=json.loads(line)
            original[x["race_id"]]={int(n):p for n,p in
                x["probabilities"]["last5_available_dq20"].items()}
    return original


def simple_top5_stats(rows, ranked):
    if len(rows)!=len(ranked):
        raise ValueError("Unpaired stage evaluation")
    overlaps=[];exact=0
    for row,group in zip(rows,ranked):
        truth=set(row["true_top5_index"])
        active_nums=[r["number"] for r in active(row)]
        truth_nums={active_nums[i] for i in truth}
        overlaps.append(len(set(group)&truth_nums))
        exact+=int(set(group)==truth_nums)
    return {"races":len(rows),"top5_overlap_mean":sum(overlaps)/len(rows),
            "top5_exact_count":exact,"top5_exact_rate":exact/len(rows)}


def main():
    if (ROOT/"evaluation.json").exists() or (MODEL/"frozen_before_test.json").exists():
        raise ValueError("Completed V4 experiment exists. Create new version to retrain.")
    config=read(CONFIG)
    if config["status"] != "RESEARCH_NO_BET":
        raise ValueError("Unauthorized training protocol")
    status("LOADING_LOCKED_ARCHIVE")
    manifest=read("reports/full_history/datasets/manifest.json")
    frames={}
    for split,info in manifest["splits"].items():
        if sha(info["file"])!=info["sha256"]:
            raise ValueError("Dataset SHA mismatch in "+split)
        with gzip.open(info["file"],"rt") as stream:
            frames[split]=[json.loads(line) for line in stream]
        if len(frames[split])!=info["races"]:
            raise ValueError("Dataset race count mismatch")
    chronological(frames["train"],frames["validation"],frames["test"])
    records,source_manifests=sources()
    cohorts,eligible,lock=load_paired_cohort()
    selected_ids={r["race_id"] for rows in frames.values() for r in rows}
    enriched,classic_audit=available_features(records,sum(frames.values(),[]),
                             config["dq_prior_strength"])
    if {r["race_id"] for r in enriched} != selected_ids:
        raise ValueError("Available feature race mismatch")
    joined,repair_audit,patches=reconcile(enriched,cohorts,eligible)
    save(ROOT/"history_reconciliation_audit.json",{
        "lock_sha256":sha("models/sport_history_cohort_v2/frozen.json"),
        "cohort_source_retrieved_retrospectively":True,
        "archive_only_no_invented_starts":True,
        "summary":repair_audit,
        "patched_runners":patches,
        "original_archive_feature_audit":classic_audit})
    joined=v4_rows(joined)
    by_id={r["race_id"]:r for r in joined}
    groups={k:[by_id[r["race_id"]] for r in rows] for k,rows in frames.items()}
    truths={r["race_id"]:finish(r["participants"]) for r in records}
    status("HISTORY_CHECKED",**repair_audit)
    if repair_audit["runners_repaired"] < config["minimum_verified_repaired_runners"]:
        raise ValueError("Too few verifiable history corrections to claim repaired training")
    sports_train=groups["train"]
    early=[r for r in groups["validation"] if r["date"]<"2025-07-01"]
    late=[r for r in groups["validation"] if r["date"]>="2025-07-01"]
    if not early or not late:
        raise ValueError("2025 split not available for independent substeps")
    sports=fit_sport(sports_train,config["winner_l2"],config["winner_iterations"],
                     config["winner_learning_rate"])
    temp=calibrate_temperature(early,
             [probabilities(r,sports) for r in early])
    save(MODEL/"winner.json",{"model":sports,"temperature":temp,
        "fit_races":len(sports_train),
        "calibration_races":len(early),"history_features":42})
    status("WINNER_RETRAINED",train_races=len(sports_train),temperature=temp)
    stage_train=add_truth(sports_train,truths)
    stage_calibration=add_truth(early,truths)
    ranker=fit_ranker(stage_train,stage_calibration,config)
    save(MODEL/"ranking.json",ranker)
    status("TOP5_RETRAINED",train_races=len(stage_train),calibration_races=len(stage_calibration))
    # Fit corrected market on DIFFERENT months than sports/ranking temperature calibration.
    val_prices, val_exclusions, val_sha=market_dataset("validation",read("config/value_correction_v2.json"))
    late_probs={r["race_id"]:p for r,p in zip(late,
         temper(late,[probabilities(r,sports) for r in late],temp))}
    market_fit=[r for r in val_prices if r["date"]>="2025-07-01"]
    for r in market_fit:
        if r["race_id"] not in late_probs:
            raise ValueError("Market training missing corresponding V4 sport data")
        r["sport"]=[late_probs[r["race_id"]][n] for n in r["numbers"]]
    if len(market_fit) < config["minimum_market_training_races"]:
        raise ValueError("Insufficient PMU complete prestart market training rows")
    market=fit_market(market_fit,read("config/value_correction_v2.json"))
    save(MODEL/"market.json",market)
    status("MARKET_RETRAINED",train_races=len(market_fit),weights=market["weights"])
    # Lock all parameters and sources BEFORE looking at test predictions/results.
    provenance={
        "status":"FROZEN_BEFORE_REUSED_2026_TEST",
        "protocol_sha256":sha(CONFIG),
        "dataset_split_sha256":{k:v["sha256"] for k,v in manifest["splits"].items()},
        "supplement_cohort_sha256":sha("models/sport_history_cohort_v2/frozen.json"),
        "source_manifests":source_manifests,
        "features_source_sha256":sha("turf_lab/available_history_research.py"),
        "data_repair_code_sha256":sha("turf_lab/v4_retrain_data.py"),
        "train_code_sha256":sha("scripts/train_v4_full.py"),
        "models_sha256":{p.name:sha(p) for p in (
            MODEL/"winner.json",MODEL/"ranking.json",MODEL/"market.json")},
        "periods":{"sports_fit":"2022-03-02..2024-12-31",
                   "sports_ranking_calibration":"2025-01-01..2025-06-30",
                   "market_fit":"2025-07-01..2025-12-31",
                   "reused_exploratory_test":"2026-01-01..2026-09-30"},
        "history_repaired_runners":repair_audit["runners_repaired"],
        "no_network_requests":True,
        "old_v3_and_v2_preserved":True,
        "production_changed":False,
        "recommendations_allowed":False,
        "limits":config["limitations"]}
    save(MODEL/"frozen_before_test.json",provenance)
    status("FROZEN_BEFORE_2026_TEST",model_hashes=provenance["models_sha256"])

    # 2026 is an already-inspected descriptive set, NEVER used to choose weights.
    test=groups["test"]
    fresh=temper(test,[probabilities(r,sports) for r in test],temp)
    previous=read_original_v3_test()
    if set(previous)!={r["race_id"] for r in test}:
        raise ValueError("Original V3 comparison cohort differs")
    base=[previous[r["race_id"]] for r in test]
    for r,p in zip(test,base):
        if set(p)!={runner["number"] for runner in r["runners"]}:
            raise ValueError("V3 comparison field changed")
    selected=add_truth(test,truths)
    evaluated={r["race_id"]:p for r,p in zip(test,fresh)}
    results_rank=[rank_top5(r,ranker) for r in selected]
    base_rank=[sorted((n for n,p in previous[r["race_id"]].items() if p>0),
                      key=lambda n:(-previous[r["race_id"]][n],n))[:5] for r in selected]
    win_evaluation={
       "new_v4":score(test,fresh)["overall"],
       "frozen_v3":score(test,base)["overall"],
       "paired_week":paired(test,base,fresh,repetitions=300)
    }
    stage_evaluation={
        "new_v4_ranking":simple_top5_stats(selected,results_rank),
        "v3_win_top5_baseline":simple_top5_stats(selected,base_rank)
    }
    test_prices,price_exclusions,price_sha=market_dataset("test",read("config/value_correction_v2.json"))
    current = {r["race_id"]:p for r,p in zip(test,fresh)}
    for r in test_prices:
        if r["race_id"] not in current:
            raise ValueError("Market test race omitted from sports test")
        r["sport"]=[current[r["race_id"]][n] for n in r["numbers"]]
    new_market,_=evaluate_market(test_prices,market["weights"])
    market_reference=read("models/value_correction_v2/hybrid.json")
    old_market_test = []
    for r in test_prices:
        copy = dict(r)
        copy["sport"]=[previous[r["race_id"]][n] for n in r["numbers"]]
        old_market_test.append(copy)
    old_market,_=evaluate_market(old_market_test,market_reference["weights"])
    price_comparison={
      "v4_retrained":{k:new_market[k] for k in ("races","log_loss","brier","top1","by_odds","positive_ev_diagnostic")},
      "frozen_v3_plus_frozen_v2":{k:old_market[k] for k in ("races","log_loss","brier","top1","by_odds","positive_ev_diagnostic")},
      "excluded_2025":val_exclusions,"excluded_2026":price_exclusions,
      "market_fit_rows":len(market_fit),"market_test_rows":len(test_prices)
    }
    summary={
       "status":"COMPLETED_RETRAINED_FULL_V4_EXPLORATORY",
       "model_family":"One integrated candidate trained from common 42-feature history data",
       "training_races":len(sports_train),
       "historical_supplement_eligible_races":repair_audit["cohort_eligible"],
       "repaired_runners":repair_audit["runners_repaired"],
       "repair_audit":repair_audit,
       "ranking_train_races":len(stage_train),
       "ranking_calibration_races":len(stage_calibration),
       "market_training_races":len(market_fit),
       "test_races":len(test),
       "test_is_reused_not_independent":True,
       "win":win_evaluation,
       "ranking":stage_evaluation,
       "market":price_comparison,
       "model_lock":str(MODEL/"frozen_before_test.json"),
       "production_changed":False,
       "recommendations_allowed":False,
       "roi":None,
       "limits":config["limitations"]
    }
    save(ROOT/"evaluation.json",summary)
    lines=["# Turf Lab V4 : réentraînement complet expérimental","",
           "**Trois ensembles réentraînés** : gagnant sur 42 variables, Top5 à cinq distributions conditionnelles, correction des cotes. Aucun ancien poids V3/V2 utilisé.",
           "",
           f"Courses de sport entraînement : **{len(sports_train)}** ; courses Top5 : **{len(stage_train)}** ; cotes calibrées : **{len(market_fit)}**.",
           f"Corrections historiques individuelles effectivement injectées : **{repair_audit['runners_repaired']}** coureurs sur **{repair_audit['races_with_verified_repair']}** courses. Les archives restantes NE SONT PAS déclarées complètes.",
           "",
           "## Évaluation 2026 réutilisée (pas vierge)","",
           "| Composant | V3/V2 figées | V4 réentraînée |",
           "|---|---:|---:|",
           f"| Gagnant log loss ↓ | {win_evaluation['frozen_v3']['log_loss']:.5f} | {win_evaluation['new_v4']['log_loss']:.5f} |",
           f"| Gagnant top1 | {win_evaluation['frozen_v3']['top1_accuracy']:.2%} | {win_evaluation['new_v4']['top1_accuracy']:.2%} |",
           f"| Top5 chevaux retrouvés (sur 5) | {stage_evaluation['v3_win_top5_baseline']['top5_overlap_mean']:.3f} | {stage_evaluation['new_v4_ranking']['top5_overlap_mean']:.3f} |",
           f"| Top5 exact | {stage_evaluation['v3_win_top5_baseline']['top5_exact_rate']:.2%} | {stage_evaluation['new_v4_ranking']['top5_exact_rate']:.2%} |",
           f"| Correction cotes log loss ↓ | {old_market['log_loss']:.5f} | {new_market['log_loss']:.5f} |",
           "",
           "**Restrictions majeures :**",
           "- Le supplément individuel sur 618 courses a été collecté rétrospectivement, pas en 2024/2025 avant départ. Seuls les départs datant strictement d'avant la course cible ont été repris.",
           "- L'évaluation 2026 a déjà été inspectée dans d'anciennes expériences ; aucune promotion automatique.",
           "- Les cotes sont des archives PMU, pas des prix ZEturf acceptés ; aucune rentabilité démontrée.",
           "- Pas de paris réels tant que la cohorte prospective V4 n'a pas établi de gain et d'absence de calibration dangereuse.",
           ""]
    (ROOT/"RESULTS.md").write_text("\n".join(lines))
    status("COMPLETED_EXPLORATORY",repaired_runners=repair_audit["runners_repaired"],
           train_races=len(sports_train),test_races=len(test),
           new_log_loss=win_evaluation["new_v4"]["log_loss"],
           new_market_log_loss=new_market["log_loss"])
    print(json.dumps({"sports_train":len(sports_train),"ranking_train":len(stage_train),
          "market_train":len(market_fit),"repaired_runners":repair_audit["runners_repaired"],
          "winner_ll":{k:v["log_loss"] for k,v in win_evaluation.items() if k!="paired_week"},
          "market_ll":{"frozen":old_market["log_loss"],"v4":new_market["log_loss"]}},
          indent=2),flush=True)


if __name__=="__main__":
    try:
        main()
    except Exception as error:
        status("FAILED",reason=type(error).__name__+": "+str(error))
        raise
