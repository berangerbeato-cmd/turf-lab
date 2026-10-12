"""Pure, conservative transformations for the individual-history audit."""
import re
from datetime import date, datetime, timezone

SHOES = {"0":"FERRE", "1":"DA", "2":"DP", "3":"D4", "4":"P4",
         "5":"PA", "6":"PA_DP", "7":"PP", "8":"DA_PP"}


def parse_time_seconds(value):
    """PMU string minutes'seconds\"centiseconds, NOT a lifetime personal record."""
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(\d+)'(\d{1,2})\"(\d{1,3})", value.strip())
    if not match:
        return None
    minutes, seconds, fraction = match.groups()
    if int(seconds) >= 60:
        return None
    result = int(minutes)*60 + int(seconds) + int(fraction)/10**len(fraction)
    return result if result > 0 else None


def race_day(run):
    if run.get("raceDate"):
        return date.fromisoformat(run["raceDate"])
    # light-performances uses seconds (not the programme's milliseconds).
    if isinstance(run.get("date"), (int,float)) and 0 < run["date"] < 10_000_000_000:
        return datetime.fromtimestamp(run["date"], timezone.utc).date()
    raise ValueError("History run lacks an unambiguous date")


def before_target(history, target_day, limit=10):
    cutoff = date.fromisoformat(target_day)
    accepted, rejected = {}, []
    for run in history.get("runner", {}).get("racesRun", []):
        try:
            day = race_day(run)
        except (ValueError, TypeError, OverflowError):
            rejected.append({"reason":"invalid_date"})
            continue
        if day >= cutoff:
            rejected.append({"date":day.isoformat(), "reason":"target_day_or_future"})
            continue
        participant = run.get("raceRunParticipant", {})
        if participant.get("place", {}).get("arrivalStatus") == "NON_PARTANT":
            rejected.append({"date":day.isoformat(), "reason":"non_runner"})
            continue
        key = (day.isoformat(), run.get("racecourseCode") or run.get("racecourse"), run.get("raceNumber"))
        if key in accepted and accepted[key] != run:
            raise ValueError("Conflicting history records: " + str(key))
        accepted[key] = run
    ordered = sorted(accepted.values(), key=race_day, reverse=True)
    return ordered[:limit], rejected, len(ordered)


def summarize_run(run):
    p = run.get("raceRunParticipant", {})
    status = p.get("place", {}).get("arrivalStatus")
    is_dq = isinstance(status, str) and (status.startswith("DISQUALIFIE") or status == "DISTANCE")
    conditions = run.get("fullConditions", "")
    category = run.get("raceCategory", {}).get("code", "")
    start = "AUTOSTART" if "AUTOSTART" in (category + conditions).upper() else "NON_PRECISE"
    base, covered = run.get("distance"), p.get("distanceCovered")
    return {"date":race_day(run).isoformat(), "venue":run.get("racecourse"),
            "racecourse_code":run.get("racecourseCode"), "race_number":run.get("raceNumber"),
            "race_name":run.get("raceName"), "discipline":run.get("discipline"),
            "distance_m":base, "distance_covered_m":covered,
            "handicap_m":covered-base if isinstance(covered,(int,float)) and isinstance(base,(int,float)) else None,
            "start_type":start, "rank":None if is_dq else p.get("place",{}).get("runnerRank"),
            "arrival_status":status, "disqualified":is_dq,
            "seconds_per_km":None if is_dq else parse_time_seconds(p.get("mileageReduction")),
            "race_time_seconds":None if is_dq else parse_time_seconds(p.get("timeRecord")),
            "driver":p.get("riderName"), "trainer":p.get("trainerName"),
            "shoes_raw":p.get("shoes"), "shoes":SHOES.get(p.get("shoes")),
            "field_size":run.get("runnersCount"), "purse_eur":run.get("earningsTotalPool"),
            "race_type":run.get("raceType"), "turn":run.get("turn"),
            "conditions":conditions, "track_condition":run.get("trackCondition"),
            "trainer_opinion_raw":p.get("trainerOpinion")}
