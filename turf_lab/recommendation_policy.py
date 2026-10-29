"""Fail-closed recommendation state, separate from immutable model probabilities."""
import json
from pathlib import Path

POLICY = Path(__file__).resolve().parents[1] / 'config/recommendation_policy.json'


def recommendation_state(path=None):
    try:
        policy = json.loads(Path(path or POLICY).read_text())
        if policy.get('status') != 'SUSPENDED' or policy.get('recommendations_allowed') is not False:
            raise ValueError('No validated resumption protocol implemented')
        reasons = policy['reasons']
        if not isinstance(reasons, list) or not reasons or not all(isinstance(r, str) and r for r in reasons):
            raise ValueError('Invalid reasons')
        return {'recommendations_allowed': False, 'recommendation_status': 'SUSPENDED',
                'recommendation_reasons': reasons, 'recommendation_audit': policy.get('audit')}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {'recommendations_allowed': False, 'recommendation_status': 'SUSPENDED',
                'recommendation_reasons': ['missing_invalid_or_unapproved_recommendation_policy']}
