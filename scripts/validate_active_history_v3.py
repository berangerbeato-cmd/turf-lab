"""Offline live-path parity check against saved full-data predictions."""
import gzip
import json
from pathlib import Path
from scripts.train_available_history_v3 import sources
from scripts.predict_operational import compute_all
from turf_lab.available_history_operational import verify_active


def main():
    policy,_=verify_active()
    records,_=sources()
    with gzip.open('reports/available_history_v3/test_predictions.jsonl.gz','rt') as f:
        predictions=[json.loads(line) for line in f]
    # Fixed first eligible test race; chosen by chronology, never model performance.
    expected=predictions[0]; target=next(r for r in records if r['race_id']==expected['race_id'])
    models,place,locks=compute_all([r for r in records if r['date']<target['date']],target)
    actual=models[policy['primary_model']]['probabilities']
    reference=expected['probabilities'][policy['variant']]
    difference=max(abs(actual[int(n)]-p) for n,p in reference.items())
    if difference>1e-12: raise ValueError('Live path differs from archived experiment: '+str(difference))
    output=dict(status='SUCCESS',race_id=target['race_id'],max_probability_difference=difference,primary_model=policy['primary_model'],
        temperature=models[policy['primary_model']]['temperature'],recommendations_allowed=False,
        verification='Offline full compute_all path against archived test probabilities; no new forecast, collection or training.')
    path=Path('reports/available_history_v3/activation_validation.json')
    path.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output),flush=True)

if __name__=='__main__':main()
