# Low-liquidity H10 historical source scope

The earlier Q3 audit of 1,310 test-universe codes does not cover the training period or all market-context contributors. `freeze_lowliq_history_scope.py` now freezes an outcome-independent **1,857,109-row / 2,949-code** price-verification footprint, from **2023-12-15 through 2026-10-02**. This is a conservative superset, not a source certificate or a replacement study.

The parent training eligibility keys and all 62 frozen test-universe files contribute **410,384 unique code/date keys / 2,402 codes**. Selection does not use training target/status, chosen picks, scores or test outcomes. The parent training, model, score, source and code hashes are pinned. The immutable v7 source SHA is `2dca1f0b55a5614a8e6faa076e881d435955775061df6ed8d098622bba36c73a`.

The footprint includes every source row from **2024-05-30**, including currently ineligible, delisted and nontrading rows; every signal-period code's 130 earlier observations; and each market-context row's prior observed per-code row. Full consecutive-up boundaries are checked against both the fit snapshot and v7 adjusted closes. Neither snapshot required an extension beyond this conservative lookback. All training label source dates through the June 30 fit cutoff are included. No test strategy return or touch result is calculated.

The market momentum ratio mathematically depends on the preceding 20 weighted returns. An independent finite-product computation agrees with the original cumulative-level computation after float32 conversion: **549 dates per market on v7 and 485 per market on the fit snapshot**, zero mismatches; maximum float64 difference `1.23e-13`. This is empirical parity for these pinned snapshots. Full source panels remain the computational inputs; the footprint does not replace them or promise identical cumulative rounding under arbitrary future revisions.

Each request spans at most 90 calendar days, with explicit expected source dates. Both nominal and adjusted prices require **65,796 requests**. `capture_lowliq_history.py` bounds new calls and elapsed time, spaces calls by at least 0.35 seconds by default, takes a process lock, preserves parsed provider JSON with hashes, and verifies identity/payload/inspection before reuse. Missing dates, empty provider history and request failures remain explicit. Error receipts are not silently retried or overwritten. A separate reviewed capture epoch is needed for retries. A completed attempt count is not complete source coverage.

Initial live probe: **10 calls / 10 CAPTURED**, 3.28 seconds. A subsequent bounded 1,000-call batch was started. It uses read-only provider requests and does not restart the natural operational batch. Capture progress remains under issue `swing-main-d277`.

Validation: **20 tests passed**, covering old market-context predecessors, long up-runs, fit-snapshot boundary extension, all-code coverage, duplicate-key failure, complete request partitioning, request-budget resume, preserved errors, missing dates and corrupted receipt rejection. Actual scope regeneration made **zero network calls** and preserved all three artifacts' hashes, sizes and modification times.

Artifacts under production `runtime_state/audit/lowliq_history_scope_20261007`:

| Artifact | SHA256 |
|---|---|
| `plan.json` | `096169882e8f3ef773516d7dbec19c90fb1acde8047f1df54b1e45970f35636a` |
| `footprint.parquet` | `8b825b3e390da6e9df3b87c21e6fa334315426209d60d3a0a2f31a278b972da1` |
| `signal_keys.parquet` | `55222786e672733934f008564f38143f7de32d345104a137fdc7fa7e15e3b3ea` |

Captures are separate in `runtime_state/audit/lowliq_history_capture_20261007`. KIS daily price bars alone do not independently certify market-cap weights, historical market membership, publication timestamps, dividends, corporate-action wealth, or dates absent from the source itself. Those remain explicit limitations. Revised prices require a renewed scope check and a separately registered study; old models/scores remain immutable. The user target of 2–3 firing dates per five observed market sessions and H10 +5% touch ≥70% remains unqualified.

Independent actual-file checks passed: all 410,384 signal keys have their complete conservative stock lookbacks in the footprint; all 3,714,218 expected key/basis pairs occur exactly once; all source rows from May 30 are included. Both markets have all 21 preceding context dates (36,406 KOSDAQ and 20,018 KOSPI rows), and all **1,567,715** applicable context observations retain their exact prior per-code source row. Receipts are `independent_scope_verification.json`, `independent_context_verification.json`, and `repeat_verification.json`.
