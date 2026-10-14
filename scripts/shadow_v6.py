"""Immutable V5/V6 sidecars, calculated from the exact V5 capture inputs."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from scripts.v6_holdout import verify
from turf_lab.month_history import build_history
from turf_lab.opposition import augment as opposition
from turf_lab.connections import augment_connections
from turf_lab.demographics_tandem import augment, candidate
from turf_lab.pilot import probabilities
from turf_lab.evidence import dump


def compute(history, target):
    _, lock, p, models = verify()
    if any(r['date'] >= target['date'] for r in history):
        raise ValueError('History must precede target day')
    records = history + [target]
    rows = augment_connections(opposition(build_history(records, lookback_days=p['lookback_days'])), records,
        window=p['connections_window_days'], strength=p['connections_prior_strength'],
        equipment_days=p['equipment_history_days'])
    v6p = json.loads(Path('config/demographics_tandem_v6_protocol.json').read_text())
    rows = augment(rows, records, v6p['tandem_window_days'], v6p['prior_strength'])
    row = next(r for r in rows if r['race_id'] == target['race_id'])
    result = {}
    for name, variant in [('v5', 'v5'), ('v6', 'combined')]:
        frame = candidate([row], variant)[0]
        probs = probabilities(frame, models[name])
        if any(not math.isfinite(v) or not 0 <= v <= 1 for v in probs.values()) or abs(sum(probs.values())-1) > 1e-9:
            raise ValueError('Invalid probabilities')
        result[name] = {'probabilities': probs, 'runners': frame['runners']}
    return lock, result


def capture(history, source_path):
    source_path = Path(source_path)
    source = json.loads(source_path.read_text())
    now = datetime.now(timezone.utc)
    if now >= datetime.fromisoformat(source['scheduled_start']):
        raise ValueError('V6 capture after start forbidden')
    if hashlib.sha256(json.dumps(history, sort_keys=True).encode()).hexdigest() != source['history_sha256']:
        raise ValueError('V5/V6 history mismatch')
    lock, models = compute(history, source['target_snapshot'])
    baseline = {str(k): v for k,v in models['v5']['probabilities'].items()}
    if baseline != source['models'][source['frozen']['selected']]['probabilities']:
        raise ValueError('V5 baseline reproduction failed')
    now = datetime.now(timezone.utc)
    if now >= datetime.fromisoformat(source['scheduled_start']):
        raise ValueError('Start passed during V6 computation')
    path = Path('predictions_v6') / source_path.relative_to('predictions_v5')
    if path.exists():
        raise ValueError('Existing V6 snapshot is immutable')
    output = dict(source, models=models, predicted_at=now.isoformat(), frozen=lock,
        v5_snapshot=str(source_path), v5_snapshot_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
        capture_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    dump(path, output)
    return str(path)
