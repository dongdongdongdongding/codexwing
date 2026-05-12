# Learning Cycle Report (nightly)

- generated_at: 2026-05-12T14:50:16.704969+00:00
- action: dataset_refresh
- reason: nightly_learning_dataset_refreshed
- total_resolved: 5210
- new_resolved_since_last_cycle: 58
- resolved_by_market: {'NASDAQ': 92, 'AMEX': 81, 'KOSDAQ': 2863, 'KOSPI': 2155, 'KR': 18, 'US': 1}
- resolved_by_bucket: {'watchlist': 3045, 'picked': 927, 'exception_leader': 358, 'ignored': 880}

## Commands
- python3 multi_agent/tools/export_scan_archive_learning_dataset.py: OK (returncode=0)
- python3 multi_agent/tools/report_kr_walkforward_release_gate.py --market KOSPI: OK (returncode=0)
- python3 multi_agent/tools/report_kr_walkforward_release_gate.py --market KOSDAQ: OK (returncode=0)
