# Historical freshness incident — 16 October 2026

The manual R2C5 forecast used the extended classic model but source history only through October 13. Existing scheduled workflows observed limited pilot cohorts; they did not append all daily French harness results to the extended-history inputs. This was an operational integration gap, not an intentional historical exclusion.

Recovery collected 12 races on October 14 and 13 on October 15; all 25 passed the daily final-arrival and existing quality checks. The combined loader was exercised locally: 29,815 races through October 15, excluding the documented historical month/race exclusions and with no same-day results.

New operational commands (research branch):

```
python -m scripts.refresh_recent_history
python -m scripts.predict_full_history_live --reunion 2 --course 5
```

The prediction command requires complete daily inputs through yesterday, verifies model/calibration hashes, obtains current participants and refuses late completion. Historical gaps already documented remain; daily completeness is relative to PMU-listed French harness races. Future non-runners remain outside the current placement calibration cohort.

The default-branch workflow `.github/workflows/recent_history.yml` schedules daily collection at 04:20 and 06:20 UTC (second run retries incomplete days). It checks out and saves to the research branch. It never retrains or replaces models. GitHub scheduling can be delayed; the prediction freshness gate is the enforcement mechanism, not the cron alone.

The original R2C5 forecast and its late timestamp are preserved. The user-requested hypothetical 14 place ticket is recorded separately with one-euro reference stake and excluded from prospective validation. No retroactive corrected prediction is substituted.

Three focused freshness tests pass. Full prospective success of the new prediction command awaits a future race; the model and feature computation were executed separately for R2C5. Full historical feature reconstruction still takes several minutes and is not yet cached for fast live inference.
