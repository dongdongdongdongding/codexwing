#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_readiness_reports(report_dir: Path = REPORT_DIR) -> Dict[str, Dict[str, Any]]:
    full_candidates: List[Dict[str, Any]] = []
    fallback_full_candidates: List[Dict[str, Any]] = []
    retry_candidates: List[Dict[str, Any]] = []
    for path in sorted(report_dir.glob("kis_kr_universe_readiness_*.json")):
        payload = _read_json(path)
        if not payload:
            continue
        payload["_path"] = str(path)
        requested = payload.get("requested_tickers") if isinstance(payload.get("requested_tickers"), list) else []
        universe = payload.get("universe") if isinstance(payload.get("universe"), dict) else {}
        selected_total = sum(int((meta or {}).get("selected_count") or 0) for meta in universe.values() if isinstance(meta, dict))
        if requested:
            retry_candidates.append(payload)
        elif selected_total > 1000:
            full_candidates.append(payload)
        elif selected_total > 0:
            fallback_full_candidates.append(payload)
    return {
        "full": full_candidates[-1] if full_candidates else (fallback_full_candidates[-1] if fallback_full_candidates else {}),
        "retry": retry_candidates[-1] if retry_candidates else {},
    }


def _summary_for_market(report: Mapping[str, Any], market: str) -> Dict[str, Any]:
    quote_summary = report.get("quote_summary") if isinstance(report.get("quote_summary"), dict) else {}
    market_summary = quote_summary.get(market) if isinstance(quote_summary.get(market), dict) else {}
    missing = (
        market_summary.get("core_field_missing_count")
        if isinstance(market_summary.get("core_field_missing_count"), dict)
        else {}
    )
    total = int(market_summary.get("universe_count") or 0)
    ok = int(market_summary.get("quote_ok_count") or 0)
    errors = int(market_summary.get("quote_error_count") or 0)
    return {
        "universe_count": total,
        "quote_ok_count": ok,
        "quote_error_count": errors,
        "quote_success_rate_pct": float(market_summary.get("quote_success_rate_pct") or 0.0),
        "sector_name_missing_count": int(missing.get("sector_name") or 0),
        "sector_name_missing_rate_pct": round((int(missing.get("sector_name") or 0) / ok * 100.0) if ok else 0.0, 3),
        "failed_tickers_sample": market_summary.get("failed_tickers_sample") or [],
    }


def _endpoint_result_map(report: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    checks = report.get("feature_checks") if isinstance(report.get("feature_checks"), list) else []
    out: Dict[str, Dict[str, Any]] = {}
    for item in checks:
        if isinstance(item, dict) and item.get("name"):
            out[str(item["name"])] = dict(item)
    return out


def _endpoint_rollup(report: Mapping[str, Any]) -> Dict[str, Any]:
    checks = list(_endpoint_result_map(report).values())
    ok = [item for item in checks if item.get("ok")]
    failed = [item for item in checks if not item.get("ok")]
    return {
        "checked_count": len(checks),
        "ok_count": len(ok),
        "failed_count": len(failed),
        "failed": [
            {
                "name": item.get("name"),
                "error_type": item.get("error_type"),
                "error": item.get("error"),
            }
            for item in failed
        ],
    }


def _effective_quote_coverage(full: Mapping[str, Any], retry: Mapping[str, Any]) -> Dict[str, Any]:
    markets: Dict[str, Any] = {}
    for market in ("KOSPI", "KOSDAQ"):
        full_summary = _summary_for_market(full, market)
        retry_summary = _summary_for_market(retry, market)
        recovered = min(full_summary["quote_error_count"], retry_summary["quote_ok_count"])
        effective_ok = min(full_summary["universe_count"], full_summary["quote_ok_count"] + recovered)
        markets[market] = {
            **full_summary,
            "retry_ok_count": retry_summary["quote_ok_count"],
            "retry_error_count": retry_summary["quote_error_count"],
            "recovered_rate_limit_count": recovered,
            "effective_quote_ok_count": effective_ok,
            "effective_quote_success_rate_pct": round(
                (effective_ok / full_summary["universe_count"] * 100.0) if full_summary["universe_count"] else 0.0,
                3,
            ),
        }
    total_universe = sum(item["universe_count"] for item in markets.values())
    total_effective_ok = sum(item["effective_quote_ok_count"] for item in markets.values())
    return {
        "markets": markets,
        "total_universe_count": total_universe,
        "total_effective_quote_ok_count": total_effective_ok,
        "total_effective_quote_success_rate_pct": round(
            (total_effective_ok / total_universe * 100.0) if total_universe else 0.0,
            3,
        ),
    }


def _requirement_matrix() -> List[Dict[str, Any]]:
    return [
        {
            "area": "scanner_price_snapshot",
            "current_need": "current price, day change, OHLC, volume, turnover, market cap, status warning",
            "kis_support": "quote_snapshot",
            "readiness": "ready_with_throttle",
            "decision": "KIS가 이 경로를 지원할 수 있다. 운영 적용 전 초당 제한 대응, 캐시, 재시도 정책이 필요하다.",
        },
        {
            "area": "scanner_daily_ohlcv",
            "current_need": "50+ daily OHLCV rows for alpha/tech/model features",
            "kis_support": "daily_bars",
            "readiness": "adapter_work_needed",
            "decision": "샘플 endpoint는 동작했다. 다만 KIS 응답을 OHLCV DataFrame으로 바꾸는 이력 adapter와 장기간 커버리지 검증이 필요하다.",
        },
        {
            "area": "scanner_intraday_ohlcv",
            "current_need": "same-day and recent intraday bars for live daily refresh and intraday mode",
            "kis_support": "today_minute_bars, daily_minute_bars",
            "readiness": "adapter_work_needed",
            "decision": "당일 분봉 샘플은 성공했다. 운영에는 기간/시간창 adapter와 fallback 정책이 필요하다.",
        },
        {
            "area": "investor_flow",
            "current_need": "foreigner/institution/retail 1d/3d/10d and whale score",
            "kis_support": "stock_investor_daily, foreign_institution_total",
            "readiness": "partial_time_gated",
            "decision": "시장 단위 수급은 동작했다. 종목별 수급은 시간 제한이 있어 15:40 KST 이후 재검증해야 한다.",
        },
        {
            "area": "rank_and_market_microstructure",
            "current_need": "volume rank, fluctuation rank, execution strength, VI status",
            "kis_support": "volume_rank, fluctuation_rank, volume_power_rank, vi_status",
            "readiness": "ready_with_parameter_review",
            "decision": "대부분의 랭킹 endpoint는 동작했다. 다만 KOSDAQ volume_rank는 1행만 반환되어 파라미터 재검토가 필요하다.",
        },
        {
            "area": "top_deep_price_news_flow",
            "current_need": "price tail, news headlines/sentiment, investor flow breakdown",
            "kis_support": "daily_bars, quote_snapshot, news_titles, investor_flow_snapshot",
            "readiness": "partial",
            "decision": "KIS가 가격과 뉴스 제목은 보강할 수 있다. 감성 분석과 시간 제한 수급은 기존 provider 또는 wrapper가 필요하다.",
        },
        {
            "area": "sector_theme_context",
            "current_need": "sector rotation, instrument master, theme membership, theme day strength",
            "kis_support": "quote sector_name, stock_info/financial endpoints",
            "readiness": "not_enough_alone",
            "decision": "KIS quote의 sector_name 커버리지가 부족하다. 기존 테마/종목 마스터 파이프라인은 유지해야 한다.",
        },
        {
            "area": "macro_context",
            "current_need": "KOSPI/KOSDAQ index, USD/KRW, VIX, US rates/global risk",
            "kis_support": "industry_price for KR indices only",
            "readiness": "partial",
            "decision": "KIS는 KR 지수 조회를 보강할 수 있지만 FX/VIX/TNX/글로벌 리스크 컨텍스트는 대체하지 못한다.",
        },
        {
            "area": "model_training_features",
            "current_need": "alpha, tech, ML, volume, flow, theme, rank/outcome aligned features",
            "kis_support": "quote, flow, rank, VI, financial ratio, minute/daily bars",
            "readiness": "promising_not_proven",
            "decision": "KIS 보강 challenger는 유망하지만, 피처를 저장하고 백테스트하기 전까지 더 좋은 모델이라고 증명할 수 없다.",
        },
    ]


def _model_lift_assessment(coverage: Mapping[str, Any], endpoint_rollup: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "verdict": "KIS 보강 모델은 가능성이 있다. 그러나 KIS 단독 즉시 대체와 모델 성능 개선은 아직 증명되지 않았다.",
        "high_value_candidate_features": [
            "quote_snapshot의 거래대금(value_traded)과 시가총액(market_cap)",
            "전일대비 거래량 비율(prev_volume_ratio)과 분봉 기반 실시간 거래량 곡선",
            "종목별 endpoint가 가능한 시간대의 외국인/기관/개인 금액 수급",
            "거래량/등락률/체결강도 랭킹 포함 여부와 순위",
            "VI/status warning 기반 위험 필터",
            "PER/PBR/EPS/BPS 저빈도 스타일/레짐 통제 피처",
        ],
        "why_not_proven_yet": [
            "KIS 피처의 과거 아카이브가 아직 없어 직접적인 OOS 성능 개선을 측정할 수 없다.",
            "실측 당시 종목별 투자자 수급 endpoint가 시간 제한에 걸렸다.",
            "quote_snapshot의 sector_name 커버리지가 부족해 테마 컨텍스트를 대체할 수 없다.",
            "운영 스캐너는 아직 yfinance/PyKrx 형태의 OHLCV DataFrame을 기대한다.",
        ],
        "recommended_validation_sequence": [
            "quote/daily/minute/flow/rank용 비운영 KIS feature snapshot adapter를 만든다.",
            "추천 로직은 바꾸지 않고 기존 scanner row 옆에 KIS 피처를 병렬 저장한다.",
            "KOSPI/KOSDAQ SWING 및 INTRADAY 결과를 최소 2-4주 수집한다.",
            "KIS 피처군을 on/off한 challenger 모델을 학습하고 segment별 Top5 positive rate, 평균 5D 수익률, bad path, stop-first를 비교한다.",
            "현재 운영 release gate를 넘고 tail loss가 악화되지 않을 때만 승격한다.",
        ],
        "coverage_reference": {
            "effective_quote_success_rate_pct": coverage.get("total_effective_quote_success_rate_pct"),
            "endpoint_ok_count": endpoint_rollup.get("ok_count"),
            "endpoint_failed_count": endpoint_rollup.get("failed_count"),
        },
    }


def build_report(report_dir: Path = REPORT_DIR) -> Dict[str, Any]:
    reports = _load_readiness_reports(report_dir)
    full = reports.get("full") or {}
    retry = reports.get("retry") or {}
    coverage = _effective_quote_coverage(full, retry)
    endpoint_rollup = _endpoint_rollup(full)
    matrix = _requirement_matrix()
    blockers = [
        item
        for item in matrix
        if item["readiness"] in {"partial_time_gated", "not_enough_alone", "promising_not_proven", "adapter_work_needed"}
    ]
    return {
        "tool": "report_kis_operational_readiness",
        "source_reports": {
            "full_universe": full.get("_path"),
            "retry_subset": retry.get("_path"),
        },
        "summary": {
            "operational_replacement_verdict": "KR 운영 전체를 지금 KIS로 일괄 전환하면 안 된다. 먼저 KIS를 단계적 보강 데이터 소스로 써야 한다.",
            "smooth_operation_status": "현재가/랭킹/뉴스 제목/KR 지수 경로는 사용 가능하다. OHLCV adapter, 시간 제한 수급, 섹터/테마 결측은 남아 있다.",
            "model_lift_status": "모델 개선 가능성은 있지만 아직 증명되지 않았다. KIS 피처 병렬 아카이브와 challenger 검증이 필요하다.",
        },
        "quote_coverage": coverage,
        "endpoint_rollup": endpoint_rollup,
        "requirement_matrix": matrix,
        "blockers_or_gaps": blockers,
        "model_lift_assessment": _model_lift_assessment(coverage, endpoint_rollup),
    }


def _md_table(rows: Iterable[Mapping[str, Any]]) -> List[str]:
    lines = [
        "| 영역 | KIS 준비도 | 판단 |",
        "|---|---:|---|",
    ]
    for row in rows:
        lines.append(f"| {row.get('area')} | {row.get('readiness')} | {row.get('decision')} |")
    return lines


def render_markdown(report: Mapping[str, Any]) -> str:
    coverage = report.get("quote_coverage") if isinstance(report.get("quote_coverage"), dict) else {}
    markets = coverage.get("markets") if isinstance(coverage.get("markets"), dict) else {}
    endpoint = report.get("endpoint_rollup") if isinstance(report.get("endpoint_rollup"), dict) else {}
    model = report.get("model_lift_assessment") if isinstance(report.get("model_lift_assessment"), dict) else {}
    lines = [
        "# KIS 운영 전환 및 모델 개선 가능성 검증",
        "",
        "## 결론",
        f"- 운영 전환 판단: {report.get('summary', {}).get('operational_replacement_verdict')}",
        f"- 원활한 운영 상태: {report.get('summary', {}).get('smooth_operation_status')}",
        f"- 모델 개선 판단: {report.get('summary', {}).get('model_lift_status')}",
        "",
        "## 실측 근거",
        f"- 전체+재시도 기준 quote 유효 커버리지: {coverage.get('total_effective_quote_ok_count')}/{coverage.get('total_universe_count')} ({coverage.get('total_effective_quote_success_rate_pct')}%)",
    ]
    for market, item in markets.items():
        lines.append(
            f"- {market}: 전체 스윕 {item.get('quote_ok_count')}/{item.get('universe_count')} 성공, "
            f"rate-limit 재시도 회복 {item.get('recovered_rate_limit_count')}건, "
            f"실효 성공률 {item.get('effective_quote_success_rate_pct')}%, "
            f"sector_name 결측 {item.get('sector_name_missing_rate_pct')}%"
        )
    lines.extend(
        [
            f"- 기능 endpoint 체크: {endpoint.get('ok_count')}/{endpoint.get('checked_count')} 성공, 실패 {endpoint.get('failed_count')}건",
            "",
            "## 운영 기능별 판단",
            *_md_table(report.get("requirement_matrix", []) if isinstance(report.get("requirement_matrix"), list) else []),
            "",
            "## 모델 개선 가능성",
            f"- 판정: {model.get('verdict')}",
            "- 유망 KIS 추가 피처:",
        ]
    )
    for item in model.get("high_value_candidate_features", []) or []:
        lines.append(f"  - {item}")
    lines.append("- 아직 증명되지 않은 이유:")
    for item in model.get("why_not_proven_yet", []) or []:
        lines.append(f"  - {item}")
    lines.append("- 권장 검증 순서:")
    for item in model.get("recommended_validation_sequence", []) or []:
        lines.append(f"  - {item}")
    lines.extend(["", "## 실패/제약 endpoint"])
    for item in endpoint.get("failed", []) or []:
        lines.append(f"- {item.get('name')}: {item.get('error')}")
    return "\n".join(lines) + "\n"


def write_report(report: Mapping[str, Any], output_dir: Path = REPORT_DIR) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "kis_operational_readiness.json"
    md_path = output_dir / "kis_operational_readiness.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Report KIS operational readiness and model-lift potential.")
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    report = build_report(args.report_dir)
    paths = write_report(report, args.output_dir)
    print(json.dumps({"paths": paths, "summary": report.get("summary")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
