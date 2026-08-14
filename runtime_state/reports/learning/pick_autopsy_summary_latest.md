# Pick autopsy — 2026-08-14 (총 721건, 신규 8)

## mode × lane
```
mode                 LOSS_DEEP  LOSS_SHALLOW  LOSS_TAIL  WIN_DRIFT  WIN_TOUCH
lane                                                                         
b_market_neutral            71            57        113        159          0
kosdaq_intraday              0             2          1          2          2
kospi_intraday               2             4         16          9         14
nasdaq_session_tape          3             1          7          1         27
swing_candidate              7            16         23         17         98
swing_ensemble              37             0          0          2         30
```

## mode × mkt_state (가설 리드: 상태별 실패 편중)
```
mode       LOSS_DEEP  LOSS_SHALLOW  LOSS_TAIL  WIN_DRIFT  WIN_TOUCH
mkt_state                                                          
NORMAL             1             2          2          8          1
RISK_OFF         116            77        151        181        143
```

## LOSS_TAIL 명부 (160건 — 최우선 부검 대상)
- 2026-07-16 b_market_neutral 950160 -76.84% p=3.795 state=RISK_OFF
- 2026-07-20 b_market_neutral 950160 -63.74% p=7.453 state=RISK_OFF
- 2026-07-21 b_market_neutral 950160 -48.83% p=4.452 state=RISK_OFF
- 2026-07-03 b_market_neutral 028300 -44.8% p=1.77 state=RISK_OFF
- 2026-07-06 swing_candidate 065170.KQ -44.47% p=0.7484 state=RISK_OFF
- 2026-07-20 swing_candidate 049080.KQ -42.98% p=0.7789 state=RISK_OFF
- 2026-07-24 swing_candidate 475150.KS -42.83% p=0.6749 state=RISK_OFF
- 2026-07-27 kospi_intraday 000500.KS -41.07% p=0.6568 state=RISK_OFF
- 2026-07-23 kospi_intraday 475150.KS -39.58% p=0.7456 state=RISK_OFF
- 2026-07-16 b_market_neutral 049080 -39.11% p=10.131 state=RISK_OFF
- 2026-07-22 swing_candidate 950160.KQ -37.29% p=0.7635 state=RISK_OFF
- 2026-07-22 b_market_neutral 950160 -34.45% p=9.905 state=RISK_OFF
- 2026-07-08 b_market_neutral 028300 -33.98% p=1.981 state=RISK_OFF
- 2026-06-30 b_market_neutral 093370 -33.7% p=4.393 state=RISK_OFF
- 2026-06-30 b_market_neutral 240810 -33.3% p=2.521 state=RISK_OFF
