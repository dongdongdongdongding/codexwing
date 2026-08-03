import warnings
warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
from scipy import stats as st

S = '/private/tmp/claude-501/-Users-dongdong-Projects-codex-swing-swing-main/e19b0723-564d-40e2-a95d-bc86f82da948/scratchpad'
coh = pd.read_parquet(f'{S}/cohort.parquet')
elig = pd.read_parquet(f'{S}/elig.parquet')
pool = elig[~elig['is_low']]

# ---- 1) date-level consistency: per sample date, cohort mean ex vs non-low pool mean ex ----
for h in (20, 60):
    a = coh.groupby('date')[f'ex{h}'].mean().dropna()
    b = pool.groupby('date')[f'ex{h}'].mean().dropna()
    j = a.index.intersection(b.index)
    d = (a[j] - b[j])
    t, p = st.wilcoxon(d)
    print(f'date-level ex{h}: dates={len(j)}, cohort>pool on {(d>0).mean()*100:.0f}% of dates, '
          f'mean D {d.mean():+.2f}, median D {d.median():+.2f}, wilcoxon p={p:.4f}', flush=True)

# ---- 2) skew / tail dependence of cohort mean ----
for h in (20, 60):
    e = coh[f'ex{h}'].dropna()
    tr = st.trim_mean(e, 0.05)
    e_p = pool[f'ex{h}'].dropna()
    tr_p = st.trim_mean(e_p, 0.05)
    big = (e > 50).mean() * 100
    top5cut = e.quantile(0.95)
    contrib = e[e >= top5cut].sum() / len(e)
    print(f'ex{h}: mean {e.mean():+.2f} | 5% trimmed mean {tr:+.2f} (pool trimmed {tr_p:+.2f}, D_trim {tr-tr_p:+.2f}) '
          f'| P(ex>+50%)={big:.1f}% | top-5% rows contribute {contrib:+.2f}pp to mean', flush=True)

# ---- 3) "no bad news" sub-test using dart_events (2023-10+ only) ----
ev = pd.read_parquet('/Users/dongdong/research_cache/dart_events.parquet')
ev['ann'] = pd.to_datetime(ev['ann'], format='%Y%m%d')
bad = ev[ev['edir'] == '-'][['code', 'ann']]
sub = coh[coh['date'] >= '2023-12-01'].copy()  # need 60d lookback after events start 2023-10
badmap = bad.groupby('code')['ann'].apply(np.array)
def had_bad(row, lookback=60):
    arr = badmap.get(row['code'])
    if arr is None: return False
    lo = row['date'] - pd.Timedelta(days=lookback * 1.45)  # ~60 trading days in calendar days
    return bool(((arr >= lo) & (arr <= row['date'])).any())
sub['bad60'] = sub.apply(had_bad, axis=1)
print(f'\nsub-window 2023-12+ cohort n={len(sub)}, with bad-event(60d) {sub["bad60"].mean()*100:.0f}%')
for h in (20, 60):
    for flag, d in sub.groupby('bad60'):
        e = d[f'ex{h}'].dropna()
        if len(e) == 0: continue
        tag = 'BAD-EVENT' if flag else 'NO-BAD  '
        print(f'  ex{h} {tag}: n={len(e):>4} mean {e.mean():+6.2f} med {e.median():+6.2f} win {(e>0).mean()*100:4.1f}% trim5 {st.trim_mean(e,0.05):+6.2f}', flush=True)

# ---- 4) how deep is "low"? distance-to-low granularity inside cohort ----
coh['dist'] = (coh['close'] / coh['min504'] - 1) * 100
coh['at_low'] = coh['dist'] <= 1.0
for h in (20, 60):
    for flag, d in coh.groupby('at_low'):
        e = d[f'ex{h}'].dropna()
        tag = 'AT-LOW(<=1%)' if flag else '1-5% above '
        print(f'  ex{h} {tag}: n={len(e):>4} mean {e.mean():+6.2f} med {e.median():+6.2f} win {(e>0).mean()*100:4.1f}%', flush=True)
