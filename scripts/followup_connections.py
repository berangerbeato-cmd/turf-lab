"""Refresh before the first declared start; tolerate delayed scheduled jobs."""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.shadow_connections import main as capture, record_failure
from scripts.score_connections_shadow import main as score


def needs_refresh(snapshots, now, today):
    if today != '2026-10-14':
        return False
    existing = [p for values in snapshots.values() for p in values]
    refreshed = all(any(p.get('history_gap_days') == 0 and p['predicted_at'][:10] == today for p in values)
                    for values in snapshots.values())
    return bool(existing) and not refreshed and now < min(datetime.fromisoformat(p['scheduled_start']) for p in existing)


def main():
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo('Europe/Paris')).date().isoformat()
    if today == '2026-10-14':
        policy = json.loads(Path('config/v5_followup.json').read_text())
        snapshots = {rid: [json.loads(path.read_text()) for path in Path('predictions_v5').glob(rid[:10]+'/'+rid+'_*/prediction.json')]
                     for rid in policy['race_ids']}
        if needs_refresh(snapshots, now, today):
            state = {}
            try:
                capture(state, today)
            except (ValueError, RuntimeError, FileNotFoundError, KeyError, TypeError) as error:
                record_failure(state, error)
                raise
    score()
    score(v6=True)


if __name__ == '__main__':
    main()
