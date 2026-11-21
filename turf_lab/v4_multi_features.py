"""Three jointly added V4 inputs: relative historical class, weighted form, R.

1. Relative class is a strictly prior *ordinal gain-points proxy*, NOT
   historical career euros: previous official 1st/2nd/3rd/4th/5th returns
   [10,6,4,2,1] points. Historic PMU career-euro as-of availability is not
   independently attested; no post-event earnings may enter the model.
2. Weighted recent form uses pretarget five official starts and prespecified
   weights 35%,25%,18%,12%,10% (newest first); DQ is a negative result.
3. R is a descriptive data-completeness INDEX, not calibrated certainty.
   Market conditioning of R will be FIT, not set by a handmade probability.

Same-day results are appended only after EVERY target on that date was
transformed. History Repair can change the 5-start coverage of a target;
that repaired coverage is passed via its 43-feature row.
"""
import hashlib
import json
import math
from collections import defaultdict
from itertools import groupby
from copy import deepcopy
from pathlib import Path

from turf_lab.month_history import identity

WEIGHTS=(.35,.25,.18,.12,.10)
POINTS={1:10.,2:6.,3:4.,4:2.,5:1.}
VERSION="v4_integrated_class_form_reliability_1"


def known_score(result):
    incident=str(result.get("incident") or "")
    if incident.startswith("DISQUALIFIE") or incident=="DISTANCE":
        return -0.70
    rank=result.get("ordreArrivee")
    if not isinstance(rank,int) or isinstance(rank,bool) or rank<=0:
        return None
    return {1:1.,2:.65,3:.45,4:.20,5:.20}.get(rank,0.)


def fingerprint(entries):
    """A source pointer/checksum only; no result of today's race in this input."""
    raw=json.dumps(entries,sort_keys=True,ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def derive(rows,records):
    """Compute three features for every target race, past days ONLY.

    row features have EXACTLY 43 values: 42 frozen V4 + V7 chrono.
    """
    by_id={r["race_id"]:r for r in rows}
    if len(by_id)!=len(rows) or len({r["race_id"] for r in records})!=len(records):
        raise ValueError("Duplicate race in class/form/R evidence")
    if not set(by_id)<= {r["race_id"] for r in records}:
        raise ValueError("Target race missing from official class/form/R data")
    historical=defaultdict(list);class_points=defaultdict(float)
    results={};counts={"runners":0,"valid_form":0,"prior_class":0,
                       "races":0,"runners_with_5_observed":0}
    # Never read same-day outcomes before all that day's target features.
    for day,iterator in groupby(sorted(records,key=lambda r:(r["date"],r["race_id"])),
                                key=lambda r:r["date"]):
        group=list(iterator)
        for source in group:
            rid=source["race_id"]
            if rid not in by_id:
                continue
            frame=by_id[rid]
            current={p["numPmu"]:p for p in source["participants"]}
            if set(current)!={r["number"] for r in frame["runners"]}:
                raise ValueError("Relative class and form runner set changed")
            for runner in frame["runners"]:
                if identity(current[runner["number"]])!=runner["horse_id"]:
                    raise ValueError("Relative class horse identity disagreement")
                if len(runner["features"])!=43:
                    raise ValueError("Relative class/form/R requires 43 base features")
            eligible=[r for r in frame["runners"] if not r["non_runner"]]
            score={r["number"]:math.log1p(class_points[r["horse_id"]]) for r in eligible}
            # Relative class compares only current opponents; no global bonus.
            field_mean=sum(score.values())/len(score) if score else 0
            result={}
            for runner in frame["runners"]:
                n=runner["number"];ident=runner["horse_id"]
                latest=historical[ident][-5:][::-1]
                observed=[(w,known_score(v)) for w,v in zip(WEIGHTS,latest)]
                observed=[(w,s) for w,s in observed if s is not None]
                form=(sum(w*s for w,s in observed)/sum(w for w,_ in observed)
                      if observed else None)
                completeness=sum(w for w,_ in observed)
                # The 5-start feature was itself reconciled by History Repair;
                # R accounts for both recalled and explicitly observed evidence.
                avail=runner["features"][4]
                if (not isinstance(avail,(float,int)) or isinstance(avail,bool)
                        or not math.isfinite(avail) or not 0<=avail<=1):
                    raise ValueError("History Repair 5-start coverage invalid")
                speed_available=runner["features"][42] is not None
                R=.5*avail + .3*completeness + .2*float(speed_available)
                if not 0<=R<=1.00000001:
                    raise ValueError("Invalid data completeness R")
                rel=(math.log1p(class_points[ident])-field_mean if n in score else 0.0)
                result[n]={"horse_id":ident,"relative_class_proxy":rel,
                           "weighted_recent_form":form,
                           "reliability_R":R,
                           "prior_career_points":class_points[ident],
                           "known_form_weight":completeness,
                           "count_recent_observed":len(latest),
                           "class_is_verified_euros":False}
                if not runner["non_runner"]:
                    counts["runners"]+=1
                    counts["valid_form"]+=form is not None
                    counts["prior_class"]+=class_points[ident]>0
                    counts["runners_with_5_observed"]+=len(latest)==5
            results[rid]=result
            counts["races"]+=1
        for source in group:
            for p in source["participants"]:
                if p.get("statut")!="PARTANT":continue
                key=identity(p)
                event={"ordreArrivee":p.get("ordreArrivee"),
                       "incident":p.get("incident")}
                historical[key].append(event)
                rank=p.get("ordreArrivee")
                if (isinstance(rank,int) and not isinstance(rank,bool)
                        and rank in POINTS
                        and not (str(p.get("incident") or "").startswith("DISQUALIFIE"))):
                    class_points[key]+=POINTS[rank]
    if set(results)!=set(by_id):
        raise ValueError("Some history/form targets not evaluated")
    return results,counts


def attach(rows, feature_data):
    """Append 3 predictors, preserving the existing 43 untouched."""
    out=[];counts={"races":len(rows),"runners":0,"form_missing":0}
    for row in rows:
        per=feature_data.get(row["race_id"])
        if per is None or set(per)!={r["number"] for r in row["runners"]}:
            raise ValueError("Missing/changed extra feature field")
        updated=dict(row,runners=[])
        for horse in row["runners"]:
            values=per[horse["number"]]
            if horse["horse_id"]!=values["horse_id"] or len(horse["features"])!=43:
                raise ValueError("46 feature identity/width mismatch")
            added=[values["relative_class_proxy"],
                   values["weighted_recent_form"],values["reliability_R"]]
            if any(v is not None and
                   (not isinstance(v,(float,int)) or not math.isfinite(v))
                   for v in added):
                raise ValueError("Nonfinite added class/form/reliability")
            updated["runners"].append(dict(horse,features=list(horse["features"])+added))
            if not horse["non_runner"]:
                counts["runners"]+=1
                counts["form_missing"]+=values["weighted_recent_form"] is None
        out.append(updated)
    return out,counts


def live_context(prior_records,target,base43):
    """Reuse same historical derivation for the live race; never target result."""
    from datetime import datetime, timezone
    if (not prior_records or
            any(r["date"]>=target["date"] for r in prior_records) or
            len({r["race_id"] for r in prior_records})!=len(prior_records)):
        raise ValueError("Class/Form/R evidence must be from earlier days")
    if base43["race_id"]!=target["race_id"]:
        raise ValueError("Mismatched live 43-feature target")
    outputs,_=derive([base43],list(prior_records)+[target])
    per=outputs[target["race_id"]]
    _,check=attach([base43],outputs)
    return {
        "version":VERSION,"race_id":target["race_id"],
        "target_date":target["date"],
        "captured_at":datetime.now(timezone.utc).isoformat(),
        "prior_races":len(prior_records),
        "last_prior_day":max(x["date"] for x in prior_records),
        "source_hash":fingerprint([(r["race_id"],r["date"]) for r in prior_records]),
        "same_day_result_used":False,
        "class_basis":"prior_official_finish_points_relative_to_current_field_NOT_EUR_GAIN",
        "form_weights_newest_first":list(WEIGHTS),
        "reliability_is_data_completeness_not_a_probability":True,
        "per_runner":{str(n):v for n,v in sorted(per.items())},
        "active_horses":check["runners"],
        "contains_target_outcome":False
    }
