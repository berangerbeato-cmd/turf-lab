# January 2024 extension protocol

Purpose: validate full-calendar collection before any multi-year backfill.

- Population: all French ATTELE/TROT_ATTELE races listed by the PMU programmes, January 1–31 2024. This does not assert coverage of unlisted French races.
- Raw sources: programme, participants, race detail. No odds scraping or market endpoints.
- Budget: 1,800 requests per run, cached successful and failed responses, 0.5 seconds between requests. No automated bypass or repeated access-denied retry.
- Acceptance: a retrieved programme for every day; declared runner count, identities, final arrival and unique winning label checked per race. Exclusions remain in the denominator and have explicit reasons.
- Archive: compressed raw response bytes and SHA-256 manifests committed to Git, plus controlled race records. Actions artifacts are diagnostic copies only.
- Model features: previous retained races strictly before the target calendar day. No current result, current time, current odds, retrospective music or current cumulative gain used as predictors.
- Identity: exact normalized name and both parents when available; otherwise official horse ID. Do not bridge uncertain identities. Contradictory official IDs/pedigrees fail construction.
- Missing history: retain explicit cold starts. Last observed race need not be last actual race. A month alone is insufficient to claim complete career histories or reliable rest intervals.
- Features reuse pilot definitions (last five observed starts): win/top-three/DQ rates, days since last observed start, observed depth. No new fitting or scoring in this phase.
- Expansion gate: inspect missing daily programmes, race quarantine reasons, regional representation, start-type availability and observed-history coverage. Choose any additional period before training; preserve separate chronological train/validation/test periods and the frozen prospective model.
- Pilot test on October 5, 2026 has already been inspected and is not a fresh holdout for model selection.

Current deployment: initial monthly collection run 38313938501. Completion and durable save must be verified; do not infer success from deployment alone.
