"""S40 low-base cohort recheck on the survivorship-free panel (px_delisted).

Cohort definition mirrors research/harness_2026_07/lowbase_test.py exactly:
  close within +5% of trailing 2y (504d) low, 3y+ observed (>=756 rows),
  20d avg traded value >= 1e9 KRW, per-date bottom-decile vol20 excluded,
  month-first sampling, forward 5/20/60d close-to-close.
Differences (stated):
  - panel = ~/research_cache/px_delisted.parquet (KRX marcap snapshots incl. delisted,
    split/merge adjusted) instead of survivor-only px_long
  - liq uses 20d rolling mean of actual traded value (amount) instead of close*volume
  - market excess uses an INTERNAL cap-weighted benchmark per market (prev-day marcap
    weights, adjusted returns) - no external index (repo discipline)
  - delisted forward fill: after a code's last quote (liquidation trading included),
    position is assumed liquidated at the last adjusted close; separate -100% sensitivity
"""
import warnings
warnings.filterwarnings("ignore")
import pandas as pd, numpy as np, os

CACHE = os.path.expanduser("~/research_cache")
SCRATCH = os.path.dirname(os.path.abspath(__file__))
HORIZONS = (5, 20, 60)

df = pd.read_parquet(f"{CACHE}/px_delisted.parquet",
                     columns=["code", "date", "market", "adj_close", "volume", "amount", "marcap", "delist_date"])
df = df.sort_values(["code", "date"]).reset_index(drop=True)
panel_end = df["date"].max()
print(f"panel: {len(df):,} rows, {df.code.nunique()} codes, {df.date.min().date()}..{panel_end.date()}", flush=True)

g = df.groupby("code", sort=False)
df["ret1"] = g["adj_close"].pct_change()
df["liq"] = g["amount"].rolling(20, min_periods=20).mean().reset_index(level=0, drop=True)
df["vol20"] = g["ret1"].rolling(20, min_periods=20).std().reset_index(level=0, drop=True) * 100
df["min504"] = g["adj_close"].rolling(504, min_periods=504).min().reset_index(level=0, drop=True)
df["age"] = g.cumcount()
for h in HORIZONS:
    df[f"fwd{h}"] = (g["adj_close"].shift(-h) / df["adj_close"] - 1) * 100

# ---------- delisted terminal fill ----------
last = g["date"].transform("max")
last_px = g["adj_close"].transform("last")
df["exited"] = last < (panel_end - pd.Timedelta(days=14))  # left the panel before the end
exited_codes = df.loc[df["exited"], "code"].nunique()
print(f"exited codes (vanished >14d before panel end): {exited_codes}", flush=True)
term = (last_px / df["adj_close"] - 1) * 100
for h in HORIZONS:
    fill = df["exited"] & df[f"fwd{h}"].isna()
    df[f"fwd{h}_filled"] = fill
    df.loc[fill, f"fwd{h}"] = term[fill]

# ---------- internal cap-weighted benchmark (per market) ----------
df["w"] = g["marcap"].shift(1)
b = df.dropna(subset=["ret1", "w"])
num = b.groupby(["market", "date"]).apply(lambda d: np.average(d["ret1"], weights=d["w"]))
idx_fwd = {}
for m in ("KOSPI", "KOSDAQ"):
    r = num.loc[m].sort_index()
    lvl = (1 + r).cumprod()
    for h in HORIZONS:
        idx_fwd[(m, h)] = (lvl.shift(-h) / lvl - 1) * 100
for h in HORIZONS:
    df[f"ifwd{h}"] = np.nan
    for m in ("KOSPI", "KOSDAQ"):
        sel = df["market"] == m
        df.loc[sel, f"ifwd{h}"] = df.loc[sel, "date"].map(idx_fwd[(m, h)]).values
    df[f"ex{h}"] = df[f"fwd{h}"] - df[f"ifwd{h}"]

# ---------- eligibility (mirrors lowbase_test.py) ----------
elig = df[(df["age"] >= 756) & (df["liq"] >= 1e9) & df["min504"].notna() & df["fwd20"].notna()].copy()
vol_floor = elig.groupby("date")["vol20"].transform(lambda s: s.quantile(0.10))
elig = elig[elig["vol20"] > vol_floor]

all_dates = np.sort(elig["date"].unique())
ds = pd.Series(all_dates)
month_first = ds.groupby(ds.dt.to_period("M")).min().values
elig = elig[elig["date"].isin(month_first)]
print(f"sample dates (month-first): {len(month_first)}, eligible rows: {len(elig):,}", flush=True)

elig["is_low"] = elig["adj_close"] <= elig["min504"] * 1.05
coh = elig[elig["is_low"]].copy()
print(f"cohort rows: {len(coh):,}, unique codes: {coh['code'].nunique()}, dates hit: {coh['date'].nunique()}", flush=True)
n_exit_rows = {h: int(coh[f'fwd{h}_filled'].sum()) for h in HORIZONS}
print(f"cohort rows with delist-terminal fill: fwd5 {n_exit_rows[5]}, fwd20 {n_exit_rows[20]}, fwd60 {n_exit_rows[60]} "
      f"({n_exit_rows[60]/len(coh)*100:.1f}% of cohort at 60d)", flush=True)
print(f"cohort rows on exited codes (eventually delisted): {int(coh['exited'].sum())} "
      f"({coh['exited'].mean()*100:.1f}%)", flush=True)

def stats(d, tag):
    print(f"--- {tag} ---", flush=True)
    out = {}
    for h in HORIZONS:
        a, e = d[f"fwd{h}"].dropna(), d[f"ex{h}"].dropna()
        et = e.sort_values().iloc[int(len(e)*0.01):int(len(e)*0.99)] if len(e) > 100 else e
        out[h] = dict(n=len(a), abs_mean=a.mean(), ex_mean=e.mean())
        print(f"  fwd{h:>2}d n={len(a):>5} | abs mean {a.mean():+6.2f} med {a.median():+6.2f} win {(a>0).mean()*100:5.1f}% "
              f"| excess mean {e.mean():+6.2f} med {e.median():+6.2f} win {(e>0).mean()*100:5.1f}% "
              f"| ex trim1% {et.mean():+6.2f}", flush=True)
    return out

s_coh = stats(coh, "COHORT (<=2y-low +5%), delisted incl., last-price liquidation")
s_pool = stats(elig, "ELIGIBLE POOL (same dates/filters)")

# survivor-only subset (codes alive at panel end) - isolates the survivorship effect
surv = coh[~coh["exited"]]
stats(surv, "COHORT survivor-only subset (same panel/benchmark)")

# -100% sensitivity: delisted position written to zero instead of last price
sens = coh.copy()
for h in HORIZONS:
    sens.loc[sens[f"fwd{h}_filled"], f"fwd{h}"] = -100.0
    sens[f"ex{h}"] = sens[f"fwd{h}"] - sens[f"ifwd{h}"]
stats(sens, "COHORT sensitivity: delisted = -100%")

# halt-masking sensitivity: KR delistings are preceded by long suspensions during which
# the panel carries frozen-price zero-volume rows; a close-to-close mark at t+h taken on
# such a row overstates the position value (cannot be sold there). Re-mark at the NEXT
# traded price at/after t+h (per code; final row price if none) - "next-trade mark".
nt = df["adj_close"].where(df["volume"] > 0)
nt = nt.groupby(df["code"], sort=False).bfill()
nt = nt.fillna(last_px)  # suspended into the end with no further trade: last (frozen) price
df["nt_px"] = nt
gnt = df.groupby("code", sort=False)["nt_px"]
sus = coh.copy()
n_susp = {}
for h in HORIZONS:
    fwd_nt = (gnt.shift(-h) / df["adj_close"] - 1) * 100
    fwd_nt = fwd_nt.where(~(df["exited"] & fwd_nt.isna()), term)  # beyond last row: terminal
    sus[f"fwd{h}"] = fwd_nt.reindex(sus.index)
    sus[f"ex{h}"] = sus[f"fwd{h}"] - sus[f"ifwd{h}"]
    mark_vol = df.groupby("code", sort=False)["volume"].shift(-h).reindex(sus.index)
    n_susp[h] = int((mark_vol == 0).sum())
print(f"cohort rows marked on a no-trade (frozen) row: fwd5 {n_susp[5]}, fwd20 {n_susp[20]}, fwd60 {n_susp[60]}", flush=True)
stats(sus, "COHORT sensitivity: suspended marks -> next traded price")

# ---------- placebo (200 reps, date x market matched counts) ----------
rng = np.random.default_rng(42)
cnt = coh.groupby(["date", "market"]).size()
pool_g = {k: v for k, v in elig.groupby(["date", "market"])}
REPS = 200
ph = {h: np.empty(REPS) for h in HORIZONS}
for r in range(REPS):
    picks = []
    for key, n in cnt.items():
        p = pool_g.get(key)
        if p is None or len(p) == 0:
            continue
        picks.append(p.sample(n=min(n, len(p)), random_state=rng.integers(1 << 31)))
    P = pd.concat(picks)
    for h in HORIZONS:
        ph[h][r] = P[f"ex{h}"].mean()
print("--- PLACEBO (200 reps, date x market matched counts, excess mean) ---", flush=True)
for h in HORIZONS:
    cm = coh[f"ex{h}"].mean()
    pm, psd = ph[h].mean(), ph[h].std()
    pct = (ph[h] < cm).mean() * 100
    print(f"  fwd{h:>2}d cohort_ex {cm:+.2f} | placebo {pm:+.2f} +/- {psd:.2f} | Delta {cm-pm:+.2f} | cohort > {pct:.0f}% of draws", flush=True)

# ---------- yearly ----------
coh["yr"] = coh["date"].dt.year
elig["yr"] = elig["date"].dt.year
for hh in (20, 60):
    print(f"--- YEARLY (fwd{hh}) ---", flush=True)
    for yr, d in coh.groupby("yr"):
        p = elig[elig["yr"] == yr]
        e, pe = d[f"ex{hh}"].dropna(), p[f"ex{hh}"].dropna()
        if len(e) == 0:
            continue
        print(f"  {yr}: n={len(e):>4} | abs {d[f'fwd{hh}'].mean():+6.2f} | ex {e.mean():+6.2f} med {e.median():+6.2f} "
              f"(win {(e>0).mean()*100:4.1f}%) | D_pool {e.mean()-pe.mean():+6.2f} | delist-fill {int(d[f'fwd{hh}_filled'].sum())}", flush=True)

print("--- REFERENCE: S40 survivor panel (px_long, external index) ---", flush=True)
print("  ex20 win 42.4%, placebo Delta +0.89pp, trimmed mean negative (see harness_2026_07/lowbase_test.py log)", flush=True)

keep = ["date", "code", "market", "adj_close", "liq", "vol20", "min504", "exited"] + \
       [f"{p}{h}" for h in HORIZONS for p in ("fwd", "ex", "ifwd")] + [f"fwd{h}_filled" for h in HORIZONS]
coh[keep].to_parquet(f"{SCRATCH}/lowbase_delisted_cohort.parquet")
elig[keep + ["is_low"]].to_parquet(f"{SCRATCH}/lowbase_delisted_elig.parquet")
print("saved cohort/elig parquet next to this script", flush=True)
