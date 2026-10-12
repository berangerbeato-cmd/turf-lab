"""One-day deep PMU data availability audit. No model/database changes."""
import argparse, collections, json, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE="https://offline.turfinfo.api.pmu.fr/rest/client/7/programme"
def get(url):
    try:
        with urlopen(Request(url,headers={"Accept":"application/json","User-Agent":"TurfLabAudit/1.0"}),timeout=25) as r:
            return json.load(r),r.status
    except HTTPError as e: return None,e.code
    except (URLError,TimeoutError,ValueError) as e: return None,str(e)
def flatten(prefix,obj,acc):
    if isinstance(obj,dict):
        for k,v in obj.items(): flatten(prefix+"."+k if prefix else k,v,acc)
    elif isinstance(obj,list):
        acc[prefix+"[]"]+=1
        if obj: flatten(prefix+"[]",obj[0],acc)
    else: acc[prefix]+=1
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--date",default="2026-10-05")
    a=p.parse_args(); date=a.date; d=date[8:10]+date[5:7]+date[:4]
    out=Path("data/deep_audit")/date;out.mkdir(parents=True,exist_ok=True)
    programme,status=get(f"{BASE}/{d}")
    if not isinstance(programme,dict): raise SystemExit(f"programme: {status}")
    (out/"programme.json").write_text(json.dumps(programme,ensure_ascii=False),encoding="utf-8")
    reunions=programme.get("programme",{}).get("reunions",[])
    keys=collections.Counter();missing=collections.Counter();examples={};counts=collections.Counter();endpoints=[]
    for reunion in reunions:
        if reunion.get("pays",{}).get("code") != "FRA":continue
        rn=reunion.get("numOfficiel")
        for course in reunion.get("courses",[]):
            if course.get("discipline") not in ("ATTELE","TROT_ATTELE"):continue
            cn=course.get("numOrdre");counts["races"]+=1
            flatten("course",course,keys)
            for endpoint in ("participants","rapports-definitifs", ""):
                url=f"{BASE}/{d}/R{rn}/C{cn}"+(f"/{endpoint}" if endpoint else "")
                data,status=get(url);counts["requests"]+=1
                endpoints.append({"race":f"R{rn}C{cn}","endpoint":endpoint or "course_detail","status":status})
                if data is not None:
                    filename=f"R{rn}C{cn}_{endpoint or 'course_detail'}.json"
                    (out/filename).write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
                    flatten(endpoint or "course_detail",data,keys)
                    if endpoint=="participants":
                        for runner in data.get("participants",[]):
                            counts["runners"]+=1
                            for k,v in runner.items():
                                if v is not None and v!="": missing[k]+=1
                                if k not in examples and v is not None: examples[k]=v
                time.sleep(0.25)
    report={"date":date,"counts":dict(counts),"runner_non_null_counts":dict(missing),
            "runner_examples":examples,"observed_json_paths":dict(keys),
            "endpoints":endpoints,
            "notes":["Post-race fields must not be used as pre-race features.",
                     "This audit measures field presence, not historical pre-race availability.",
                     "Cotes and payout fields need timestamp and units validation."]}
    (out/"audit_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("DEEP_AUDIT_SUMMARY",json.dumps({"counts":dict(counts),"endpoint_status":{f"{endpoint}:{status}": count for (endpoint, status), count in collections.Counter((x["endpoint"],str(x["status"])) for x in endpoints).items()}},ensure_ascii=False))
if __name__=="__main__":main()
