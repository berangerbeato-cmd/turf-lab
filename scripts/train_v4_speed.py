"""Re-train one isolated 43-feature V4 speed challenger, not a public V5.

Reuse exact 42-feature V4 repaired historical data and append ONE old
V7 contextual speed feature from verified original raw PMU partitions.
New winner, FIVE conditional rankers, new market correction.
Only 2022-2025 fit/calibrate, 2026 previously inspected descriptive test.
No execution/acceptance of ZEturf wagers or automatic production promotion.
"""
import gzip
import json
from pathlib import Path
import numpy as np

from scripts.train_v4_full import (add_truth, fit_ranker, rank_top5, read,
  read_original_v3_test, save, sha, simple_top5_stats)
from scripts.train_available_history_v3 import sources
from scripts.train_market_repair import dataset as market_dataset, evaluate as evaluate_market
from turf_lab.available_history_research import (available_features,calibrate_temperature)
from turf_lab.context_speed import augment as old_speed_augment
from turf_lab.fast_logit import fit as fit_sport
from turf_lab.full_history_evaluation import chronological,score,paired,temper
from turf_lab.market_repair import fit as fit_market
from turf_lab.pilot import probabilities
from turf_lab.ranking_research import finish
from turf_lab.v4_retrain_data import reconcile,v4_rows,load_paired_cohort
from turf_lab.v4_speed_data import raw_pace_records,dated_speed_features,append_speed
from turf_lab.evidence import dump

ROOT=Path("reports/v4_speed")
MODELS=Path("models/v4_speed")
POLICY=Path("config/v4_speed_ablation.json")


def main():
    if (ROOT/"evaluation.json").exists() or (MODELS/"frozen_before_test.json").exists():
        raise ValueError("Frozen V4 speed experiment exists; refusing to re-fit from test")
    cfg=read(POLICY)
    if cfg["status"]!="EXPLORATORY_NOT_PROMOTED" or cfg["recommendations_allowed"] is not False:
        raise ValueError("No policy to promote or bet")
    base_cfg=read("config/v4_full_training.json")
    original=read("reports/v4_full/evaluation.json")
    existing_lock=read("models/v4_full/frozen_before_test.json")
    if existing_lock["models_sha256"]!={p:sha(Path("models/v4_full")/p) for p in ("winner.json","ranking.json","market.json")}:
        raise ValueError("Baseline V4 weights have been modified")
    if original["status"]!="COMPLETED_RETRAINED_FULL_V4_EXPLORATORY":
        raise ValueError("Baseline full V4 was not trained")
    raw_manifest=read("reports/full_history/datasets/manifest.json")
    frames={}
    for group,item in raw_manifest["splits"].items():
        if sha(item["file"])!=item["sha256"]:
            raise ValueError("V4 base dataset SHA mismatch")
        with gzip.open(item["file"],"rt") as fd:
            frames[group]=[json.loads(line) for line in fd]
        if len(frames[group])!=item["races"]:
            raise ValueError("Race count mismatch")
    chronological(frames["train"],frames["validation"],frames["test"])
    records,source_manifest=sources()
    expected_ids={r["race_id"] for sample in frames.values() for r in sample}
    base_aug,old_audit=available_features(records,sum(frames.values(),[]),
                                          base_cfg["dq_prior_strength"])
    if {r["race_id"] for r in base_aug} != expected_ids:
        raise ValueError("V4 full source cohort mismatch")
    supplemental,eligible,history_lock=load_paired_cohort()
    checked,repair_audit,changes=reconcile(base_aug,supplemental,eligible)
    if repair_audit["runners_repaired"]!=original["repaired_runners"]:
        raise ValueError("Reconstructed history not identical to baseline V4")
    corrected=v4_rows(checked)
    dated_timing=raw_pace_records(records)
    policy=read(cfg["speed_policy_file"])
    speed,history_coverage=dated_speed_features(dated_timing,policy)
    extra,train_cover=append_speed(corrected,speed)
    by_base={r["race_id"]:r for r in corrected}
    by_speed={r["race_id"]:r for r in extra}
    groups={s:[by_speed[r["race_id"]] for r in rows] for s,rows in frames.items()}
    original_groups={s:[by_base[r["race_id"]] for r in rows] for s,rows in frames.items()}
    cover={}
    for split,rows in groups.items():
        total=sum(not r["non_runner"] for x in rows for r in x["runners"])
        count=sum(not r["non_runner"] and r["features"][-1] is not None
                  for x in rows for r in x["runners"])
        cover[split]={"active_runners":total,"with_context_speed":count,
                      "fraction":count/max(1,total)}
    for split in ("train","test"):
        if cover[split]["fraction"] < cfg["minimum_speed_coverage_"+split]:
            raise ValueError("Speed evidence under required coverage in "+split)
    save(ROOT/"data_audit.json",{
        "history_repair":repair_audit,
        "speed_coverage_all":history_coverage,
        "speed_coverage_target":train_cover,
        "coverage_by_split":cover,
        "only_one_new_feature":True,
        "history_repair_locked_sha256":sha("models/sport_history_cohort_v2/frozen.json"),
        "speed_protocol_sha256":sha(cfg["speed_policy_file"]),
        "retrospective_timing_not_original_prestart_snapshot":True
    })
    print("Reconciled and speed features built",json.dumps(cover),flush=True)

    train=groups["train"]
    early=[r for r in groups["validation"] if r["date"]<"2025-07-01"]
    late=[r for r in groups["validation"] if r["date"]>="2025-07-01"]
    if not train or not early or not late or any(len(x["features"]) != 43
                   for r in extra for x in r["runners"]):
        raise ValueError("V4 speed training chronological groups or width invalid")

    sport=fit_sport(train,cfg["winner_l2"],cfg["winner_iterations"],
                   cfg["winner_learning_rate"])
    temperature=calibrate_temperature(early,[probabilities(r,sport) for r in early])
    save(MODELS/"winner.json",{
        "model":sport,"temperature":temperature,
        "features":43,"fit_races":len(train),"calibration_races":len(early)
    })
    print("Winner V4+Speed trained",temperature,flush=True)

    truths={r["race_id"]:finish(r["participants"]) for r in records}
    stage_train=add_truth(train,truths)
    stage_cal=add_truth(early,truths)
    ranking=fit_ranker(stage_train,stage_cal,{"ranking_ridge":cfg["ranker_ridge"]})
    save(MODELS/"ranking.json",ranking)
    print("Top5 V4+Speed trained",len(stage_train),flush=True)

    market_policy=read("config/value_correction_v2.json")
    price_validation,discarded_fit,fit_sources=market_dataset("validation",market_policy)
    late_probs={r["race_id"]:p for r,p in zip(late,
                temper(late,[probabilities(r,sport) for r in late],temperature))}
    market_train=[r for r in price_validation if r["date"]>="2025-07-01"]
    for r in market_train:
        if r["race_id"] not in late_probs:
            raise ValueError("Unexpected market fit cohort")
        r["sport"]=[late_probs[r["race_id"]][n] for n in r["numbers"]]
    if len(market_train) != original["market_training_races"]:
        raise ValueError("V4 baseline and V4 Speed market fit cohorts differ")
    market=fit_market(market_train,market_policy)
    save(MODELS/"market.json",market)
    print("New market correction fitted",market["weights"],flush=True)

    # Freeze all new weights and source/feature policy BEFORE inspecting 2026.
    lock={
        "version":cfg["version"],"status":"FROZEN_BEFORE_REUSED_TEST",
        "frozen_v4_sha256":sha("models/v4_full/frozen_before_test.json"),
        "config_sha256":sha(POLICY),
        "old_speed_protocol_sha256":sha(cfg["speed_policy_file"]),
        "speed_reconstruction_code_sha256":sha("turf_lab/v4_speed_data.py"),
        "prior_speed_builder_sha256":sha("turf_lab/context_speed.py"),
        "training_code_sha256":sha("scripts/train_v4_speed.py"),
        "source_manifest_shas":source_manifest,
        "datasets_sha":{k:v["sha256"] for k,v in raw_manifest["splits"].items()},
        "three_new_model_hashes":{x:sha(MODELS/x) for x in ("winner.json","ranking.json","market.json")},
        "repaired_runners":repair_audit["runners_repaired"],
        "speed_coverage":cover,
        "test_already_examined":True,"production_changed":False,"recommendations_allowed":False,
        "limits":cfg["limitations"]
    }
    save(MODELS/"frozen_before_test.json",lock)
    print("All three V4+Speed models FROZEN; now test 2026",flush=True)

    test=groups["test"]
    plain=original_groups["test"]
    reference_winner=read("models/v4_full/winner.json")
    baseline=temper(plain,[probabilities(r,reference_winner["model"]) for r in plain],
                    reference_winner["temperature"])
    baseline_report=score(plain,baseline)["overall"]
    if (abs(baseline_report["log_loss"]-original["win"]["new_v4"]["log_loss"])>1e-9
            or abs(baseline_report["brier_multiclass"]-original["win"]["new_v4"]["brier_multiclass"])>1e-9):
        raise ValueError("Original V4 winner could not be reproduced exactly")
    candidate=temper(test,[probabilities(r,sport) for r in test],temperature)
    sport_new=score(test,candidate)["overall"]
    sport_pair=paired(test,baseline,candidate,repetitions=500)

    compare_ranking=read("models/v4_full/ranking.json")
    selected=add_truth(test,truths)
    original_selected=add_truth(plain,truths)
    new_top=[rank_top5(r,ranking) for r in selected]
    old_top=[rank_top5(r,compare_ranking) for r in original_selected]
    old_rank=simple_top5_stats(original_selected,old_top)
    if (abs(old_rank["top5_overlap_mean"]-original["ranking"]["new_v4_ranking"]["top5_overlap_mean"])>1e-12
            or old_rank["top5_exact_count"]!=original["ranking"]["new_v4_ranking"]["top5_exact_count"]):
        raise ValueError("V4 baseline ranking is not reproducible")
    new_rank=simple_top5_stats(selected,new_top)
    price_test,discarded_test,price_sources=market_dataset("test",market_policy)
    if len(price_test)!=original["market"]["market_test_rows"]:
        raise ValueError("Original V4 price evaluation race set changed")
    current={r["race_id"]:p for r,p in zip(test,candidate)}
    prior={r["race_id"]:p for r,p in zip(plain,baseline)}
    previous_price_weights=read("models/v4_full/market.json")["weights"]
    old_market=[]
    for row in price_test:
        if row["race_id"] not in prior or row["race_id"] not in current:
            raise ValueError("Market evaluation missing same sports event")
        past=dict(row,sport=[prior[row["race_id"]][n] for n in row["numbers"]])
        old_market.append(past)
        row["sport"]=[current[row["race_id"]][n] for n in row["numbers"]]
    old_price,_=evaluate_market(old_market,previous_price_weights)
    if abs(old_price["log_loss"]-original["market"]["v4_retrained"]["log_loss"])>1e-10:
        raise ValueError("Original V4 market evaluation not reproducible")
    new_price,_=evaluate_market(price_test,market["weights"])
    evaluation={
      "version":cfg["version"],"status":"COMPLETED_EXPLORATORY_REUSED_2026",
      "production_changed":False,"recommendations_allowed":False,
      "all_3_weights_freshly_refitted":True,"speed_features_added":1,
      "baseline":"FROZEN_TURF_LAB_V4_FULL","candidate":"V4_PLUS_CONTEXT_CORRECTED_SPEED",
      "training_races":len(train),"ranking_train_races":len(stage_train),
      "ranking_calibration_races":len(stage_cal),"market_fit_races":len(market_train),
      "test_races":len(test),"ranking_test_races":len(selected),
      "speed_coverage":cover,"history_repaired_runners":repair_audit["runners_repaired"],
      "winner":{"v4_frozen":baseline_report,"v4_speed":sport_new,
                "paired_week_v4_speed_minus_v4":sport_pair},
      "top5":{"v4_frozen":old_rank,"v4_speed":new_rank},
      "market":{"v4_frozen":{k:old_price[k] for k in
                              ("races","log_loss","brier","top1","by_odds","positive_ev_diagnostic")},
                "v4_speed":{k:new_price[k] for k in
                              ("races","log_loss","brier","top1","by_odds","positive_ev_diagnostic")}},
      "test_not_independent":True,"roi":None,
      "decision":"DO_NOT_PROMOTE_WITHOUT_PRESTART_PARITY_AND_VIRGIN_TEST",
      "limitations":cfg["limitations"]
    }
    save(ROOT/"evaluation.json",evaluation)
    lines=["# V4 + anciens chronos corrigés V7 : essai isolé","",
        "**Trois nouvelles séries de poids, sans modification de la V4 publique.**",
        f"Entraînement gagnant {len(train)} courses, classement {len(stage_train)}, cotes {len(market_train)}.",
        f"Chronos antérieurs présents : train {cover['train']['fraction']:.1%}, test {cover['test']['fraction']:.1%}.",
        "Les mêmes 365 coureurs historiques vérifiés restent corrigés dans les deux variantes.","",
        "## Résultats 2026 : test déjà vu, pas indépendant",
        "| Mesure | V4 actuelle | V4 + vitesse |",
        "|---|---:|---:|",
        f"| Gagnant log loss ↓ | {baseline_report['log_loss']:.6f} | {sport_new['log_loss']:.6f} |",
        f"| Gagnant Brier ↓ | {baseline_report['brier_multiclass']:.6f} | {sport_new['brier_multiclass']:.6f} |",
        f"| Premier cheval gagnant | {baseline_report['top1_accuracy']:.2%} | {sport_new['top1_accuracy']:.2%} |",
        f"| Top5 chev. trouvés / 5 | {old_rank['top5_overlap_mean']:.4f} | {new_rank['top5_overlap_mean']:.4f} |",
        f"| Top5 exact | {old_rank['top5_exact_count']}/{len(selected)} | {new_rank['top5_exact_count']}/{len(selected)} |",
        f"| Correction cotes log loss ↓ | {old_price['log_loss']:.6f} | {new_price['log_loss']:.6f} |",
        "",
        "Comparaison log loss appariée hebdomadaire : "+
              json.dumps(sport_pair["metrics"]["log_loss"],ensure_ascii=False)+".",
        "",
        "**Ne pas promouvoir automatiquement** : période de test 2026 déjà inspectée, problème d'équivalence de calcul du chrono sur les courses futures encore à vérifier, prix PMU rétrospectifs, aucun ROI ZEturf.",
        "La V4 publique et tous ses fichiers gelés demeurent inchangés."
    ]
    (ROOT/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"v4_ll":baseline_report["log_loss"],"speed_ll":sport_new["log_loss"],
       "v4_top5":old_rank["top5_exact_count"],"speed_top5":new_rank["top5_exact_count"],
       "v4_market_ll":old_price["log_loss"],"speed_market_ll":new_price["log_loss"]},
      indent=2),flush=True)
    return evaluation


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        dump(ROOT/"failure.json",{"error":type(exc).__name__+": "+str(exc),
                                 "promoted":False,"production_changed":False})
        raise
