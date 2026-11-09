"""Isolated outcome-aware sports experiment, not production inference."""
from datetime import date
import math


def outcome(rank, incident):
    incident = str(incident or '')
    dq = incident.startswith('DISQUALIFIE') or incident == 'DISTANCE'
    positive_rank = type(rank) is int and rank > 0
    if positive_rank and incident:
        return None  # contradictory observation, never turn into a non-win
    if dq:
        return (0, 0, 1, 0)
    if incident in ('ARRETE', 'TOMBE'):
        return (0, 0, 0, 1)
    if positive_rank:
        return (int(rank == 1), int(rank <= 3), 0, 0)
    return None


def repaired_features(history, day):
    if any(h['date'] >= day for h in history):
        raise ValueError('Target/future history forbidden')
    recent = sorted((h for h in history if (date.fromisoformat(day)-date.fromisoformat(h['date'])).days <= 60),
                    key=lambda h: (h['date'], h['race_id']), reverse=True)[:5]
    n = len(recent)
    if not n:
        return [None, None, None, None, 0.0, None, None]
    values = [outcome(h['rank'], h['incident']) for h in recent]
    known = [x for x in values if x is not None]
    rates = [sum(x[i] for x in known)/len(known) if known else None for i in range(3)]
    rest = math.log1p((date.fromisoformat(day)-date.fromisoformat(recent[0]['date'])).days)
    return rates + [rest, n/5, (n-len(known))/n, sum(x[3] for x in known)/n]


def replace_features(original, history, day):
    if len(original) != 38:
        raise ValueError('Expected frozen 38-feature frame')
    repaired = repaired_features(history, day)
    return repaired[:5] + original[5:] + repaired[5:]
