# 모델별 매매전략 - 2026-06-24

이 문서는 현재 코드와 연구 문서 기준으로 모델별 매매 계약, 사용 여부, 진입/청산, 검증 상태를 정리한다. 파일이 존재한다는 이유만으로 운영 중이라고 판단하지 않는다.

## 확인한 근거 파일

- `multi_agent/tools/report_swing_ensemble.py`
- `multi_agent/tools/report_kospi_intraday_swing.py`
- `multi_agent/tools/report_kosdaq_intraday_vwap_guard.py`
- `modules/kosdaq_intraday_vwap_guard.py`
- `modules/intraday_candidate_registry.py`
- `multi_agent/tools/report_kospi_normal_pead_shadow.py`
- `multi_agent/tools/report_firsttouch_down_shadow.py`
- `modules/scanner_services.py`
- `modules/quant_analysis.py`
- `multi_agent/agents/planner_runtime.py`
- `docs/research/RESEARCH_JOURNEY_2026-06.md`
- `runtime_state/reports/learning/intraday_claude_codex_synthesis_latest.md`
- `runtime_state/reports/learning/intraday_3d_t5_model_training_latest.md`
- `runtime_state/reports/learning/intraday_3d_t5_monthly_failure_diagnosis_latest.md`
- `runtime_state/reports/learning/intraday_3d_t5_return_optimized_latest.md`

## 전략 요약표

| 전략 | 시장 | 모드 | 운영 사용 | 목표 | 현재 판단 |
|---|---|---|---|---|---|
| SWING price-ML ensemble | KOSPI/KOSDAQ | `SWING` | 사용 | 5일 내 +5% first-touch | modest daily signal, 목표 75% 아님 |
| KOSPI intraday 3D +5% | KOSPI | `INTRADAY` 성격 | 사용 | 3일 내 +5% touch | live-forward, artifact 안정화 필요 |
| KOSDAQ intraday 15:00 VWAP guard | KOSDAQ | `INTRADAY` | 사용 | 3일 내 +5% touch | 현재 핵심 후보 |
| KOSPI intraday 09:05 5D | KOSPI | `INTRADAY` | 미사용/registry | 5D path | ledger 연결 필요 |
| KOSDAQ tail guard | KOSDAQ | `INTRADAY` | 연구용 | 5D tail-safe | 승률 낮아 promotion 아님 |
| KOSPI NORMAL PEAD | KOSPI | `SWING` | shadow만 | 5D | falsification ledger, production 아님 |
| first-touch down | KR | `SWING` | 기본 OFF | down/rebound | beta/fragile 판정 |
| Exception Leader | KR | `SWING` | legacy/관찰 | 고승률 주장 | durable 검증 부족 |
| Practical-80 | KR | `SWING` | 비활성/주의 | 고승률 주장 | 교정 벤치에서 production edge 아님 |
| phase25 legacy | KR/US | 혼재 | 레거시 지원 | 다양 | 운영 핵심 아님, 일부 inverted/retired |
| KIS touch5/dd10 challengers | KOSPI/KOSDAQ | `SWING` 연구 | 연구/백필 | touch5/dd10 | 아직 production 아님 |

## 1. SWING Price-ML Ensemble

파일:

- `multi_agent/tools/report_swing_ensemble.py`

모델:

- LGBM
- XGBoost
- ExtraTrees
- trailing daily `px_long.parquet`
- price-only feature set

목표:

- `ft_5_5`: 5거래일 안에 +5%를 -5%보다 먼저 터치하는지.

유니버스:

- KOSPI, KOSDAQ
- 현재 기본 유동성 floor: `>=100억`

선정:

- 시장별 ensemble probability 상위 약 1%
- 기본 command: `--top-pct 1.0 --min-liq 100`

진입:

- producer route는 latest close reference를 사용한다.
- ledger resolve는 first-touch 판정에서 다음날 open을 entry로 사용한다.

청산/보유:

- 5거래일
- +5% first-touch 진단
- -5% first-touch 실패 label
- tight live stop은 주계약에 없음

현재 해석:

- live-forward 검증 레인.
- 보조 daily signal.
- 75% 목표 모델로 쓰면 안 된다.

운영 산출물:

- `runtime_state/reports/experimental/swing_ensemble_latest.json`
- `runtime_state/reports/experimental/swing_ensemble_latest.md`
- `runtime_state/reports/experimental/swing_ensemble_ledger.jsonl`
- Supabase `market_scan_results`
- Supabase `scan_deep_reports`

## 2. KOSPI Intraday 3D +5% Context VWAP Guard

파일:

- `multi_agent/tools/report_kospi_intraday_swing.py`

모델:

- LGBM
- XGBoost
- ExtraTrees
- producer 내부에서 `~/research_cache/intraday_3d_panel.parquet`와 daily context를 사용해 학습

목표:

- 3거래일 내 +5% MFE touch

유니버스:

- KOSPI
- 기본 유동성 floor: `>=100억`

선정:

- ensemble probability top2
- `close_vwap>=0`
- `idx_vol20>=8`
- 유동성 통과

진입:

- full-session minute bar 이후 close-buy 성격
- 15:00 중간 진입 모델이 아니다.

청산/보유:

- 3D close hold
- +5% touch는 diagnostic target
- tight stop 없음

현재 해석:

- live-forward 레인.
- backtest headline은 높지만 volatility guard가 약한 월을 보수한 것이므로 forward 검증 필요.
- KOSDAQ보다 production artifact discipline이 약하다. 모델 bundle 고정화가 필요하다.

운영 산출물:

- `runtime_state/reports/experimental/kospi_intraday_swing_latest.json`
- `runtime_state/reports/experimental/kospi_intraday_swing_latest.md`
- `runtime_state/reports/experimental/kospi_intraday_swing_ledger.jsonl`
- Supabase route: `decision_bucket=kospi_intraday`

## 3. KOSDAQ Intraday 15:00 VWAP Guard

파일:

- `modules/kosdaq_intraday_vwap_guard.py`
- `multi_agent/tools/report_kosdaq_intraday_vwap_guard.py`

candidate id:

```text
kosdaq_intraday_1500_3d_t5_vwap_guard_shadow_v1
```

strategy family:

```text
KR_INTRADAY_3D_T5
```

모델 artifact:

```text
models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl
```

모델:

- LightGBM classifier
- 이전월 isotonic calibration
- 저장된 joblib bundle
- bundle 안에 feature list와 selection policy 포함

목표:

- `target_touch3d_t5`: 15:00 entry price 기준 3거래일 안에 고가가 +5% 터치하는지.

유니버스:

- KOSDAQ 전용
- `~/research_cache/px_long.parquet` 기반 universe
- 최근 90일 median liquidity

유동성 lane:

- `>=30억`: main edge lane
- `>=100억`: tradeability lane

진입:

- 15:00 minute-confirmed entry
- KIS minute bar를 15:00 이후 가져온다.
- feature는 09:00~15:00 bar만 사용한다.
- post-entry leakage 방지 구조다.

선정:

- `p_cal>=0.80`
- `pre_vwap_dist_pct>=0`
- daily top2
- `liq_prev_eok>=min_liq`

청산/보유:

- primary return policy: 3D close hold
- diagnostic target: +5% touch
- 현재 primary contract에 tight stop 없음

비용:

- `ROUNDTRIP_COST_PCT = 0.33`

현재 검증 수치:

- `>=30억`: n=81, hit 90.12%, CI low 81.70%, close3 net@0.33 +10.27%, month hit min 80%
- `>=100억`: n=40, hit 85.00%, CI low 70.93%, close3 net@0.33 +5.11%, month hit min 75%

현재 해석:

- 현재 가장 중요한 KOSDAQ intraday deployment.
- live-forward 검증 중.
- 완전 승급은 forward micro-production gate 통과 후.

forward gate:

- forward picks 60개 이상
- forward days 30일 이상
- forward months 2개월 이상
- touch3d_t5 75% 이상
- day hit 80% 이상
- net 3D close return > 0
- liquidity-decile excess > 0
- n>=5 월에서 65% 미만 없음
- realized slippage <=0.50%

운영 산출물:

- `runtime_state/reports/experimental/kosdaq_intraday_1500_3d_t5_vwap_guard_latest.json`
- `runtime_state/reports/experimental/kosdaq_intraday_1500_3d_t5_vwap_guard_latest.md`
- `runtime_state/reports/experimental/kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl`

주의:

- bucket이 아직 `MODEL_VALIDATED_LANES`에 없어서 `/signals`에서 누락될 수 있다.

## 4. KOSPI Intraday 09:05 5D Shadow

파일:

- `modules/intraday_candidate_registry.py`

상태:

- registry 후보
- live forward ledger 연결 필요
- 현재 운영 메인 아님

의미:

- KOSPI 09:05 인트라데이 후보로 기록된 shadow concept.
- KOSDAQ 15:00 VWAP guard와 혼동하면 안 된다.

## 5. KOSDAQ Intraday Tail Guard Research

파일/리포트:

- `modules/intraday_candidate_registry.py`
- 관련 experimental/learning report

상태:

- 연구 전용
- live promotion 아님

이유:

- net/excess가 양호한 구간이 있어도 win/day-win이 낮다.
- 운영 목표가 70~75% touch 확률이면 맞지 않는다.

## 6. KOSPI NORMAL PEAD Shadow

파일:

- `multi_agent/tools/report_kospi_normal_pead_shadow.py`

상태:

- shadow ON
- production OFF

현재 해석:

- 엣지 후보가 아니라 falsification ledger.
- 이전 +1.5% 시장초과 narrative는 외부 KS11/벤치마크 artifact로 철회됨.
- panel/internal correction 후 production edge 아님.

운영 원칙:

- 관찰은 가능.
- 추천/매수 모델로 쓰지 않는다.
- `AG_KOSPI_NORMAL_PEAD_PRODUCTION=1` 금지 unless 새 검증 완료.

## 7. First-Touch Down Shadow

파일:

- `multi_agent/tools/report_firsttouch_down_shadow.py`
- `models/firsttouch_down_v1.pkl`

상태:

- 기본 OFF
- production 아님

이유:

- 하락장 반등 베타/fragile로 판단됨.
- same-day control 및 시장중립 검증에서 production edge로 남지 못함.

## 8. Exception Leader

관련:

- `multi_agent/agents/planner_runtime.py`
- legacy planner bucket/decision path

현재 해석:

- 짧은 window에서 양성 신호가 관찰됐으나 durable 검증 부족.
- 과거 높은 win-rate narrative는 상승장/표본/벤치마크 교정 전 수치와 섞여 있었다.
- forward 관찰 가치는 있지만 production core로 쓰지 않는다.

## 9. Practical-80

관련:

- `modules/practical_entry_gate.py`
- planner promotion/gate path

현재 해석:

- 4월 편중 window에서 headline win-rate가 높았다.
- size/liquidity matched, 월별 분해, 비용 교정 후 production edge로 확정되지 않음.
- gate disable 또는 conservative observe 유지가 맞다.

## 10. Phase25 Legacy Models

관련 파일:

- `modules/quant_analysis.py`
- `modules/phase25_governance.py`
- `models/phase25_*`

상태:

- 레거시 호환/보조 모델군
- 현재 핵심 배포 모델 아님

주의:

- `phase25_kosdaq_intraday`는 과거 inverted/retired 이력이 있다.
- `models/`에 파일이 있다는 이유로 운영 모델이라고 판단하지 않는다.
- 일부 phase25 값은 UI/trace 호환 필드로 남아 있다.

## 11. KIS touch5/dd10 Challenger Stream

관련:

- `models/scan_universe_challengers/*`
- `train_scan_universe_admission_challenger.py`
- `research_kis_three_stage_ev_ranker.py`
- `sweep_kis_sidecar_thresholds.py`
- 관련 Beads 이슈 `n6u3`, `xuy1`, `u9sq`, `yf9n`

상태:

- 연구/백필/검증 스트림
- production 아님

목표:

- KIS sidecar, flow, failure risk, touch5/dd10 조건을 이용해 SWING 후보 개선 가능성 확인.

주의:

- 현재 메인 목표인 KOSDAQ intraday 3D +5%와 별도 축이다.

## 실전 해석

현재 매매전략 우선순위:

1. KOSDAQ intraday 15:00 VWAP guard
   - 현재 목표와 가장 가깝다.
   - forward ledger를 쌓으며 consumer parity를 먼저 고친다.

2. KOSPI intraday 3D +5%
   - 보조 live-forward.
   - artifact 고정화와 guard 검증이 필요하다.

3. SWING ensemble
   - modest daily 보조 레인.
   - 75% 목표로 해석하지 않는다.

4. old daily narrative/legacy models
   - 기록/관찰/호환용.
   - 새 검증 없이 production edge로 쓰지 않는다.
