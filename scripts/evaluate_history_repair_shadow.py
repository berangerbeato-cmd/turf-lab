"""Paired exploratory scoring of immutable prestart history-repair replays.

No training, no betting, no retrospective price reconstruction. Scoring is kept
separate from replay feature construction and requires an independently
stored final result with unchanged race identities.
"""
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from turf_lab.evidence import dump
from turf_lab.history_repair_shadow import replay
from turf_lab.history_sync import History
from turf_lab.pilot import norm_name

SOURCE = Path('predictions_operational')
OUTPUT = Path('reports/history_repair_shadow_v1')
USER_REIMS = Path('reports/manual_bets/2026-11-21_R4C5_Z4.json')


def verified_finish(history, prediction, cache):
    rid = prediction['race_id']
    day = rid[:10]
    if day not in cache:
        try:
            state = history.day(day)
            cache[day] = {r['race_id']: r for r in state['records']}
        except (OSError, ValueError, KeyError, TypeError) as error:
            cache[day] = {}
    actual = cache[day].get(rid)
    if actual:
        snap = {p['numPmu']: p for p in prediction['target_snapshot']['participants']}
        current = {p['numPmu']: p for p in actual['participants']}
        if set(snap) != set(current):
            return None, 'OFFICIAL_FIELD_MISMATCH'
        if any(norm_name(snap[n]['nom']) != norm_name(current[n]['nom'])
               or snap[n]['statut'] != current[n]['statut'] for n in snap):
            return None, 'OFFICIAL_HORSE_IDENTITY_OR_STATUS_MISMATCH'
        ranks = {}
        for p in actual['participants']:
            rank = p.get('ordreArrivee')
            if isinstance(rank, int) and 1 <= rank <= 5:
                if rank in ranks:
                    return None, 'NON_UNIQUE_FINISH'
                ranks[rank] = p['numPmu']
        if set(ranks) != {1,2,3,4,5}:
            return None, 'INCOMPLETE_OFFICIAL_TOP5'
        return [ranks[n] for n in range(1,6)], 'VERIFIED_ARCHIVE'
    if rid == '2026-11-21_R4C5' and USER_REIMS.exists():
        user = json.loads(USER_REIMS.read_text())
        return user['result_reported_by_user_screenshot'][:5], 'ZETURF_SCREENSHOT'
    return None, 'PENDING_OFFICIAL_RESULT'


def score(report, finish):
    winner = finish[0]
    result = {}
    for k in ('v3_baseline','research_candidate'):
        p = {int(n): v for n,v in report[k]['probabilities'].items()}
        order = sorted(p, key=lambda n:(-p[n],n))
        result[k] = {
            'winner_probability': p[winner],
            'log_loss': -math.log(max(1e-15,p[winner])),
            'brier': sum((prob - int(n == winner)) ** 2 for n,prob in p.items()),
            'top1_correct': int(order[0] == winner),
            'top4_overlap': len(set(order[:4]) & set(finish[:4])),
            'top5_overlap': len(set(order[:5]) & set(finish[:5])),
            'top4_exact': int(set(order[:4]) == set(finish[:4])),
            'top5_exact': int(set(order[:5]) == set(finish[:5])),
        }
    return result


def run():
    snapshots = defaultdict(list)
    errors = []
    for path in sorted(SOURCE.glob('*/*/prediction.json')):
        try:
            summary = json.loads(path.read_text())
            if summary.get('primary_model') != 'available_history_v3' or summary.get('status') != 'PRESTART_RESEARCH':
                continue
            if not (path.parent / 'individual_history_evidence/manifest.json').exists():
                errors.append({'path':str(path),'status':'NO_ARCHIVED_INDIVIDUAL_EVIDENCE'})
                continue
            snapshots[summary['race_id']].append((summary['predicted_at'], path, summary))
        except (ValueError, TypeError, KeyError, OSError) as error:
            errors.append({'path':str(path),'status':'BAD_PREDICTION','reason':str(error)})
    chosen = [sorted(values, key=lambda x:x[0])[0] for values in snapshots.values()]
    history = History()
    outcome_cache = {}
    scored = []
    pending = []
    sample = []
    for _, path, prediction in sorted(chosen):
        rid = prediction['race_id']
        try:
            report = replay(path)
            output = OUTPUT / 'replays_corrected' / (path.parent.name+'.json')
            if output.exists():
                if json.loads(output.read_text()) != report:
                    raise ValueError('Immutable research replay would change')
            else:
                dump(output, report)
            finish, result_source = verified_finish(history, prediction, outcome_cache)
            rec = {'race_id':rid, 'source_prediction':str(path),
                   'source_report':str(output),
                   'changed_runners':report['runners_changed_recent5'],
                   'runner_status_counts':dict(sorted(
                       {status:sum(r['status']==status for r in report['runner_audit'])
                        for status in {r['status'] for r in report['runner_audit']}}.items()))}
            if finish is not None:
                rec.update(result_source=result_source, finish_top5=finish,
                           comparisons=score(report,finish))
                scored.append(rec)
            else:
                rec['result_status'] = result_source
                pending.append(rec)
            sample.append(rec)
        except (ValueError,TypeError,KeyError,OSError) as error:
            errors.append({'race_id':rid,'path':str(path),'status':'REPLAY_FAILED','reason':str(error)})
    keys = ('log_loss','brier','top1_correct','top4_overlap','top5_overlap','top4_exact','top5_exact')
    paired = {k:{metric:mean(r['comparisons'][k][metric] for r in scored)
                 for metric in keys} for k in ('v3_baseline','research_candidate')} if scored else {}
    report = {
      'status':'POSTRACE_EXPLORATORY_PAIRED_REPLAY',
      'model':'history_repair_shadow_v1_recent5_only',
      'research_only':True, 'recommendations_allowed':False,
      'prospective_independent_test':False,
      'selection_rule':'Earliest archived prestart V3 prediction per race with original horse evidence',
      'races_with_candidate_evidence':len(chosen),
      'races_replayed':len(sample),
      'races_with_results':len(scored),
      'races_without_verified_results':len(pending),
      'races_with_candidate_changes':sum(x['changed_runners']>0 for x in sample),
      'paired_metrics':paired,
      'scored_races':scored,
      'pending_results':pending,
      'excluded_or_failed':errors,
      'caveats': [
          'Candidate was developed after reviewing Reims; earlier races are retrospective replays, NOT a virgin holdout.',
          'Frozen V3 benchmark and all archived predictions remain unchanged.',
          'Supplemental sources recorded prestart may be incomplete even if verified by hash.',
          'Any future promotion requires an independent prospective comparison and calibration review.',
          'No value or payout ROI computed.'
      ]
    }
    dump(OUTPUT/'batch_summary.json',report)
    print(json.dumps({
        'replayed':len(sample),'scored':len(scored),'pending':len(pending),
        'excluded_or_failed':len(errors),'paired_metrics':paired,
        'scored_races':[{k:r[k] for k in ('race_id','changed_runners')}
                        for r in scored],
    },indent=2))
    return report


if __name__=='__main__':
    run()
