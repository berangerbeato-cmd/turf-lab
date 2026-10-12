"""Probe historical PMU race results endpoints without assuming their availability."""
import argparse
import json
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://offline.turfinfo.api.pmu.fr/rest/client/7/programme"
CANDIDATES = ("rapports-definitifs", "arrivee-definitive", "participants")
OUT = Path("data/results_probe")


def request_json(url):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "TurfLabResearch/0.2"})
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", default="2026-10-05")
    p.add_argument("--days", type=int, default=2)
    p.add_argument("--max-races", type=int, default=5)
    args = p.parse_args()
    if not (1 <= args.days <= 7 and 1 <= args.max_races <= 20):
        p.error("days must be 1..7, max-races must be 1..20")
    OUT.mkdir(parents=True, exist_ok=True)
    summary = []
    for offset in range(args.days):
        day = date.fromisoformat(args.date) + timedelta(days=offset)
        ds = day.strftime("%d%m%Y")
        programme = request_json(f"{BASE}/{ds}")
        reunions = programme.get("programme", {}).get("reunions", programme.get("reunions", []))
        found = 0
        for reunion in reunions:
            rn = reunion.get("numOfficiel") or reunion.get("numeroReunion")
            for course in reunion.get("courses", []):
                cn = course.get("numOrdre") or course.get("numeroCourse")
                if not rn or not cn or str(course.get("discipline", "")).upper() not in ("ATTELE", "TROT_ATTELE"):
                    continue
                for endpoint in CANDIDATES:
                    url = f"{BASE}/{ds}/R{rn}/C{cn}/{endpoint}"
                    record = {"date": day.isoformat(), "reunion": rn, "course": cn, "endpoint": endpoint}
                    try:
                        data = request_json(url)
                        path = OUT / f"{day}_R{rn}C{cn}_{endpoint}.json"
                        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                        record.update(status="ok", bytes=path.stat().st_size)
                    except HTTPError as e:
                        record.update(status="http_error", code=e.code)
                    except (URLError, TimeoutError, ValueError) as e:
                        record.update(status="error", error=str(e))
                    summary.append(record)
                    print(json.dumps(record), flush=True)
                    time.sleep(0.4)
                found += 1
                if found >= args.max_races:
                    break
            if found >= args.max_races:
                break
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if not summary:
        raise SystemExit("No races found for probe")


if __name__ == "__main__":
    main()
