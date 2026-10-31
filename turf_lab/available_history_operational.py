"""Frozen available-history V3 inference. No fitting or network access."""
import hashlib
import json
from pathlib import Path
from turf_lab.available_history_research import available_features, variant
from turf_lab.full_history_evaluation import temper
from turf_lab.pilot import probabilities

POLICY = Path('config/active_model.json')


def verify_active():
    policy = json.loads(POLICY.read_text())
    if policy['primary_model'] != 'available_history_v3':
        raise ValueError('Unsupported active model; no silent fallback')
    for path, expected in policy['files_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('Active model dependency changed: '+path)
    frozen = json.loads(Path(policy['selection_file']).read_text())
    if frozen['selected'] != policy['variant']:
        raise ValueError('Selected variant mismatch')
    if frozen['model_sha256'][policy['variant']] != policy['files_sha256'][policy['model_file']]:
        raise ValueError('Model selection hash mismatch')
    temperature = frozen['temperatures'][policy['variant']]
    if not .5 <= temperature <= 3:
        raise ValueError('Invalid frozen temperature')
    return policy, temperature


def compute(records, classic_row):
    policy, temperature = verify_active()
    target = classic_row['race_id']; day = classic_row['date']
    if sum(r['race_id'] == target for r in records) != 1:
        raise ValueError('Target must occur exactly once')
    if any(r['date'] >= day for r in records if r['race_id'] != target):
        raise ValueError('History must precede target day')
    rows, _ = available_features(records, [classic_row])
    frame = variant(rows, policy['variant'])[0]
    model = json.loads(Path(policy['model_file']).read_text())
    probs = temper([frame], [probabilities(frame, model)], temperature)[0]
    return dict(probabilities=probs, runners=frame['runners'], temperature=temperature,
                role='primary', selection_file=policy['selection_file'],
                feature_version=policy['variant']), policy
