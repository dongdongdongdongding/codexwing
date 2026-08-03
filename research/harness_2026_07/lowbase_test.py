import warnings, socket
warnings.filterwarnings("ignore")
socket.setdefaulttimeout(15)
import pandas as pd, numpy as np, os

CACHE = '/Users/dongdong/research_cache'
SCRATCH = os.path.dirname(os.path.abspath(__file__))

# ---------- load panel ----------
cols = ['date', 'code', 'market', 'close', 'liq', 'vol20']
df = pd.read_parquet(f'{CACHE}/px_long.parquet', columns=cols)
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values(['code', 'date']).reset_index(drop=True)
print(f'panel: {len(df):,} rows, {df["code"].nunique()} codes, {df.date.min().date()}..{df.date.max().date()}', flush=True)

g = df.groupby('code', sort=False)
# rolling 504d (2y) min of close, window includes today
df['min504'] = g['close'].rolling(504, min_periods=504).min().reset_index(level=0, drop=True)
# listing age proxy: trading days observed in panel (panel starts 2018-01 so pre-2018 listings are floored there)
df['age'] = g.cumcount()
# forward close-to-close returns (%)
c = df['close']
for h in (5, 20, 60):
    df[f'fwd{h}'] = (g['close'].shift(-h) / c - 1) * 100

# ---------- market index (for market-excess) ----------
idx_path = f'{SCRATCH}/kr_idx.parquet'
if os.path.exists(idx_path):
    idx = pd.read_parquet(idx_path)
else:
    import FinanceDataReader as fdr
    ks = fdr.DataReader('KS11', '2018-01-01', '2026-08-03')['Close'].rename('KOSPI')
    kq = fdr.DataReader('KQ11', '2018-01-01', '2026-08-03')['Close'].rename('KOSDAQ')
    idx = pd.concat([ks, kq], axis=1)
    idx.index = pd.to_datetime(idx.index)
    idx = idx.reset_index().rename(columns={idx.index.name or 'index': 'date', 'Date': 'date'})
    idx.to_parquet(idx_path)
idx = idx.set_index('date').sort_index()
for h in (5, 20, 60):
    fwd = (idx.shift(-h) / idx - 1) * 100
    for m in ('KOSPI', 'KOSDAQ'):
        df.loc[df['market'] == m, f'ifwd{h}'] = df.loc[df['market'] == m, 'date'].map(fwd[m]).values
for h in (5, 20, 60):
    df[f'ex{h}'] = df[f'fwd{h}'] - df[f'ifwd{h}']

# ---------- eligibility pool (mechanical, no eyeballing) ----------
# 3y+ listed (>=756 obs in panel), 20d avg value traded >= 1e9 KRW,
# not bottom-decile 20d volatility that day (dead/suspended-stock exclusion; vol60 not in panel, vol20 used - stated)
elig = df[(df['age'] >= 756) & (df['liq'] >= 1e9) & df['min504'].notna() & df['fwd20'].notna()].copy()
vol_floor = elig.groupby('date')['vol20'].transform(lambda s: s.quantile(0.10))
elig = elig[elig['vol20'] > vol_floor]

# ---------- monthly sampling (first trading day of each month; overlap reduction - stated) ----------
all_dates = np.sort(elig['date'].unique())
ds = pd.Series(all_dates)
month_first = ds.groupby(ds.dt.to_period('M')).min().values
elig = elig[elig['date'].isin(month_first)]
print(f'sample dates (month-first): {len(month_first)}, eligible rows: {len(elig):,}', flush=True)

# ---------- cohort: close within +5% of trailing 2y low ----------
elig['is_low'] = elig['close'] <= elig['min504'] * 1.05
coh = elig[elig['is_low']]
print(f'cohort rows: {len(coh):,}, unique codes: {coh["code"].nunique()}, dates hit: {coh["date"].nunique()}', flush=True)
print('cohort per-date size: mean %.1f  median %.0f  max %d' % (
    coh.groupby('date').size().mean(), coh.groupby('date').size().median(), coh.groupby('date').size().max()), flush=True)

def stats(d, tag):
    out = {}
    for h in (5, 20, 60):
        a, e = d[f'fwd{h}'].dropna(), d[f'ex{h}'].dropna()
        out[h] = dict(n=len(a), abs_mean=a.mean(), abs_med=a.median(), abs_win=(a > 0).mean() * 100,
                      ex_mean=e.mean(), ex_med=e.median(), ex_win=(e > 0).mean() * 100)
    print(f'--- {tag} ---')
    for h, s in out.items():
        print(f'  fwd{h:>2}d n={s["n"]:>5} | abs mean {s["abs_mean"]:+6.2f} med {s["abs_med"]:+6.2f} win {s["abs_win"]:5.1f}% '
              f'| excess mean {s["ex_mean"]:+6.2f} med {s["ex_med"]:+6.2f} win {s["ex_win"]:5.1f}%', flush=True)
    return out

s_coh = stats(coh, 'COHORT (<=2y-low +5%)')
s_pool = stats(elig, 'ELIGIBLE POOL (same dates/filters)')

# ---------- placebo: per date x market, same count random draws from eligible pool, 200 reps ----------
rng = np.random.default_rng(42)
cnt = coh.groupby(['date', 'market']).size()
pool_g = {k: v for k, v in elig.groupby(['date', 'market'])}
REPS = 200
ph = {h: np.empty(REPS) for h in (5, 20, 60)}
for r in range(REPS):
    picks = []
    for key, n in cnt.items():
        p = pool_g.get(key)
        if p is None or len(p) == 0:
            continue
        picks.append(p.sample(n=min(n, len(p)), random_state=rng.integers(1 << 31)))
    P = pd.concat(picks)
    for h in (5, 20, 60):
        ph[h][r] = P[f'ex{h}'].mean()
print('--- PLACEBO (200 reps, date x market matched counts, excess mean) ---')
for h in (5, 20, 60):
    cm = coh[f'ex{h}'].mean()
    pm, psd = ph[h].mean(), ph[h].std()
    pct = (ph[h] < cm).mean() * 100
    print(f'  fwd{h:>2}d cohort_ex {cm:+.2f} | placebo {pm:+.2f} +/- {psd:.2f} | Delta {cm-pm:+.2f} | cohort > {pct:.0f}% of placebo draws', flush=True)

# ---------- year-by-year (fwd20 excess) ----------
print('--- YEARLY (fwd20) ---')
coh['yr'] = coh['date'].dt.year
elig['yr'] = elig['date'].dt.year
for yr, d in coh.groupby('yr'):
    p = elig[elig['yr'] == yr]
    print(f'  {yr}: n={len(d):>4} | abs {d["fwd20"].mean():+6.2f} (win {(d["fwd20"]>0).mean()*100:4.1f}%) '
          f'| ex {d["ex20"].mean():+6.2f} med {d["ex20"].median():+6.2f} (win {(d["ex20"]>0).mean()*100:4.1f}%) '
          f'| pool_ex {p["ex20"].mean():+6.2f} | D_pool {d["ex20"].mean()-p["ex20"].mean():+6.2f}', flush=True)
print('--- YEARLY (fwd60) ---')
for yr, d in coh.groupby('yr'):
    p = elig[elig['yr'] == yr]
    e, pe = d['ex60'].dropna(), p['ex60'].dropna()
    if len(e) == 0: continue
    print(f'  {yr}: n={len(e):>4} | abs {d["fwd60"].mean():+6.2f} | ex {e.mean():+6.2f} med {e.median():+6.2f} '
          f'(win {(e>0).mean()*100:4.1f}%) | D_pool {e.mean()-pe.mean():+6.2f}', flush=True)

coh.to_parquet(f'{SCRATCH}/cohort.parquet')
elig[['date','code','market','close','liq','vol20','min504','fwd5','fwd20','fwd60','ex5','ex20','ex60','is_low']].to_parquet(f'{SCRATCH}/elig.parquet')
print('saved cohort/elig to scratchpad', flush=True)
