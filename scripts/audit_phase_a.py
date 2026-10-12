"""Bounded, resumable audit. No mass collection, definitive database or training.

Run from repository root: python -m scripts.audit_phase_a
All results are regenerated from cached raw evidence on subsequent runs.
"""
import argparse
import collections
import json
from datetime import date, timedelta
from pathlib import Path

from turf_lab.evidence import EvidenceStore, dump, races, start_type

DATES = ["2024-01-28", "2024-05-15", "2024-07-13", "2024-11-01",
         "2025-01-26", "2025-05-14", "2025-08-09", "2025-11-01"]


def select_sample(programme, limit=4):
    candidates = list(races(programme))
    selected = []
    # Prefer coverage of venues and start types over a convenient first N races.
    seen = set()
    for r, c in candidates:
        category = (r.get("hippodrome", {}).get("code"), start_type(c))
        if category not in seen and len(selected) < limit:
            selected.append((r, c))
            seen.add(category)
    for pair in candidates:
        if len(selected) >= limit:
            break
        if pair not in selected:
            selected.append(pair)
    return selected


def fields(value, prefix=""):
    """Count presence once per participant, with explicit empty/null distinction."""
    result = {}
    for key, item in value.items():
        path = prefix + key
        if isinstance(item, dict):
            result.update(fields(item, path + "."))
        else:
            result[path] = item is not None and item != "" and item != []
    return result


def audit(store):
    inventory, examples, records, day_stats = {}, {}, [], []
    for day in DATES + ["2026-10-05"]:
        programme = store.programme(day)
        all_races = list(races(programme, False))
        french = list(races(programme))
        chosen = french if day == "2026-10-05" else select_sample(programme)
        day_stats.append({"date": day, "all_attele_races": len(all_races),
                          "french_attele_races": len(french), "sampled": len(chosen),
                          "venues": sorted({r['hippodrome']['libelleCourt'] for r, _ in french})})
        for reunion, course in chosen:
            rn, cn = reunion["numOfficiel"], course["numOrdre"]
            participants = store.race(day, rn, cn, "participants")
            detail = store.race(day, rn, cn, "")
            runners = (participants or {}).get("participants", [])
            rec = {"date": day, "race_id": f"{day}_R{rn}C{cn}", "reunion": rn, "course_number": cn,
                   "venue": reunion.get("hippodrome", {}).get("libelleCourt"),
                   "country": reunion.get("pays", {}).get("code"), "runners": len(runners),
                   "start_type": start_type(course), "distance_m": course.get("distance"),
                   "scheduled_start_ms": course.get("heureDepart"),
                   "definitive_result": course.get("arriveeDefinitive"),
                   "course": course, "reunion_metadata": {k:v for k,v in reunion.items() if k != "courses"},
                   "participants": runners, "detail": detail}
            records.append(rec)
            year = day[:4]
            inv = inventory.setdefault(year, {"n":0, "fields":{}, "races":0})
            inv["races"] += 1
            for runner in runners:
                inv["n"] += 1
                for field, nonempty in fields(runner).items():
                    row = inv["fields"].setdefault(field, {"present":0, "nonempty":0})
                    row["present"] += 1
                    row["nonempty"] += int(nonempty)
                    if nonempty and field not in examples:
                        node = runner
                        for part in field.split("."):
                            node = node[part]
                        examples[field] = node
    # Programmes alone verify the geographical scope of the old seven-day probe.
    week = []
    for offset in range(7):
        day = (date(2026, 10, 5) + timedelta(days=offset)).isoformat()
        p = store.programme(day)
        rr = list(races(p, False))
        week.append({"date": day, "all_attele_races":len(rr),
                     "france_attele_races":sum(r.get("pays",{}).get("code")=="FRA" for r,c in rr),
                     "countries":dict(collections.Counter(r.get("pays",{}).get("code") for r,c in rr))})
    return {"sampling_plan": "4 races/date where available, diversified by venue/start; all French attelé on 2026-10-05",
            "historical_dates":DATES, "days":day_stats, "week_programmes":week,
            "inventory_by_year":inventory, "examples":examples, "races":records,
            "request_status":dict(collections.Counter(str(m['status']) for m in store.manifest.values()))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--evidence", default="evidence/phase_a_2026-10-12")
    p.add_argument("--output", default="reports/audit_phase_a.json")
    args = p.parse_args()
    store = EvidenceStore(args.evidence, max_requests=160)
    report = audit(store)
    dump(args.output, report)
    print(json.dumps({"races":len(report["races"]), "runners":sum(x["runners"] for x in report["races"]),
                      "inventory":{y:{"n":v['n'],"races":v['races']} for y,v in report['inventory_by_year'].items()},
                      "status": report["request_status"]}))


if __name__ == "__main__":
    main()
