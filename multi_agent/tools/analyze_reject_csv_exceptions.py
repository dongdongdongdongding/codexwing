from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.regime_ticker_profiles import compute_profile_adjustment, get_ticker_profile, resolve_profile_market
from modules.quant_analysis import QuantStrategy


def _to_float(value: Any) -> float | None:
    try:
        text = str(value or '').strip().replace(',', '')
        if not text:
            return None
        return float(text)
    except Exception:
        return None


def _load_rows(path: Path) -> List[Dict[str, Any]]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def _resolve_ticker_names(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    tickers = [str(row.get('Ticker') or '').strip().upper() for row in rows if str(row.get('Ticker') or '').strip()]
    if not tickers:
        return {}
    kr_tickers = [ticker for ticker in tickers if ticker.endswith('.KS') or ticker.endswith('.KQ')]
    if not kr_tickers:
        return {}
    market = 'KOSDAQ' if any(t.endswith('.KQ') for t in kr_tickers) else 'KOSPI'
    try:
        market_map = QuantStrategy.get_market_tickers(market)
        if not isinstance(market_map, dict):
            return {}
        normalized = {str(k).strip().upper(): str(v) for k, v in market_map.items() if str(k).strip()}
        return {ticker: normalized.get(ticker, '') for ticker in tickers}
    except Exception:
        return {}


def _score_exception_candidate(row: Dict[str, Any], regime: str, ticker_names: Dict[str, str]) -> Dict[str, Any]:
    ticker = str(row.get('Ticker') or '').strip().upper()
    reason = str(row.get('Reason') or '').strip()
    market = resolve_profile_market(None, ticker)
    profile = get_ticker_profile(ticker=ticker, market_type=market, market_gate=regime)
    overlay = compute_profile_adjustment(profile)

    alpha = _to_float(row.get('Alpha'))
    conviction = _to_float(row.get('Conviction'))
    prob5 = _to_float(row.get('Prob5'))
    clean = _to_float(row.get('Clean'))
    tier = _to_float(row.get('Tier'))
    trend = str(row.get('Trend') or '').strip().upper()

    exception_score = 0.0
    reasons: List[str] = []

    if overlay.get('policy') == 'POSITIVE':
        exception_score += 30.0 + float(overlay.get('score_adjustment', 0.0) or 0.0)
        reasons.append('POSITIVE_BEAR_PROFILE')
        if profile:
            if float(profile.get('win_5d_pct', 0.0) or 0.0) >= 65.0:
                exception_score += 8.0
                reasons.append('PROFILE_WINRATE_STRONG')
            if float(profile.get('avg_5d_pct', 0.0) or 0.0) >= 8.0:
                exception_score += 8.0
                reasons.append('PROFILE_EDGE_STRONG')

    if alpha is not None:
        if alpha >= 55:
            exception_score += 18.0
            reasons.append('ALPHA_55_PLUS')
        elif alpha >= 45:
            exception_score += 10.0
            reasons.append('ALPHA_45_PLUS')

    if conviction is not None:
        if conviction >= 65:
            exception_score += 12.0
            reasons.append('CONVICTION_65_PLUS')
        elif conviction >= 58:
            exception_score += 6.0
            reasons.append('CONVICTION_58_PLUS')

    if prob5 is not None and prob5 >= 35:
        exception_score += 6.0
        reasons.append('PROB5_35_PLUS')
    if clean is not None and clean >= 25:
        exception_score += 5.0
        reasons.append('CLEAN_25_PLUS')

    if trend == 'UP':
        exception_score += 8.0
        reasons.append('TREND_UP')
    elif trend == 'NEUTRAL':
        exception_score += 2.0
        reasons.append('TREND_NEUTRAL')

    if reason == 'KR_HARD_FILTER_FAIL' and alpha is not None and alpha >= 45:
        exception_score += 8.0
        reasons.append('HARD_FILTER_BORDERLINE')
    if reason == 'PRECISION_GATE_T3_LOW_ML_SUPPORT' and conviction is not None and conviction >= 58:
        exception_score += 8.0
        reasons.append('PRECISION_GATE_BORDERLINE')
    if reason in {'KR_SIGNAL_WINDOW_FAIL', 'KR_BASELINE_FILTER_FAIL'}:
        exception_score -= 6.0
    if reason == 'LIQUIDITY_FILTER_FAIL':
        exception_score -= 15.0

    recommend = exception_score >= 28.0 and reason != 'LIQUIDITY_FILTER_FAIL'

    result = dict(row)
    result.update(
        {
            'Name': str(ticker_names.get(ticker, '') or ''),
            'Market': market,
            'Regime': regime,
            'ExceptionScore': round(exception_score, 1),
            'RecommendException': 'Y' if recommend else 'N',
            'ExceptionReasons': ';'.join(reasons),
            'ProfilePolicy': overlay.get('policy', 'NONE'),
            'ProfileAdjustment': overlay.get('score_adjustment', 0.0),
            'ProfileConfidence': overlay.get('confidence', 0.0),
            'ProfileSignals': (profile or {}).get('signals', ''),
            'ProfileWin5D': (profile or {}).get('win_5d_pct', ''),
            'ProfileAvg5D': (profile or {}).get('avg_5d_pct', ''),
            'ProfileRR': (profile or {}).get('risk_reward_ratio', ''),
        }
    )
    return result


def _build_markdown(rows: List[Dict[str, Any]], csv_path: Path, regime: str) -> str:
    top = [row for row in rows if row.get('RecommendException') == 'Y']
    lines = []
    lines.append(f'# Reject Exception Analysis')
    lines.append('')
    lines.append(f'- Source: `{csv_path}`')
    lines.append(f'- Regime assumption: `{regime}`')
    lines.append(f'- Total rejects: `{len(rows)}`')
    lines.append(f'- Exception candidates: `{len(top)}`')
    lines.append('')
    if not top:
        lines.append('No exception candidates met the current threshold.')
        return '\n'.join(lines)
    lines.append('## Top Exception Candidates')
    lines.append('')
    for row in top[:15]:
        lines.append(
            f"- `{row.get('Ticker')}` ({row.get('Name')}) | reason=`{row.get('Reason')}` | score=`{row.get('ExceptionScore')}` | "
            f"alpha=`{row.get('Alpha')}` | conviction=`{row.get('Conviction')}` | profile=`{row.get('ProfilePolicy')}` | "
            f"why=`{row.get('ExceptionReasons')}`"
        )
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description='Analyze reject CSV for bear/bull exception candidates.')
    parser.add_argument('csv_path')
    parser.add_argument('--regime', default='BEAR', choices=['BULL', 'BEAR', 'NEUTRAL'])
    parser.add_argument('--out-dir', default='runtime_state/reports/scanner')
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = _load_rows(csv_path)
    ticker_names = _resolve_ticker_names(rows)
    enriched = [_score_exception_candidate(row, args.regime, ticker_names) for row in rows]
    enriched.sort(key=lambda row: (row.get('RecommendException') == 'Y', float(row.get('ExceptionScore') or 0.0)), reverse=True)

    stamp = datetime.now().strftime('%Y-%m-%d')
    csv_out = out_dir / f'reject_exception_candidates_{stamp}.csv'
    md_out = out_dir / f'reject_exception_candidates_{stamp}.md'
    json_out = out_dir / f'reject_exception_candidates_{stamp}.json'

    if enriched:
        fields = list(enriched[0].keys())
        with csv_out.open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(enriched)

    summary = {
        'source_csv': str(csv_path),
        'regime': args.regime,
        'total_rejects': len(enriched),
        'exception_candidates': sum(1 for row in enriched if row.get('RecommendException') == 'Y'),
        'top_candidates': [
            {
                'ticker': row.get('Ticker'),
                'name': row.get('Name'),
                'reason': row.get('Reason'),
                'exception_score': row.get('ExceptionScore'),
                'profile_policy': row.get('ProfilePolicy'),
                'exception_reasons': row.get('ExceptionReasons'),
            }
            for row in enriched[:15]
        ],
        'csv_path': str(csv_out),
        'md_path': str(md_out),
    }
    json_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    md_out.write_text(_build_markdown(enriched, csv_path, args.regime), encoding='utf-8')

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
