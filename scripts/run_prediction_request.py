"""Run explicit inputs or the versioned ChatGPT request; never silently use V1."""
import json,os
from datetime import datetime,timezone
from pathlib import Path
from turf_lab.evidence import dump


def record_history_repair_shadow(prediction_path, state):
    """Best-effort experimental forecast; never block or replace frozen V3."""
    try:
        from turf_lab.history_repair_shadow import replay
        report = replay(prediction_path)
        completed = datetime.now(timezone.utc)
        start = datetime.fromisoformat(report['scheduled_start'])
        if completed >= start:
            state['history_repair_shadow_status'] = 'LATE_NOT_ARCHIVED'
            state['history_repair_shadow_reason'] = 'Replay ended after start; not a prospective observation'
            return
        report['status'] = 'PRESTART_HISTORY_REPAIR_SHADOW'
        report['shadow_calculated_at'] = completed.isoformat()
        report['source_request_id'] = state['request_id']
        report['is_independent_prospective_validation'] = False
        report['research_only'] = True
        report['recommendations_allowed'] = False
        dump(prediction_path.parent / 'history_repair_shadow_v1_1.json', report)
        state['history_repair_shadow_status'] = 'PRESTART_RECORDED'
    except Exception as error:
        # The production frozen models and odds comparison remain usable.
        state['history_repair_shadow_status'] = 'UNAVAILABLE'
        state['history_repair_shadow_reason'] = type(error).__name__ + ': ' + str(error)


def main():
    values=[os.environ.get(k,'') for k in ('RACE_DATE','RACE_MEETING','RACE_NUMBER')]
    if any(values) and not all(values):raise ValueError('All three explicit inputs required')
    explicit=any(values)
    data=json.loads(Path('config/prediction_request.json').read_text()) if not explicit else {}
    if not explicit:values=[str(data[k]) for k in ('date','reunion','course')]
    state={'request_id':data.get('request_id',os.getenv('GITHUB_RUN_ID','explicit-local')),
           'race_id':f'{values[0]}_R{int(values[1])}C{int(values[2])}',
           'started_at':datetime.now(timezone.utc).isoformat(),'status':'RUNNING',
           'github_run_id':os.getenv('GITHUB_RUN_ID')}
    dump('reports/operational/request_status.json',state)
    try:
        from scripts.predict_operational import run
        path=run(values[0],int(values[1]),int(values[2]))
        # V4 source evidence lives OUTSIDE scripts/predict_operational.py
        # because its original V3 SHA is permanently frozen.
        try:
            from scripts.capture_v4_context import capture_from_original
            captured=capture_from_original(path)
            state['v4_feature_status']=captured['status']
            state['v4_money_evidence']=captured['money_evidence']
        except (ValueError,KeyError,TypeError,OSError,RuntimeError) as error:
            state['v4_feature_status']='BLOCKED_NO_BET'
            state['v4_feature_reason']=type(error).__name__+': '+str(error)
        record_history_repair_shadow(path, state)
        if data.get('quotes'):
            from turf_lab.operational_quotes import compare
            result=compare(json.loads(path.read_text()),data['quotes'])
            dump(path.parent/'quotes.json',data['quotes'])
            dump(path.parent/'comparison.json',result)
            # Optional, isolated comparison: same frozen V2 weights applied to
            # both sports histories on exactly this verified prestart board.
            # Failure cannot alter existing market comparison or paper ticket.
            try:
                from turf_lab.value_history_pair import paired
                candidate_path = path.parent/'history_repair_shadow_v1_1.json'
                if not candidate_path.exists():
                    raise ValueError('No eligible prestart History Repair V1.1 sidecar')
                pair = paired(json.loads(path.read_text()),
                              json.loads(candidate_path.read_text()),
                              data['quotes'],result)
                if pair['status'] != 'PRESTART_PAIRED_ON_DEMAND':
                    raise ValueError('Candidate comparison was not computed before departure')
                dump(path.parent/'value_history_pair_v1.json',pair)
                state['value_history_pair_status']='PRESTART_RECORDED'
            except (ValueError, KeyError, TypeError, OSError) as error:
                state['value_history_pair_status']='UNAVAILABLE'
                state['value_history_pair_reason']=str(error)
            dump('reports/operational/latest_comparison.json',dict(result,request_id=state['request_id']))
            # Independently record the daily paper-ticket rule, even when an early
            # odds snapshot is not eligible for the prospective SG J-15 study.
            try:
                from turf_lab.daily_ticket import make_ticket,load_protocol
                ticket=make_ticket(json.loads(path.read_text()),data['quotes'],result,load_protocol())
                dump(path.parent/'daily_ticket.json',ticket)
                dump('reports/operational/latest_ticket.json',dict(ticket,request_id=state['request_id']))
                state['daily_ticket_status']='PAPER_RECORDED'
            except ValueError as error:
                state['daily_ticket_status']='UNAVAILABLE'
                state['daily_ticket_reason']=str(error)
            from turf_lab.sg_strategy_comparison import archive
            try:
                archive(json.loads(path.read_text()),data['quotes'])
                state['sg_comparison_status']='ARCHIVED'
            except ValueError as error:
                state['sg_comparison_status']='INELIGIBLE'
                state['sg_comparison_reason']=str(error)
        # The only user-facing V4 report. Required history repair cannot
        # silently fall back to V3. Older frozen outputs stay untouched.
        try:
            from turf_lab.v4_multifeature_inference import record as record_v4
            repair_file = path.parent/'history_repair_shadow_v1_1.json'
            speed_file = path.parent/'v4_speed_context.json'
            aux_file = path.parent/'v4_aux_context.json'
            if not repair_file.exists():
                raise ValueError('Required History Repair V1.1 unavailable')
            if not speed_file.exists():
                raise ValueError('Required prestart contextual chrono unavailable')
            if not aux_file.exists():
                raise ValueError('Required prior-class/gains/form/R evidence unavailable')
            # ONE V4 with 47 features and a trained reliability-conditioned
            # market correction. Never silently reintroduce an older engine.
            prices_file = path.parent/'quotes.json'
            if not prices_file.exists():
                prices_file = None
            v4 = record_v4(path,repair_file,speed_file,aux_file,prices_file)
            dump('reports/v4/latest.json',v4)
            state['v4_status'] = v4['status']
            state['v4_report'] = str(path.parent/'v4_integrated.json')
        except (ValueError,TypeError,KeyError,OSError,RuntimeError) as error:
            state['v4_status'] = 'BLOCKED_NO_BET'
            state['v4_reason'] = str(error)
            dump('reports/v4/latest.json',{'version':'turf_lab_v4_fully_integrated_1',
                'race_id':state['race_id'],'status':'BLOCKED_NO_BET',
                'recommendations_allowed':False,'decision':'NO BET',
                'reason':str(error),'single_public_response':True})
        state.update(status='SUCCESS',prediction=str(path),quotes_compared=bool(data.get('quotes')))
        latest=json.loads(Path('reports/operational/latest.json').read_text())
        dump('reports/operational/latest.json',dict(latest,request_id=state['request_id']))
    except Exception as error:
        state.update(status='FAILED',error=str(error));raise
    finally:
        state['completed_at']=datetime.now(timezone.utc).isoformat()
        dump('reports/operational/request_status.json',state)

if __name__=='__main__':main()
