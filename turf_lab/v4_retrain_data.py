"""V4 training-time history reconciliation, strictly before each target date.

Source: dated PMU historical records and immutable 618-race supplemental
reconciliation cohort. No invented starts, no cross-runner imputation.
The historical individual responses were collected retrospectively; that is
recorded explicitly and no independent virgin holdout is claimed.
"""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

from turf_lab.available_history_research import variant

COHORT = Path("reports/sport_history_cohort_v2")
LOCK = Path("models/sport_history_cohort_v2/frozen.json")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_paired_cohort():
    lock = json.loads(LOCK.read_text())
    files = {k:COHORT/(k+".jsonl.gz") for k in ("original","enriched")}
    for name,path in files.items():
        if digest(path) != lock["provenance"]["datasets"][name]:
            raise ValueError("Supplemental individual history cohort SHA changed")
    groups = {}
    for name,path in files.items():
        with gzip.open(path,"rt") as stream:
            data = [json.loads(s) for s in stream]
        groups[name] = {r["race_id"]:r for r in data}
        if len(groups[name]) != len(data):
            raise ValueError("Duplicate supplemental cohort target")
    if groups["original"].keys() != groups["enriched"].keys():
        raise ValueError("Supplemental cohort pairing mismatch")
    collection = json.loads((COHORT/"collection.json").read_text())
    approved = {r["race_id"]:r for r in collection["audit"] if r["status"] == "ELIGIBLE"}
    if set(approved) != set(groups["original"]):
        raise ValueError("Supplemental cohort eligibility mismatch")
    return groups,approved,lock


def reconcile(augmented, cohorts, audit, window_dates=("2022-03-02","2026-09-30")):
    """Correct only *verifiable matching* historical five-start features.

    V3 five-available-start baseline and the old 60-day cohort need not
    match: if they differ, no patched version is silently substituted.
    """
    result = []
    details = Counter()
    modifications = []
    old = cohorts["original"]
    enriched = cohorts["enriched"]
    for row in augmented:
        rid = row["race_id"]
        if not window_dates[0] <= row["date"] <= window_dates[1]:
            raise ValueError("Unexpected training date")
        if rid not in old:
            details["races_archive_only"] += 1
            result.append(row)
            continue
        prior = old[rid]
        updated = enriched[rid]
        if rid != prior["race_id"] or rid != updated["race_id"] or row["date"] != prior["date"] != updated["date"]:
            raise ValueError("Supplemental race identity mismatch")
        a = {r["number"]:r for r in prior["runners"]}
        b = {r["number"]:r for r in updated["runners"]}
        if set(a) != set(b) or set(a) != {r["number"] for r in row["runners"]}:
            raise ValueError("Supplemental horse field changed")
        for runner in row["runners"]:
            number = runner["number"]
            x,y = a[number],b[number]
            if (x["horse_id"] != y["horse_id"] or x["horse_id"] != runner["horse_id"]
                    or x["won"] != y["won"] or x["won"] != runner["won"]
                    or x["non_runner"] != y["non_runner"] or x["non_runner"] != runner["non_runner"]):
                raise ValueError("Supplemental horse identity/outcome mismatch")
            if runner["non_runner"]:
                continue
            baseline = runner["available_recent"]
            if baseline != x["features"][:5]:
                details["runners_cohort_baseline_mismatch_abstained"] += 1
                continue
            candidate = y["features"][:5]
            if len(candidate) != 5:
                raise ValueError("Invalid individual history feature width")
            if candidate == baseline:
                details["runners_verified_unchanged"] += 1
                continue
            if not 0 <= candidate[4] <= 1 or candidate[4] < baseline[4]:
                # A purported repair must not make a verified record disappear.
                raise ValueError("Repair unexpectedly removes known starts")
            # Value is derived from strict pre-target dated individual history
            # in the locked, already-audited supplemental cohort.
            runner["available_recent"] = candidate
            modifications.append({"race_id":rid,"number":number,"from":baseline,"to":candidate})
            details["runners_repaired"] += 1
        details["races_cohort_available"] += 1
        result.append(row)
    details["races_input"] = len(augmented)
    details["races_with_verified_repair"] = len({r["race_id"] for r in modifications})
    details["cohort_eligible"] = len(old)
    details["cohort_historical_detail_extra_starts"] = sum(int(a.get("added_starts",0)) for a in audit.values())
    return result, dict(details), modifications


def v4_rows(augmented):
    """Uniform 42-feature sports and stage matrices after limited corrections."""
    return variant(augmented,"last5_available_dq20")
