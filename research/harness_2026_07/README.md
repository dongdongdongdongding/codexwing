# 연구 하네스 아카이브 — 2026-07-03~05 집중 연구 (RESEARCH_LOG §5~§13 재현 스크립트)

스크래치패드(휘발)에서 보존. 결론·수치의 정본은 RESEARCH_LOG.md — 이 디렉토리는 재현/재사용용.
데이터 의존: ~/research_cache/{px_long,flow,credit,intraday_3d_panel,ohlc_daily}.parquet,
intraday/(분봉), us_daily/(나스닥 8y 패널·시간봉·어닝스).

| 스크립트 | 로그 섹션 | 판정 |
|---|---|---|
| flow_increment_research / event_ensemble | §5-A | 수급·이벤트 증분 無 |
| exit_policy_research | §5-C | 터치익절 계약 (승격 근거) |
| skill_baserate_decomposition | §6-A | 6월 = 베이스레이트 붕괴 |
| swing_firsttouch_ranker_8y | §7-A | 스윙 +0.65 천장 |
| swing_tape_ranker | §8 | 테이프→스윙 기각 |
| model_zoo_intraday / seq_model / build_seq_dataset | §10 | EVREG 채택, MLP·CNN 기각 |
| wvdd_compare / build_kosdaq_1500_panel / p1_kosdaq_frequency | §11-A, P1 | LambdaRank 기각, 재학습 채택 |
| b_model_zoo / p2_b_* | §11-B, §13-B | top3 채택, credit·HOLD 기각 |
| nasdaq_edge_p1 / pead_test / nasdaq_session_p2 | §12 | 플라시보 기각·PEAD 소·테이프 생존 |
| p4_meta_labeling / p4_meta_safe | §13-C | 메타라벨링 hindsight 기각 |
