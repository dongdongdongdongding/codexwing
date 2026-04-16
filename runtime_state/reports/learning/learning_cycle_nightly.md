# Learning Cycle Report (nightly)

- generated_at: 2026-04-16T14:50:20.845357+00:00
- action: dataset_refresh
- reason: nightly_learning_dataset_refreshed
- total_resolved: 2548
- new_resolved_since_last_cycle: 213
- resolved_by_market: {'NASDAQ': 92, 'AMEX': 81, 'KOSDAQ': 1746, 'KOSPI': 627, 'KR': 1, 'US': 1}
- resolved_by_bucket: {'watchlist': 823, 'picked': 927, 'exception_leader': 268, 'ignored': 530}

## Commands
- python3 multi_agent/tools/export_scan_archive_learning_dataset.py: OK (returncode=0)
- python3 multi_agent/tools/report_kr_walkforward_release_gate.py --market KOSPI: OK (returncode=0)
- python3 multi_agent/tools/report_kr_walkforward_release_gate.py --market KOSDAQ: OK (returncode=0)
