import argparse,json
from pathlib import Path
from turf_lab.evidence import dump
from turf_lab.operational_quotes import compare

def main():
 p=argparse.ArgumentParser();p.add_argument('prediction');p.add_argument('quotes');a=p.parse_args()
 result=compare(json.loads(Path(a.prediction).read_text()),json.loads(Path(a.quotes).read_text()))
 root=Path(a.prediction).parent/'quotes'/result['calculated_at'].replace(':','')
 dump(root/'source.json',json.loads(Path(a.quotes).read_text()));dump(root/'comparison.json',result)
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
