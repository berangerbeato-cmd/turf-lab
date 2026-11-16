"""Consistent, paper-only daily SG + ZE5 ticket from a verified prestart comparison.

The SG selection uses estimated EV; the ZE5 is a top-five *win-probability*
heuristic, NOT a calibrated probability for finishing in the top five.
No operator bet is placed by this module.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from turf_lab.operational_quotes import stamp

PROTOCOL = Path("config/daily_ticket_strategy_v2.json")


def make_ticket(prediction, quotes, comparison, protocol):
    race_id = prediction["race_id"]
    if race_id != quotes.get("race_id") or race_id != comparison.get("race_id"):
        raise ValueError("Ticket sources refer to different races")
    model_name = protocol["model"]
    if prediction.get("primary_model") != model_name:
        raise ValueError("Unexpected primary model for ticket")

    runners = prediction["target_snapshot"]["participants"]
    active = {p["numPmu"] for p in runners if p["statut"] == "PARTANT"}
    quote_numbers = [q["number"] for q in quotes["quotes"]]
    rows = comparison["rows"]
    row_numbers = [r["number"] for r in rows]
    if not active or len(quote_numbers) != len(set(quote_numbers)) or set(quote_numbers) != active:
        raise ValueError("Ticket requires complete odds for active runners")
    if len(rows) != len(active) or len(row_numbers) != len(set(row_numbers)) or set(row_numbers) != active:
        raise ValueError("Ticket requires a complete race comparison")

    observed = stamp(quotes["observed_at"])
    start = stamp(prediction["scheduled_start"])
    if observed >= start:
        raise ValueError("Quote must predate start")

    ranked = sorted(rows, key=lambda r: (-r["models"][model_name]["probability"], r["number"]))
    if any(r["models"][model_name]["probability"] < 0 for r in ranked):
        raise ValueError("Invalid model probabilities")
    if abs(sum(r["models"][model_name]["probability"] for r in ranked) - 1) > 1e-8:
        raise ValueError("Model probabilities are not normalized")

    sg = protocol["simple_gagnant"]
    minimum_ev = sg["minimum_ev"]
    sg_selected = []
    for rank, runner in enumerate(ranked, 1):
        if rank > sg["max_rank"]:
            break
        metrics = runner["models"][model_name]
        if metrics["ev"] + 1e-12 >= minimum_ev:
            sg_selected.append({
                "rank": rank,
                "number": runner["number"],
                "name": runner["name"],
                "probability_win": metrics["probability"],
                "observed_win_odds": runner["odds"],
                "estimated_ev": metrics["ev"],
            })

    ze5_config = protocol["ze5"]
    number = ze5_config["number_of_horses"]
    offered = quotes.get("ze5_offered")
    if offered not in (None, True, False):
        raise ValueError("ze5_offered must be boolean if provided")
    ze5_numbers = [r["number"] for r in ranked[:number]] if len(ranked) >= number else []
    ze5_status = (
        "INSUFFICIENT_STARTERS" if len(ranked) < number else
        "NOT_OFFERED" if offered is False else
        "OFFER_CONFIRMED_BY_USER" if offered is True else
        "OFFER_UNVERIFIED"
    )

    lead_seconds = (start - observed).total_seconds()
    return {
        "status": "PAPER_RESEARCH_ONLY",
        "recommendations_allowed": False,
        "race_id": race_id,
        "model": model_name,
        "model_sha256": prediction["models"][model_name]["model_sha256"],
        "protocol_version": protocol["version"],
        "protocol_sha256": hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest(),
        "observed_at": quotes["observed_at"],
        "scheduled_start": prediction["scheduled_start"],
        "eligible_for_j15_prospective_sg_comparison": 0 < lead_seconds <= 900,
        "sg": {
            "selection": sg_selected,
            "top1_selection": [r for r in sg_selected if r["rank"] <= 1],
            "top2_selection": [r for r in sg_selected if r["rank"] <= 2],
            "top3_selection": [r for r in sg_selected if r["rank"] <= 3],
            "top4_selection": sg_selected,
            "minimum_ev": minimum_ev,
            "ranking_rule": "Frozen V3 winning probability, descending",
            "stake_eur": None,
        },
        "ze5": {
            "numbers": ze5_numbers,
            "type": ze5_config["type"],
            "stake_eur_total": ze5_config["stake_eur_total"] if ze5_status not in ("NOT_OFFERED", "INSUFFICIENT_STARTERS") else 0,
            "status": ze5_status,
            "ranking_rule": "Top five by predicted win probability, not calibrated top-five finish chances",
        },
        "notes": [
            "Quotes may change; no betting execution",
            "Top-5 ZE5 ticket is a heuristic and can lose in full",
            "Early quote snapshot is not an eligible J-15 prospective selection",
        ],
    }


def load_protocol():
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))
