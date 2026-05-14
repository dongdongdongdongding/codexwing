# Target Before Stop Shadow Testbed

- version: `target_before_stop_shadow_v1`
- mode: `shadow_only_not_production`
- rows_seen: `15903`
- policy: `{'horizon_days': 5, 'target_pct': 5.0, 'stop_pct': 5.0, 'include_entry_day': False, 'same_bar_policy': 'stop_first'}`

## Status Counts
- `proxy_no_touch`: `800`
- `proxy_stop_only`: `2970`
- `proxy_target_and_stop_touch_order_unknown`: `1553`
- `proxy_target_touch_no_stop_touch`: `3050`
- `proxy_target_touch_only`: `7530`

## Cohort Summary

| market | scan_mode | decision_bucket | n | ordered_label_n | target_before_stop_win_pct | target_touch_proxy_pct | stop_touch_proxy_pct | avg_close_return_pct | avg_mfe_pct | avg_mae_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AMEX | INTRADAY | unknown | 88 | 0 | None | 0.0 | None | None | None | None |
| AMEX | INTRADAY | watchlist | 30 | 10 | 0.0 | 66.6667 | 13.3333 | 4.544561 | 9.395472 | -2.20828 |
| AMEX | SWING | watchlist | 53 | 25 | 0.0 | 52.8302 | 22.6415 | 3.725061 | 7.568454 | -3.108891 |
| KOSDAQ | INTRADAY | exception_leader | 29 | 4 | 0.0 | 65.5172 | 30.4348 | 0.475267 | 10.382703 | -4.628273 |
| KOSDAQ | INTRADAY | picked | 356 | 100 | 0.0 | 59.8315 | 49.8403 | 5.578702 | 15.708559 | -6.06881 |
| KOSDAQ | INTRADAY | unknown | 1182 | 163 | 0.0 | 29.78 | 33.7864 | 4.422454 | 18.650403 | -5.255547 |
| KOSDAQ | INTRADAY | watchlist | 427 | 136 | 0.0 | 65.3396 | 50.8434 | 4.68536 | 16.024213 | -6.711385 |
| KOSDAQ | SWING | exception_leader | 194 | 46 | 0.0 | 62.8866 | 38.1579 | 5.66606 | 11.978766 | -4.305879 |
| KOSDAQ | SWING | picked | 17 | 4 | 0.0 | 76.4706 | 76.4706 | 1.034956 | 10.61024 | -6.789547 |
| KOSDAQ | SWING | unknown | 765 | 44 | 0.0 | 35.5556 | 38.125 | 2.141979 | 12.351941 | -4.210799 |
| KOSDAQ | SWING | watchlist | 1078 | 260 | 0.0 | 49.4434 | 57.2404 | 1.187168 | 12.18073 | -7.343139 |
| KOSPI | INTRADAY | exception_leader | 13 | 1 | 0.0 | 46.1538 | 14.2857 | 9.623945 | 31.942425 | -2.171557 |
| KOSPI | INTRADAY | picked | 86 | 18 | 0.0 | 79.0698 | 41.8605 | 7.438779 | 19.226693 | -5.083342 |
| KOSPI | INTRADAY | unknown | 273 | 8 | 0.0 | 4.0293 | 15.7895 | 4.725075 | 8.944384 | -2.472438 |
| KOSPI | INTRADAY | watchlist | 536 | 110 | 0.0 | 38.0597 | 27.3885 | 4.636021 | 15.612906 | -3.782445 |
| KOSPI | SWING | exception_leader | 87 | 8 | 0.0 | 77.0115 | 10.6061 | 9.232601 | 13.150995 | -0.005347 |
| KOSPI | SWING | picked | 224 | 4 | 0.0 | 8.4821 | 27.2727 | 7.964115 | 14.531062 | -1.293867 |
| KOSPI | SWING | unknown | 558 | 49 | 0.0 | 30.2867 | 43.1818 | 3.828302 | 10.953226 | -5.467315 |
| KOSPI | SWING | watchlist | 1995 | 417 | 0.0 | 50.4762 | 37.4526 | 5.562599 | 12.325491 | -3.395677 |
| KR | INTRADAY | picked | 3368 | 1811 | 0.0 | 34.0558 | 68.3232 | 2.226772 | 7.443273 | -7.123365 |
| KR | INTRADAY | unknown | 752 | 0 | None | 0.0 | None | None | None | None |
| KR | INTRADAY | watchlist | 961 | 491 | 0.0 | 32.5702 | 78.9801 | -0.519084 | 4.745787 | -8.911114 |
| KR | SWING | exception_leader | 31 | 7 | 0.0 | 77.4194 | 29.0323 | 1.47549 | 9.738099 | -5.496577 |
| KR | SWING | picked | 42 | 11 | 0.0 | 73.8095 | 54.7619 | 0.676809 | 11.54472 | -4.951598 |
| KR | SWING | unknown | 389 | 2 | 0.0 | 67.8663 | 50.0 | 4.194678 | 7.446482 | -0.330141 |
| KR | SWING | watchlist | 82 | 16 | 0.0 | 74.3902 | 35.8209 | 1.414564 | 12.218906 | -3.365193 |
| NASDAQ | INTRADAY | watchlist | 28 | 5 | 0.0 | 82.1429 | 7.1429 | 8.29901 | 14.75962 | -1.391984 |
| NASDAQ | SWING | watchlist | 30 | 10 | 0.0 | 53.3333 | 0.0 | 6.245472 | 8.656026 | 1.850822 |
| US | INTRADAY | unknown | 2085 | 0 | None | 0.0 | None | None | None | None |
| US | SWING | unknown | 126 | 2 | 0.0 | 15.0794 | 0.0 | 5.817166 | 13.244404 | 4.444073 |

## Notes
- This report is an internal testbed only.
- Proxy labels from archive rows are not a production replacement for OHLCV path-order labels.
- target_before_stop remains null when target/stop order cannot be determined.
