"""Paired scores of immutable V3/V5 forecasts; never renormalize after results."""
import math
from datetime import datetime
from turf_lab.month_history import identity
from turf_lab.connections import entity, equipment
from turf_lab.opposition import is_dq


def score(prediction, detail, participants):
    def reject(reason):
        return {'status': 'QUARANTINE', 'reason': reason}
    captured = datetime.fromisoformat(prediction['predicted_at'])
    scheduled = datetime.fromisoformat(prediction['scheduled_start'])
    if captured >= scheduled:
        return reject('prediction_not_before_start')
    if detail.get('heureDepart') and captured.timestamp()*1000 >= detail['heureDepart']:
        return reject('prediction_after_revised_start')
    if detail.get('statut') == 'COURSE_ANNULEE' or detail.get('categorieStatut') == 'ANNULEE':
        return reject('cancelled_race')
    if not (detail.get('arriveeDefinitive') or detail.get('isArriveeDefinitive')):
        return {'status': 'PENDING', 'reason': 'result_not_definitive'}
    original = prediction['target_snapshot']['participants']
    if any(p.get('statut') not in ('PARTANT', 'NON_PARTANT') for p in original+participants):
        return reject('unknown_status')
    old = [p for p in original if p['statut'] == 'PARTANT']
    new = [p for p in participants if p['statut'] == 'PARTANT']
    def signature(p):
        return (p['numPmu'], identity(p), entity(p.get('driver')), entity(p.get('entraineur')), equipment(p.get('deferre')))
    if len({p['numPmu'] for p in original}) != len(original) or len({p['numPmu'] for p in participants}) != len(participants):
        return reject('duplicate_runner')
    if {signature(p) for p in old} != {signature(p) for p in new}:
        return reject('field_identity_driver_trainer_or_equipment_changed')
    winners = [p['numPmu'] for p in new if p.get('ordreArrivee') == 1]
    order = detail.get('ordreArrivee') or []
    if len(winners) != 1 or not order or order[0] != winners:
        return reject('ambiguous_or_inconsistent_winner')
    if any(is_dq(p) for p in new if p['numPmu'] == winners[0]):
        return reject('disqualified_winner')
    names = ['v3', prediction['frozen']['selected']]
    if set(prediction['models']) != set(names):
        return reject('model_pair_mismatch')
    results = {}
    numbers = {p['numPmu'] for p in old}
    all_numbers = {p['numPmu'] for p in original}
    for name in names:
        values = {int(k): v for k, v in prediction['models'][name]['probabilities'].items()}
        if set(values) != all_numbers or any(not isinstance(v, (float,int)) or not math.isfinite(v) or not 0 <= v <= 1 for v in values.values()):
            return reject('invalid_probabilities')
        if any(values[k] != 0 for k in all_numbers-numbers) or abs(sum(values.values())-1) > 1e-8:
            return reject('invalid_probability_sum_or_nonrunner')
        active = {k: values[k] for k in numbers}
        best = min(active, key=lambda k: (-active[k], k))
        results[name] = {'log_loss': -math.log(max(1e-15, active[winners[0]])),
            'brier_multiclass': sum((p-int(k == winners[0]))**2 for k,p in active.items()),
            'top1_hit': int(best == winners[0])}
    return {'status': 'SCORED', 'winner': winners[0], 'models': results, 'active_runners': len(numbers)}


def choose_snapshot(candidates):
    # Selection uses capture timestamps only, before inspecting any arrival.
    valid = [(path, p) for path,p in candidates if datetime.fromisoformat(p['predicted_at']) < datetime.fromisoformat(p['scheduled_start'])]
    return max(valid, key=lambda x: (datetime.fromisoformat(x[1]['predicted_at']), str(x[0]))) if valid else None
