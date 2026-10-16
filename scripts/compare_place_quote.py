"""Research-only comparison of a frozen place ticket with an evidenced quote.

This consumes an independently prepared ticket; it does not generate forecasts,
verify screenshots, or certify the final mutual-pool dividend.
"""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def timestamp(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Timezone required')
    return stamp.astimezone(timezone.utc)


def positive(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError('Expected finite positive number')
    return value


def compare(ticket, quote):
    for key in ('race_id', 'selection', 'market'):
        if ticket[key] != quote[key]:
            raise ValueError('Ticket/quote mismatch: ' + key)
    if ticket['market'] != 'place3' or ticket['selection_method'] != 'classic_max_probability':
        raise ValueError('Unsupported calibration scope')
    if not 10 <= ticket['field_size'] <= 20 or ticket['nonrunners'] != 0:
        raise ValueError('Outside studied cohort')
    for key in ('prediction_evidence', 'calibration_evidence', 'field_evidence'):
        if not ticket.get(key):
            raise ValueError('Missing ticket evidence: ' + key)
    for key in ('operator', 'source_evidence', 'start_evidence'):
        if not quote.get(key):
            raise ValueError('Missing quote evidence: ' + key)
    if quote['kind'] != 'probable' or quote['includes_stake'] is not True:
        raise ValueError('Need probable total-return quote including stake')
    p = positive(ticket['probability'])
    if p >= 1:
        raise ValueError('Probability must be strictly below one')
    created = timestamp(ticket['created_at'])
    observed = timestamp(quote['observed_at'])
    start = timestamp(quote['verified_start_at'])
    if not created <= observed < start:
        raise ValueError('Forecast must precede quote; quote must precede verified start')
    unit = positive(quote['unit_stake'])
    low, high = positive(quote['return_low']) / unit, positive(quote['return_high']) / unit
    if low > high:
        raise ValueError('Reversed quote range')
    return {
        'status': 'RESEARCH_SCENARIO_ONLY_NO_BET',
        'race_id': ticket['race_id'], 'selection': ticket['selection'],
        'operator': quote['operator'], 'probability': p,
        'break_even_total_return_per_euro': 1 / p,
        'probable_total_return_per_euro': [low, high],
        'conditional_net_return_scenarios': [p * low - 1, p * high - 1],
        'lower_quote_above_model_break_even': p * low > 1,
        'limits': [
            'Probable range is not a guaranteed final payout range.',
            'Scenarios assume fixed paid return; no realized ROI or validated EV.',
            'Evidence references must be checked independently.',
            'Calibration of all top selections does not establish calibration after price filtering.',
            'This historical check does not certify a quote is still current.'
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ticket', type=Path)
    parser.add_argument('quote', type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(json.loads(args.ticket.read_text()), json.loads(args.quote.read_text())), indent=2))


if __name__ == '__main__':
    main()
