# KIS Period-Sidecar Guarded Research Decision

- generated_at: `2026-06-14T18:45:00+09:00`
- status: `research_shadow_candidates_only`
- data_basis: real KIS ticker-period sidecar caches; no dummy fill
- validation_basis: walk-forward three-stage model selections, then chronological selected-case train/holdout guard validation

## Data State

- KOSPI period-sidecar prepared cache: flow coverage `93.1177%`, financial coverage `87.2694%`, news date checks `100%`
- KOSDAQ period-sidecar prepared cache: flow coverage `92.8912%`, financial coverage `98.1307%`, news date checks `100%`
- Backfill gap report has no remaining sidecar priority gaps for the period-sidecar cache path.

## Static Policy Result

Static tail-safe policies are rejected for this dataset.

| market | best policy | n | days | hit5_dd10 | avg_exit | min_low | decision |
|---|---|---:|---:|---:|---:|---:|---|
| KOSPI | volume_leadership_defense topN=1 | 51 | 51 | 17.6471 | -2.89715 | -15.738485 | reject |
| KOSDAQ | volume_leadership_defense topN=2 | 84 | 46 | 22.619 | -2.114004 | -16.102893 | reject |

Static rules expanded sample size but destroyed hit rate. Continue model-ranked paths only.

## Guarded Three-Stage Findings

### KOSPI

- Best focused base path: `prefilter/k10/final1/ev/tail0.8`
- Base metrics: n=`21`, days=`21`, hit5=`57.1429`, hit10=`47.619`, tail=`23.8095`, avg_exit=`-0.262821`, dynamic_exit=`1.634711`, min_low=`-21.860866`
- Best holdout guard: `kis_financial_roe <= 20.58`
- Holdout guarded metrics: n=`6`, days=`6`, hit5=`83.3333`, hit10=`100.0`, tail=`16.6667`, avg_exit=`2.167882`, dynamic_exit=`6.318733`, min_low=`-10.056783`
- All guarded metrics: n=`15`, days=`15`, hit5=`53.3333`, hit10=`60.0`, tail=`20.0`, avg_exit=`-0.261671`, dynamic_exit=`2.062806`, min_low=`-21.860866`
- Additional small-sample clean path: `prefilter/k10/final1/ev_hit10/tail0.75` with `kis_whale_flow_10d >= -45012`, holdout n=`3`, hit5=`100.0`, avg_exit=`4.601458`, min_low=`-8.545508`

KOSPI remains blocked for production because sample size is below gate and min-low control is not stable across all guarded observations. It is the primary forward-shadow candidate because holdout hit rate and dynamic exit improved materially.

Observed KOSPI loss traits among selected cases:

- Theme stop prior is higher in bad paths: bad median `40.112994`, good median `32.06725`
- Revenue growth is lower in bad paths: bad median `3.45`, good median `22.485`
- 20D return is lower in bad paths: bad median `2.298851`, good median `10.401432`
- Prefilter fluctuation rank is worse in bad paths: bad median `27.0`, good median `21.0`

### KOSDAQ

- Best focused base path: `day_return/k5/final1/success_tail/tail0.6`
- Base metrics: n=`13`, days=`13`, hit5=`69.2308`, hit10=`84.6154`, tail=`30.7692`, avg_exit=`0.108702`, dynamic_exit=`3.557102`, min_low=`-37.326529`
- Best holdout guard: `kis_whale_flow_3d <= 19.8`
- Holdout guarded metrics: n=`3`, days=`3`, hit5=`100.0`, hit10=`100.0`, tail=`0.0`, avg_exit=`4.601458`, dynamic_exit=`9.58248`, min_low=`-8.486291`
- All guarded metrics: n=`9`, days=`9`, hit5=`88.8889`, hit10=`100.0`, tail=`11.1111`, avg_exit=`2.979074`, dynamic_exit=`7.406649`, min_low=`-19.899875`
- Best larger guarded observation: `day_return/k10/final1/ev_hit10/tail0.8` with `kis_prefilter_rank_fluctuation <= 3`, all n=`11`, hit5=`90.9091`, avg_exit=`3.274053`, dynamic_exit=`7.802255`, min_low=`-15.535445`; holdout n=`3`, hit5=`100.0`, min_low=`-1.960784`

KOSDAQ is blocked for production and should not be promoted. The guarded observations show strong upside after excluding extreme whale-flow or weak fluctuation-rank cases, but sample is too small and train-side tail losses still remain.

Observed KOSDAQ loss traits among selected cases:

- Whale score is much higher in bad paths: bad median `55.0`, good median `11.0`
- Close location is lower in bad paths: bad median `74.876847`, good median `100.0`
- 20D return is sharply lower in bad paths: bad median `-16.902405`, good median `10.8527`
- ROE is lower in bad paths: bad median `-26.14`, good median `0.0`

## Decision

1. Do not promote any KIS model to production from this run.
2. Keep KOSPI as the primary forward-shadow lane using the three-stage prefilter paths and guard candidates above.
3. Keep KOSDAQ out of production; only observe guarded `day_return` top1 paths in shadow because sample is too small and historical min-low is still unstable.
4. Stop spending time on static tail-safe policies for this data window; they increased sample but broke hit rate.
5. Next research should implement a shadow watch for the KOSPI guarded candidates and separately test compound loss guards for KOSDAQ before any additional promotion attempt.
