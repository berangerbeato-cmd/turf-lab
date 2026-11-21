"""Restore actual historical pace evidence for an isolated V4 speed ablation.

The normal V4 training source intentionally strips numeric race times. This
module reopens only the SAME verified immutable PMU partitions, checks source
hashes and identity, and reuses the dated V7 speed builder without touching
the frozen V4 input/features. Every target day's pace is computed before any
result of that day is inserted in the history.
"""
from collections import Counter
from pathlib import Path
import gzip
import hashlib
import json
import math

from turf_lab.context_speed import augment as old_v7_augment
from turf_lab.month_history import identity


def digest(data):
    return hashlib.sha256(data).hexdigest()


def raw_pace_records(original):
    """Read exactly the history scope already used by original frozen V4."""
    expected={r["race_id"]:r for r in original}
    if len(expected)!=len(original):
        raise ValueError("Duplicate authoritative race")
    result=[]
    for path in sorted(Path("data").glob("month_*/manifest.json")):
        manifest=json.loads(path.read_text())
        for entry in manifest["partitions"]:
            rid=entry["race_id"]
            if rid not in expected:
                continue
            raw=gzip.decompress(Path(entry["file"]).read_bytes())
            if digest(raw)!=entry["sha256"]:
                raise ValueError("Timed PMU partition source SHA changed: "+rid)
            obj=json.loads(raw)
            frozen=expected[rid]
            if (obj["race_id"]!=rid or obj["date"]!=frozen["date"] or
                    obj["venue"]!=frozen["venue"] or
                    obj["start_type"]!=frozen["start_type"] or
                    obj["distance_m"]!=frozen["distance_m"]):
                raise ValueError("Time evidence race identity or context conflict: "+rid)
            before={p["numPmu"]:(identity(p),p["statut"]) for p in frozen["participants"]}
            now={p["numPmu"]:(identity(p),p["statut"]) for p in obj["participants"]}
            if before!=now or len(now)!=len(obj["participants"]):
                raise ValueError("Timed evidence participant mismatch: "+rid)
            source_participants=[]
            for p in obj["participants"]:
                source_participants.append({
                    k:p.get(k) for k in ("numPmu","nom","nomMere","nomPere",
                        "idCheval","statut","incident","ordreArrivee",
                        "reductionKilometrique","tempsObtenu","handicapDistance")
                })
            result.append({
                "race_id":rid,"date":obj["date"],"venue":obj["venue"],
                "start_type":obj["start_type"],"distance_m":obj["distance_m"],
                "participants":source_participants
            })
    if len(result)!=len(original) or {r["race_id"] for r in result}!=set(expected):
        raise ValueError("Timed evidence did not cover the same historical V4 races")
    return sorted(result,key=lambda r:(r["date"],r["race_id"]))


def dated_speed_features(records, speed_policy):
    # Initial historical 2022 warmup is included even when outside the
    # V4 training target split. Never read an outcome after the target day.
    synthetic=[{
        "race_id":r["race_id"],"date":r["date"],
        "runners":[{
            "number":p["numPmu"],"horse_id":identity(p),
            "non_runner":p["statut"]=="NON_PARTANT"
        } for p in r["participants"]]
    } for r in records]
    generated,coverage=old_v7_augment(synthetic,records,speed_policy)
    if len(generated)!=len(records):
        raise ValueError("V7 speed reconstruction omitted races")
    result={}
    for row in generated:
        rid=row["race_id"]
        if rid in result:
            raise ValueError("Duplicate speed feature target")
        per={}
        for runner in row["runners"]:
            value=runner["speed_features"][0]
            count=runner["speed_history_count"]
            if (value is not None and (not math.isfinite(value) or count<1
                                       or count>speed_policy["last_starts"])):
                raise ValueError("Invalid dated speed residual")
            per[runner["number"]]=(runner["horse_id"],value,count)
        result[rid]=per
    return result,coverage


def append_speed(rows, speed):
    """Preserve all 42 previously repaired features; add only one value."""
    out=[]
    available=total=0
    for race in rows:
        rid=race["race_id"]
        if rid not in speed:
            raise ValueError("Missing dated speed row: "+rid)
        per=speed[rid]
        by={r["number"]:r for r in race["runners"]}
        if set(by)!=set(per):
            raise ValueError("Speed runner set not equal to corrected V4 runner set")
        copy=dict(race,runners=[])
        for r in race["runners"]:
            horse_id,value,n=per[r["number"]]
            if horse_id!=r["horse_id"] or len(r["features"])!=42:
                raise ValueError("Speed identity mismatch or V4 feature width not 42")
            x=dict(r,features=list(r["features"])+[value])
            copy["runners"].append(x)
            if not r["non_runner"]:
                total+=1
                available+=value is not None
        out.append(copy)
    return out,{"total_active":total,"with_past_context_speed":available,
                "fraction":available/max(1,total),"missing":total-available}
