# KIS Model Market Comparison

- generated_at: `2026-06-08T02:11:26.848878+00:00`
- metric_contract: `2d is intentionally excluded; report uses completed 1d/3d/5d scan_universe outcome labels only.`

## KOSPI
- source: `runtime_state/reports/learning/scan_universe_admission_challenger_after_full_kis_sidecar_backfill.json`
- source_generated_at: `2026-06-07T20:47:05.647154+00:00`
- current_kis: `pos_5d` / `kis_sidecar_only` / `random_forest` / `top1`
- current_kis sample: n=`29`, active_days=`9`, active_runs=`26`
- current_kis returns: 1d 승률/평균/최저/최고 100%/5.7342%/0.8824%/11.2957%; 3d 승률/평균/최저/최고 96.5517%/20.0381%/-10.3448%/46.5517%; 5d 승률/평균/최저/최고 96.5517%/23.2462%/-1.5674%/76.9103%
- current_kis 5d path: avg_max_high=`39.1636%`, min_low=`-18.0251%`, max_low=`1.1842%`

| baseline | n | active_days | 1d win/avg/min/max | 3d win/avg/min/max | 5d win/avg/min/max | 5d avg_high/min_low |
|---|---:|---:|---|---|---|---|
| current_top1 | 25 | 7 | 60%/2.5496%/-7.6473%/14.1134% | 68%/6.0467%/-23.0769%/37.2738% | 68%/8.4304%/-24.0906%/63.6912% | 18.7382%/-26.6809% |
| current_top3 | 70 | 7 | 52.8571%/2.7241%/-19.1554%/30% | 62.8571%/9.4211%/-23.0769%/68.7023% | 64.2857%/9.2162%/-27.7846%/98.7277% | 23.1623%/-32.3745% |
| current_top5 | 110 | 7 | 50%/1.7271%/-19.1554%/30% | 55.4545%/6.0501%/-23.0769%/68.7023% | 54.5455%/5.687%/-27.7846%/98.7277% | 19.1878%/-32.3745% |

## KOSDAQ
- source: `runtime_state/reports/learning/scan_universe_admission_challenger_kosdaq_after_20260526_27_backfill.json`
- source_generated_at: `2026-06-06T18:22:53.364105+00:00`
- current_kis: `touch10_guard_5d` / `kis_sidecar_only` / `random_forest` / `top3_p0.65`
- current_kis sample: n=`11`, active_days=`3`, active_runs=`5`
- current_kis returns: 1d 승률/평균/최저/최고 90.9091%/10.9059%/-5.8501%/18.8312%; 3d 승률/평균/최저/최고 90.9091%/20.6714%/-16.819%/62.7677%; 5d 승률/평균/최저/최고 54.5455%/15.8066%/-21.0238%/62.1087%
- current_kis 5d path: avg_max_high=`36.9399%`, min_low=`-21.3894%`, max_low=`4.6128%`

| baseline | n | active_days | 1d win/avg/min/max | 3d win/avg/min/max | 5d win/avg/min/max | 5d avg_high/min_low |
|---|---:|---:|---|---|---|---|
| current_top1 | 13 | 6 | 61.5385%/0.9887%/-9.3458%/17.616% | 30.7692%/-4.2665%/-18.1619%/17.616% | 7.6923%/-11.0718%/-23.4136%/12.7835% | 10.5471%/-25.5288% |
| current_top3 | 35 | 6 | 51.4286%/-0.0833%/-14.6231%/19.5691% | 25.7143%/-4.581%/-23.7965%/17.9533% | 20%/-7.7265%/-30.9718%/21.7235% | 10.3465%/-34.9682% |
| current_top5 | 53 | 6 | 49.0566%/0.2248%/-14.6231%/19.5691% | 35.8491%/-3.0957%/-23.7965%/17.9533% | 24.5283%/-6.2743%/-30.9718%/32.4143% | 12.9566%/-34.9682% |
