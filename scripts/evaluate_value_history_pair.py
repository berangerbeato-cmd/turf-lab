"""Descriptive one-race replay of two V2 chains on immutable Reims inputs.

Both odds and original V3+V2 were archived BEFORE start; repaired-history
candidate was calculated later. Never classify as prospective V1.1/V2 proof.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from turf_lab.evidence import dump
from turf_lab.value_history_pair import paired

ROOT = Path("predictions_operational/2026-11-21/2026-11-21_R4C5_20261121T172911422587Z")
HISTORY = Path("reports/history_repair_shadow_v1/replays_nancy_alias_v1_1/2026-11-21_R4C5_20261121T172911422587Z.json")
RESULT = Path("reports/manual_bets/2026-11-21_R4C5_Z4.json")
OUTPUT = Path("reports/value_history_pair_v1/reims_r4c5_retrospective.json")


def run(out=OUTPUT):
    prediction=json.loads((ROOT/"prediction.json").read_text())
    history=json.loads(HISTORY.read_text())
    quotes=json.loads((ROOT/"quotes.json").read_text())
    reference=json.loads((ROOT/"comparison.json").read_text())
    report=paired(prediction,history,quotes,reference,
                  now=datetime(2026,11,21,19,0,tzinfo=timezone.utc))
    if report["status"] != "RETROSPECTIVE_PAIRED_REPLAY":
        raise ValueError("Replay falsely classified as prospective")
    result=json.loads(RESULT.read_text())
    if result["race_id"] != report["race_id"]:
        raise ValueError("Result belongs to a different race")
    winner=result["result_reported_by_user_screenshot"][0]
    row=next(r for r in report["rows"] if r["number"]==winner)
    probabilities={
        "market_normalized":row["market_probability"],
        "v3_sport":row["v3_sport_probability"],
        "history_sport":row["history_sport_probability"],
        "v3_plus_v2":row["v3_plus_v2_probability"],
        "history_plus_v2":row["history_plus_v2_probability"],
    }
    report["postrace_descriptive"]={
        "winner":winner,"result_source":"ZETURF_SCREENSHOT_USER_SUPPLIED",
        "single_race_log_losses":{k:-math.log(p) for k,p in probabilities.items()},
        "positive_ev_counts":{
            "v3_plus_v2":sum(r["v3_plus_v2_indicative_ev"]>0 for r in report["rows"]),
            "history_plus_v2":sum(r["history_plus_v2_indicative_ev"]>0 for r in report["rows"])},
        "roi":None,
        "limit":"Result was known when candidate was joined to V2; this comparison is retrospective only."
    }
    if Path(out).exists() and json.loads(Path(out).read_text()) != report:
        raise ValueError("Immutable original retrospective study cannot be rewritten")
    dump(out,report)
    print(json.dumps({
        "race_id":report["race_id"],"status":report["status"],
        "winner":winner,"winner_probs":probabilities,
        "log_losses":report["postrace_descriptive"]["single_race_log_losses"],
        "positive_ev_counts":report["postrace_descriptive"]["positive_ev_counts"]},
        indent=2))
    return report


if __name__ == "__main__":
    run()
