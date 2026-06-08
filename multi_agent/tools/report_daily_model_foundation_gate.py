#!/usr/bin/env python3
"""Aggregate daily learning and promotion-safety gates into one report.

The report is read-only: it never fabricates scanner/model rows and never calls
external data APIs. It only normalizes existing operational artifacts so daily
automation can tell the difference between "safe to keep verifying in shadow"
and "ready to promote".
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


REPORT_VERSION = "daily_model_foundation_gate_v1"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports"
DEFAULT_OUTPUT_JSON = DEFAULT_REPORT_DIR / "learning" / "daily_model_foundation_gate.json"
DEFAULT_OUTPUT_MD = DEFAULT_REPORT_DIR / "learning" / "daily_model_foundation_gate.md"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"invalid_json:{exc}"
    if not isinstance(payload, dict):
        return None, "not_object"
    return payload, None


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _age_hours(value: Any, now: datetime) -> Optional[float]:
    dt = _parse_dt(value)
    if dt is None:
        return None
    return round(max(0.0, (now - dt).total_seconds() / 3600.0), 3)


def _number(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    except Exception:
        return None


def _int(value: Any, default: int = 0) -> int:
    number = _number(value)
    if number is None:
        return default
    return int(number)


def _path_text(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except Exception:
        return str(path)


def _check(
    checks: List[Dict[str, Any]],
    *,
    code: str,
    passed: bool,
    severity: str,
    detail: str,
    source_path: Optional[Path] = None,
    next_action: Optional[str] = None,
    metrics: Optional[Mapping[str, Any]] = None,
) -> None:
    row: Dict[str, Any] = {
        "code": code,
        "passed": bool(passed),
        "severity": severity,
        "detail": detail,
    }
    if source_path is not None:
        row["source_path"] = _path_text(source_path)
    if next_action:
        row["next_action"] = next_action
    if metrics:
        row["metrics"] = dict(metrics)
    checks.append(row)


def _first_existing(root: Path, candidates: Iterable[str]) -> Path:
    for rel in candidates:
        path = root / rel
        if path.exists():
            return path
    return root / next(iter(candidates))


def _report_paths(report_dir: Path) -> Dict[str, Path]:
    return {
        "learning_cycle_nightly": report_dir / "learning" / "learning_cycle_nightly.json",
        "learning_cycle_weekly": report_dir / "learning" / "learning_cycle_weekly.json",
        "retrain_v2": report_dir / "learning" / "retrain_v2_report.json",
        "kis_model_market_comparison": report_dir / "learning" / "kis_model_market_comparison.json",
        "supabase_scan_quality": report_dir / "validation" / "supabase_scan_data_quality.json",
        "walkforward_kospi": _first_existing(
            report_dir,
            (
                "validation/kr_walkforward_release_gate_kospi.json",
                "learning/kr_walkforward_release_gate_kospi.json",
            ),
        ),
        "walkforward_kosdaq": _first_existing(
            report_dir,
            (
                "validation/kr_walkforward_release_gate_kosdaq.json",
                "learning/kr_walkforward_release_gate_kosdaq.json",
            ),
        ),
        "promotion_challenger": _first_existing(
            report_dir,
            (
                "validation/kr_promotion_challenger_gate.json",
                "learning/kr_promotion_challenger_gate.json",
            ),
        ),
    }


def _evaluate_learning_cycle(
    checks: List[Dict[str, Any]],
    *,
    path: Path,
    report_name: str,
    expected_actions: Tuple[str, ...],
    max_age_hours: float,
    min_new_resolved: int,
    now: datetime,
    severity: str,
) -> None:
    payload, err = _load_json(path)
    if payload is None:
        _check(
            checks,
            code=f"{report_name.upper()}_AVAILABLE",
            passed=False,
            severity="hard_daily",
            detail=f"{report_name} report {err}",
            source_path=path,
            next_action=f"run_learning_cycle.py를 실행해 {report_name} 산출물을 재생성",
        )
        return

    age = _age_hours(payload.get("generated_at"), now)
    action = str(payload.get("action") or "")
    new_resolved = _int(payload.get("new_resolved_since_last_cycle"))
    total_resolved = _int(payload.get("total_resolved"))
    action_ok = action in expected_actions
    fresh_ok = age is not None and age <= max_age_hours
    new_ok = new_resolved >= min_new_resolved
    _check(
        checks,
        code=f"{report_name.upper()}_ACTION",
        passed=action_ok,
        severity="hard_daily",
        detail=f"action={action or 'missing'} expected={','.join(expected_actions)}",
        source_path=path,
        next_action=f"{report_name}이 defer/fail이면 outcome backfill 후 재실행",
        metrics={
            "new_resolved_since_last_cycle": new_resolved,
            "total_resolved": total_resolved,
        },
    )
    _check(
        checks,
        code=f"{report_name.upper()}_FRESHNESS",
        passed=fresh_ok,
        severity=severity,
        detail=f"age_hours={age} max_age_hours={max_age_hours}",
        source_path=path,
        next_action=f"{report_name} 자동 실행 스케줄 또는 실패 로그 확인",
    )
    _check(
        checks,
        code=f"{report_name.upper()}_NEW_OUTCOMES",
        passed=new_ok,
        severity=severity,
        detail=f"new_resolved_since_last_cycle={new_resolved} min={min_new_resolved}",
        source_path=path,
        next_action="후보 outcome resolve/backfill을 늘린 뒤 검증 재실행",
    )


def _best_threshold_rows(retrain: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    segments = retrain.get("segments")
    if not isinstance(segments, list):
        return rows
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        best = segment.get("best_threshold_row")
        if isinstance(best, dict):
            row = dict(best)
            row["segment"] = segment.get("name")
            row["auc"] = segment.get("auc")
            row["cv_median_auc"] = segment.get("cv_median_auc")
            oos = segment.get("oos_holdout")
            if isinstance(oos, dict):
                row["oos_avg_return_pct"] = oos.get("avg_return_pct")
                row["oos_win_rate_pct"] = oos.get("win_rate_pct")
                row["oos_auc"] = oos.get("auc")
            rows.append(row)
    return rows


def _evaluate_retrain(checks: List[Dict[str, Any]], *, path: Path, now: datetime) -> None:
    payload, err = _load_json(path)
    if payload is None:
        _check(
            checks,
            code="RETRAIN_REPORT_AVAILABLE",
            passed=False,
            severity="hard_daily",
            detail=f"retrain_v2 report {err}",
            source_path=path,
            next_action="retrain_v2_report.json 생성 또는 weekly learning cycle 재실행",
        )
        return

    age = _age_hours(payload.get("generated_at"), now)
    status = str(payload.get("execution_status") or "")
    rows_loaded = _int(payload.get("rows_loaded"))
    _check(
        checks,
        code="RETRAIN_EXECUTION_STATUS",
        passed=status in {"trained", "deferred_no_new_data", "deferred_not_needed"},
        severity="hard_daily",
        detail=f"execution_status={status or 'missing'}",
        source_path=path,
        next_action="retrain 실행 실패면 모델 파일을 교체하지 말고 입력 데이터/피처 오류부터 복구",
        metrics={"rows_loaded": rows_loaded, "age_hours": age},
    )
    _check(
        checks,
        code="RETRAIN_FRESHNESS",
        passed=age is not None and age <= 240.0,
        severity="soft_daily",
        detail=f"age_hours={age} max_age_hours=240",
        source_path=path,
        next_action="주간 retrain 스케줄과 learning cycle 산출물 확인",
    )

    best_rows = _best_threshold_rows(payload)
    if not best_rows:
        _check(
            checks,
            code="RETRAIN_THRESHOLD_EVIDENCE",
            passed=False,
            severity="hard_production",
            detail="best_threshold_row missing",
            source_path=path,
            next_action="threshold sweep 결과가 포함되도록 retrain 리포트 재생성",
        )
        return

    positive_rows = [row for row in best_rows if (_number(row.get("avg_return")) or 0.0) > 0.0]
    oos_positive_rows = [
        row for row in best_rows if (_number(row.get("oos_avg_return_pct")) or 0.0) > 0.0
    ]
    auc_rows = [row for row in best_rows if (_number(row.get("auc")) or 0.0) >= 0.55]
    _check(
        checks,
        code="RETRAIN_THRESHOLD_RETURN_POSITIVE",
        passed=bool(positive_rows),
        severity="hard_production",
        detail=f"positive_threshold_rows={len(positive_rows)} of {len(best_rows)}",
        source_path=path,
        next_action="음수 기대수익 segment는 승격 대상에서 제외하고 피처/라벨/시장별 분리 재검증",
        metrics={"best_threshold_rows": best_rows},
    )
    _check(
        checks,
        code="RETRAIN_OOS_RETURN_POSITIVE",
        passed=bool(oos_positive_rows),
        severity="hard_production",
        detail=f"positive_oos_rows={len(oos_positive_rows)} of {len(best_rows)}",
        source_path=path,
        next_action="OOS 수익률이 양수인 segment만 shadow 승격 후보로 유지",
    )
    _check(
        checks,
        code="RETRAIN_AUC_FLOOR",
        passed=bool(auc_rows),
        severity="hard_production",
        detail=f"auc_ge_0.55_rows={len(auc_rows)} of {len(best_rows)}",
        source_path=path,
        next_action="AUC 하한 미달 시 모델 승격 대신 룰 기반 게이트와 데이터 품질 개선 우선",
    )


def _evaluate_supabase_quality(checks: List[Dict[str, Any]], *, path: Path, now: datetime) -> None:
    payload, err = _load_json(path)
    if payload is None:
        _check(
            checks,
            code="SUPABASE_SCAN_QUALITY_AVAILABLE",
            passed=False,
            severity="hard_daily",
            detail=f"supabase_scan_data_quality report {err}",
            source_path=path,
            next_action="report_supabase_scan_quality.py 실행 후 DB 호환성/더미 여부 확인",
        )
        return

    age = _age_hours(payload.get("generated_at"), now)
    dummy_rows = _int(payload.get("kr_swing_dummy_rows"))
    missing_required = payload.get("schema_missing_required_columns")
    if not isinstance(missing_required, list):
        missing_required = []
    kr_rows = _int(payload.get("kr_swing_rows"))
    computed_rows = _int(payload.get("kr_swing_computed_complete_rows"))
    return3_rows = _int(payload.get("kr_swing_computed_complete_with_return3d_rows"))
    _check(
        checks,
        code="NO_DUMMY_SCAN_ROWS",
        passed=dummy_rows == 0,
        severity="hard_daily",
        detail=f"kr_swing_dummy_rows={dummy_rows}",
        source_path=path,
        next_action="더미 row가 발견되면 해당 run_id를 제외/삭제하고 실데이터 backfill만 허용",
        metrics={"kr_swing_rows": kr_rows},
    )
    _check(
        checks,
        code="SUPABASE_SCHEMA_COMPATIBLE",
        passed=len(missing_required) == 0,
        severity="hard_daily",
        detail=f"missing_required_columns={missing_required}",
        source_path=path,
        next_action="스캐너 저장 스키마와 Supabase 컬럼 계약을 먼저 복구",
    )
    _check(
        checks,
        code="SUPABASE_QUALITY_FRESHNESS",
        passed=age is not None and age <= 168.0,
        severity="soft_daily",
        detail=f"age_hours={age} max_age_hours=168",
        source_path=path,
        next_action="일일 품질 리포트 생성 스케줄에 report_supabase_scan_quality.py 포함",
        metrics={
            "computed_complete_rows": computed_rows,
            "computed_complete_with_return3d_rows": return3_rows,
        },
    )


def _evaluate_kis_comparison(checks: List[Dict[str, Any]], *, path: Path) -> None:
    payload, err = _load_json(path)
    if payload is None:
        _check(
            checks,
            code="KIS_MODEL_COMPARISON_AVAILABLE",
            passed=False,
            severity="hard_daily",
            detail=f"kis_model_market_comparison report {err}",
            source_path=path,
            next_action="report_kis_model_market_comparison.py 실행 후 KOSPI/KOSDAQ gate 확인",
        )
        return

    decision = payload.get("promotion_decision")
    if not isinstance(decision, dict):
        _check(
            checks,
            code="KIS_MODEL_COMPARISON_CONTRACT",
            passed=False,
            severity="hard_daily",
            detail="promotion_decision missing",
            source_path=path,
            next_action="KIS 비교 리포트 계약을 복구",
        )
        return

    no_dummy = bool(decision.get("no_dummy_data"))
    shadow_allowed = bool(decision.get("all_required_markets_shadow_display_allowed"))
    production_ready = bool(decision.get("all_required_markets_production_ready"))
    status = str(decision.get("status") or "")
    market_rows = decision.get("market_gate_rows")
    if not isinstance(market_rows, dict):
        market_rows = {}
    blockers = {
        market: row.get("production_blocking_reasons") if isinstance(row, dict) else []
        for market, row in market_rows.items()
    }
    _check(
        checks,
        code="KIS_COMPARISON_NO_DUMMY",
        passed=no_dummy,
        severity="hard_daily",
        detail=f"no_dummy_data={no_dummy}",
        source_path=path,
        next_action="KIS 비교 입력에서 실데이터 provenance만 허용",
    )
    _check(
        checks,
        code="KIS_SHADOW_DISPLAY_ALLOWED",
        passed=shadow_allowed,
        severity="hard_daily",
        detail=f"status={status} shadow_allowed={shadow_allowed}",
        source_path=path,
        next_action="shadow_display_allowed=false이면 UI/Discord 후보 노출을 중단하고 KIS gate 복구",
    )
    _check(
        checks,
        code="KIS_PROMOTION_READY",
        passed=production_ready,
        severity="hard_production",
        detail=f"status={status} market_blockers={blockers}",
        source_path=path,
        next_action="시장별 production_blocking_reasons를 해소할 때까지 기존 운영 모델 유지",
        metrics={"promotion_decision": decision},
    )


def _evaluate_walkforward(checks: List[Dict[str, Any]], *, path: Path, market: str) -> None:
    payload, err = _load_json(path)
    if payload is None:
        _check(
            checks,
            code=f"{market}_WALKFORWARD_RELEASE",
            passed=False,
            severity="hard_production",
            detail=f"{market} walk-forward report {err}",
            source_path=path,
            next_action=f"report_kr_walkforward_release_gate.py --market {market} 실행 후 릴리즈 하한 검증",
        )
        return
    release_ready = bool(payload.get("release_ready"))
    failed = []
    for row in payload.get("all_checks") or []:
        if isinstance(row, dict) and not bool(row.get("passed")):
            failed.append(row.get("code") or row.get("name") or "unknown")
    _check(
        checks,
        code=f"{market}_WALKFORWARD_RELEASE",
        passed=release_ready,
        severity="hard_production",
        detail=f"release_ready={release_ready} failed_checks={failed}",
        source_path=path,
        next_action=f"{market} lane별 평균수익/positive/avoid_down CI 하한을 통과할 때까지 shadow 유지",
        metrics={"failed_checks": failed, "confidence_level": payload.get("confidence_level")},
    )


def _promotion_candidate_count(payload: Mapping[str, Any]) -> int:
    summary = payload.get("summary")
    if isinstance(summary, dict):
        for key in ("promotion_review_candidate_count", "promotion_candidate_count"):
            if key in summary:
                return _int(summary.get(key))
    rows = payload.get("candidates")
    if not isinstance(rows, list):
        rows = payload.get("results") if isinstance(payload.get("results"), list) else []
    return sum(1 for row in rows if isinstance(row, dict) and str(row.get("status")) == "promotion_review_candidate")


def _evaluate_promotion_challenger(checks: List[Dict[str, Any]], *, path: Path) -> None:
    payload, err = _load_json(path)
    if payload is None:
        _check(
            checks,
            code="PROMOTION_CHALLENGER_CANDIDATE",
            passed=False,
            severity="hard_production",
            detail=f"promotion challenger report {err}",
            source_path=path,
            next_action="report_kr_promotion_challenger_gate.py 실행 후 후보 count 확인",
        )
        return
    count = _promotion_candidate_count(payload)
    near_count = 0
    summary = payload.get("summary")
    if isinstance(summary, dict):
        near_count = _int(summary.get("near_candidate_count"))
    _check(
        checks,
        code="PROMOTION_CHALLENGER_CANDIDATE",
        passed=count > 0,
        severity="hard_production",
        detail=f"promotion_review_candidate_count={count} near_candidate_count={near_count}",
        source_path=path,
        next_action="promotion_review_candidate가 1개 이상 나올 때까지 후보 룰/모델/exit policy를 shadow에서 검증",
        metrics={"promotion_review_candidate_count": count, "near_candidate_count": near_count},
    )


def _failed_codes(checks: Iterable[Mapping[str, Any]], severity_prefix: str) -> List[str]:
    return [
        str(row.get("code"))
        for row in checks
        if str(row.get("severity") or "").startswith(severity_prefix) and not bool(row.get("passed"))
    ]


def build_report(report_dir: Path = DEFAULT_REPORT_DIR, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    report_dir = Path(report_dir)
    now = now or _utcnow()
    paths = _report_paths(report_dir)
    checks: List[Dict[str, Any]] = []

    _evaluate_learning_cycle(
        checks,
        path=paths["learning_cycle_nightly"],
        report_name="nightly_learning",
        expected_actions=("dataset_refresh", "nightly_retrain", "weekly_retrain"),
        max_age_hours=48.0,
        min_new_resolved=1,
        now=now,
        severity="hard_daily",
    )
    _evaluate_learning_cycle(
        checks,
        path=paths["learning_cycle_weekly"],
        report_name="weekly_learning",
        expected_actions=("weekly_retrain", "dataset_refresh"),
        max_age_hours=192.0,
        min_new_resolved=1,
        now=now,
        severity="soft_daily",
    )
    _evaluate_retrain(checks, path=paths["retrain_v2"], now=now)
    _evaluate_supabase_quality(checks, path=paths["supabase_scan_quality"], now=now)
    _evaluate_kis_comparison(checks, path=paths["kis_model_market_comparison"])
    _evaluate_walkforward(checks, path=paths["walkforward_kospi"], market="KOSPI")
    _evaluate_walkforward(checks, path=paths["walkforward_kosdaq"], market="KOSDAQ")
    _evaluate_promotion_challenger(checks, path=paths["promotion_challenger"])

    hard_daily_blockers = _failed_codes(checks, "hard_daily")
    hard_production_blockers = _failed_codes(checks, "hard_production")
    soft_daily_warnings = _failed_codes(checks, "soft_daily")
    daily_ready = not hard_daily_blockers
    production_ready = daily_ready and not hard_production_blockers
    if production_ready:
        status = "production_ready"
        recommended_action = "human_review_then_controlled_promotion"
    elif daily_ready:
        status = "shadow_only"
        recommended_action = "keep_existing_production_and_run_daily_shadow_verification"
    else:
        status = "blocked"
        recommended_action = "fix_daily_data_contract_before_shadow_or_promotion"

    dummy_check_codes = {"NO_DUMMY_SCAN_ROWS", "KIS_COMPARISON_NO_DUMMY"}
    dummy_checks = [row for row in checks if str(row.get("code")) in dummy_check_codes]
    no_dummy_data = (
        {str(row.get("code")) for row in dummy_checks} == dummy_check_codes
        and all(bool(row.get("passed")) for row in dummy_checks)
    )
    next_actions = [
        str(row.get("next_action"))
        for row in checks
        if not bool(row.get("passed")) and row.get("next_action")
    ]
    seen: set[str] = set()
    deduped_actions = []
    for action in next_actions:
        if action not in seen:
            seen.add(action)
            deduped_actions.append(action)

    return {
        "version": REPORT_VERSION,
        "generated_at": now.isoformat(),
        "report_dir": _path_text(report_dir),
        "status": status,
        "daily_verification_ready": daily_ready,
        "production_promotion_ready": production_ready,
        "recommended_action": recommended_action,
        "no_dummy_data": bool(no_dummy_data),
        "blocking_reasons": {
            "hard_daily": hard_daily_blockers,
            "hard_production": hard_production_blockers,
            "soft_daily": soft_daily_warnings,
        },
        "checks": checks,
        "next_actions": deduped_actions[:12],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Daily Model Foundation Gate",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- version: {report.get('version')}",
        f"- status: **{report.get('status')}**",
        f"- daily_verification_ready: {report.get('daily_verification_ready')}",
        f"- production_promotion_ready: {report.get('production_promotion_ready')}",
        f"- no_dummy_data: {report.get('no_dummy_data')}",
        f"- recommended_action: {report.get('recommended_action')}",
        "",
        "## Blocking Reasons",
        "",
    ]
    blockers = report.get("blocking_reasons") if isinstance(report.get("blocking_reasons"), dict) else {}
    for key in ("hard_daily", "hard_production", "soft_daily"):
        values = blockers.get(key) if isinstance(blockers.get(key), list) else []
        lines.append(f"- {key}: {', '.join(map(str, values)) if values else 'none'}")

    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| severity | status | code | detail |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in report.get("checks") or []:
        if not isinstance(row, dict):
            continue
        mark = "PASS" if row.get("passed") else "FAIL"
        detail = str(row.get("detail") or "").replace("\n", " ")
        lines.append(
            f"| {row.get('severity')} | {mark} | {row.get('code')} | {detail} |"
        )

    actions = report.get("next_actions") if isinstance(report.get("next_actions"), list) else []
    lines.extend(["", "## Next Actions", ""])
    if actions:
        for action in actions:
            lines.append(f"- {action}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate daily model foundation gates.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    parser.add_argument(
        "--fail-on-daily-block",
        action="store_true",
        help="Exit non-zero when hard daily checks fail.",
    )
    parser.add_argument(
        "--fail-on-production-block",
        action="store_true",
        help="Exit non-zero when production promotion checks fail.",
    )
    args = parser.parse_args()

    report = build_report(Path(args.report_dir))
    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_path": _path_text(out_json),
                "md_path": _path_text(out_md),
                "status": report["status"],
                "daily_verification_ready": report["daily_verification_ready"],
                "production_promotion_ready": report["production_promotion_ready"],
                "blocking_reasons": report["blocking_reasons"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    if args.fail_on_daily_block and not report["daily_verification_ready"]:
        raise SystemExit(1)
    if args.fail_on_production_block and not report["production_promotion_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
