# KR Stock Theme Master (KR)

- source_path: /Users/dongdong/Downloads/kospi_kosdaq_allstocks_structured.jsonl
- records_loaded: 2660
- market_counts: {'KOSDAQ': 1820, 'KOSPI': 840}
- inference_status_distribution: {'inferred': 1977, 'blank': 601, 'rule_inferred': 82}
- rule_inferred_count: 82
- unclassified_count: 601
- spac_excluded_count: 91
- seed_conflict_count: 12

## Primary Theme Distribution
- unclassified: 601
- 바이오/헬스케어: 350
- 철강/금속/소재: 287
- 금융: 217
- 자동차: 173
- 반도체: 172
- IT서비스/플랫폼: 158
- 통신/네트워크: 130
- 소비재/유통: 127
- 건설/부동산: 120
- 게임/콘텐츠/엔터: 108
- 2차전지: 74
- 친환경/에너지: 55
- 로봇/자동화: 54
- 조선/해양: 28
- 방산: 6

## Seed Conflict Examples
- 247540.KQ 에코프로비엠: master=2차전지 / seed=반도체
- 298380.KQ 에이비엘바이오: master=바이오/헬스케어 / seed=2차전지
- 141080.KQ 리가켐바이오: master=바이오/헬스케어 / seed=반도체
- 086520.KQ 에코프로: master=2차전지 / seed=반도체
- 058470.KQ 리노공업: master=반도체 / seed=IT서비스/플랫폼
- 000250.KQ 삼천당제약: master=바이오/헬스케어 / seed=반도체
- 011200.KS HMM: master=자동차 / seed=해운
- 010120.KS 엘에스일렉트릭: master=로봇/자동화 / seed=친환경/에너지
- 010140.KS 삼성중공업: master=친환경/에너지 / seed=조선/해양
- 005490.KS POSCO홀딩스: master=철강/금속/소재 / seed=2차전지
