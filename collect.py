import argparse
import json
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://offline.turfinfo.api.pmu.fr/rest/client/7/programme"
OUT = Path("data/raw")


def fetch(url):
    req = Request(url, headers={
        "User-Agent": "TurfLabResearch/0.1",
        "Accept": "application/json",
    })
    with urlopen(req, timeout=25) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--days", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.days <= 7:
        parser.error("days must be 1..7")

    totals = {"days": 0, "races_saved": 0, "failures": []}
    for offset in range(args.days):
        day = date.fromisoformat(args.date) + timedelta(days=offset)
        ds = day.strftime("%d%m%Y")
        target = OUT / day.isoformat()
        target.mkdir(parents=True, exist_ok=True)
        programme = fetch(f"{BASE}/{ds}")
        (target / "programme.json").write_text(
            json.dumps(programme, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        reunions = programme.get("programme", {}).get(
            "reunions", programme.get("reunions", [])
        )
        totals["days"] += 1
        print(day, "reunions", len(reunions))
        for reunion in reunions:
            if reunion.get("pays", {}).get("code") != "FRA":
                continue
            rn = reunion.get("numOfficiel") or reunion.get("numeroReunion")
            for course in reunion.get("courses", []):
                cn = course.get("numOrdre") or course.get("numeroCourse")
                if not rn or not cn:
                    continue
                if str(course.get("discipline", "")).upper() not in ("ATTELE", "TROT_ATTELE"):
                    continue
                try:
                    participants = fetch(f"{BASE}/{ds}/R{rn}/C{cn}/participants")
                    (target / f"R{rn}C{cn}_participants.json").write_text(
                        json.dumps(participants, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    totals["races_saved"] += 1
                    print("saved", rn, cn)
                except Exception as exc:
                    totals["failures"].append({"date": day.isoformat(), "reunion": rn, "course": cn, "error": str(exc)})
                    print("participants failed", rn, cn, repr(exc))
                time.sleep(0.5)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(totals, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(totals))
    if totals["races_saved"] == 0 or totals["failures"]:
        raise SystemExit("Collection incomplete: inspect summary.json")


if __name__ == "__main__":
    main()
