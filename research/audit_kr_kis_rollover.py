"""Read-only fixed-cohort KIS price-vintage audit; preserve the old replay."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from multi_agent.tools.us_daily_panel_cache import file_sha
from multi_agent.tools.backfill_kr_intraday import request_deadline
from research.audit_kr_touch10_price_source import parse_bars, evaluate


def compare_prices(old, new):
    fields = ["adj_open", "adj_high", "adj_low", "adj_close", "volume"]
    changes = []
    for code, before in old.items():
        after = new[code].set_index("date")
        for _, row in before.iterrows():
            if row.date not in after.index:
                raise ValueError("missing_original_price_date")
            diff = {k: [float(row[k]), float(after.loc[row.date, k])]
                    for k in fields if row[k] != after.loc[row.date, k]}
            if diff:
                changes.append({"code": code, "date": str(row.date.date()), "fields": diff})
    return changes


def capture_paths(audit, code):
    return [p for p in [audit / f"{code}.json", *sorted(audit.glob(f"{code}_attempt_*.json"))] if p.exists()]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--retry-errors", action="store_true", help="Preserve failed attempts; retry only missing provider responses")
    args = ap.parse_args()
    spec_path = ROOT / "research/prereg_kr_rollover_audit_20261007.json"
    raw = spec_path.read_bytes(); spec = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest()

    def unchanged():
        if spec_path.read_bytes() != raw or any(file_sha(p) != sha for p, sha in spec["preserved_sha256"].items()):
            raise ValueError("registered_input_vintage_changed")

    unchanged()
    root = args.root
    original = json.loads((root / spec["prior_spec"]).read_text())
    prior = json.loads((root / "runtime_state/reports/validation/kr_touch10_kis_price_audit.json").read_text())
    original_replay = json.loads((root / "runtime_state/reports/validation/kr_touch10_replay_20261007.json").read_text())
    audit = root / "runtime_state/audit/kr_kis_rollover_20261007"
    audit.mkdir(parents=True, exist_ok=True)
    saved = audit / "prereg.json"
    if saved.exists() and saved.read_bytes() != raw:
        raise ValueError("capture_registration_changed")
    if not saved.exists():
        saved.write_bytes(raw)
    frozen = pd.to_datetime([d for d in spec["sessions"] if d <= spec["frozen_asof"]])
    current = pd.to_datetime(spec["sessions"])
    old_groups = {}
    for code in spec["codes"]:
        item = json.loads((root / f"runtime_state/audit/kr_touch10_kis_20261007/{code}.json").read_text())
        old_groups[code] = parse_bars(item["payload"], original["price_request"]["start_date"],
                                     original["price_request"]["end_date"])
    reproduced = evaluate(original, prior, old_groups, frozen)
    # Compare entire settlement outputs, not just aggregate hit rates.
    for expected, actual in zip(prior["records"], reproduced["records"]):
        for key in ["date", "ticker", "variant", "status", "reason", "touch", "policy_ret", "entry_open", "exit_date", "net"]:
            if expected.get(key) != actual.get(key):
                raise ValueError("original_replay_not_reproduced")
    if len(prior["records"]) != len(reproduced["records"]) or len(frozen) != prior["calendar_sessions"]:
        raise ValueError("original_scope_not_reproduced")
    if args.collect:
        from dotenv import load_dotenv
        from modules.kis_openapi import KISOpenAPIClient
        load_dotenv(root / ".env.local")
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"
        os.environ["KIS_LIVE_RETRY_COUNT"] = "0"
        client = KISOpenAPIClient(timeout=10)
        for code in spec["codes"]:
            attempts = capture_paths(audit, code)
            path = audit / f"{code}.json"
            if attempts:
                last = json.loads(attempts[-1].read_text())
                failed = last.get("error_type") or last.get("payload", {}).get("rt_cd") != "0"
                if not args.retry_errors or not failed:
                    continue
                path = audit / f"{code}_attempt_{len(attempts)+1:03d}.json"
            item = {"code": code, "request": spec["request"], "prereg_sha256": digest,
                    "fetched_at": datetime.now(timezone.utc).isoformat()}
            try:
                with request_deadline(20):
                    item["payload"] = client.daily_bars(code, **spec["request"])
            except Exception as exc:
                item["error_type"] = type(exc).__name__
            path.write_text(json.dumps(item))
            print(json.dumps({"captured": code, "error_type": item.get("error_type")}), flush=True)
            time.sleep(.3)
    new_groups, coverage, hashes = {}, {}, {}
    for code in spec["codes"]:
        attempts = capture_paths(audit, code)
        if not attempts:
            raise ValueError("missing_capture")
        hashes.update({p.name: file_sha(p) for p in attempts})
        path = attempts[-1]; item = json.loads(path.read_text())
        if item["request"] != spec["request"] or item["prereg_sha256"] != digest or item["code"] != code:
            raise ValueError("capture_identity_mismatch")
        bars = parse_bars(item.get("payload", {}), spec["request"]["start_date"], spec["request"]["end_date"])
        if bars.date.max() <= pd.Timestamp(spec["valuation_asof"]):
            raise ValueError("provider_date_not_rolled_over")
        bars = bars[bars.date <= pd.Timestamp(spec["valuation_asof"])]
        missing = sorted(set(current) - set(bars.date))
        if missing:
            raise ValueError("incomplete_observed_session_coverage")
        new_groups[code] = bars
        coverage[code] = {"rows": len(bars), "missing_sessions": [], "capture": path.name, "attempts": len(attempts)}
    price_changes = compare_prices(old_groups, new_groups)
    same_calendar = evaluate(original, prior, new_groups, frozen)
    new_maturity = evaluate(original, prior, new_groups, current)
    # A pending contract becoming mature on a longer calendar is not evidence
    # of a changed price vintage on the original observation window.
    new_maturity["status"] = "LATER_MATURITY_OBSERVATION"
    new_maturity["comparison_kind"] = "same_fixed_cohort_extended_outcome_calendar"
    unchanged()
    if any(file_sha(audit / name) != sha for name, sha in hashes.items()):
        raise ValueError("capture_changed_during_evaluation")
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "prereg_sha256": digest,
              "original_replay_reproduced": True, "original_sources_preserved": True,
              "cohort_picks": len(original["cohort"]), "codes": len(spec["codes"]),
              "coverage": coverage, "source_sha256": hashes, "historical_price_changes": price_changes,
              "frozen_calendar": {"asof": spec["frozen_asof"], "sessions": len(frozen), **same_calendar},
              "later_maturity": {"asof": spec["valuation_asof"], "sessions": len(current), **new_maturity},
              "selection_frequency_unchanged": original_replay["frequency"],
              "publication_allowed": False, "production_replacement_ready": False,
              "limitations": ["Same issued cohort, not a new independent holdout",
                              "Later outcome sessions do not enlarge the selection-window frequency denominator",
                              "Same-day controls and rank selection were not recalculated",
                              "Provider rollover consistency is not official exchange-price certification"]}
    path = root / "runtime_state/reports/validation/kr_kis_rollover_audit_20261007.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({"historical_price_changes": len(price_changes),
        "frozen_differences": same_calendar["differences"], "later_maturity_differences": new_maturity["differences"],
        "frozen_h10": same_calendar["metrics"]["combined/candidate_h10"],
        "later_h10": new_maturity["metrics"]["combined/candidate_h10"], "report": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
