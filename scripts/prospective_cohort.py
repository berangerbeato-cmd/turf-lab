"""Fixed-date, bounded V6/V7 observation. No training, market endpoint or bets."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo
from scripts.shadow_v7 import compute, verify as verify_models
from scripts.shadow_connections import live_record, load_partial
from scripts.backtest_extension import load_sources
from scripts.backtest_connections import digest
from scripts.collect_month import collect, git_checkpoint
from turf_lab.shadow_quarantine import apply_quarantine
from turf_lab.shadow_v5_score import score
from turf_lab.evidence import EvidenceStore, dump, races

POLICY = Path('config/prospective_cohort.json')
ROOT = Path('predictions_cohort')


def verify():
    p = json.loads(POLICY.read_text())
    lock = json.loads(Path('models/prospective_cohort_frozen.json').read_text())
    model_lock, _, _ = verify_models()
    if lock['models'] != model_lock or lock['policy_sha256'] != digest(POLICY):
        raise ValueError('Cohort freeze mismatch')
    if any(digest(path) != sha for path,sha in lock['files_sha256'].items()):
        raise ValueError('Cohort code changed')
    return p, lock


def select(items, limit):
    if limit < 2:
        raise ValueError('At least two sampling slots required')
    items = sorted(items, key=lambda rc:(rc[1]['heureDepart'],rc[0]['numOfficiel'],rc[1]['numOrdre']))
    if len(items) <= limit:
        return items
    return [items[i*(len(items)-1)//(limit-1)] for i in range(limit)]


def history_before(today, policy):
    legacy = json.loads(Path('config/connections_v5_prospective.json').read_text())
    records, coverage = load_sources({'months':legacy['completed_months'],'minimum_retained_fraction_per_month':legacy['minimum_coverage']})
    records, coverage, quarantines = apply_quarantine(records,coverage,legacy['history_quarantine'],legacy['minimum_coverage'])
    through = (today-timedelta(days=1)).isoformat()
    if through[:7] != '2026-10':
        raise ValueError('History month outside cohort scope')
    root, output = Path('evidence/month_2026-10'), Path('data/month_2026-10')
    store = EvidenceStore(root,max_requests=policy['max_history_requests'],delay=.5)
    report = collect('2026-10',store,output,lambda:git_checkpoint(root,output),through=through)
    if report['status'] == 'PAUSED_REQUEST_BUDGET':
        raise RuntimeError('History request budget reached')
    recent, partial = load_partial('2026-10',through,legacy['minimum_coverage'])
    return records+recent, {'completed':coverage,'partial':partial,'quarantine':quarantines,'through':through}


def capture(today, p, lock):
    day = today.isoformat()
    if not p['from'] <= day <= p['through']:
        return
    folder = ROOT/day
    plan_path = folder/'plan.json'
    store = EvidenceStore('evidence/cohort_capture/'+day,max_requests=1+p['max_races_per_day'],delay=.5)
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        if plan['frozen'] != lock:
            raise ValueError('Existing daily plan freeze mismatch')
    else:
        programme = store.programme(day)
        if not isinstance(programme,dict):
            raise ValueError('Programme unavailable; no substitute day')
        eligible = list(races(programme))
        selected = select(eligible,p['max_races_per_day'])
        plan = {'date':day,'frozen':lock,'planned_at':datetime.now(timezone.utc).isoformat(),
            'eligible':len(eligible),'selection':selected,'evidence_manifest':str(store.manifest_path)}
        dump(plan_path,plan)
    pending = [(m,c) for m,c in plan['selection'] if not (folder/f"{day}_R{m['numOfficiel']}C{c['numOrdre']}.json").exists()]
    if not pending:
        return
    history, coverage = history_before(today,p)
    source_sha = hashlib.sha256(json.dumps(history,sort_keys=True).encode()).hexdigest()
    for meeting, course in pending:
        rid = f"{day}_R{meeting['numOfficiel']}C{course['numOrdre']}"
        path = folder/(rid+'.json')
        try:
            if course['heureDepart'] <= datetime.now(timezone.utc).timestamp()*1000:
                raise ValueError('Missed before-start capture')
            raw = store.race(day,meeting['numOfficiel'],course['numOrdre'],'participants')
            target = live_record(day,meeting,course,(raw or {}).get('participants'),datetime.now(timezone.utc))
            _, models = compute(history,target)
            now = datetime.now(timezone.utc)
            if now.timestamp()*1000 >= course['heureDepart']:
                raise ValueError('Start passed during computation')
            record = {'status':'SHADOW_NO_BET','race_id':rid,'date':day,'models':models,'frozen':lock,
                'predicted_at':now.isoformat(),'scheduled_start':datetime.fromtimestamp(course['heureDepart']/1000,timezone.utc).isoformat(),
                'target_snapshot':target,'history_through':coverage['through'],'history_sha256':source_sha,
                'coverage':coverage,'evidence_manifest':str(store.manifest_path)}
        except (ValueError,KeyError,TypeError) as error:
            record = {'status':'REJECTED_CAPTURE','race_id':rid,'reason':str(error),'frozen':lock,
                'checked_at':datetime.now(timezone.utc).isoformat()}
        dump(path,record)


def evaluate(now,p,lock):
    day = now.astimezone(ZoneInfo('Europe/Paris')).date().isoformat()
    if not p['from'] <= day <= p['score_through']:
        return
    batch = now.strftime('%Y%m%dT%H%M%S%fZ')
    store = EvidenceStore('evidence/cohort_results/'+batch,max_requests=p['max_result_requests'],delay=.5)
    output=[]
    for path in sorted(ROOT.glob('*/*_R*C*.json')):
        prediction=json.loads(path.read_text())
        rid=prediction['race_id']
        info={'race_id':rid,'snapshot':str(path),'snapshot_sha256':digest(path)}
        result_path=Path('reports/cohort_results')/(rid+'.json')
        if prediction['frozen'] != lock:
            raise ValueError('Captured cohort freeze changed')
        if prediction['status']=='REJECTED_CAPTURE':
            output.append(dict(info,status='REJECTED_CAPTURE',reason=prediction['reason']))
            continue
        if result_path.exists():
            previous=json.loads(result_path.read_text())
            if previous['snapshot_sha256'] != info['snapshot_sha256']:
                raise ValueError('Scored snapshot changed')
            if previous['status'] in ('SCORED','QUARANTINE'):
                output.append(previous)
                continue
        if now <= datetime.fromisoformat(prediction['scheduled_start']):
            output.append(dict(info,status='PENDING',reason='race_not_started'))
            continue
        if store.requests+2 > p['max_result_requests']:
            output.append(dict(info,status='PENDING',reason='bounded_result_budget'))
            continue
        date,rn,cn=re.fullmatch(r'(\d{4}-\d{2}-\d{2})_R(\d+)C(\d+)',rid).groups()
        detail=store.race(date,int(rn),int(cn),'')
        runners=store.race(date,int(rn),int(cn),'participants')
        if not isinstance(detail,dict) or not isinstance(runners,dict) or not runners.get('participants'):
            result={'status':'PENDING','reason':'response_unavailable'}
        else:
            try:
                result=score(prediction,detail,runners['participants'],model_names=p['models'])
            except (ValueError,KeyError,TypeError) as error:
                result={'status':'QUARANTINE','reason':str(error)}
        result=dict(info,**result,evidence_manifest=str(store.manifest_path),checked_at=now.isoformat())
        dump(result_path,result)
        output.append(result)
    scored=[r for r in output if r['status']=='SCORED']
    aggregate={n:{k:mean(r['models'][n][k] for r in scored) for k in ('log_loss','brier_multiclass','top1_hit')} for n in p['models']} if scored else {}
    expected_days=[(datetime.fromisoformat(p['from']).date()+timedelta(days=i)).isoformat() for i in range((min(datetime.fromisoformat(p['through']).date(),now.astimezone(ZoneInfo('Europe/Paris')).date())-datetime.fromisoformat(p['from']).date()).days+1)]
    missing_days=[d for d in expected_days if not (ROOT/d/'plan.json').exists()]
    planned=sum(len(json.loads(x.read_text())['selection']) for x in ROOT.glob('*/plan.json'))
    report={'status':'OBSERVATION_ONLY_NO_BET','checked_at':now.isoformat(),'frozen':lock,'planned':planned,
        'scored':len(scored),'missing_capture_records':planned-len(output),'missing_programme_days':missing_days,
        'races':output,'metrics':aggregate,'promotion':False}
    dump('reports/cohort_status.json',report)
    dump('reports/cohort_runs/'+batch+'.json',report)


def main(mode):
    p,lock=verify()
    now=datetime.now(timezone.utc)
    today=now.astimezone(ZoneInfo('Europe/Paris')).date()
    if not p['from'] <= today.isoformat() <= p['score_through']:
        print('Outside fixed cohort dates; no requests')
        return
    if mode=='capture':
        capture(today,p,lock)
    evaluate(datetime.now(timezone.utc),p,lock)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['capture','score'],required=True)
    main(parser.parse_args().mode)
