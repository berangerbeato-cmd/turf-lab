"""Frozen market correction in shadow mode; never replace the sports primary."""
import hashlib,json,math
from pathlib import Path
from datetime import datetime,timedelta
from turf_lab.market_repair import predict

def shadow(prediction,quotes,rows,now):
    def blocked(reason):return dict(status='UNAVAILABLE',reason=reason,recommendations_allowed=False)
    if prediction.get('primary_model')!='available_history_v3':return blocked('Sports primary mismatch')
    active=json.loads(Path('config/active_model.json').read_text())
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    frozen=json.loads(Path('models/value_correction_v2/frozen_before_test.json').read_text())
    if sha('config/active_model.json')!=frozen['active_policy_sha256']:return blocked('Active configuration changed')
    model_path='models/value_correction_v2/hybrid.json'
    if sha(model_path)!=frozen['model_hashes']['hybrid']:return blocked('Correction weights changed')
    sport=prediction['models']['available_history_v3']
    if sport.get('model_sha256')!=active['files_sha256'][active['model_file']]:return blocked('Sports weights mismatch')
    if sport.get('temperature')!=json.loads(Path(active['selection_file']).read_text())['temperatures'][active['variant']]:
        return blocked('Sports calibration mismatch')
    parts=prediction['target_snapshot']['participants']
    if any(p.get('statut')!='PARTANT' for p in parts):return blocked('Nonrunner or uncertain field')
    if len(rows)!=len(parts) or {r['number'] for r in rows}!={p['numPmu'] for p in parts}:
        return blocked('Complete same-operator odds board required')
    start=datetime.fromisoformat(prediction['scheduled_start'].replace('Z','+00:00'))
    observed=datetime.fromisoformat(quotes['observed_at'].replace('Z','+00:00'))
    if start-observed>timedelta(minutes=15):return blocked('Quote more than 15 minutes before start')
    if now<start and now-observed>timedelta(minutes=5):return blocked('Live quote older than five minutes')
    odds=[r['odds'] for r in rows]
    if sum(1/c for c in odds)<1-1e-9:return blocked('Underround board outside training scope')
    ps=[r['models']['available_history_v3']['probability'] for r in rows]
    if any(not isinstance(p,(int,float)) or not math.isfinite(p) or p<=0 for p in ps) or abs(sum(ps)-1)>1e-8:
        return blocked('Invalid sports probability field')
    corrected=predict(odds,ps,json.loads(Path(model_path).read_text())['weights'])
    norm=sum(1/c for c in odds)
    return dict(status='PRESTART_SHADOW' if now<start else 'RETROSPECTIVE_REPLAY_NOT_PROSPECTIVE',
        model='value_correction_v2',model_sha256=sha(model_path),market_informed=True,operator=quotes['operator'],
        source_evidence=quotes['source_evidence'],observed_at=quotes['observed_at'],calculated_at=now.isoformat(),
        recommendations_allowed=False,rows=[dict(number=r['number'],probability=p,market_probability=(1/r['odds'])/norm,
        indicative_ev=p*r['odds']-1,break_even_total_return=1/p) for r,p in zip(rows,corrected)],
        limits='Shadow SG only. Trained on archived PMU reference prices; other operators and live price snapshots are out-of-sample transfer. No profit, stakes or selection rule. Recalculate if odds or field change.')
