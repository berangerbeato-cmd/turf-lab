"""Retrospective integrity check of genuinely retrained V4 coefficients.

The historical Reims result is NOT used to select or modify model weights.
"""
import json
from datetime import datetime,timezone
from pathlib import Path

from turf_lab.evidence import dump
from turf_lab.v4_full_inference import run

ROOT=Path("predictions_operational/2026-11-21/2026-11-21_R4C5_20261121T172911422587Z")
HISTORY=Path("reports/history_repair_shadow_v1/replays_nancy_alias_v1_1/2026-11-21_R4C5_20261121T172911422587Z.json")
OUT=Path("reports/v4_full/reims_r4c5_postrace_retrained_demo.json")


def main():
    r=run(ROOT/"prediction.json",HISTORY,ROOT/"quotes.json",
          now=datetime(2026,11,21,19,0,tzinfo=timezone.utc))
    if r["freshness"]!="RETROSPECTIVE" or r["recommendations_allowed"] is not False:
        raise ValueError("Reims retrospective replay misclassified")
    official=json.loads(Path("reports/manual_bets/2026-11-21_R4C5_Z4.json").read_text())
    if official["race_id"]!=r["race_id"]:
        raise ValueError("Race mismatch")
    finish=official["result_reported_by_user_screenshot"]
    r["postrace_demo"]={
        "winner":finish[0],
        "predicted_first_won":r["gagnant"]["number"]==finish[0],
        "top5_found":len(set(r["top5"]["numbers"])&set(finish[:5])),
        "not_a_prospective_validation":True,
        "no_model_selection_on_reims":True}
    if OUT.exists() and json.loads(OUT.read_text())!=r:
        raise ValueError("Frozen V4 postrace demo would be changed")
    dump(OUT,r)
    print(json.dumps({k:r[k] for k in ("version","gagnant","top5","value","history_repair",
                                      "postrace_demo","decision")},ensure_ascii=False,indent=2))
    return r


if __name__=="__main__":
    main()
