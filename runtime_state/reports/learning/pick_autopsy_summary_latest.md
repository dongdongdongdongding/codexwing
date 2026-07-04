# Pick autopsy — 2026-07-04 (총 27건, 신규 0)

## mode × lane
```
mode              LOSS_DEEP  LOSS_SHALLOW  LOSS_TAIL  WIN_DRIFT  WIN_TOUCH
lane                                                                      
b_market_neutral          1             1          1          7          0
kosdaq_intraday           0             1          1          2          1
kospi_intraday            0             1          0          1          5
swing_ensemble            3             0          0          0          2
```

## mode × mkt_state (가설 리드: 상태별 실패 편중)
```
mode       LOSS_DEEP  LOSS_SHALLOW  LOSS_TAIL  WIN_DRIFT  WIN_TOUCH
mkt_state                                                          
RISK_OFF           4             3          2         10          8
```

## LOSS_TAIL 명부 (2건 — 최우선 부검 대상)
- 2026-06-15 b_market_neutral 033640 -13.74% p=5.552 state=RISK_OFF
- 2026-06-29 kosdaq_intraday 010170.KQ -11.93% p=1.0 state=RISK_OFF
