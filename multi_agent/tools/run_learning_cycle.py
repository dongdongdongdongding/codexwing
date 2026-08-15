#!/usr/bin/env python3
from __future__ import annotations

import os

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
RETRAIN_REPORT_PATH = PROJECT_ROOT / "runtime_state" / "reports" / "learning" / "retrain_v2_report.json"


def _load_json_checked(path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
    """`(payload, error)`. error가 None이 아니면 **파일은 있는데 못 읽었다**는 뜻이다.

    "파일 없음"(정상 초기화)과 "파싱 실패"(사고)를 구분하지 않으면 손상이 조용히
    기본값으로 둔갑한다. 구분해서 후자만 표면화한다 — 정상 초기화까지 경보를 울리면
    경보가 곧 무시당하기 때문이다.
    """
    if not path.exists():
        return {}, None
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        return {}, f"{path.name}: {type(e).__name__}: {e}"
    if not isinstance(payload, dict):
        return {}, f"{path.name}: expected a JSON object, got {type(payload).__name__}"
    return payload, None


def _load_json(path: Path) -> Dict[str, Any]:
    payload, _ = _load_json_checked(path)
    return payload


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    """tmp 파일에 다 쓴 뒤 원자적으로 갈아끼운다.

    `open("w")`는 **먼저 절단하고** 그 자리에 쓴다 — 쓰기가 도중에 죽으면 원본이 잘린 채 남고,
    `_load_json`이 예외를 삼켜 전 기준선이 조용히 0으로 리셋된다. 상태파일이 262B이던
    시절엔 사실상 안 찢어졌지만, 키집합 2개를 담으면서 251,920B(**962배**)가 됐다.
    252KB는 launchd 타임아웃·절전·디스크풀·강제종료에서 얼마든지 찢어진다.

    `os.replace`는 같은 파일시스템 안에서 원자적이므로, 실패한 쓰기는 원본에 닿지 못한다.
    리포 기존 패턴과 동일하다: train_kosdaq_1500_bundle.py:167, kis_openapi.py:431.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # 실패한 쓰기의 잔재가 디스크에 쌓이지 않게 한다. 원본은 손대지 않았다.
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _iter_run_dirs(shared_dir: Path) -> Iterable[Path]:
    if not shared_dir.exists():
        return []
    return sorted([p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")], key=lambda p: p.name)


def _load_learning_state(state_path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
    """`(state, load_error)`.

    load_error가 실리면 **기준선 전체가 방금 0으로 리셋됐다**는 뜻이다. 그대로 두면
    다음 사이클이 `action=dataset_refresh`, `new_resolved=<전체>`로 게이트를 통과해
    사고가 "건강한 대량 신규 수확"처럼 보인다(실측). 그래서 리포트로 끌어올리고,
    손상본은 덮어쓰기 전에 보존해 복구 가능성을 남긴다.
    """
    payload, load_error = _load_json_checked(state_path)
    if load_error:
        try:
            shutil.copy2(state_path, state_path.with_name(state_path.name + ".corrupt"))
        except OSError:
            pass
    if not payload:
        return {
            "last_nightly_resolved_total": 0,
            "last_weekly_resolved_total": 0,
            "last_nightly_run_at": None,
            "last_weekly_run_at": None,
            "last_weekly_train_at": None,
        }, load_error
    return payload, load_error


def _collect_outcomes(shared_dir: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {
        "runs_seen": 0,
        "runs_with_outcomes": 0,
        "markets": Counter(),
        "buckets": Counter(),
        "statuses": Counter(),
    }
    for run_dir in _iter_run_dirs(shared_dir):
        stats["runs_seen"] += 1
        payload = _load_json(run_dir / "realized_outcomes.json")
        if not payload:
            continue
        outcomes = payload.get("outcomes", [])
        if not isinstance(outcomes, list) or not outcomes:
            continue
        stats["runs_with_outcomes"] += 1
        run_ctx = payload.get("run_context", {}) if isinstance(payload.get("run_context"), dict) else {}
        market = str(run_ctx.get("market", "") or "UNKNOWN").upper()
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            out = dict(row)
            out["run_id"] = out.get("run_id") or run_dir.name
            out["market"] = market
            out["outcome_key"] = f"{out['run_id']}:{out.get('ticker','')}:{int(out.get('priority_rank', 0) or 0)}"
            rows.append(out)
            stats["markets"][market] += 1
            stats["buckets"][str(out.get("decision_bucket", "") or "unknown")] += 1
            stats["statuses"][str(out.get("status", "") or "UNKNOWN").upper()] += 1
    stats["markets"] = dict(stats["markets"])
    stats["buckets"] = dict(stats["buckets"])
    stats["statuses"] = dict(stats["statuses"])
    return rows, stats


def _resolved_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    resolved = [r for r in rows if str(r.get("status", "")).upper() == "RESOLVED"]
    by_market: Dict[str, int] = defaultdict(int)
    by_bucket: Dict[str, int] = defaultdict(int)
    for row in resolved:
        by_market[str(row.get("market", "UNKNOWN")).upper()] += 1
        by_bucket[str(row.get("decision_bucket", "unknown") or "unknown")] += 1
    return {
        "total_resolved": len(resolved),
        "resolved_keys": sorted({str(r.get("outcome_key")) for r in resolved if r.get("outcome_key")}),
        "resolved_by_market": dict(by_market),
        "resolved_by_bucket": dict(by_bucket),
    }


def _run_command(cmd: List[str], cwd: Path) -> Dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=60 * 60,
        )
        result = {
            "cmd": cmd,
            "returncode": int(proc.returncode),
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-40:]),
            "stderr_tail": "\n".join(proc.stderr.splitlines()[-40:]),
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ok": proc.returncode == 0,
        }
        if cmd and str(cmd[-1]).endswith("retrain_ml.py") and RETRAIN_REPORT_PATH.exists():
            retrain_report = _load_json(RETRAIN_REPORT_PATH)
            result["semantic_status"] = retrain_report.get("execution_status")
            result["defer_reason"] = retrain_report.get("defer_reason")
            result["last_successful_model_train_at"] = retrain_report.get("last_successful_model_train_at")
        return result
    except Exception as e:
        return {
            "cmd": cmd,
            "returncode": -1,
            "stdout_tail": "",
            "stderr_tail": str(e),
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ok": False,
        }


def _render_report(report: Dict[str, Any]) -> str:
    lines = [
        f"# Learning Cycle Report ({report.get('mode')})",
        "",
        f"- generated_at: {report.get('generated_at')}",
        f"- action: {report.get('action')}",
        f"- reason: {report.get('reason')}",
        f"- total_resolved: {report.get('total_resolved', 0)}",
        f"- new_resolved_since_last_cycle: {report.get('new_resolved_since_last_cycle', 0)}",
        f"- dropped_resolved_since_last_cycle: {report.get('dropped_resolved_since_last_cycle', 0)}",
        f"- new_resolved_measurement_basis: {report.get('new_resolved_measurement_basis', 'unknown')}",
        f"- consecutive_skip_cycles: {report.get('consecutive_skip_cycles', 0)}",
        f"- state_load_error: {report.get('state_load_error')}",
        f"- counter_rebaselined_from: {report.get('counter_rebaselined_from')}",
        f"- resolved_by_market: {report.get('resolved_by_market', {})}",
        f"- resolved_by_bucket: {report.get('resolved_by_bucket', {})}",
        "",
        "## Commands",
    ]
    commands = report.get("commands", [])
    if isinstance(commands, list) and commands:
        for item in commands:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- {' '.join(item.get('cmd', []))}: "
                f"{'OK' if item.get('ok') else 'FAIL'} "
                f"(returncode={item.get('returncode')})"
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _keys_field(total_field: str) -> str:
    return total_field.replace("_resolved_total", "_resolved_keys")


def _skip_streak_field(mode: str) -> str:
    return f"consecutive_{mode}_skip_cycles"


def _bump_skip_streak(state: Dict[str, Any], mode: str, action: str) -> int:
    """연속 skip 횟수를 세어 상태파일과 리포트에 남긴다.

    2026-06-14 이후 9주간 아무도 몰랐던 진짜 이유는 skip이 '정상 상태'와 구분되지
    않았기 때문이다. 한 번의 skip은 정상이지만 63번 연속 skip은 사고다. 누적 침묵을
    셈으로 바꿔 리포트 표면에 올린다.
    """
    field = _skip_streak_field(mode)
    streak = 0 if action != "skip" else int(state.get(field, 0) or 0) + 1
    state[field] = streak
    return streak


def _stored_keys(state: Dict[str, Any], total_field: str) -> Optional[set]:
    """상태파일에 기록된 '이미 소화한 outcome_key' 집합. 없으면 None(구 상태파일)."""
    raw = state.get(_keys_field(total_field))
    if not isinstance(raw, list):
        return None
    return {str(k) for k in raw if k not in (None, "")}


def _adopt_baseline(state: Dict[str, Any], total_field: str, total_resolved: int, resolved_keys: List[str]) -> None:
    """이번 창을 새 기준선으로 채택한다. 집합 크기는 창 크기로 유한하다."""
    state[total_field] = int(total_resolved)
    state[_keys_field(total_field)] = sorted({str(k) for k in resolved_keys if k not in (None, "")})


def _measure_new_resolved(
    state: Dict[str, Any],
    total_field: str,
    total_resolved: int,
    resolved_keys: List[str],
) -> Dict[str, Any]:
    """직전 기준선 이후 새로 생긴 표본 수를 센다.

    `total_resolved` 델타는 **누적 카운터**를 가정한다. 실제 원천은 그렇지 않다 —
    `_collect_outcomes`가 매번 `shared_dir` 전체를 재스캔하므로 total_resolved는
    *현재 창의 개수*다. 창이 주기적으로 정리되면(매일 N건 추가 / N건 제거) total은
    줄지도 늘지도 않고 **평평해지고**, `max(0, total - previous)`는 영구히 0을 낸다.
    그러면 사이클이 영원히 skip인데 `counter_rebaselined_from`은 null이라 리포트에
    아무 이상도 안 뜬다 — 2026-06-14 이후 9주간 아무도 몰랐던 그 조용한 실패와
    증상·가시성이 똑같다. 감소(<)만 잡는 재기준선으로는 정체(=)를 절대 못 잡는다.

    그래서 델타가 아니라 처리한 `outcome_key` 집합의 차분으로 센다
    (`_resolved_summary`가 `resolved_keys`를 이미 만들어 놓고 안 쓰고 있었다).
    집합은 '마지막으로 실제 작업한 사이클의 창'만 담으므로 크기가 창 크기로 유한하다.

    구 상태파일(키 집합 없음)에는 기존 델타 + 축소-재기준선 동작을 그대로 유지하고,
    어느 근거로 셌는지를 `new_resolved_measurement_basis`로 리포트에 남긴다.
    """
    previous_total = int(state.get(total_field, 0) or 0)
    current_keys = {str(k) for k in resolved_keys if k not in (None, "")}
    seen_keys = _stored_keys(state, total_field)

    if seen_keys is not None:
        return {
            "new_resolved": len(current_keys - seen_keys),
            "dropped_resolved": len(seen_keys - current_keys),
            "rebaselined_from": None,
            "basis": "outcome_key_set",
        }

    # --- 구 상태파일 경로 (1회성 마이그레이션) ---
    if total_resolved < previous_total:
        # 축소 사건: 현재 창을 새 기준선으로 채택하고 키 집합도 이때 채운다.
        _adopt_baseline(state, total_field, total_resolved, resolved_keys)
        return {
            "new_resolved": 0,
            "dropped_resolved": max(0, previous_total - total_resolved),
            "rebaselined_from": previous_total,
            "basis": "total_delta_fallback",
        }
    return {
        "new_resolved": max(0, total_resolved - previous_total),
        "dropped_resolved": 0,
        "rebaselined_from": None,
        "basis": "total_delta_fallback",
    }


def run_learning_cycle(
    *,
    mode: str,
    shared_dir: Path,
    report_dir: Path,
    state_path: Path,
    nightly_min_new_resolved: int,
    weekly_min_total_resolved: int,
    weekly_min_new_resolved: int,
    run_kis_touch5_full_matrix: bool = False,
) -> Dict[str, Any]:
    rows, collect_stats = _collect_outcomes(shared_dir)
    resolved = _resolved_summary(rows)
    state, state_load_error = _load_learning_state(state_path)
    total_resolved = int(resolved["total_resolved"])

    resolved_keys: List[str] = list(resolved["resolved_keys"])

    if mode == "nightly":
        measured = _measure_new_resolved(state, "last_nightly_resolved_total", total_resolved, resolved_keys)
        new_resolved = int(measured["new_resolved"])
        rebaselined_from = measured["rebaselined_from"]
        min_needed = int(nightly_min_new_resolved)
        action = "skip"
        reason = "insufficient_new_resolved"
        commands: List[Dict[str, Any]] = []
        if new_resolved >= min_needed:
            commands.append(
                _run_command(
                    ["python3", "multi_agent/tools/export_scan_archive_learning_dataset.py"],
                    PROJECT_ROOT,
                )
            )
            for _market in ("KOSPI", "KOSDAQ"):
                commands.append(
                    _run_command(
                        ["python3", "multi_agent/tools/report_kr_walkforward_release_gate.py", "--market", _market],
                        PROJECT_ROOT,
                    )
                )
            if run_kis_touch5_full_matrix:
                commands.append(
                    _run_command(
                        ["python3", "multi_agent/tools/report_kis_touch5_slice_ablation.py", "--full-matrix"],
                        PROJECT_ROOT,
                    )
                )
            action = "dataset_refresh"
            reason = "nightly_learning_dataset_refreshed"
        report = {
            "mode": mode,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "reason": reason,
            "total_resolved": total_resolved,
            "new_resolved_since_last_cycle": new_resolved,
            "dropped_resolved_since_last_cycle": int(measured["dropped_resolved"]),
            "new_resolved_measurement_basis": measured["basis"],
            "minimum_required_new_resolved": min_needed,
            "counter_rebaselined_from": rebaselined_from,
            "resolved_by_market": resolved["resolved_by_market"],
            "resolved_by_bucket": resolved["resolved_by_bucket"],
            "collection_stats": collect_stats,
            "state_load_error": state_load_error,
            "kis_touch5_full_matrix_requested": bool(run_kis_touch5_full_matrix),
            "commands": commands,
        }
        state["last_nightly_run_at"] = report["generated_at"]
        if action != "skip":
            _adopt_baseline(state, "last_nightly_resolved_total", total_resolved, resolved_keys)
        report["consecutive_skip_cycles"] = _bump_skip_streak(state, "nightly", action)
    else:
        measured = _measure_new_resolved(state, "last_weekly_resolved_total", total_resolved, resolved_keys)
        new_resolved = int(measured["new_resolved"])
        rebaselined_from = measured["rebaselined_from"]
        commands = []
        if total_resolved < int(weekly_min_total_resolved):
            action = "skip"
            reason = "insufficient_total_resolved"
        elif new_resolved < int(weekly_min_new_resolved):
            action = "skip"
            reason = "insufficient_new_resolved"
        else:
            commands.append(
                _run_command(
                    ["python3", "multi_agent/tools/export_scan_archive_learning_dataset.py"],
                    PROJECT_ROOT,
                )
            )
            # 2026-07-19 운영자 승인 정리: phase25 모델 재학습 중지 (AUC~0.5 랜덤 판정, 신웹 미소비).
            # 데이터셋 export(위)는 유지 — 수집 파이프라인은 계속. 복원: AG_PHASE25_RETRAIN=1.
            if os.getenv("AG_PHASE25_RETRAIN", "0").strip() in ("1", "true", "True"):
                commands.append(_run_command(["python3", "retrain_ml.py"], PROJECT_ROOT))
                action = "weekly_retrain"
            else:
                action = "weekly_dataset_only"
            retrain_cmd = next((cmd for cmd in commands if str((cmd.get("cmd") or [""])[-1]).endswith("retrain_ml.py")), {})
            if all(cmd.get("ok") for cmd in commands):
                reason = (
                    "weekly_retrain_deferred_not_failed"
                    if retrain_cmd.get("semantic_status") == "deferred_not_failed"
                    else "weekly_retrain_executed"
                )
            else:
                reason = "weekly_retrain_failed"
        report = {
            "mode": mode,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "reason": reason,
            "total_resolved": total_resolved,
            "new_resolved_since_last_cycle": new_resolved,
            "dropped_resolved_since_last_cycle": int(measured["dropped_resolved"]),
            "new_resolved_measurement_basis": measured["basis"],
            "minimum_required_total_resolved": int(weekly_min_total_resolved),
            "minimum_required_new_resolved": int(weekly_min_new_resolved),
            "counter_rebaselined_from": rebaselined_from,
            "resolved_by_market": resolved["resolved_by_market"],
            "resolved_by_bucket": resolved["resolved_by_bucket"],
            "collection_stats": collect_stats,
            "state_load_error": state_load_error,
            "commands": commands,
        }
        state["last_weekly_run_at"] = report["generated_at"]
        commands_ok = bool(commands) and all(cmd.get("ok") for cmd in commands)
        # 기준선 전진 조건에서 `action == "weekly_retrain"`을 뺀다.
        # 2026-07-19 운영자 결정으로 AG_PHASE25_RETRAIN=0이 기본이라 action은 항상
        # `weekly_dataset_only`이고, 그래서 기준선이 **영원히** 전진하지 않았다.
        # 그 결과 `new_resolved_since_last_cycle`이 "직전 주기 이후"가 아니라
        # "마지막 성공 재학습 이후"를 뜻하는 거짓 라벨이 됐고(무한 증가),
        # `weekly_min_new_resolved` 게이트도 첫 통과 이후 영구 무력화됐다.
        # 표본을 어디까지 소화했는가(기준선)와 모델을 언제 학습했는가(train_at)는 서로 다른 사실이다.
        if action != "skip" and commands_ok:
            _adopt_baseline(state, "last_weekly_resolved_total", total_resolved, resolved_keys)
        if (
            action == "weekly_retrain"
            and commands_ok
            and retrain_cmd.get("semantic_status") != "deferred_not_failed"
        ):
            state["last_weekly_train_at"] = report["generated_at"]
        report["consecutive_skip_cycles"] = _bump_skip_streak(state, "weekly", action)

    report_json = report_dir / f"learning_cycle_{mode}.json"
    report_md = report_dir / f"learning_cycle_{mode}.md"
    _write_json(report_json, report)
    _write_text(report_md, _render_report(report))
    _write_json(state_path, state)
    report["report_paths"] = {"json_path": str(report_json), "md_path": str(report_md), "state_path": str(state_path)}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run nightly learning refresh or weekly retraining with safety gates.")
    parser.add_argument("--mode", choices=["nightly", "weekly"], required=True)
    parser.add_argument("--shared-dir", default="runtime_state/shared_working")
    parser.add_argument("--report-dir", default="runtime_state/reports/learning")
    parser.add_argument("--state-path", default="runtime_state/long_term/learning/training_state.json")
    parser.add_argument("--nightly-min-new-resolved", type=int, default=20)
    parser.add_argument("--weekly-min-total-resolved", type=int, default=50)
    parser.add_argument("--weekly-min-new-resolved", type=int, default=10)
    parser.add_argument(
        "--run-kis-touch5-full-matrix",
        action="store_true",
        help="Run the full KIS touch5 period x feature ablation matrix during nightly refresh.",
    )
    args = parser.parse_args()

    report = run_learning_cycle(
        mode=str(args.mode),
        shared_dir=Path(args.shared_dir),
        report_dir=Path(args.report_dir),
        state_path=Path(args.state_path),
        nightly_min_new_resolved=int(args.nightly_min_new_resolved),
        weekly_min_total_resolved=int(args.weekly_min_total_resolved),
        weekly_min_new_resolved=int(args.weekly_min_new_resolved),
        run_kis_touch5_full_matrix=bool(args.run_kis_touch5_full_matrix),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
