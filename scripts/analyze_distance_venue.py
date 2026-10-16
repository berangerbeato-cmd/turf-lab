"""Exploratory distance/venue audit of frozen selected-ticket probabilities."""
import argparse,gzip,hashlib,json,subprocess
from collections import Counter,defaultdict
from datetime import date
from pathlib import Path
import numpy as np


def distance_band(d):
    if not isinstance(d,(int,float)) or isinstance(d,bool) or not np.isfinite(d) or d<=0:return 'unknown'
    return '<2100' if d<2100 else '2100-2399' if d<2400 else '2400-2799' if d<2800 else '>=2800'


def season(day):
    m=int(day[5:7]);return 'winter' if m in (12,1,2) else 'spring' if m in (3,4,5) else 'summer' if m in (6,7,8) else 'autumn'


def summary(rows):
    if not rows:return {'n':0}
    n=len(rows);hits=sum(r['hit'] for r in rows);pred=sum(r['p'] for r in rows)/n
    blocks=defaultdict(lambda:np.zeros(3))
    for r in rows:blocks[r['week']]+=np.array([1,r['hit'],r['p']])
    a=np.array(list(blocks.values()));rng=np.random.default_rng(20261015)
    sampled=a[rng.integers(0,len(a),(3000,len(a)))].sum(axis=1)
    rate=sampled[:,1]/sampled[:,0];bias=(sampled[:,2]-sampled[:,1])/sampled[:,0]
    return {'n':n,'weeks':len(a),'hits':hits,'hit_rate':hits/n,'mean_prediction':pred,
      'prediction_minus_observed':pred-hits/n,'hit_rate_week_bootstrap95':np.quantile(rate,[.025,.975]).tolist(),
      'bias_week_bootstrap95':np.quantile(bias,[.025,.975]).tolist(),
      'selected_ticket_brier':sum((r['p']-r['hit'])**2 for r in rows)/n,
      'mean_field_size':sum(r['field'] for r in rows)/n,
      'autostart_fraction':sum(r['start']=='AUTOSTART' for r in rows)/n,
      'vincennes_fraction':sum(r['venue']=='VINCENNES' for r in rows)/n,
      'seasons':dict(Counter(r['season'] for r in rows))}


def adjusted_venue(rows, fields):
    """Common-support direct standardization; fixed observed pooled weights."""
    by=defaultdict(lambda:[[],[]])
    for r in rows:by[tuple(r[k] for k in fields)][int(r['venue']!='VINCENNES')].append(r)
    eligible={k:v for k,v in by.items() if min(map(len,v))>=10}
    if not eligible:return {'status':'INSUFFICIENT_COMMON_SUPPORT'}
    keys=list(eligible);weeks=sorted({r['week'] for pair in eligible.values() for group in pair for r in group})
    wi={w:i for i,w in enumerate(weeks)};a=np.zeros((len(weeks),len(keys),2,3))
    for si,k in enumerate(keys):
        for gi,group in enumerate(eligible[k]):
            for r in group:a[wi[r['week']],si,gi]+=np.array([1,r['hit'],r['p']])
    totals=a.sum(axis=0);weights=totals[:,:,0].sum(axis=1);weights/=weights.sum()
    rates=(totals[:,:,1]/totals[:,:,0]*weights[:,None]).sum(axis=0)
    predictions=(totals[:,:,2]/totals[:,:,0]*weights[:,None]).sum(axis=0)
    rng=np.random.default_rng(20261015);delta=[]
    for _ in range(3000):
        s=a[rng.integers(0,len(weeks),len(weeks))].sum(axis=0)
        if (s[:,:,0]==0).any():continue
        rr=(s[:,:,1]/s[:,:,0]*weights[:,None]).sum(axis=0);delta.append(rr[1]-rr[0])
    return {'strata_fields':fields,'strata':len(keys),'n_common_support':int(totals[:,:,0].sum()),
      'n_by_group':totals[:,:,0].sum(axis=0).astype(int).tolist(),
      'vincennes_standardized_hit':float(rates[0]),'other_standardized_hit':float(rates[1]),
      'standardized_predictions':predictions.tolist(),'other_minus_vincennes':float(rates[1]-rates[0]),
      'difference_week_bootstrap95':np.quantile(delta,[.025,.975]).tolist(),
      'valid_bootstrap_replicates':len(delta),'note':'Pooled weights on overlapping strata with >=10 races per group; descriptive, not causal.'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--git-ref');args=ap.parse_args()
    def read(path):
        return subprocess.check_output(['git','show',args.git_ref+':'+path]) if args.git_ref else Path(path).read_bytes()
    feature_bytes=read('reports/full_history/datasets/test.jsonl.gz');ticket_bytes=read('reports/market_evaluation/calibrated_tickets.jsonl.gz')
    features={r['race_id']:r for r in map(json.loads,gzip.decompress(feature_bytes).splitlines())}
    tickets=list(map(json.loads,gzip.decompress(ticket_bytes).splitlines()));rows=[]
    for t in tickets:
        if t['market']!='place3':continue
        r=features[t['race_id']];field=len(r['runners'])
        rows.append({'race_id':t['race_id'],'date':t['date'],'week':date.fromisoformat(t['date']).isocalendar()[:2],
          'hit':t['observed_hit'],'p':t['probability'],'venue':r['venue'],'distance':r['distance_m'],
          'band':distance_band(r['distance_m']),'start':r['start_type'],'field':field,
          'field_band':'10-12' if field<=12 else '13-15' if field<=15 else '16-20','season':season(t['date'])})
    if len({r['race_id'] for r in rows})!=len(rows):raise ValueError('Duplicate selected ticket')
    out={'status':'EXPLORATORY_REUSED_TEST_NO_PRICE_OR_PROFIT_CLAIM','n':len(rows),
         'source_sha256':{'features':hashlib.sha256(feature_bytes).hexdigest(),'tickets':hashlib.sha256(ticket_bytes).hexdigest()},
         'distance_bands':{},'exact_distances':{},'venue_distance':{},'distance_start':{},'venue':{},'adjusted_venue':[]}
    for key,target in [('band','distance_bands'),('distance','exact_distances'),('venue','venue')]:
        groups=defaultdict(list)
        for r in rows:groups[str(r[key])].append(r)
        out[target]={k:summary(v) for k,v in sorted(groups.items())}
    for fields,target in [(('venue','band'),'venue_distance'),(('band','start'),'distance_start')]:
        groups=defaultdict(list)
        for r in rows:
            k=' | '.join(('VINCENNES' if r[f]=='VINCENNES' else 'OTHER_TRACKS') if f=='venue' else r[f] for f in fields)
            groups[k].append(r)
        out[target]={k:summary(v) for k,v in sorted(groups.items())}
    out['adjusted_venue']=[adjusted_venue(rows,['band']),adjusted_venue(rows,['band','start','field_band','season'])]
    out['limits']=['No causal distance effect: distance, track geometry, race class, start method, season and field composition may confound.',
      '2026 results previously inspected; subgroup discovery exploratory, intervals not corrected for multiple comparisons.',
      'No price dataset joined: hit rates and calibration cannot establish value or ROI.',
      'Only classic maximum-probability place tickets, 10-20 runners, no non-runners, unique known top4.',
      'Weekly blocks retain some dependence through repeated horses; tiny cells and few-week intervals unreliable.',
      'UNKNOWN start type is never assumed to be a volte start.']
    root=Path('reports/market_evaluation');root.mkdir(parents=True,exist_ok=True)
    (root/'distance_venue.json').write_text(json.dumps(out,indent=2)+'\n')
    lines=['# Distance and venue audit','','Exploratory simple-place study; no price/value claim.','',
      '| Distance (m) | Races | Observed placed | Predicted placed | 95% weekly interval | Autostart |',
      '|---|---:|---:|---:|---|---:|']
    for k in ['<2100', '2100-2399', '2400-2799', '>=2800', 'unknown']:
        if k not in out['distance_bands']:continue
        s=out['distance_bands'][k]
        ci=s['hit_rate_week_bootstrap95'];lines.append(f"| {k} | {s['n']} | {s['hit_rate']:.1%} | {s['mean_prediction']:.1%} | {ci[0]:.1%}–{ci[1]:.1%} | {s['autostart_fraction']:.1%} |")
    lines+=['','## Findings',
      '- Distance alone shows no clear separation: weekly uncertainty intervals overlap.',
      '- The 2100–2399 m autostart subgroup deserves prospective checking, not an automatic betting rule.',
      '- Distance-only standardization preserves the venue gap. Matching also on start, field size and season produces a much smaller, uncertain gap on a restricted overlap sample. This does not establish a causal explanation.',
      '', '## Distance and start',
      '| Group | Races | Observed | Predicted |', '|---|---:|---:|---:|']
    for k,s in out['distance_start'].items():
        lines.append(f"| {k.replace(' | ', ' / ')} | {s['n']} | {s['hit_rate']:.1%} | {s['mean_prediction']:.1%} |")
    lines+=['','## Vincennes versus other tracks, standardized',
      '| Adjustment | Common races | Vincennes | Other tracks | Other minus Vincennes (95% weekly interval) |',
      '|---|---:|---:|---:|---|']
    for a in out['adjusted_venue']:
        ci=a['difference_week_bootstrap95']
        lines.append(f"| {', '.join(a['strata_fields'])} | {a['n_common_support']} | {a['vincennes_standardized_hit']:.1%} | {a['other_standardized_hit']:.1%} | {100*a['other_minus_vincennes']:.1f} pp ({100*ci[0]:.1f} to {100*ci[1]:.1f}) |")
    lines+=['', 'Only strata with at least 10 races in each venue group are included; pooled stratum weights are fixed. The two adjustments use different samples.', '', '## Limits']+['- '+x for x in out['limits']]
    (root/'DISTANCE_VENUE.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:out[k] for k in ['n','distance_bands','venue_distance','distance_start','adjusted_venue']}))

if __name__=='__main__':main()
