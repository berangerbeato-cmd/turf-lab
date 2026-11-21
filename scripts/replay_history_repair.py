"""Replay immutable prestart horse histories without changing a frozen forecast."""
import argparse
import json
from pathlib import Path
from turf_lab.evidence import dump
from turf_lab.history_repair_shadow import replay


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--prediction', required=True)
    p.add_argument('--result-file')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    report = replay(args.prediction, args.result_file)
    out = Path(args.output)
    if out.exists():
        previous = json.loads(out.read_text())
        if previous != report:
            raise ValueError('Immutable history-repair replay report would change')
    dump(out, report)
    print(json.dumps({
        'race_id': report['race_id'],
        'status': report['status'],
        'changed_runners': report['runners_changed_recent5'],
        'v3_top4': report['v3_baseline']['top4'],
        'candidate_top4': report['research_candidate']['top4'],
        'postrace_check': report.get('postrace_check'),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
