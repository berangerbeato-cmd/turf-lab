"""Reproduce the V4 user-facing prototype on Reims with honest post-race labeling.

Historical replay is a regression test, NEVER proof of prospective skill.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from turf_lab.evidence import dump
from turf_lab.v4_unified import assemble

ROOT = Path("predictions_operational/2026-11-21/2026-11-21_R4C5_20261121T172911422587Z")
REPAIR = Path("reports/history_repair_shadow_v1/replays_nancy_alias_v1_1/2026-11-21_R4C5_20261121T172911422587Z.json")
PAIR = Path("reports/value_history_pair_v1/reims_r4c5_retrospective.json")
OUTPUT = Path("reports/v4/reims_2026-11-21_R4C5_replay_only.json")


def main():
    result = assemble(ROOT/"prediction.json",REPAIR,PAIR,ROOT/"quotes.json",
                      now=datetime(2026,11,21,19,0,tzinfo=timezone.utc))
    if result["freshness"] != "RETROSPECTIVE" or result["decision"] != "NO BET":
        raise ValueError("Cannot label original Reims V4 as prospective or recommend a wager")
    user = json.loads(Path("reports/manual_bets/2026-11-21_R4C5_Z4.json").read_text())
    outcome = user["result_reported_by_user_screenshot"]
    diagnostic = {
        "status":"AFTER_THE_FACT_REPLAY_NOT_PROSPECTIVE",
        "race_id":result["race_id"],
        "winner":outcome[0],
        "winner_ranked_top1":result["gagnant"]["number"]==outcome[0],
        "top5_correct_horses":len(set(result["top5"]["numbers"]) & set(outcome[:5])),
        "not_valid_for_model_selection":True,
        "note":"Reims was analyzed before this V4 interface existed. No parameter tuning allowed."
    }
    out = dict(result,postrace_diagnostic=diagnostic)
    if OUTPUT.exists() and json.loads(OUTPUT.read_text()) != out:
        raise ValueError("Historical demonstration already archived; refuse to rewrite")
    dump(OUTPUT,out)
    print(json.dumps({"version":result["version"],"race":result["race_id"],
                      "winner":result["gagnant"],"top5":result["top5"]["numbers"],
                      "history_uncertain":len(result["history_repair"]["unresolved"]),
                      "decision":result["decision"],"diagnostic":diagnostic},
                     ensure_ascii=False,indent=2))
    return out


if __name__ == "__main__":
    main()
