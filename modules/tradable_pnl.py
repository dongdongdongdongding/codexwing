from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

COST_MODEL_VERSION = "kr_tradable_pnl_cost_v1"
PNL_HORIZONS = (3, 5)


@dataclass(frozen=True)
class TradableCostModel:
    version: str = COST_MODEL_VERSION
    buy_fee_bps: float = 1.5
    sell_fee_bps: float = 1.5
    buy_slippage_bps: float = 8.0
    sell_slippage_bps: float = 8.0
    spread_bps: float = 4.0
    sell_tax_bps: float = 15.0
    fill_rate: float = 1.0


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        result = float(str(value).replace("%", "").replace(",", "").strip())
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def _metrics(values: List[float]) -> Dict[str, Any]:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return {"n": 0, "win_pct": None, "avg_pct": None, "min_pct": None, "max_pct": None}
    return {
        "n": len(clean),
        "win_pct": round(sum(1 for value in clean if value > 0.0) / len(clean) * 100.0, 4),
        "avg_pct": round(sum(clean) / len(clean), 6),
        "min_pct": round(min(clean), 6),
        "max_pct": round(max(clean), 6),
    }


def compute_net_return_pct(gross_return_pct: Any, cost_model: TradableCostModel | None = None) -> Optional[float]:
    gross = _safe_float(gross_return_pct)
    if gross is None:
        return None
    model = cost_model or TradableCostModel()
    fill_rate = min(1.0, max(0.0, float(model.fill_rate)))
    entry_cost_bps = float(model.buy_fee_bps) + float(model.buy_slippage_bps) + float(model.spread_bps) / 2.0
    exit_cost_bps = float(model.sell_fee_bps) + float(model.sell_slippage_bps) + float(model.spread_bps) / 2.0 + float(model.sell_tax_bps)
    entry_notional = 1.0 * (1.0 + entry_cost_bps / 10000.0)
    exit_notional = (1.0 + gross / 100.0) * (1.0 - exit_cost_bps / 10000.0)
    net_if_filled = ((exit_notional / entry_notional) - 1.0) * 100.0
    expected_net = fill_rate * net_if_filled
    return round(float(expected_net), 6)


def build_tradable_pnl_rows(
    rows: Iterable[Dict[str, Any]],
    *,
    cost_model: TradableCostModel | None = None,
) -> List[Dict[str, Any]]:
    model = cost_model or TradableCostModel()
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        item = {
            "pnl_model_version": model.version,
            "cost_assumptions": asdict(model),
            "run_id": row.get("run_id"),
            "ticker": row.get("ticker"),
            "stock_name": row.get("stock_name"),
            "market": row.get("market"),
            "scan_mode": row.get("scan_mode"),
            "section": row.get("section") or row.get("analysis_section"),
            "priority_rank": row.get("priority_rank"),
            "section_rank": row.get("section_rank"),
            "decision": row.get("decision"),
            "decision_bucket": row.get("decision_bucket"),
            "action_label": row.get("action_label") or row.get("signal_label"),
            "ledger_status": row.get("ledger_status"),
            "entry_reference_price": _safe_float(row.get("scan_entry_reference_price") or row.get("entry_reference_price")),
        }
        for horizon in PNL_HORIZONS:
            gross = _safe_float(row.get(f"return_{horizon}d_pct"))
            net = compute_net_return_pct(gross, model)
            item[f"gross_return_{horizon}d_pct"] = gross
            item[f"net_return_{horizon}d_pct"] = net
            item[f"net_win_{horizon}d"] = None if net is None else bool(net > 0.0)
        item["data_warnings"] = []
        if item["entry_reference_price"] is None:
            item["data_warnings"].append("MISSING_ENTRY_REFERENCE_PRICE")
        if all(item.get(f"gross_return_{horizon}d_pct") is None for horizon in PNL_HORIZONS):
            item["data_warnings"].append("MISSING_3D_5D_RETURNS")
        out.append(item)
    return out


def summarize_tradable_pnl(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    row_list = [row for row in rows or [] if isinstance(row, dict)]
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in row_list:
        key = (
            str(row.get("market") or "-"),
            str(row.get("section") or "-"),
            str(row.get("action_label") or row.get("decision") or "-"),
        )
        groups.setdefault(key, []).append(row)
    summary_rows: List[Dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        item: Dict[str, Any] = {"market": key[0], "section": key[1], "action_label": key[2], "rows": len(group)}
        for horizon in PNL_HORIZONS:
            gross = _metrics([_safe_float(row.get(f"gross_return_{horizon}d_pct")) for row in group])
            net = _metrics([_safe_float(row.get(f"net_return_{horizon}d_pct")) for row in group])
            for metric_name, value in gross.items():
                item[f"gross_{horizon}d_{metric_name}"] = value
            for metric_name, value in net.items():
                item[f"net_{horizon}d_{metric_name}"] = value
            if gross["avg_pct"] is not None and net["avg_pct"] is not None:
                item[f"cost_drag_{horizon}d_pct"] = round(float(gross["avg_pct"]) - float(net["avg_pct"]), 6)
            else:
                item[f"cost_drag_{horizon}d_pct"] = None
        summary_rows.append(item)
    regression_groups = []
    for row in summary_rows:
        for horizon in PNL_HORIZONS:
            gross_avg = row.get(f"gross_{horizon}d_avg_pct")
            net_avg = row.get(f"net_{horizon}d_avg_pct")
            if gross_avg is not None and net_avg is not None and float(gross_avg) > 0.0 and float(net_avg) <= 0.0:
                regression_groups.append(
                    {
                        "market": row.get("market"),
                        "section": row.get("section"),
                        "action_label": row.get("action_label"),
                        "horizon": f"{horizon}d",
                        "gross_avg_pct": gross_avg,
                        "net_avg_pct": net_avg,
                    }
                )
    return {
        "model_version": COST_MODEL_VERSION,
        "rows": len(row_list),
        "groups": summary_rows,
        "missing_return_rows": sum(1 for row in row_list if "MISSING_3D_5D_RETURNS" in (row.get("data_warnings") or [])),
        "net_regression_groups": regression_groups,
        "release_gate_pass": len(regression_groups) == 0,
    }


def load_post_scan_ledger_rows(shared_dir: Path, run_ids: Iterable[str] | None = None, limit_runs: int = 200) -> List[Dict[str, Any]]:
    if run_ids:
        run_dirs = [shared_dir / str(run_id) for run_id in run_ids]
    else:
        run_dirs = sorted(
            [
                path
                for path in shared_dir.glob("RUN-*")
                if path.is_dir() and (path / "post_scan_outcome_ledger.json").exists()
            ],
            key=lambda path: (path / "post_scan_outcome_ledger.json").stat().st_mtime,
            reverse=True,
        )[: int(limit_runs)]
    rows: List[Dict[str, Any]] = []
    for run_dir in run_dirs:
        path = run_dir / "post_scan_outcome_ledger.json"
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            rows.extend([row for row in payload["rows"] if isinstance(row, dict)])
    return rows
