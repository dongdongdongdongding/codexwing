#!/usr/bin/env python3
"""만료된 결과를 소급 점수화한다 (EXPIRED → RESOLVED_BACKFILL).

배경: 정산기와 수익률 지표 산출기가 둘 다 RUN 디렉터리를 **이름순**으로 골랐다
(`update_realized_outcomes.py:61`, `update_outcome_return_metrics.py:160`). RUN-<랜덤16진수>
에는 시간 정보가 없어 "최근 N개"가 고정된 임의 N개였고, 나머지 RUN 의 `return_{h}d_pct` 가
한 번도 계산되지 않아 정산기가 근거 없이 만료시켰다. 만료 사유는 전건
`HORIZON_ELAPSED_NO_RESOLUTION` — **데이터 부재가 아니라 창 초과**다.

가격은 지금도 있으므로 소급 계산이 가능하다. 다만 소급분은 **forward 기록이 아니다.**

## 출처 구분 (설계 제약 1)

forward 원장의 가치는 라이브로 기록됐다는 데 있다. 소급분을 조용히 섞으면 측정 대상 자체가
오염된다. 그래서 두 겹으로 표시한다:

- `status = "RESOLVED_BACKFILL"` — 기존 소비자는 `status == "RESOLVED"` **정확 일치**로
  거른다(`run_learning_cycle.py:100`, `export_scan_archive_learning_dataset.py:286,396`).
  따라서 이 값은 **소비자를 고치지 않고도 기본 제외**된다. 새 필드만 추가하고 status 를
  RESOLVED 로 두면 전 소비자가 조용히 포함해버린다 — 그건 제약 1 위반이다.
- `resolution_source = "backfill_px_long_v1"` — 방법과 판을 명시한다. 포함하려는 소비자는
  이 값을 보고 명시적으로 선택하면 된다.

원본 `expiry_reason` 과 `outcome_label` 은 지우지 않는다. 무엇이 왜 만료됐는지가 남아야 한다.

## 계산 계약 (설계 제약 4)

`update_outcome_return_metrics._compute_row_returns` 와 **같은 식**을 쓴다:

    base_trade_date = recommended_at 을 시장 타임존으로 변환한 날짜 이후 첫 거래일
    base_close      = 그 거래일 종가
    return_{h}d_pct = (close[base_pos + h] / base_close - 1) * 100      # 거래일 오프셋

가격원만 다르다(원래는 FinanceDataReader/yfinance 네트워크, 여기서는 로컬 px_long).
같은 값을 내는지는 기록된 RESOLVED 로 검증했다 — `--validate` 참조.

**한계**: px_long 은 KR(.KS/.KQ) 전용이다. NASDAQ 행은 소급 불가로 남긴다.

멱등: 같은 입력에 같은 값을 쓴다. 두 번 돌려도 결과가 같고, 이미 처리된 행은 건너뛴다.

  python3 multi_agent/tools/backfill_expired_outcome_returns.py --validate
  python3 multi_agent/tools/backfill_expired_outcome_returns.py            # dry-run
  python3 multi_agent/tools/backfill_expired_outcome_returns.py --apply --backup-dir DIR
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SHARED = PROJECT_ROOT / "runtime_state" / "shared_working"
DEFAULT_PX = Path("~/research_cache/px_long.parquet").expanduser()

KR_TZ = ZoneInfo("Asia/Seoul")
US_TZ = ZoneInfo("America/New_York")
BACKFILL_STATUS = "RESOLVED_BACKFILL"
RESOLUTION_SOURCE = "backfill_px_long_v1"
HORIZONS = {"T+1D": 1, "T+2D": 2, "T+3D": 3, "T+5D": 5}


def _market_tz(ticker: str) -> ZoneInfo:
    return KR_TZ if str(ticker).upper().endswith((".KS", ".KQ")) else US_TZ


def _parse_iso(value: Any) -> Optional[dt.datetime]:
    try:
        d = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    return d.replace(tzinfo=dt.timezone.utc) if d.tzinfo is None else d


def _horizon_days(value: Any) -> Optional[int]:
    return HORIZONS.get(str(value or "").strip().upper())


def load_prices(px_path: Path) -> Dict[str, Any]:
    import pandas as pd

    df = pd.read_parquet(px_path, columns=["code", "date", "close"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values(["code", "date"])
    return {code: part.reset_index(drop=True) for code, part in df.groupby("code", sort=False)}


def compute_return(prices: Dict[str, Any], ticker: str, recommended_at: Any,
                   horizon: Any) -> Tuple[Optional[Dict[str, Any]], str]:
    """계약대로 지평 수익률을 계산한다. (결과, 사유) — 결과가 None 이면 사유가 이유다."""
    tkr = str(ticker or "")
    if not tkr.endswith((".KS", ".KQ")):
        return None, "non_kr_no_local_prices"
    days = _horizon_days(horizon)
    if days is None:
        return None, "unknown_horizon"
    rec = _parse_iso(recommended_at)
    if rec is None:
        return None, "no_recommended_at"
    series = prices.get(tkr.split(".")[0])
    if series is None:
        return None, "no_price_series"
    want = rec.astimezone(_market_tz(tkr)).date()
    idx = series.index[series["date"] >= want]
    if len(idx) == 0:
        return None, "base_after_history"
    base = int(idx[0])
    target = base + days
    if target >= len(series):
        return None, "horizon_beyond_history"
    base_close = float(series["close"].iloc[base])
    if base_close <= 0:
        return None, "bad_base_close"
    target_close = float(series["close"].iloc[target])
    return {
        "return_pct": round((target_close / base_close - 1.0) * 100.0, 6),
        "horizon_days": days,
        "base_trade_date": str(series["date"].iloc[base]),
        "base_close": round(base_close, 6),
        "target_trade_date": str(series["date"].iloc[target]),
    }, "ok"


def apply_to_row(row: Dict[str, Any], computed: Dict[str, Any], now_iso: str) -> bool:
    """행에 소급 결과를 반영한다. 이미 같은 값이면 False(멱등)."""
    key = f"return_{computed['horizon_days']}d_pct"
    desired = {
        "status": BACKFILL_STATUS,
        "resolution_source": RESOLUTION_SOURCE,
        key: computed["return_pct"],
        "backfill_return_pct": computed["return_pct"],
        "backfill_horizon_days": computed["horizon_days"],
        "backfill_base_trade_date": computed["base_trade_date"],
        "backfill_base_close": computed["base_close"],
        "backfill_target_trade_date": computed["target_trade_date"],
        "backfill_price_source": "px_long",
    }
    if all(row.get(k) == v for k, v in desired.items()):
        return False
    row.update(desired)
    row.setdefault("backfill_recorded_at", now_iso)
    return True


def iter_run_files(shared_dir: Path) -> List[Path]:
    return sorted(p / "realized_outcomes.json"
                  for p in shared_dir.iterdir()
                  if p.is_dir() and p.name.startswith("RUN-")
                  and (p / "realized_outcomes.json").exists())


def _rows_of(payload: Any) -> Optional[List[Dict[str, Any]]]:
    rows = payload.get("outcomes") if isinstance(payload, dict) else payload
    return rows if isinstance(rows, list) else None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shared-dir", default=str(DEFAULT_SHARED))
    ap.add_argument("--px-path", default=str(DEFAULT_PX))
    ap.add_argument("--apply", action="store_true", help="실제로 기록한다 (기본은 dry-run)")
    ap.add_argument("--backup-dir", default="", help="--apply 시 필수: 원본 백업 위치")
    ap.add_argument("--validate", action="store_true",
                    help="기록된 RESOLVED 를 재계산해 방법을 검증만 하고 끝낸다")
    args = ap.parse_args()

    # 인자 검증은 가격 로딩(수백 MB) 전에 — 잘못된 호출이 비싼 작업 뒤에 실패하면 안 된다
    if args.apply and not args.backup_dir:
        print(json.dumps({"status": "error", "reason": "--apply 에는 --backup-dir 가 필요하다"},
                         ensure_ascii=False))
        return 1

    shared = Path(args.shared_dir)
    prices = load_prices(Path(args.px_path))
    files = iter_run_files(shared)
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()

    if args.validate:
        agree = total = 0
        diffs: List[float] = []
        for fp in files:
            rows = _rows_of(json.loads(fp.read_text(encoding="utf-8"))) or []
            for row in rows:
                if str(row.get("status", "")).upper() != "RESOLVED":
                    continue
                got, _ = compute_return(prices, row.get("ticker"), row.get("recommended_at"),
                                        row.get("horizon"))
                if got is None:
                    continue
                recorded = row.get(f"return_{got['horizon_days']}d_pct")
                if recorded is None:
                    continue
                total += 1
                delta = abs(float(recorded) - got["return_pct"])
                diffs.append(delta)
                agree += delta <= 1e-4
        diffs.sort()
        print(json.dumps({
            "mode": "validate", "compared": total, "exact_within_1e-4": agree,
            "reproduction_rate": round(agree / total, 4) if total else None,
            "median_abs_diff": diffs[len(diffs) // 2] if diffs else None,
            "max_abs_diff": diffs[-1] if diffs else None,
            "within_0.1pp": sum(d <= 0.1 for d in diffs),
        }, ensure_ascii=False))
        return 0

    backup_root = Path(args.backup_dir) if args.backup_dir else None
    if args.apply and backup_root is not None:
        backup_root.mkdir(parents=True, exist_ok=True)

    skipped: Dict[str, int] = {}
    changed_rows = changed_files = 0
    manifest: List[Dict[str, str]] = []
    for fp in files:
        payload = json.loads(fp.read_text(encoding="utf-8"))
        rows = _rows_of(payload)
        if rows is None:
            continue
        touched = False
        for row in rows:
            if str(row.get("status", "")).upper() != "EXPIRED":
                continue
            got, why = compute_return(prices, row.get("ticker"), row.get("recommended_at"),
                                      row.get("horizon"))
            if got is None:
                skipped[why] = skipped.get(why, 0) + 1
                continue
            if apply_to_row(row, got, now_iso):
                changed_rows += 1
                touched = True
        if touched:
            changed_files += 1
            if args.apply and backup_root is not None:
                before = sha256(fp)
                dest = backup_root / fp.parent.name / fp.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fp, dest)
                assert sha256(dest) == before, f"백업 무결성 실패: {fp}"
                manifest.append({"run": fp.parent.name, "sha256": before})
                fp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    if args.apply and backup_root is not None:
        (backup_root / "manifest.json").write_text(
            json.dumps({"created_at": now_iso, "files": manifest}, ensure_ascii=False, indent=1),
            encoding="utf-8")

    print(json.dumps({
        "mode": "apply" if args.apply else "dry_run",
        "status": BACKFILL_STATUS, "resolution_source": RESOLUTION_SOURCE,
        "changed_rows": changed_rows, "changed_files": changed_files,
        "skipped": skipped, "backup_dir": str(backup_root) if backup_root else None,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
