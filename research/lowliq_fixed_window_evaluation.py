"""Fixed-window statistics only; never publication or source certification.

Arithmetic is frozen in LOWLIQ_EVALUATION_IMPLEMENTATION_2026-10-07.md.
Input hashes bind supplied data; upstream evidence must be independently audited.
The outcome loader is never invoked before source/maturity/input preflight passes.
"""
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
import math

import numpy as np

VARIANTS = tuple(f'{kind}_{seed}' for kind in ('real', 'noise') for seed in range(3))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def _dates(values):
    if any(not isinstance(d, str) or len(d) != 10 or date.fromisoformat(d).isoformat() != d for d in values):
        raise ValueError('invalid_dates')
    if list(values) != sorted(set(values)):
        raise ValueError('duplicate_or_unordered_dates')
    return list(values)


def preflight(spec, calendar, proof):
    """Metadata-only: a known rejected source cannot become an alpha result."""
    reasons = []
    if proof.get('source_verdict') != 'ACCEPTED_FOR_RESEARCH':
        reasons.append('source_not_accepted')
    for field in ('calendar_verified', 'contract_verified', 'complete_universe_verified', 'model_score_replay_verified'):
        if proof.get(field) is not True:
            reasons.append(field + '_missing')
    if proof.get('source_sha256') != spec['source']['panel_sha256']:
        reasons.append('source_identity_mismatch')
    calendar = _dates(calendar)
    fixed = [d for d in calendar if spec['test_signal_start'] <= d <= spec['test_signal_end']]
    observed = proof.get('source_observed_through', '')
    as_of = proof.get('as_of', '')
    try:
        _dates([observed]); _dates([as_of])
    except (ValueError, TypeError):
        reasons.append('invalid_observation_dates')
        observed = as_of = ''
    if spec['fit_cutoff'] >= spec['test_signal_start']:
        reasons.append('fit_cutoff_not_before_test')
    horizon = spec['contract']['horizon_sessions']
    if not fixed or len([d for d in calendar if fixed[-1] < d <= min(observed, as_of)]) < horizon:
        reasons.append('fixed_window_immature')
    if proof.get('fixed_signal_dates') != fixed:
        reasons.append('fixed_calendar_mismatch')
    return {'ready': not reasons, 'reasons': reasons, 'fixed_signal_dates': fixed,
            'publication_allowed': False, 'outcomes_loaded': False}


def block_ci(sums, counts, *, block, draws, seed):
    """Pick-weighted moving blocks, including abstention sessions."""
    sums, counts = np.asarray(sums, float), np.asarray(counts, float)
    if len(sums) != len(counts) or len(sums) < block or counts.sum() <= 0:
        return {'ci': None, 'empty_draws': draws}
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(sums)-block+1, size=(draws, math.ceil(len(sums)/block)))
    indices = (starts[..., None]+np.arange(block)).reshape(draws, -1)[:, :len(sums)]
    den = counts[indices].sum(axis=1)
    valid = den > 0
    values = sums[indices].sum(axis=1)[valid] / den[valid]
    return {'ci': np.quantile(values, [.025, .975]).tolist() if len(values) else None,
            'empty_draws': int((~valid).sum())}


def placebo_excess(groups, observed, *, draws, seed, family):
    """Each group is (all eligible net returns, observed selected count)."""
    rng = np.random.default_rng(seed)
    simulated = np.zeros(draws)
    total_count = 0
    for values, count in groups:
        values = np.asarray(values, float)
        if count <= 0 or count >= len(values):
            raise ValueError('placebo_without_controls')
        total_count += count
        # Independent random keys on each row give uniform subsets without
        # replacement WITHIN a draw, not one global without-replacement sample.
        for start in range(0, draws, 128):
            size = min(128, draws-start)
            keys = rng.random((size, len(values)))
            chosen = np.argpartition(keys, count-1, axis=1)[:, :count]
            selected = values[chosen].sum(axis=1)
            remaining_mean = (values.sum()-selected)/(len(values)-count)
            simulated[start:start+size] += selected-count*remaining_mean
    simulated /= total_count
    p = (1+int(np.count_nonzero(simulated >= observed)))/(draws+1)
    return {'statistic': 'same_date_market_excess_pp', 'observed': observed,
            'draws': draws, 'raw_p': p, 'family_size': family,
            'family_adjusted_p': min(1.0, p*family),
            'null_mean': float(simulated.mean()),
            'null_interval': np.quantile(simulated, [.025,.975]).tolist()}


class Unresolved(ValueError):
    pass


def evaluate(spec, calendar, universe, selections, source_picks, proof, outcome_loader):
    """Lists of universe/outcome rows keyed by (date,code); picks are date->codes.

    selections/source_picks map all six variant names to every fixed date, with
    explicit [] on abstentions. Loader returns one outcome for every universe
    row, including pending rows. Required pending rows prevent primary metrics.
    """
    check = preflight(spec, calendar, proof)
    if not check['ready']:
        return {'status': 'NOT_EVALUABLE_PREFLIGHT', **check}
    fixed = check['fixed_signal_dates']
    binding = fingerprint({'spec': spec, 'calendar': calendar, 'universe': universe,
                           'selections': selections, 'source_picks': source_picks})
    if proof.get('input_binding_sha256') != binding:
        return {'status': 'NOT_EVALUABLE_INPUTS', 'reason': 'input_binding_mismatch',
                'outcomes_loaded': False, 'publication_allowed': False}
    ev = spec['evaluation']
    if (spec['contract']['horizon_sessions'] != 10 or spec['contract']['tp'] != .05
            or spec['model']['seeds'] != [0,1,2] or spec['model']['primary_seed'] != 0
            or ev['block_sessions'] != 5 or ev['bootstrap_draws'] != 5000
            or ev['statistics_seed'] != 20261007 or ev['family_size'] not in (3,4)
            or spec['contract']['primary_roundtrip_cost_pct'] != 1.0
            or spec['selection']['top_k_combined_markets'] != 3
            or ev['minimum_resolved'] != 30 or ev['minimum_firing_dates'] != 20
            or ev['touch_rate_all_selected_min'] != .7
            or ev['firing_dates_per_five_sessions'] != [2,3]
            or ev['net_ev_block_ci_lower_gt'] != 0 or ev['same_day_excess_block_ci_lower_gt'] != 0
            or ev['paired_excess_min_pp'] != .3 or ev['unresolved_selected_or_control_max'] != 0
            or ev['family_adjusted_ticker_p_max'] != .05):
        raise ValueError('unsupported_preregistered_contract')
    if set(selections) != set(VARIANTS) or set(source_picks) != set(VARIANTS):
        raise ValueError('missing_or_extra_seed')
    by_key = {}
    groups = defaultdict(list)
    for row in universe:
        key = (row['date'], row['code'])
        if key in by_key or key[0] not in fixed or row['market'] not in ('KOSPI','KOSDAQ'):
            raise ValueError('invalid_universe_identity')
        by_key[key] = row
        groups[(row['date'],row['market'])].append(key)
    for name in VARIANTS:
        if set(selections[name]) != set(fixed) or set(source_picks[name]) != set(fixed):
            raise ValueError('missing_or_extra_signal_date')
        for day in fixed:
            picked, original = selections[name][day], source_picks[name][day]
            if (len(set(original)) != len(original) or len(original) > spec['selection']['top_k_combined_markets']
                    or any((day,c) not in by_key for c in original)
                    or (picked and picked != original)):
                raise ValueError('changed_frozen_selection')
            if len(picked) != len(selections['real_0'][day]):
                raise ValueError('seed_cadence_or_count_mismatch')
    loaded = outcome_loader()
    if proof.get('outcomes_sha256') != fingerprint(loaded):
        return {'status': 'NOT_EVALUABLE_OUTCOMES', 'reason': 'outcome_binding_mismatch',
                'outcomes_loaded': True, 'publication_allowed': False}
    outcomes = {}
    for row in loaded:
        key = (row['date'],row['code'])
        if key in outcomes or key not in by_key or row.get('market') != by_key[key]['market']:
            raise ValueError('invalid_outcome_identity')
        expected_end = calendar[calendar.index(row['date'])+10]
        if row.get('horizon_end') != expected_end:
            raise ValueError('wrong_outcome_horizon')
        outcomes[key] = row
    if set(outcomes) != set(by_key):
        return {'status':'NOT_EVALUABLE_OUTCOMES', 'reason':'missing_universe_outcome_record',
                'outcomes_loaded':True, 'publication_allowed':False}

    def numbers(key, cost):
        row = outcomes[key]
        status = row.get('status')
        if status not in ('resolved','unfilled_entry'):
            raise Unresolved('required_selected_or_control_unresolved')
        gross, touch = row.get('policy_ret'), row.get('touch')
        if (isinstance(gross,bool) or not isinstance(gross,(int,float)) or not math.isfinite(gross)
                or type(touch) is not int or touch not in (0,1) or gross < -100):
            raise Unresolved('invalid_settled_outcome')
        if status == 'unfilled_entry':
            if gross != 0 or touch != 0:
                raise Unresolved('nonzero_unfilled_outcome')
            return 0.0, 0, False
        if (touch == 1 and gross < 5) or (touch == 0 and gross >= 5):
            raise Unresolved('touch_return_contract_mismatch')
        return gross-cost, touch, True

    def sample(picks, cost):
        daily = {d: {'sum':0.0,'excess':0.0,'count':0} for d in fixed}
        records, placebo_groups = [], []
        for day in fixed:
            selected = {(day,c) for c in picks[day]}
            for market in ('KOSPI','KOSDAQ'):
                chosen = [k for k in groups[(day,market)] if k in selected]
                if not chosen:
                    continue
                controls = [k for k in groups[(day,market)] if k not in selected]
                if not controls:
                    raise Unresolved('same_date_market_control_missing')
                all_values = {k:numbers(k,cost) for k in groups[(day,market)]}
                control_mean = float(np.mean([all_values[k][0] for k in controls]))
                placebo_groups.append(([all_values[k][0] for k in groups[(day,market)]],len(chosen)))
                for key in chosen:
                    net,touch,filled = all_values[key]
                    records.append({'date':day,'market':market,'net':net,'touch':touch,
                                    'filled':filled,'excess':net-control_mean})
                    daily[day]['sum'] += net
                    daily[day]['excess'] += net-control_mean
                    daily[day]['count'] += 1
        return records, daily, placebo_groups

    cost = spec['contract']['primary_roundtrip_cost_pct']
    try:
        samples = {name:sample(selections[name],cost) for name in VARIANTS}
    except Unresolved as exc:
        return {'status':'NOT_EVALUABLE_OUTCOMES', 'reason':str(exc),
                'outcomes_loaded':True, 'publication_allowed':False,
                'outcome_status_counts':dict(Counter(r.get('status') for r in loaded))}
    if any(not values[0] for values in samples.values()):
        return {'status':'REJECTED_SCREEN', 'reasons':['no_selected_records'],
                'outcomes_loaded':True, 'publication_allowed':False}
    flags = [bool(selections['real_0'][d]) for d in fixed]
    cadence = 5*sum(flags)/len(fixed)
    max_rolling = max((sum(flags[i:i+5]) for i in range(len(flags)-4)),default=sum(flags))
    output = {}

    def summaries(records):
        filled = [r for r in records if r['filled']]
        return {'selected':len(records), 'resolved_filled':len(filled),
                'unfilled':len(records)-len(filled),
                'touch_all_selected':float(np.mean([r['touch'] for r in records])) if records else None,
                'touch_filled_only':float(np.mean([r['touch'] for r in filled])) if filled else None,
                'net_ev':float(np.mean([r['net'] for r in records])) if records else None,
                'same_day_excess':float(np.mean([r['excess'] for r in records])) if records else None}

    for name,(records,daily,placebo_groups) in samples.items():
        counts = [daily[d]['count'] for d in fixed]
        metrics = summaries(records)
        metrics['net_block'] = block_ci([daily[d]['sum'] for d in fixed],counts,
            block=5,draws=5000,seed=ev['statistics_seed'])
        metrics['excess_block'] = block_ci([daily[d]['excess'] for d in fixed],counts,
            block=5,draws=5000,seed=ev['statistics_seed'])
        metrics['ticker_placebo'] = placebo_excess(placebo_groups,metrics['same_day_excess'],
            draws=5000,seed=ev['statistics_seed'],family=ev['family_size'])
        metrics['markets'] = {m:summaries([r for r in records if r['market']==m]) for m in ('KOSPI','KOSDAQ')}
        metrics['cost_sensitivities'] = {}
        for sensitivity in spec['contract']['cost_sensitivities_pct']:
            sensitivity_rows,_,_ = sample(selections[name],sensitivity)
            metrics['cost_sensitivities'][str(sensitivity)] = summaries(sensitivity_rows)
        if name.startswith('real'):
            paired_sums = []
            for d in fixed:
                if not daily[d]['count']:
                    paired_sums.append(0.0)
                    continue
                noise_mean = np.mean([samples[f'noise_{i}'][1][d]['sum']/samples[f'noise_{i}'][1][d]['count'] for i in range(3)])
                paired_sums.append(daily[d]['sum']-daily[d]['count']*noise_mean)
            metrics['paired_noise_excess'] = float(sum(paired_sums)/sum(counts))
            metrics['paired_noise_block'] = block_ci(paired_sums,counts,block=5,draws=5000,seed=ev['statistics_seed'])
        reasons = []
        if metrics['resolved_filled'] < ev['minimum_resolved']: reasons.append('resolved_sample_below_minimum')
        if sum(flags) < ev['minimum_firing_dates']: reasons.append('firing_dates_below_minimum')
        if metrics['touch_all_selected'] < ev['touch_rate_all_selected_min']: reasons.append('touch_target_missed')
        if not ev['firing_dates_per_five_sessions'][0] <= cadence <= ev['firing_dates_per_five_sessions'][1]:
            reasons.append('cadence_target_missed')
        if max_rolling > spec['selection']['cadence']['max_firing_dates']: reasons.append('rolling_cadence_exceeded')
        for field,threshold in [('net_block',ev['net_ev_block_ci_lower_gt']),('excess_block',ev['same_day_excess_block_ci_lower_gt'])]:
            if metrics[field]['ci'] is None or metrics[field]['ci'][0] <= threshold: reasons.append(field+'_not_positive')
        if name.startswith('real') and metrics['paired_noise_excess'] < ev['paired_excess_min_pp']:
            reasons.append('paired_noise_excess_below_minimum')
        if metrics['ticker_placebo']['family_adjusted_p'] > ev['family_adjusted_ticker_p_max']:
            reasons.append('family_adjusted_placebo_failed')
        metrics['screen_pass'] = not reasons
        metrics['reasons'] = reasons
        output[name] = metrics
    shifts = []
    for offset in range(1,len(fixed)):
        rotated = np.roll(flags,offset)
        picks = {d:source_picks['real_0'][d] if rotated[i] else [] for i,d in enumerate(fixed)}
        try:
            rows,_,_ = sample(picks,cost)
            shifts.append({'offset':offset,'status':'DIAGNOSTIC_ONLY',**summaries(rows)})
        except Unresolved as exc:
            shifts.append({'offset':offset,'status':'UNAVAILABLE','reason':str(exc)})
    return {'status':'RETROSPECTIVE_SCREEN_PASS' if output['real_0']['screen_pass'] else 'REJECTED_SCREEN',
            'primary_variant':'real_0','variants':output,'fixed_sessions':len(fixed),
            'firing_dates':sum(flags),'firing_dates_per_five_sessions':cadence,
            'max_rolling_five':max_rolling,'circular_shifts':shifts,
            'input_binding_sha256':binding,'outcomes_sha256':proof['outcomes_sha256'],
            'outcomes_loaded':True,'publication_allowed':False,
            'per_pick_probability_calibrated':False,'prospective_evidence':False}
