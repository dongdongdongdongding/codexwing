"""Nominal-price, whole-position cash settlement for a NEW research epoch.

Pure arithmetic only. Caller must independently validate nominal prices, the
market calendar and complete corporate-action coverage. Coverage digests bind
inputs; they do not authenticate an evidence claim. Never uses quote adjustment
factors as share entitlements. No I/O, model fitting or publication authority.
"""
from datetime import date
from fractions import Fraction
import hashlib
import json
import math


CONTRACT_ID = 'nominal_whole_position_cash_v1'


def schedule_sha256(actions):
    return hashlib.sha256(json.dumps(actions, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def _day(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError('invalid_date')
    date.fromisoformat(value)
    return value


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError('invalid_number')
    result = Fraction(str(value))
    if not math.isfinite(float(result)):
        raise ValueError('nonfinite_number')
    return result


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _ratio(action):
    pair = action.get('ratio')
    if not isinstance(pair, list) or len(pair) != 2 or any(type(v) is not int or v <= 0 for v in pair):
        raise ValueError('invalid_entitlement_ratio')
    return Fraction(*pair)


def settle_nominal(bars, sessions, signal_date, *, code, actions, coverage,
                   horizon=10, tp='0.05', initial_shares=1, roundtrip_cost_pct='1.0'):
    """Next-session open; entry counts; TP on cash from ALL tradeable shares.

    bars: one security, list of date/open/high/low/close/volume nominal bars.
    actions: exact coverage-bound schedule. share_conversion ratio = new/old;
    bonus ratio = ADDITIONAL shares/held share. Rights, cash dividends, mergers,
    unknown events and fractional claims are unresolved, never quote-ratio fills.
    Effective dates occur before open. Entry on that date earns no old entitlement.
    Pending shares must become tradeable before full-position liquidation. Even
    an apparent early touch requires the whole source horizon to be present.
    """
    trace = []
    base = {'contract_id': CONTRACT_ID, 'code': code, 'signal_date': signal_date,
            'touch': None, 'policy_ret': None, 'net_ret': None, 'trace': trace,
            'publication_allowed': False, 'source_certified': False, 'execution_verified': False}

    def result(status, reason=None, **fields):
        return {**base, 'status': status, **({'reason': reason} if reason else {}), **fields}

    try:
        _day(signal_date)
        if not isinstance(bars, list) or not isinstance(actions, list) or any(
            not isinstance(item, dict) for item in bars + actions
        ):
            raise ValueError('malformed_input')
        if not isinstance(code, str) or not code:
            raise ValueError('invalid_code')
        if type(horizon) is not int or horizon <= 0 or type(initial_shares) is not int or initial_shares <= 0:
            raise ValueError('invalid_contract')
        tp_value, cost = _number(tp), _number(roundtrip_cost_pct)
        if tp_value <= 0 or cost < 0:
            raise ValueError('invalid_contract')
        calendar = [_day(d) for d in sessions]
        if calendar != sorted(set(calendar)) or signal_date not in calendar:
            raise ValueError('invalid_calendar')
        future = calendar[calendar.index(signal_date)+1:][:horizon]
        if len(future) < horizon:
            return result('pending_maturity', 'whole_horizon_not_observed')
        entry_date, last_date = future[0], future[-1]
        base.update(entry_date=entry_date, horizon_end=last_date,
                    label_available_date=last_date, initial_shares=initial_shares)
        if not isinstance(coverage, dict) or coverage.get('code') != code or coverage.get('price_basis') != 'nominal':
            return result('source_unverified', 'coverage_identity_or_basis_missing')
        if (_day(coverage.get('start')) > entry_date or _day(coverage.get('end')) < last_date
                or not _hash(coverage.get('evidence_sha256'))
                or coverage.get('prices_sha256') != schedule_sha256(bars)
                or coverage.get('actions_sha256') != schedule_sha256(actions)):
            return result('source_unverified', 'coverage_incomplete_or_changed')
        base['evidence_binding'] = {k: coverage[k] for k in
                                   ('evidence_sha256', 'prices_sha256', 'actions_sha256')}
        parsed = {}
        for bar in bars:
            day = _day(bar.get('date'))
            if day in parsed:
                raise ValueError('duplicate_price_date')
            if bar.get('code', code) != code:
                raise ValueError('mixed_security_bars')
            values = {k: _number(bar.get(k)) for k in ('open', 'high', 'low', 'close', 'volume')}
            if min(values.values()) < 0:
                raise ValueError('negative_price_or_volume')
            o, h, l, c, v = [values[k] for k in ('open', 'high', 'low', 'close', 'volume')]
            if v > 0 and (min(o, h, l, c) <= 0 or h < max(o, l, c) or l > min(o, h, c)):
                raise ValueError('invalid_traded_ohlc')
            parsed[day] = values
        if any(d not in parsed for d in future):
            return result('data_error', 'missing_horizon_bar')
        first = parsed[entry_date]
        if first['volume'] == 0 or first['open'] <= 0:
            return result('unfilled_entry', 'scheduled_entry_unfilled', touch=0,
                          policy_ret=0.0, net_ret=0.0)
        events = {}
        seen = set()
        for action in actions:
            effective = _day(action.get('effective_date'))
            identity = action.get('id')
            if not isinstance(identity, str) or not identity or identity in seen or action.get('code') != code:
                raise ValueError('invalid_action_identity')
            seen.add(identity)
            if not _hash(action.get('evidence_sha256')):
                return result('source_unverified', 'action_evidence_missing')
            if entry_date < effective <= last_date:
                if effective not in future:
                    return result('action_unresolved', 'effective_date_outside_calendar', action_id=identity)
                events.setdefault(effective, []).append(action)
        # Multiple actions on one date need an explicit economic ordering. Never
        # let incidental JSON order decide entitlement or wealth.
        shares = Fraction(initial_shares)
        pending = []
        initial_cash = first['open'] * shares
        target_cash = initial_cash * (1 + tp_value)
        base.update(entry_open=float(first['open']), entry_cash=float(initial_cash))
        trace.append({'date': entry_date, 'kind': 'entry', 'tradeable_shares': int(shares)})

        def exit_position(day, price, touch):
            cash = shares * price
            gross = (cash / initial_cash - 1) * 100
            trace.append({'date': day, 'kind': 'exit', 'shares': int(shares),
                          'price': float(price), 'cash': float(cash)})
            return result('resolved', touch=touch, policy_ret=float(gross),
                          net_ret=float(gross-cost), exit_date=day,
                          exit_price=float(price), exit_cash=float(cash))

        for day in future:
            if len(events.get(day, [])) > 1:
                return result('action_unresolved', 'simultaneous_action_order_unverified')
            for action in events.get(day, []):
                kind = action.get('kind')
                if kind not in ('share_conversion', 'bonus'):
                    return result('action_unresolved', 'unsupported_entitlement', action_id=action['id'])
                if pending:
                    return result('action_unresolved', 'overlapping_pending_entitlements', action_id=action['id'])
                if action.get('availability_status') != 'verified':
                    return result('action_unresolved', 'availability_unverified', action_id=action['id'])
                available = _day(action.get('available_date'))
                if available < day:
                    raise ValueError('availability_before_effective')
                ratio = _ratio(action)
                entitlement = shares * ratio
                if entitlement.denominator != 1:
                    return result('action_unresolved', 'fractional_entitlement', action_id=action['id'])
                if kind == 'share_conversion':
                    shares = Fraction(0)
                pending.append((available, entitlement, action['id']))
                trace.append({'date': day, 'kind': kind, 'action_id': action['id'],
                              'new_shares': int(entitlement), 'available_date': available})
            for available, quantity, identity in pending:
                if available <= day:
                    shares += quantity
                    trace.append({'date': day, 'kind': 'shares_available', 'action_id': identity,
                                  'shares': int(quantity)})
            pending = [p for p in pending if p[0] > day]
            bar = parsed[day]
            if pending or shares <= 0 or bar['volume'] == 0:
                continue
            target_price = target_cash / shares
            if bar['high'] >= target_price:
                # The entire position can be liquidated; no cash is imputed to
                # unlisted bonus shares or rights. Daily bars are a fill model,
                # not an observed execution/capacity or limit-queue certificate.
                price = target_price if day == entry_date else max(target_price, bar['open'])
                return exit_position(day, price, 1)
        if pending:
            return result('action_unresolved', 'unavailable_shares_at_horizon',
                          pending_shares=sum(int(p[1]) for p in pending))
        last = parsed[last_date]
        if last['volume'] == 0 or last['open'] <= 0:
            return result('pending_exit', 'scheduled_exit_unfilled')
        return exit_position(last_date, last['close'], 0)
    except (ValueError, TypeError, KeyError, ZeroDivisionError, OverflowError) as exc:
        # No exception text from arbitrary external objects is exposed.
        reason = str(exc) if isinstance(exc, ValueError) and str(exc) in {
            'invalid_date', 'invalid_number', 'nonfinite_number', 'invalid_code',
            'invalid_contract', 'invalid_calendar', 'duplicate_price_date',
            'mixed_security_bars', 'negative_price_or_volume', 'invalid_traded_ohlc',
            'invalid_action_identity', 'availability_before_effective', 'invalid_entitlement_ratio'
        } else 'malformed_input'
        return result('data_error', reason)
