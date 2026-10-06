"""Current issued NASDAQ composition, distinct from the retired hourly study.

Read-only diagnostics: recorded close-reference returns are not verified fills,
model scores are not calibrated TP5/H10 probabilities, and pooled legacy evidence
cannot qualify the current composition. No outcome is rewritten here.
"""
from collections import Counter
import math

from modules.trading_costs import US_ROUNDTRIP_COST_PCT as COST
from modules.swing_epoch_evidence import block_ci

CURRENT_H = 20
CURRENT_TP = .05


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def is_current(row):
    return (finite(row.get('xq')) and 0 <= row['xq'] <= 1
            and row.get('contract_h') == CURRENT_H and row.get('contract_tp') == CURRENT_TP)


def current_rows(rows):
    selected = [r for r in rows if is_current(r)]
    counts = Counter(r.get('date') for r in selected)
    ambiguous = {d for d, n in counts.items() if n > 1 or not d}
    return [r for r in selected if r.get('date') not in ambiguous and r.get('in_contract') is not False]


def statistics(rows):
    done = [r for r in rows if finite(r.get('policy_ret'))]
    gross = [r['policy_ret'] for r in done]
    net = [v-COST for v in gross]
    touch = [r['touch5'] for r in done if finite(r.get('touch5')) and r['touch5'] in (0, 1)]
    return {'n': len(done), 'issued_picks': len(rows),
            'unique_dates': len({r.get('date') for r in done if r.get('date')}),
            'ev_avg': round(sum(gross)/len(gross), 2) if gross else None,
            'fwd_ev': round(sum(net)/len(net), 4) if net else None,
            'win_pct': round(100*sum(v > 0 for v in net)/len(net), 1) if net else None,
            'worst': min(gross) if gross else None,
            'touch_n': len(touch), 'touch_pct': round(100*sum(touch)/len(touch), 1) if touch else None,
            'return_basis': 'recorded gross policy_ret; win means net > 0', 'cost_pct': COST}


def current_epoch(rows, sessions=()):
    scoped = current_rows(rows)
    stats = statistics(scoped)
    done = [dict(date=r['date'], net=r['policy_ret']-COST) for r in scoped if finite(r.get('policy_ret'))]
    dates = sorted({r['date'] for r in done})
    calendar = [d for d in sessions if dates and dates[0] <= d <= dates[-1]]
    ci = block_ci(done, calendar) if dates and set(dates) <= set(calendar) else None
    unmet = []
    if stats['n'] < 30:
        unmet.append('n_below_30')
    if stats['unique_dates'] < 20:
        unmet.append('unique_dates_below_20')
    if ci is None or ci[0] <= 0:
        unmet.append('positive_block_ci_not_established')
    # A matching fixed research basis and executable entry have not been validated.
    # Do not substitute the retired 351-symbol hourly expectation or a high score.
    unmet += ['matching_research_basis_not_validated', 'executable_entry_not_verified']
    return {**stats, 'fwd_win': stats['win_pct'], 'fwd_ci': ci,
            'scope': {'marker': 'xq at issue time', 'contract_h': CURRENT_H, 'contract_tp': CURRENT_TP,
                      'entry_reference': 'signal_session_close'},
            'excluded_marked_picks': sum(r.get('xq') is not None for r in rows)-len(scoped),
            'ci_method': '5_market_session_moving_blocks_5000',
            'verdict': 'OBSERVING', 'confirm_qualified': False,
            'publication_block': True, 'publication_block_reason': ';'.join(unmet),
            'h10_tp5_probability_verified': False,
            'basis': 'current issued composition; recorded returns, unverified executable fills'}


def contract_groups(rows):
    groups = {}
    for row in rows:
        if row.get('xq') is not None:
            continue
        # Legacy resolver contract defaults; preserve explicit issued values.
        key = (row.get('contract_h') or 5, row.get('contract_tp') or .05)
        groups.setdefault(key, []).append(row)
    return [{'contract_h': h, 'contract_tp': tp, **statistics(group)}
            for (h, tp), group in sorted(groups.items(), key=lambda item: str(item[0]))]
