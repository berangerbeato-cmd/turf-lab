"""Fit the missing DQ-to-winner coefficient on 2025 H1 BEFORE 2026 review.

Already fitted: 47f win model, 2022-24 DQ logistic, 2025 H1 groupwise
course temperatures, H2 market R and price-bands. To avoid double-penalizing
a horse for DQ, learn a SIGNED, regularized residual correction to the
baseline on 2025 H1 only. The optimum is allowed to be zero or negative.
No gambling is authorized.
"""
import gzip
import json
import math
from pathlib import Path
from scipy.optimize import minimize_scalar

from scripts.train_available_history_v3 import sources
from scripts.train_v4_full import read,save,sha
from turf_lab.available_history_research import available_features
from turf_lab.full_history_evaluation import chronological,temper
from turf_lab.pilot import active,probabilities
from turf_lab.v4_retrain_data import reconcile,v4_rows,load_paired_cohort
from turf_lab.v4_speed_data import raw_pace_records,dated_speed_features,append_speed
from turf_lab.v4_multi_features import bring_historical_money,derive,attach
from turf_lab.v4_multifeature_inference import frozen as frozen_47
from turf_lab.v4_next_inference import frozen as frozen_bundle
from turf_lab.v4_next_research import predict_dq,apply_context
from turf_lab.v4_active_final import residual_dq
from turf_lab.evidence import dump

OUT=Path("models/v4_active_activation")
LOCK=OUT/"frozen_activation.json"
PARAM=OUT/"dq_residual.json"
REPORT=Path("reports/v4_active_activation/RESULTS.md")
POLICY=Path("config/v4_all_active_policy.json")


def main():
    if LOCK.exists() or PARAM.exists():
        raise ValueError("Active DQ residual already fitted; do not re-optimize")
    protocol=read(POLICY)
    if (protocol["status"]!="SINGLE_V4_ALL_ACTIVE_NO_BET" or
            protocol["recommendations_allowed"] is not False):
        raise ValueError("Active V4 policy is missing")
    allmodels,oldlock=frozen_47()
    bundle,bundlelock=frozen_bundle()
    manifest=read("reports/full_history/datasets/manifest.json")
    splits={}
    for split,meta in manifest["splits"].items():
        if sha(meta["file"])!=meta["sha256"]:
            raise ValueError("Original historical dataset SHA mismatch")
        with gzip.open(meta["file"],"rt") as f:
            splits[split]=[json.loads(line) for line in f]
        if len(splits[split])!=meta["races"]:
            raise ValueError("Historical race count mismatch")
    chronological(splits["train"],splits["validation"],splits["test"])
    records,original_sources=sources()
    original=sum(splits.values(),[])
    base,original_audit=available_features(
        records,original,read("config/v4_full_training.json")["dq_prior_strength"])
    supplemental,allowed,lock=load_paired_cohort()
    repaired,diagnostics,changes=reconcile(base,supplemental,allowed)
    if diagnostics["runners_repaired"]!=365:
        raise ValueError("Expected old verified history patch cohort changed")
    base42=v4_rows(repaired)
    timed,pace_audit=dated_speed_features(raw_pace_records(records),
                                         read("config/speed_v7_protocol.json"))
    base43,_=append_speed(base42,timed)
    augmented_money=bring_historical_money(records)
    extra,_=derive(base43,augmented_money)
    enriched,_=attach(base43,extra)
    byid={r["race_id"]:r for r in enriched}
    if len(byid)!=len(enriched):
        raise ValueError("Duplicate new V4 row")
    validation=[
        byid[r["race_id"]] for r in splits["validation"]
        if "2025-01-01"<=r["date"]<="2025-06-30"
    ]
    if len(validation)<2500 or any(len(h["features"])!=47 for r in validation
                                    for h in r["runners"]):
        raise ValueError("Insufficient 2025 H1 historical correction samples")
    win=allmodels["winner"]
    basic=temper(validation,
       [probabilities(r,win["model"]) for r in validation],
       win["temperature"])
    dqs=predict_dq(validation,bundle["disqualification"])
    rows=[]
    for race,p in zip(validation,basic):
        race_id=race["race_id"]
        context,group=apply_context(
            {h["number"]:p[h["number"]] for h in active(race)},
            race["venue"],race["start_type"],race["distance_m"],
            bundle["race_context"])
        risk=dqs[race_id]
        if set(context)!=set(risk):
            raise ValueError("Disqualification and same-race context fields differ")
        winner=next(h["number"] for h in active(race) if h["won"])
        rows.append((race_id,context,risk,winner))
    ridge=float(protocol["dq_residual_ridge"])
    if not 0<=ridge<=1:
        raise ValueError("DQ ridge outside predeclared protocol")
    def loss(weight):
        nll=0.
        for rid,p,dq,winner in rows:
            fixed=residual_dq(p,dq,weight)
            nll-=math.log(max(1e-15,fixed[winner]))
        return nll/len(rows) + ridge*weight*weight
    solution=minimize_scalar(loss,method="bounded",
                             bounds=tuple(protocol["dq_residual_bounds"]),
                             options={"xatol":1e-9,"maxiter":200})
    if not solution.success:
        raise ValueError("DQ residual fit failed")
    coefficient=float(solution.x)
    model={"version":"dq_survival_residual_fit_2025h1",
           "method":"AS_OF_LOG_DQ_SURVIVAL_RESIDUAL",
           "coefficient":coefficient,
           "training_period":["2025-01-01","2025-06-30"],
           "training_races":len(rows),"ridge":ridge,
           "fitting_brier_or_profit_not_claimed":True,
           "fit_log_loss_at_zero":loss(0.),
           "fit_log_loss_fitted":loss(coefficient),
           "status":"FITTED_ACTIVE_IN_SINGLE_RESEARCH_V4",
           "positive_weight_means_extra_risk_penalty":coefficient>0,
           "negative_weight_compensates_baseline_overpenalty":coefficient<0,
           "approved_stakes":False}
    save(PARAM,model)
    activation={
        "version":"turf_lab_v4_fully_integrated_1",
        "status":"ACTIVATED_SINGLE_V4_ALL_COMPONENTS",
        "model_name":"TURF_LAB_V4",
        "features":47,
        "prior_bundle_lock_sha256":sha("models/v4_next_bundle/frozen_before_test.json"),
        "v4_47f_lock_sha256":sha("models/v4_multifeature/frozen_before_test.json"),
        "dq_residual_sha256":sha(PARAM),
        "activation_policy_sha256":sha(POLICY),
        "active_engine_sha256":sha("turf_lab/v4_active_final.py"),
        "training_code_sha256":sha("scripts/calibrate_v4_active_final.py"),
        "all_applied":["history_repair_v2","disqualification_fitted_signed_residual",
                       "venue_start_distance_temperature","odds_band_after_R_market",
                       "quinte_max_unordered_joint","past_47_features"],
        "dq_fitted_before_2026":True,
        "2026_not_used_to_select_DQ_residual":True,
        "prospective_independent_validation_done":False,
        "recommendations_allowed":False,
        "actual_betting_roi_known":False}
    save(LOCK,activation)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(
        "# V4 unique : activation de toutes les améliorations\n\n"
        "Tous les blocs sont désormais appliqués dans **le calcul principal** du moteur unique V4 : "
        "47 variables, History Repair V2 comme contrôle strict, correction signée DQ calibrée, "
        "températures parcours/départ/distance, modèle R de marché suivi de la calibration par "
        "tranche de cote pour une grille pré-départ vérifiée, et Quinté choisi par la meilleure "
        "probabilité jointe sans ordre.\n\n"
        f"**Coefficient DQ signé (appris avant 2026)** : {coefficient:.9f}. "
        f"Log loss ajustée 2025 H1, λ=0 : {loss(0.):.8f} ; "
        f"λ ajusté : {loss(coefficient):.8f} ; courses : {len(rows)}.\n\n"
        "**Attention** : 2025 H1 avait déjà servi à calibrer le gagnant et la "
        "température par groupe. Ce n'est donc **pas une validation indépendante**. "
        "Les cotes réelles et les résultats prospectifs restent à collecter. "
        "Pas de preuve de ROI, **NO BET** conservé.\n",encoding="utf-8")
    print(json.dumps({
        "status":"FITTED_AND_ACTIVATION_LOCKED",
        "dq_weight":coefficient,
        "baseline_fit_loss":loss(0.),
        "fitted_fit_loss":loss(coefficient),
        "fitted_races":len(rows)
    },indent=2),flush=True)


if __name__=="__main__":
    try:main()
    except Exception as exc:
        dump("reports/v4_active_activation/failure.json",
             {"status":"NOT_ACTIVE","error":type(exc).__name__+": "+str(exc),
              "no_betting":True})
        raise
