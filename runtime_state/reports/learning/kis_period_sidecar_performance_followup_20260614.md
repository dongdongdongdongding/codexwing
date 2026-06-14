# KIS Period-Sidecar Performance Follow-up

- dummy_data_used: `False`
- production_ready: `False`
- best_current_use: `shadow_research_only`

## Backfill
- lookup_rows: `{'flow': 383848, 'financial': 275690, 'news': 292167}`
- call_counts: `{'stock_investor_daily': 13838, 'financial_ratio': 2770, 'news_titles_by_date': 106}`
- failure_counts: `{'stock_investor_daily:KISOpenAPIError': 5, 'financial_ratio:KISOpenAPIError': 8}`

## Coverage
- KOSPI: rows=`100490` days=`106` flow=`93.1177%` financial=`87.2694%` news_checked=`100.0%` augmented_rows=`100485`
- KOSDAQ: rows=`191677` days=`106` flow=`92.8912%` financial=`98.1307%` news_checked=`100.0%` augmented_rows=`191676`

## Best Expanded Results
- KOSPI: cfg=`{'pool': 'prefilter', 'pool_k': 10, 'final_topn': 1, 'score_mode': 'ev_hit10', 'max_tail_prob': 0.8}` gate=`blocked` blockers=`['n_lt_30', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']` n=`20` days=`20` hit5=`70.0` hit10=`55.0` tail=`15.0` avg_exit=`1.146858` dynamic=`3.637369` min_low=`-19.214396`
- KOSDAQ: cfg=`{'pool': 'day_return', 'pool_k': 5, 'final_topn': 1, 'score_mode': 'success_tail', 'max_tail_prob': 0.85}` gate=`blocked` blockers=`['n_lt_45', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']` n=`22` days=`22` hit5=`63.6364` hit10=`77.2727` tail=`27.2727` avg_exit=`0.022675` dynamic=`3.192416` min_low=`-37.326529`

## Decision
- production_ready: False
- best_current_use: shadow_research_only
- kospi_candidate: expanded KOSPI prefilter pool_k=10 final_topn=1 ev_hit10 max_tail_prob=0.8 improved dynamic exit but blocked by n/hit5/min_low/economics
- kospi_shadow_safe_observation: expanded KOSPI prefilter pool_k=5 final_topn=1/2 tail=0.75 has tail 0 and min_low above -10 but n<=10, observation only
- kosdaq_candidate: expanded KOSDAQ day_return pool_k=5 final_topn=1 success_tail max_tail_prob=0.85 improved dynamic exit but blocked by n/hit5/min_low/economics
- kosdaq_lowtail_result: low-tail sweep found n=2 perfect sample, rejected as too small; n>=10 candidates still have severe min_low around -37
