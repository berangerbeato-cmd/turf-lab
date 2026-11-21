"""History Repair V2: conservative source reconciliation and reasoned quarantine.

Never reinterpret a mismatch of 60-day and 5-available-start vectors as
automatically incorrect. Individual cohort was retrieved retrospectively;
cross-source agreement is not proof of prestart historical publication.

The frozen V4 47-feature model is NEVER modified by this audit.
"""
from collections import Counter
from math import isclose


def vector_equal(a,b):
    return len(a)==len(b)==5 and all(
        (x is None and y is None) or
        (isinstance(x,(float,int)) and isinstance(y,(float,int))
         and isclose(float(x),float(y),abs_tol=1e-10,rel_tol=0))
        for x,y in zip(a,b))


def reconcile_v2(rows, cohorts):
    old,new=cohorts["original"],cohorts["enriched"]
    if set(old)!=set(new):
        raise ValueError("Supplemental History Repair V2 cohorts do not match")
    report=Counter();cases=[];covered=set()
    for race in rows:
        rid=race["race_id"]
        if rid not in old:
            report["archive_only_races"]+=1
            continue
        before=old[rid];after=new[rid]
        if before["race_id"]!=rid or after["race_id"]!=rid or any(
                x["date"]!=race["date"] for x in (before,after)):
            raise ValueError("Repaired source date / target mismatch")
        b={r["number"]:r for r in before["runners"]}
        a={r["number"]:r for r in after["runners"]}
        current={r["number"]:r for r in race["runners"]}
        if len(b)!=len(before["runners"]) or len(a)!=len(after["runners"]) or set(a)!=set(b) or set(a)!=set(current):
            raise ValueError("Repaired field duplicate or participant mismatch")
        for n,r in current.items():
            prior=b[n];verified=a[n]
            if (prior["horse_id"]!=verified["horse_id"] or
                prior["horse_id"]!=r["horse_id"] or
                prior["non_runner"]!=verified["non_runner"] or
                prior["non_runner"]!=r["non_runner"] or
                prior["won"]!=verified["won"] or prior["won"]!=r["won"]):
                raise ValueError("Repaired historical horse/outcome identity mismatch")
            if r["non_runner"]:
                report["non_runners"]+=1
                continue
            canonical=r["available_recent"]
            baseline=prior["features"][:5]
            detail=verified["features"][:5]
            if vector_equal(canonical,baseline):
                kind="VERIFIED_UPDATED" if not vector_equal(canonical,detail) else "VERIFIED_UNCHANGED"
            elif vector_equal(canonical,detail):
                kind="CANONICAL_ALREADY_MATCHES_INDIVIDUAL"
            elif (isinstance(canonical[4],(int,float)) and
                  isinstance(detail[4],(int,float)) and
                  canonical[4] >= detail[4]):
                # A longer history window should not be truncated to 60 days.
                kind="LONG_WINDOW_NOT_REPLACED"
            else:
                kind="MULTI_SOURCE_CONFLICT_NO_PATCH"
            report[kind]+=1
            if kind in ("MULTI_SOURCE_CONFLICT_NO_PATCH","LONG_WINDOW_NOT_REPLACED"):
                if len(cases)<1000:
                    cases.append({"race_id":rid,"number":n,"reason":kind,
                                  "archive_available_5":canonical[4],
                                  "old_60d_available_5":baseline[4],
                                  "individual_60d_available_5":detail[4]})
        covered.add(rid)
    report["cohort_races_examined"]=len(covered)
    report["archive_races_examined"]=len(rows)
    report["supplemental_races_remaining_unexamined"]=len(set(old)-covered)
    return {"version":"history_repair_v2","summary":dict(report),
            "review_cases":cases,
            "retrospective_source":True,
            "new_corrections_claimed":0,
            "automatic_overwrite_of_disputed_histories":False,
            "original_V4_weights_untouched":True,
            "limitations":["60-day and unrestricted five-start windows are not equivalent",
                           "One verified retrospective observation does not prove its prestart availability",
                           "Disputed history is quarantined, never converted into a false positive repair"]}


def verify_prestart_sidecar(repair,original):
    """V2 quality layer on top of mandatory original V1.1 evidence.

    This is intentionally a strict audit, NOT a fabricated second source.
    """
    if repair["race_id"]!=original["race_id"]:
        raise ValueError("Cross-race History Repair audit")
    audits=repair["runner_audit"]
    if len(audits)!=len(original["target_snapshot"]["participants"]):
        raise ValueError("Missing horse histories")
    bad=[];counts=Counter()
    good=("UPDATED","UNCHANGED","NON_RUNNER")
    for a in audits:
        status=a["status"];counts[status]+=1
        if status not in good:
            bad.append({"number":a["number"],"reason":status})
    if len({a["number"] for a in audits})!=len(audits):
        raise ValueError("Duplicate history runner")
    return {"version":"history_repair_v2","status":"CHECKED" if not bad else "QUARANTINED_UNCERTAINTY",
            "quality_counts":dict(counts),"unresolved":bad,
            "frozen_prior_evidence_reused":True,
            "additional_verified_repair_count":0,
            "was_any_original_feature_rewritten":False}
