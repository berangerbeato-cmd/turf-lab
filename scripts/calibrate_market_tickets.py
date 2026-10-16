"""Calibrate ONLY maximum-probability classic tickets on 2025, evaluate 2026."""
import gzip,hashlib,json
from collections import defaultdict,Counter
from datetime import date
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from turf_lab.pilot import probabilities
from turf_lab.full_history_evaluation import temper,season
from turf_lab.market_probabilities import markets
from turf_lab.evidence import dump
from scripts.evaluate_markets import ROOT,new_stats,update,finish


def fit_calibration(rows):
    if not rows or any(not r['date'].startswith('2025-') for r in rows):
        raise ValueError('Calibration accepts only fixed 2025 validation tickets')
    p=np.clip([r['probability'] for r in rows],1e-9,1-1e-9);x=np.log(p/(1-p))
    y=np.array([r['observed_hit'] for r in rows]);ridge=.001
    def loss(t):
        z=t[0]*x+t[1];res=expit(z)-y
        return (float(np.mean(np.logaddexp(0,z)-y*z)+ridge*((t[0]-1)**2+t[1]**2)/2),
          np.array([np.mean(res*x)+ridge*(t[0]-1),np.mean(res)+ridge*t[1]]))
    fit=minimize(loss,[1.,0.],jac=True,method='L-BFGS-B',bounds=[(0.,None),(None,None)],options={'maxiter':500})
    if not fit.success:raise ValueError('Calibration optimization failed: '+fit.message)
    return {'slope':float(fit.x[0]),'intercept':float(fit.x[1]),'ridge':ridge,'validation_tickets':len(rows)}


def apply_calibration(p,c):
    p=np.clip(p,1e-9,1-1e-9)
    return float(expit(c['slope']*np.log(p/(1-p))+c['intercept']))


def main():
    model_path=Path('models/full_history/classic.json');model=json.loads(model_path.read_text())
    frozen=json.loads(Path('models/full_history/frozen.json').read_text())
    source=Path('reports/full_history/datasets/validation.jsonl.gz')
    rows=[json.loads(line) for line in gzip.decompress(source.read_bytes()).splitlines()]
    entries={}
    for month in sorted({r['date'][:7] for r in rows}):
        manifest=json.loads(Path(f'data/month_{month}/manifest.json').read_text())
        entries.update({e['race_id']:e for e in manifest['partitions']})
    val=defaultdict(list);excluded=Counter()
    for i,r in enumerate(rows):
        e=entries[r['race_id']];raw=gzip.decompress(Path(e['file']).read_bytes())
        if hashlib.sha256(raw).hexdigest()!=e['sha256']:raise ValueError('Source digest mismatch')
        rec=json.loads(raw);ps=rec['participants'];arrival=rec.get('course',{}).get('ordreArrivee',[])
        if not 10<=len(ps)<=20 or any(p.get('statut')=='NON_PARTANT' for p in ps):excluded['field_or_nonrunner']+=1;continue
        if len(arrival)<4 or any(len(a)!=1 for a in arrival[:4]):excluded['missing_or_tied_top4']+=1;continue
        top=[a[0] for a in arrival[:4]];ranks={p['numPmu']:p.get('ordreArrivee') for p in ps}
        if len(set(top))!=4 or any(ranks.get(num)!=rank for rank,num in enumerate(top,1)):excluded['arrival_disagreement']+=1;continue
        nums=sorted(ranks);pred=temper([r],[probabilities(r,model)],frozen['temperatures']['classic'])[0]
        mm=markets(nums,[pred[num] for num in nums])
        for market,(sels,pp) in mm.items():
            best=int(np.argmax(pp));selected=sels[best]
            target=set(top[:1] if market=='win' else top[:4] if market=='pair_top4' else top[:3])
            hit=int(set(selected if isinstance(selected,tuple) else (selected,))<=target)
            val[market].append({'date':r['date'],'probability':float(pp[best]),'observed_hit':hit})
        if i%1000==0:print('Calibration source races',i,flush=True)
    calibrators={k:fit_calibration(v) for k,v in val.items()}
    lock={'calibrators':calibrators,'validation_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'classic_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),
          'selection':'classic maximum-probability ticket only, one per race and market; no value selection',
          'fit_year':2025,'test_year':2026,'validation_exclusions':dict(excluded)}
    dump(ROOT/'calibration_frozen.json',lock) # Persist BEFORE reading 2026 outcomes.
    tests=[json.loads(line) for line in gzip.decompress((ROOT/'tickets.jsonl.gz').read_bytes()).splitlines()]
    totals=defaultdict(new_stats);seasons=defaultdict(new_stats);week=defaultdict(list);out=[]
    for r in tests:
        if r['model']!='classic':continue
        if not r['date'].startswith('2026-'):raise ValueError('Test year mismatch')
        c=calibrators[r['market']];p=apply_calibration(r['probability'],c);y=r['observed_hit']
        update(totals[r['market']],np.array([p]),np.array([y]))
        update(seasons[(r['market'],season(r['date']))],np.array([p]),np.array([y]))
        week[(r['market'],date.fromisoformat(r['date']).isocalendar()[:2])].append((p-y,(p-y)**2-(r['probability']-y)**2))
        out.append({**r,'raw_probability':r['probability'],'probability':p,
                    'break_even_total_return':1/max(p,1e-12),'total_return_for_5pct_scenario_ev':1.05/max(p,1e-12),
                    'status':'NO_BET_CALIBRATED_SELECTED_TICKET_ONLY_NO_PRICE'})
    result={'status':'EXPLORATORY_SELECTED_TICKET_CALIBRATION_NO_VALUE_PROOF','frozen':lock,'markets':{}}
    for market,s in totals.items():
        blocks=[v for (m,w),v in week.items() if m==market];sums=np.array([np.sum(v,axis=0) for v in blocks]);counts=np.array([len(v) for v in blocks])
        rng=np.random.default_rng(42);est=[]
        for _ in range(1000):
            ix=rng.integers(0,len(blocks),len(blocks));est.append(sums[ix].sum(axis=0)/counts[ix].sum())
        ci=np.quantile(est,[.025,.975],axis=0)
        result['markets'][market]={'overall':finish(s),'season':{se:finish(seasons[(market,se)]) for se in ('winter','spring','summer','autumn')},
          'weekly_bootstrap_95':{'mean_prediction_minus_frequency':ci[:,0].tolist(),'brier_calibrated_minus_raw':ci[:,1].tolist()}}
    result['limits']=['This calibrator applies ONLY to the classic maximum-probability ticket selection, not arbitrary tickets or EV-selected tickets.',
      'Probabilities across distinct markets are calibrated separately and are not a coherent joint arrival distribution.',
      '2026 already inspected: exploratory reused holdout; requires prospective validation.',
      'No ZEturf prices joined; no demonstrated value or profitability. Historical raw source publication timing unproven.',
      'The 2025 winner-temperature selection and placement calibration reuse validation; no nested calibration claim.',
      'Baseline and calibrator checked on the same restricted common cohort; exclusions may bias generalization.']
    dump(ROOT/'calibrated_comparison.json',result)
    (ROOT/'calibrated_tickets.jsonl.gz').write_bytes(gzip.compress(('\n'.join(json.dumps(r) for r in out)+'\n').encode(),mtime=0))
    lines=['# Selected-ticket calibration','','Fit: 2025 only. Test: 2026. Classic maximum-probability ticket only. No ROI claim.','',
       '| Market | Test races | Observed hits | Calibrated prediction | Selected-ticket Brier |', '|---|---:|---:|---:|---:|']
    for market,v in result['markets'].items():
        s=v['overall'];lines.append(f"| {market} | {s['races']} | {s['top_probability_hit_rate']:.2%} | {s['top_probability_mean_prediction']:.2%} | {s['race_weighted_binary_brier']:.5f} |")
    lines+=['']+result['limits'];(ROOT/'CALIBRATION.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({m:v['overall'] for m,v in result['markets'].items()}))

if __name__=='__main__':main()
