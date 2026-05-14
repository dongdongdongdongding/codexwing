# KR Asymmetric Target-Before-Stop Validation

- generated_at: `2026-05-14T04:00:37.698460+00:00`
- selected_rows: `851`
- labeled_rows: `2962`
- histories_fetched: `238` / `238`
- same-bar policy: `stop_first`
- targets are validation thresholds, not profit caps.

| Market | Cohort | Profile | R:R | n | Target-before-stop % | Stop-first % | Avg close % | Close win % | Avg MFE % | MFE>=10 % | MFE>=15 % | Avg MAE % |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| KOSPI | Top5 | 1D_launch_3v3 | 1.0 | 330 | 40.3 | 40.0 | 1.5506 | 54.55 | 5.1275 | 12.42 | 8.18 | -2.1866 |
| KOSPI | Top5 | 3D_impulse_5v3 | 1.67 | 262 | 40.84 | 49.24 | 3.6391 | 66.03 | 5.7377 | 13.74 | 8.78 | -2.6852 |
| KOSPI | Top5 | 5D_runner_10v5 | 2.0 | 223 | 41.26 | 32.29 | 5.8695 | 67.26 | 8.7301 | 41.26 | 17.04 | -2.9989 |
| KOSPI | Top5 | 5D_big_runner_15v5 | 3.0 | 223 | 26.01 | 32.29 | 5.8695 | 67.26 | 9.6053 | 41.26 | 26.01 | -3.014 |
| KOSPI | Exception Leader | 1D_launch_3v3 | 1.0 | 87 | 42.53 | 37.93 | 0.9222 | 48.28 | 3.5826 | 5.75 | 1.15 | -1.7719 |
| KOSPI | Exception Leader | 3D_impulse_5v3 | 1.67 | 87 | 45.98 | 43.68 | 4.7466 | 81.61 | 4.6709 | 9.2 | 1.15 | -1.9379 |
| KOSPI | Exception Leader | 5D_runner_10v5 | 2.0 | 78 | 52.56 | 12.82 | 9.1636 | 85.9 | 9.4621 | 52.56 | 5.13 | -1.9775 |
| KOSPI | Exception Leader | 5D_big_runner_15v5 | 3.0 | 78 | 20.51 | 12.82 | 9.1636 | 85.9 | 11.3043 | 52.56 | 20.51 | -1.9775 |
| KOSDAQ | Top5 | 1D_launch_3v3 | 1.0 | 240 | 32.08 | 54.58 | -0.7402 | 42.08 | 3.9844 | 7.92 | 1.67 | -3.9862 |
| KOSDAQ | Top5 | 3D_impulse_5v3 | 1.67 | 225 | 33.33 | 63.56 | 1.0289 | 50.67 | 5.2592 | 14.22 | 4.0 | -4.2394 |
| KOSDAQ | Top5 | 5D_runner_10v5 | 2.0 | 207 | 34.3 | 50.24 | 3.5539 | 57.97 | 8.1928 | 35.75 | 14.01 | -5.2847 |
| KOSDAQ | Top5 | 5D_big_runner_15v5 | 3.0 | 207 | 22.71 | 54.59 | 3.5539 | 57.97 | 9.0447 | 35.75 | 23.67 | -5.5806 |
| KOSDAQ | Exception Leader | 1D_launch_3v3 | 1.0 | 194 | 38.66 | 51.55 | -0.4006 | 52.06 | 4.227 | 11.86 | 3.61 | -4.1861 |
| KOSDAQ | Exception Leader | 3D_impulse_5v3 | 1.67 | 181 | 39.78 | 51.93 | 1.6798 | 56.91 | 4.9195 | 13.26 | 4.42 | -4.2356 |
| KOSDAQ | Exception Leader | 5D_runner_10v5 | 2.0 | 170 | 35.88 | 43.53 | 5.6661 | 65.88 | 7.331 | 35.88 | 14.12 | -4.6347 |
| KOSDAQ | Exception Leader | 5D_big_runner_15v5 | 3.0 | 170 | 20.59 | 44.71 | 5.6661 | 65.88 | 8.5337 | 35.88 | 20.59 | -4.8025 |
