"""Market-free feature-repair sensitivity. NOT a retrained or validated model."""
from copy import deepcopy
import math
from turf_lab.pilot import probabilities


def repaired_frame(model_result,checks):
    frame={'runners':deepcopy(model_result['runners'])}
    by={r['number']:r for r in checks['runners']}
    if len(by)!=len(checks['runners']):raise ValueError('Duplicate history check')
    changed=[]
    for r in frame['runners']:
        if r['non_runner']:continue
        check=by.get(r['number'])
        if not check or check['status'] not in ('MODEL_HISTORY_INCOMPLETE','NO_DISCREPANCY_IN_RETURNED_WINDOW'):
            raise ValueError('Unverified or conflicting history')
        values=check.get('supplemented_recent_features_for_research')
        if not isinstance(values,list) or len(values)!=5 or any(v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)) for v in values):
            raise ValueError('Invalid repaired features')
        if r['features'][:5]!=values:changed.append(r['number'])
        r['features'][:5]=values
    return frame,changed


def sensitivity(model_result,checks,model):
    frame,changed=repaired_frame(model_result,checks)
    return {'status':'FEATURE_REPAIR_SENSITIVITY_NOT_RETRAINED','market_informed':False,
        'recommendations_allowed':False,'probabilities':probabilities(frame,model),
        'changed_runners':changed,'changed_features':['win_rate','top3_rate','dq_rate','log_rest','history_coverage'],
        'limits':['Old fitted weights applied to enriched features: distribution shift, research sensitivity only.',
                  'Elo, driver, trainer and tandem features are not rebuilt from incomplete individual race fields.',
                  'No validation or economic advantage established.']}
