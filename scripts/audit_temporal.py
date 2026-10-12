"""Check whether date-keyed historical performance responses stay before target."""
import collections
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from turf_lab.evidence import EvidenceStore, dump

CASES=[('2024-01-28',1,1),('2024-05-15',1,1),('2025-01-26',1,1),('2025-05-14',1,1)]


def main():
    store=EvidenceStore('evidence/temporal_audit_2026-10-12',max_requests=8)
    out={'cases':[]}
    for day,rn,cn in CASES:
        # Slash belongs to the endpoint, not to the on-disk evidence key.
        ds=datetime.fromisoformat(day).strftime('%d%m%Y')
        url=f'https://offline.turfinfo.api.pmu.fr/rest/client/7/programme/{ds}/R{rn}/C{cn}/performances-detaillees/pretty'
        data=store.get(url,f'{day}_R{rn}C{cn}_performances_pretty')
        item={'race_id':f'{day}_R{rn}C{cn}','status':'unavailable','horses':0,'history_rows':0,'on_or_after_target':0,'max_history_per_horse':0}
        if isinstance(data,dict) and data.get('participants'):
            dates=[];fields=collections.Counter();item['status']='available';item['horses']=len(data['participants'])
            for horse in data['participants']:
                histories=horse.get('coursesCourues',[])
                item['max_history_per_horse']=max(item['max_history_per_horse'],len(histories))
                for run in histories:
                    item['history_rows']+=1
                    for key,value in run.items():
                        if value is not None and value!='' and value!=[]:fields[key]+=1
                    stamp=run.get('date')
                    if stamp is None:
                        item['invalid_dates']=item.get('invalid_dates',0)+1
                        continue
                    date_string=(datetime.fromtimestamp(stamp/1000,timezone.utc)+timedelta(milliseconds=run.get('timezoneOffset',0))).date().isoformat()
                    dates.append(date_string)
                    if date_string>=day:item['on_or_after_target']+=1
                    selected=[r for r in run.get('participants',[]) if r.get('itsHim') is True]
                    if len(selected)!=1:item['ambiguous_self_rows']=item.get('ambiguous_self_rows',0)+1
            item.update(first_history_date=min(dates) if dates else None,last_history_date=max(dates) if dates else None,
                        field_counts=dict(fields))
        out['cases'].append(item)
        dump('reports/temporal_audit.json',out)
    print(json.dumps(out,ensure_ascii=False))


if __name__=='__main__':main()
