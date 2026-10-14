"""Frozen experimental V6/V7 prestart pair. Never promote or backdate."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from scripts.v6_holdout import verify as verify_v6
from scripts.backtest_connections import digest
from turf_lab.month_history import build_history
from turf_lab.opposition import augment as opposition
from turf_lab.connections import augment_connections
from turf_lab.demographics_tandem import augment as demographics
from turf_lab.context_speed import augment, candidate
from turf_lab.pilot import probabilities
from turf_lab.evidence import dump


def verify():
    _, baseline, base, _ = verify_v6()
    lock = json.loads(Path('models/speed_v7_frozen.json').read_text())
    if lock['baseline_frozen'] != baseline:
        raise ValueError('V7 baseline changed')
    if any(digest(path) != sha for path,sha in lock['files_sha256'].items()):
        raise ValueError('V7 frozen model or feature code changed')
    models = json.loads(Path('models/speed_v7_candidates.json').read_text())['models']
    return lock, base, models


def compute(history, target):
    lock, base, models = verify()
    if any(r['date'] >= target['date'] for r in history):
        raise ValueError('History must precede target day')
    records = history + [target]
    rows = augment_connections(opposition(build_history(records, lookback_days=base['lookback_days'])), records,
        window=base['connections_window_days'], strength=base['connections_prior_strength'],
        equipment_days=base['equipment_history_days'])
    vp = json.loads(Path('config/demographics_tandem_v6_protocol.json').read_text())
    rows = demographics(rows, records, vp['tandem_window_days'], vp['prior_strength'])
    rows, _ = augment(rows, records, json.loads(Path('config/speed_v7_protocol.json').read_text()))
    row = next(r for r in rows if r['race_id'] == target['race_id'])
    result = {}
    for name in ('v6', 'v7_speed'):
        frame = candidate([row], name)[0]
        probs = probabilities(frame, models[name])
        if any(not math.isfinite(v) or not 0 <= v <= 1 for v in probs.values()) or abs(sum(probs.values())-1) > 1e-9:
            raise ValueError('Invalid V7 probabilities')
        result[name] = {'probabilities': probs, 'runners': frame['runners']}
    return lock, result


def capture(history, v5_path):
    v5_path = Path(v5_path)
    source_path = Path('predictions_v6') / v5_path.relative_to('predictions_v5')
    source = json.loads(source_path.read_text())
    if datetime.now(timezone.utc) >= datetime.fromisoformat(source['scheduled_start']):
        raise ValueError('V7 capture after start forbidden')
    if hashlib.sha256(json.dumps(history, sort_keys=True).encode()).hexdigest() != source['history_sha256']:
        raise ValueError('V6/V7 history mismatch')
    lock, models = compute(history, source['target_snapshot'])
    if {str(k):v for k,v in models['v6']['probabilities'].items()} != source['models']['v6']['probabilities']:
        raise ValueError('V6 baseline reproduction failed')
    now = datetime.now(timezone.utc)
    if now >= datetime.fromisoformat(source['scheduled_start']):
        raise ValueError('Start passed during V7 computation')
    path = Path('predictions_v7') / v5_path.relative_to('predictions_v5')
    if path.exists():
        raise ValueError('Existing V7 snapshot is immutable')
    dump(path, dict(source, models=models, frozen=lock, predicted_at=now.isoformat(),
        v6_snapshot=str(source_path), v6_snapshot_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
        capture_code_sha256=digest(__file__), experimental=True, promoted=False))
    return str(path)
