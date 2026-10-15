# Distance and venue audit

Exploratory simple-place study; no price/value claim.

| Distance (m) | Races | Observed placed | Predicted placed | 95% weekly interval | Autostart |
|---|---:|---:|---:|---|---:|
| <2100 | 99 | 49.5% | 47.8% | 40.7%–57.6% | 71.7% |
| 2100-2399 | 456 | 46.7% | 49.3% | 43.1%–50.5% | 79.6% |
| 2400-2799 | 1316 | 49.5% | 49.5% | 46.3%–52.7% | 34.1% |
| >=2800 | 1144 | 49.5% | 50.5% | 46.1%–52.7% | 2.4% |

## Findings
- Distance alone shows no clear separation: weekly uncertainty intervals overlap.
- The 2100–2399 m autostart subgroup deserves prospective checking, not an automatic betting rule.
- Distance-only standardization preserves the venue gap. Matching also on start, field size and season produces a much smaller, uncertain gap on a restricted overlap sample. This does not establish a causal explanation.

## Distance and start
| Group | Races | Observed | Predicted |
|---|---:|---:|---:|
| 2100-2399 / AUTOSTART | 363 | 44.6% | 49.8% |
| 2100-2399 / NON_PRECISE | 93 | 54.8% | 47.2% |
| 2400-2799 / AUTOSTART | 449 | 50.1% | 48.8% |
| 2400-2799 / NON_PRECISE | 867 | 49.1% | 49.9% |
| <2100 / AUTOSTART | 71 | 52.1% | 49.1% |
| <2100 / NON_PRECISE | 28 | 42.9% | 44.6% |
| >=2800 / AUTOSTART | 28 | 50.0% | 47.8% |
| >=2800 / NON_PRECISE | 1116 | 49.5% | 50.6% |

## Vincennes versus other tracks, standardized
| Adjustment | Common races | Vincennes | Other tracks | Other minus Vincennes (95% weekly interval) |
|---|---:|---:|---:|---|
| band | 2916 | 43.5% | 49.9% | 6.3 pp (1.2 to 11.8) |
| band, start, field_band, season | 1131 | 49.4% | 50.2% | 0.8 pp (-8.0 to 7.1) |

Only strata with at least 10 races in each venue group are included; pooled stratum weights are fixed. The two adjustments use different samples.

## Limits
- No causal distance effect: distance, track geometry, race class, start method, season and field composition may confound.
- 2026 results previously inspected; subgroup discovery exploratory, intervals not corrected for multiple comparisons.
- No price dataset joined: hit rates and calibration cannot establish value or ROI.
- Only classic maximum-probability place tickets, 10-20 runners, no non-runners, unique known top4.
- Weekly blocks retain some dependence through repeated horses; tiny cells and few-week intervals unreliable.
- UNKNOWN start type is never assumed to be a volte start.
