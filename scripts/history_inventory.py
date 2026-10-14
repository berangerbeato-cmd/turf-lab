"""Read-only monthly inventory of collected PMU archives. No network or training."""
import argparse
import calendar
import csv
import json
from pathlib import Path


def inventory(root, start=2022, end=2026, through="2026-10"):
    rows = []
    for year in range(start, end + 1):
        for month in range(1, 13):
            key = f"{year:04d}-{month:02d}"
            if key > through:
                continue
            path = root / f"month_{key}" / "manifest.json"
            row = {"month": key, "status": "MISSING", "days": 0,
                   "expected_days": calendar.monthrange(year, month)[1],
                   "candidate_races": 0, "retained_races": 0,
                   "quarantined_races": 0, "participants": 0,
                   "coverage_fraction": None}
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("month") != key:
                    raise ValueError(f"Month mismatch: {path}")
                days = data.get("days", [])
                dates = [d.get("date") for d in days]
                if len(dates) != len(set(dates)):
                    raise ValueError(f"Duplicate dates: {path}")
                candidates = sum(d.get("candidate_races", 0) for d in days)
                retained = len({p["race_id"] for p in data.get("partitions", [])})
                quarantine = len({q["race_id"] for q in data.get("quarantine", [])})
                fraction = retained / candidates if candidates else None
                complete_days = len(days) == row["expected_days"] and all(d.get("status") == "OK" for d in days)
                row.update(days=len(days), candidate_races=candidates, retained_races=retained,
                           quarantined_races=quarantine, participants=data.get("participants", 0),
                           coverage_fraction=fraction,
                           status=("COMPLETE" if complete_days and fraction is not None and fraction >= 0.98
                                   and data.get("status") in ("COLLECTED", "COLLECTED_WITH_GAPS")
                                   else "PARTIAL"))
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("reports/history_inventory"))
    parser.add_argument("--through", default="2026-10")
    args = parser.parse_args()
    rows = inventory(args.data, through=args.through)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(rows, indent=2) + "\n")
    with args.output.with_suffix(".csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"months": len(rows), "complete": sum(r["status"] == "COMPLETE" for r in rows),
                      "partial": sum(r["status"] == "PARTIAL" for r in rows),
                      "missing": sum(r["status"] == "MISSING" for r in rows)}))


if __name__ == "__main__":
    main()
