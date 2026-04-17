"""
backtest_framework.py
═══════════════════════════════════════════════════════
Pillar 1: Walk-Forward Optimization Backtester  (V2)
═══════════════════════════════════════════════════════

목적:
  - ATR/Volume 배수 등 경험적 파라미터를 데이터로 최적화
  - Walk-Forward 방식: 학습 → 검증 (Overfitting 방지)
  - 수수료 + 슬리피지 반영
  - 전체 데이터를 한 번에 fetch 후 윈도우만 슬라이싱 (MA200 NaN 방지)

결과:
  - optimal_params.json 저장 → quant_analysis.py에 반영
"""

import os, sys, json, warnings, itertools
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf

warnings.filterwarnings('ignore')

# ── 상수 ──────────────────────────────────────────────────
COMMISSION = 0.00015   # 매수/매도 각 0.015%
SLIPPAGE   = 0.0005    # 0.05%
HOLD_DAYS  = 5

GRID = {
    "ATR_stop_mult":   [1.0, 1.2, 1.5, 2.0],
    "ATR_target_mult": [2.0, 2.5, 3.0, 3.5],
    "Vol_mult":        [0.8, 1.0, 1.2, 1.5],
    "alpha_threshold": [30, 40, 50, 55],
}

DEFAULT_UNIVERSE = [
    '005930.KS','000660.KS','005380.KS','051910.KS','006400.KS',
    '003670.KS','035720.KS','035420.KS','068270.KS','011200.KS',
    '028260.KS','207940.KS','012330.KS','000270.KS','018260.KS',
    '259960.KQ','028300.KQ','103140.KQ','042700.KS','095660.KQ',
    '086520.KQ','035900.KQ','293490.KQ','145020.KQ','214370.KQ',
]


# ══════════════════════════════════════════════════════════
# 1. 지표 계산 (전체 기간에 대해 한 번만 계산)
# ══════════════════════════════════════════════════════════
def _calc_indicators(df):
    c, h, l, v = df['Close'], df['High'], df['Low'], df['Volume']

    df['MA20']  = c.rolling(20).mean()
    df['MA50']  = c.rolling(50).mean()

    # RSI
    d = c.diff()
    g = d.clip(lower=0).rolling(14).mean()
    ls = (-d.clip(upper=0)).rolling(14).mean()
    rs = g / ls.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    e12 = c.ewm(span=12, adjust=False).mean()
    e26 = c.ewm(span=26, adjust=False).mean()
    df['MACD']     = e12 - e26
    df['MACD_Sig'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # BB
    std20 = c.rolling(20).std()
    df['BB_Upper'] = df['MA20'] + 2 * std20
    df['BB_Lower'] = df['MA20'] - 2 * std20

    # ATR
    tr = pd.concat([h-l, (h-c.shift(1)).abs(), (l-c.shift(1)).abs()], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(14).mean()

    # Volume MA
    df['Vol20'] = v.rolling(20).mean()

    # ── TechScore (0-100) ─────────────────────────────────
    # 기본 점수 (max ~85)
    score = pd.Series(0.0, index=df.index)
    rsi = df['RSI']
    score += np.where(rsi < 30, 20, 0)                        # 과매도
    score += np.where((rsi > 50) & (rsi < 70), 10, 0)         # 불리시
    score += np.where(c > df['MA20'], 10, 0)                  # MA20 상위
    score += np.where(df['MA20'] > df['MA50'], 15, 0)         # 골든크로스
    score += np.where(df['MACD'] > df['MACD_Sig'], 15, 0)     # MACD 위
    bb_denom = (df['BB_Upper'] - df['BB_Lower']).replace(0, 0.001)
    bb_pct = (c - df['BB_Lower']) / bb_denom
    score += np.where(bb_pct < 0.2, 15, 0)                    # BB 하단 매수존
    vol_surge = (v > df['Vol20'] * 1.5)
    score += np.where(vol_surge, 10, 0)                        # 거래량 급증

    # V31 촉매 보너스 (-10 ~ +15)
    rsi_prev = rsi.shift(1)
    cat = pd.Series(0.0, index=df.index)
    cat += np.where((rsi_prev < 30) & (rsi > rsi_prev), 5, 0)
    cat += np.where(rsi > 70, -5, 0)
    macd_cross = (df['MACD'] > df['MACD_Sig']) & (df['MACD'].shift(1) <= df['MACD_Sig'].shift(1))
    cat += np.where(macd_cross, 5, 0)
    cat += np.where(v / df['Vol20'].replace(0, 1) >= 2.0, 5, 0)
    cat = cat.clip(-10, 15)

    df['TechScore'] = (score + cat).clip(0, 100)

    # NaN 행만 제거 (MA50 이후 = 50일차부터)
    df = df.dropna(subset=['MA50', 'ATR14', 'RSI', 'Vol20'])
    return df


def fetch_universe(tickers, start, end):
    data = {}
    for t in tickers:
        try:
            df = yf.download(t, start=start, end=end, progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            if df.empty or len(df) < 60:
                continue
            df = _calc_indicators(df)
            if len(df) < 30:
                continue
            data[t] = df
        except Exception:
            pass
    print(f"  📦 Fetched {len(data)}/{len(tickers)} tickers")
    return data


# ══════════════════════════════════════════════════════════
# 2. 백테스트 엔진
# ══════════════════════════════════════════════════════════
def _backtest_period(data, start, end, atrs, atrt, volm, alpha_thr):
    trades = []

    for ticker, df_full in data.items():
        idx = df_full.index
        # tz-aware 대응
        try:
            if hasattr(idx, 'tz') and idx.tz is not None:
                s = pd.Timestamp(start, tz=idx.tz)
                e = pd.Timestamp(end, tz=idx.tz)
            else:
                s = pd.Timestamp(start)
                e = pd.Timestamp(end)
        except Exception:
            s = pd.Timestamp(start)
            e = pd.Timestamp(end)

        df = df_full[(idx >= s) & (idx < e)]
        if len(df) < 5:
            continue

        cl = df['Close'].values
        hi = df['High'].values
        lo = df['Low'].values
        vo = df['Volume'].values
        v20= df['Vol20'].values
        atr= df['ATR14'].values
        ts = df['TechScore'].values
        m20= df['MA20'].values
        m50= df['MA50'].values
        n  = len(df)

        for i in range(n - HOLD_DAYS - 1):
            close = cl[i]
            if close <= 0:
                continue

            # Trend: close > MA20 (MA20 > MA50 제거 = 약간 관대하게)
            if close < m20[i]:
                continue

            # Alpha
            if ts[i] < alpha_thr:
                continue

            # Volume
            vr = vo[i] / v20[i] if v20[i] > 0 else 0
            if vr < volm:
                continue

            # 진입 / 손절 / 목표
            entry  = close * (1 + SLIPPAGE)
            stop   = entry - atr[i] * atrs
            target = entry + atr[i] * atrt
            cost_pct = COMMISSION * 2 * 100  # 수수료 %단위 (약 0.03%)

            # 포워드 시뮬 — 품질 라벨 포함
            exit_pnl = None
            days_to_exit = HOLD_DAYS
            stop_hit_first = False   # 손절선이 목표보다 먼저 터치됐는지
            mae_pct = 0.0            # Maximum Adverse Excursion (%) — 보유 중 최대 낙폭
            target_hit = False

            for j in range(i+1, min(i+1+HOLD_DAYS, n)):
                bar_low_ret  = (lo[j] - entry) / entry * 100
                bar_high_ret = (hi[j] - entry) / entry * 100
                mae_pct = min(mae_pct, bar_low_ret)  # 누적 최대 낙폭

                if lo[j] <= stop:
                    exit_pnl = (stop - entry) / entry * 100 - cost_pct
                    days_to_exit = j - i
                    stop_hit_first = True
                    break
                elif hi[j] >= target:
                    exit_pnl = (target - entry) / entry * 100 - cost_pct
                    days_to_exit = j - i
                    target_hit = True
                    break

            if exit_pnl is None:
                last = cl[min(i+HOLD_DAYS, n-1)]
                exit_pnl = (last - entry) / entry * 100 - cost_pct

            # ── 매매 품질 라벨 ──────────────────────────────
            is_win = exit_pnl > 0

            # clean_hit: 목표 도달 + 보유 중 MAE가 -2% 미만 (손절 근처 없이 깔끔하게)
            clean_hit = bool(target_hit and mae_pct > -2.0)

            # dirty_hit: 목표 도달했지만 중간에 -2% 이상 낙폭 경험
            dirty_hit = bool(target_hit and mae_pct <= -2.0)

            # fast_hit: 1~3일 내 목표 도달
            fast_hit = bool(target_hit and days_to_exit <= 3)

            # late_hit: HOLD_DAYS 말미(4~5일째)에 목표 도달
            late_hit = bool(target_hit and days_to_exit >= 4)

            # stop_first: 손절선이 목표보다 먼저 터치됨
            stop_first = stop_hit_first

            # peak_chase_failure: 손절 + 진입가 대비 이미 고점(ATR 1.5배 이상 위에서 진입)
            # 고점 추격 실패 = 손절 + 진입 시점 이미 ATR 범위를 크게 벗어난 경우
            peak_chase_failure = bool(
                stop_hit_first
                and atr[i] > 0
                and (close - m20[i]) / atr[i] > 1.5
            )

            trades.append({
                # ── 결과 ──
                "pnl":                exit_pnl,
                "days_to_exit":       days_to_exit,
                "mae_pct":            round(mae_pct, 3),
                "clean_hit":          int(clean_hit),
                "dirty_hit":          int(dirty_hit),
                "fast_hit":           int(fast_hit),
                "late_hit":           int(late_hit),
                "stop_first":         int(stop_first),
                "peak_chase_failure": int(peak_chase_failure),
                # ── 진입 시점 피처 (Meta-Quality Model 훈련용) ──
                "alpha_score":        round(float(ts[i]), 2),
                "vol_ratio":          round(float(vr), 3),
                "atr_pct":            round(float(atr[i] / close) * 100, 3) if close > 0 else 0.0,
                "price_to_ma20":      round(float(close / m20[i]), 4) if m20[i] > 0 else 1.0,
                "price_to_ma50":      round(float(close / m50[i]), 4) if m50[i] > 0 else 1.0,
                "ticker":             ticker,
            })

    if not trades:
        return {"n_trades": 0, "win_rate": 0, "avg_pnl": 0, "profit_factor": 0}

    df_t = pd.DataFrame(trades)
    a = df_t["pnl"].values
    w = a[a > 0]
    l = a[a <= 0]
    pf = w.sum() / (-l.sum()) if l.sum() != 0 else 99.0

    return {
        "n_trades":            len(df_t),
        "win_rate":            round((a > 0).mean() * 100, 1),
        "avg_pnl":             round(float(a.mean()), 3),
        "profit_factor":       round(pf, 2),
        "avg_mae_pct":         round(float(df_t["mae_pct"].mean()), 3),
        "clean_hit_rate":      round(float(df_t["clean_hit"].mean()) * 100, 1),
        "dirty_hit_rate":      round(float(df_t["dirty_hit"].mean()) * 100, 1),
        "fast_hit_rate":       round(float(df_t["fast_hit"].mean()) * 100, 1),
        "late_hit_rate":       round(float(df_t["late_hit"].mean()) * 100, 1),
        "stop_first_rate":     round(float(df_t["stop_first"].mean()) * 100, 1),
        "peak_chase_fail_rate":round(float(df_t["peak_chase_failure"].mean()) * 100, 1),
        "trades":              df_t.to_dict(orient="records"),
    }


# ══════════════════════════════════════════════════════════
# 3. Walk-Forward 최적화
# ══════════════════════════════════════════════════════════
def walk_forward_optimize(universe=None, total_years=2,
                          train_months=4, val_months=2):
    if universe is None:
        universe = DEFAULT_UNIVERSE

    end_date   = datetime.now()
    # 충분한 lookback 포함 (MA50 = 50일 필요)
    start_date = end_date - timedelta(days=365 * total_years + 120)

    print(f"\n{'='*60}")
    print(f"🔬 Walk-Forward Optimization (V2)")
    print(f"   Universe:  {len(universe)} tickers")
    print(f"   Period:    {start_date:%Y-%m-%d} ~ {end_date:%Y-%m-%d}")
    print(f"   Train/Val: {train_months}m / {val_months}m")
    print(f"{'='*60}")

    print("\n[0/3] 데이터 수집 중...")
    data = fetch_universe(universe, start_date.strftime('%Y-%m-%d'),
                          end_date.strftime('%Y-%m-%d'))
    if not data:
        print("ERROR: 데이터 없음")
        return {}

    # 데이터 분포 확인
    total_rows = sum(len(v) for v in data.values())
    print(f"  총 데이터행: {total_rows:,}")

    # 파라미터 조합
    keys   = list(GRID.keys())
    combos = list(itertools.product(*[GRID[k] for k in keys]))
    print(f"\n[1/3] 파라미터 조합: {len(combos)}개")

    # Walk-Forward 윈도우
    windows = []
    cursor  = start_date + timedelta(days=70)  # MA50 warmup
    while True:
        tr_end  = cursor + timedelta(days=30 * train_months)
        val_end = tr_end + timedelta(days=30 * val_months)
        if val_end > end_date:
            break
        windows.append((cursor.strftime('%Y-%m-%d'),
                        tr_end.strftime('%Y-%m-%d'),
                        val_end.strftime('%Y-%m-%d')))
        cursor = tr_end  # 전진

    if not windows:
        print("ERROR: 기간 부족")
        return {}

    print(f"[2/3] Walk-Forward 윈도우: {len(windows)}개\n")

    all_val = []
    best_params_list = []

    for w_idx, (tr_s, tr_e, val_e) in enumerate(windows):
        # ── Train: Grid Search ────────────────────────────
        best_score = -999
        best_combo = None
        best_r     = None

        for combo in combos:
            p = dict(zip(keys, combo))
            r = _backtest_period(data, tr_s, tr_e,
                                 p['ATR_stop_mult'], p['ATR_target_mult'],
                                 p['Vol_mult'], p['alpha_threshold'])
            if r['n_trades'] < 3:
                continue
            score = r['win_rate'] * 0.6 + r['avg_pnl'] * 10  # 가중 목적함수
            if score > best_score:
                best_score = score
                best_combo = p
                best_r     = r

        if best_combo is None:
            print(f"  Window {w_idx+1}/{len(windows)} | ⚠️  No valid combo (n_trades<3 for all)")
            continue

        # ── Val: OOS 검증 ─────────────────────────────────
        val_r = _backtest_period(data, tr_e, val_e,
                                  best_combo['ATR_stop_mult'],
                                  best_combo['ATR_target_mult'],
                                  best_combo['Vol_mult'],
                                  best_combo['alpha_threshold'])
        val_r.update({
            "window": w_idx+1, "train": f"{tr_s}~{tr_e}", "val": f"{tr_e}~{val_e}",
            **best_combo
        })
        all_val.append(val_r)
        best_params_list.append(best_combo)

        print(f"  Window {w_idx+1}/{len(windows)} | "
              f"Train WR={best_r['win_rate']:.0f}% ({best_r['n_trades']}t) → "
              f"Val WR={val_r['win_rate']:.0f}% ({val_r['n_trades']}t) | "
              f"ATRs={best_combo['ATR_stop_mult']} ATRt={best_combo['ATR_target_mult']} "
              f"Vol={best_combo['Vol_mult']} α≥{best_combo['alpha_threshold']}")

    if not all_val:
        print("\n⚠️  유효한 결과 없음")
        return {}

    # ── 종합 OOS 리포트 ───────────────────────────────────
    df_res = pd.DataFrame(all_val)
    avg_wr       = df_res['win_rate'].mean()
    avg_pnl      = df_res['avg_pnl'].mean()
    avg_pf       = df_res['profit_factor'].replace([99.0], np.nan).mean()
    total_t      = df_res['n_trades'].sum()
    avg_clean    = df_res['clean_hit_rate'].mean() if 'clean_hit_rate' in df_res.columns else float('nan')
    avg_stop     = df_res['stop_first_rate'].mean() if 'stop_first_rate' in df_res.columns else float('nan')
    avg_peak_fail= df_res['peak_chase_fail_rate'].mean() if 'peak_chase_fail_rate' in df_res.columns else float('nan')
    avg_mae      = df_res['avg_mae_pct'].mean() if 'avg_mae_pct' in df_res.columns else float('nan')

    print(f"\n{'='*60}")
    print(f"[3/3] Walk-Forward OOS 종합 결과")
    print(f"{'='*60}")
    print(f"📊 OOS 평균 WIN RATE      : {avg_wr:.1f}%")
    print(f"📊 OOS 평균 PnL           : {avg_pnl:.3f}%")
    print(f"📊 OOS 평균 PF            : {avg_pf:.2f}")
    print(f"📊 OOS 총 거래수          : {int(total_t)}")
    print(f"🎯 80% 목표 갭            : {max(0, 80 - avg_wr):.1f}%p")
    print(f"\n[Trade Quality Labels]")
    print(f"  Clean Hit Rate          : {avg_clean:.1f}%  (손절 없이 깔끔하게 목표 도달)")
    print(f"  Stop First Rate         : {avg_stop:.1f}%  (손절선 먼저 터치)")
    print(f"  Peak Chase Fail Rate    : {avg_peak_fail:.1f}%  (고점 추격 후 손절)")
    print(f"  Avg MAE                 : {avg_mae:.3f}%  (보유 중 평균 최대 낙폭)")

    # 최적 파라미터 (최빈값)
    def _mode(vals):
        s = pd.Series(vals)
        m = s.mode()
        return float(m.iloc[0]) if len(m) > 0 else float(vals[0])

    optimal = {
        "ATR_stop_mult":        _mode([p['ATR_stop_mult']   for p in best_params_list]),
        "ATR_target_mult":      _mode([p['ATR_target_mult'] for p in best_params_list]),
        "Vol_mult":             _mode([p['Vol_mult']        for p in best_params_list]),
        "alpha_threshold":      _mode([p['alpha_threshold'] for p in best_params_list]),
        "OOS_win_rate":         round(avg_wr, 1),
        "OOS_avg_pnl":          round(avg_pnl, 3),
        "OOS_profit_factor":    round(avg_pf, 2) if not np.isnan(avg_pf) else 0,
        "OOS_total_trades":     int(total_t),
        "OOS_clean_hit_rate":   round(avg_clean, 1) if not np.isnan(avg_clean) else None,
        "OOS_stop_first_rate":  round(avg_stop, 1) if not np.isnan(avg_stop) else None,
        "OOS_peak_chase_fail":  round(avg_peak_fail, 1) if not np.isnan(avg_peak_fail) else None,
        "OOS_avg_mae_pct":      round(avg_mae, 3) if not np.isnan(avg_mae) else None,
        "computed_at":          datetime.now().strftime('%Y-%m-%d %H:%M'),
    }

    print(f"\n✅ 최종 권장 파라미터:")
    print(f"   ATR 손절 배수:   {optimal['ATR_stop_mult']}")
    print(f"   ATR 목표 배수:   {optimal['ATR_target_mult']}")
    print(f"   거래량 배수:     {optimal['Vol_mult']}")
    print(f"   알파 임계치:     {optimal['alpha_threshold']}")

    # 저장
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'optimal_params.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(optimal, f, indent=2, ensure_ascii=False)
    print(f"\n💾 파라미터 저장: {out_path}")

    # 윈도우별 상세 출력
    print(f"\n{'─'*70}")
    print("윈도우별 상세:")
    for row in all_val:
        print(f"  [{row['window']}] {row['val']} | WR={row['win_rate']}% "
              f"PnL={row['avg_pnl']:.3f}% PF={row['profit_factor']} "
              f"Trades={row['n_trades']}")
    print(f"{'─'*70}")

    return optimal


if __name__ == "__main__":
    print("\n" + "🔥" * 30)
    print("  PILLAR 1: WALK-FORWARD BACKTESTER V2")
    print("🔥" * 30)

    result = walk_forward_optimize(
        universe     = DEFAULT_UNIVERSE,
        total_years  = 2,
        train_months = 4,
        val_months   = 2,
    )

    if result:
        print(f"\n{'='*60}")
        print("다음 단계: quant_analysis.py 의 ATR 배수를 위 최적값으로 교체.")
        print(f"{'='*60}\n")
    else:
        print("\n결과 없음.")
