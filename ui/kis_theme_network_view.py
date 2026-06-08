from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.kis_theme_valuechain import (
    VALUECHAIN_CONFIDENCE_FLOOR,
    build_kis_theme_valuechain_payload,
    load_kis_theme_valuechain_payload,
)
from modules.scan_artifact_archive import load_local_scan_archive_rows
from ui.view_chrome import render_section_intro, render_status_banner


NODE_COLORS = {
    "theme": "#2970ff",
    "ticker": "#17b26a",
    "sector": "#f79009",
    "style": "#7a5af8",
    "event": "#f04438",
}

EDGE_COLORS = {
    "verified_valuechain": "#111827",
    "theme_membership": "#2970ff",
    "kis_category_membership": "#f79009",
    "kis_style_membership": "#7a5af8",
    "kis_news_event": "#f04438",
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except Exception:
        return default
    if math.isnan(numeric) or math.isinf(numeric):
        return default
    return numeric


def _node_layout(nodes: List[Mapping[str, Any]]) -> Dict[str, Tuple[float, float]]:
    groups: Dict[str, List[Mapping[str, Any]]] = {}
    for node in nodes:
        groups.setdefault(str(node.get("type") or "unknown"), []).append(node)
    order = ["theme", "sector", "style", "event", "ticker", "unknown"]
    positions: Dict[str, Tuple[float, float]] = {}
    for col_idx, node_type in enumerate(order):
        group = groups.get(node_type) or []
        if not group:
            continue
        count = len(group)
        x = float(col_idx)
        for idx, node in enumerate(sorted(group, key=lambda row: str(row.get("label") or ""))):
            y = 0.0 if count == 1 else (idx - (count - 1) / 2.0) / max(1.0, count / 5.0)
            positions[str(node.get("id"))] = (x, y)
    return positions


def build_kis_theme_network_plot_payload(
    payload: Mapping[str, Any],
    *,
    include_context_edges: bool = True,
    confidence_floor: float = VALUECHAIN_CONFIDENCE_FLOOR,
) -> Dict[str, Any]:
    nodes = [dict(row) for row in (payload.get("nodes") or []) if isinstance(row, Mapping)]
    node_ids = {str(row.get("id") or "") for row in nodes}
    edges: List[Dict[str, Any]] = []
    for row in payload.get("edges") or []:
        if not isinstance(row, Mapping):
            continue
        edge = dict(row)
        edge_kind = str(edge.get("edge_kind") or "")
        confidence = _safe_float(edge.get("confidence"))
        if edge_kind == "verified_valuechain":
            if confidence < float(confidence_floor):
                continue
        elif not include_context_edges:
            continue
        if str(edge.get("source") or "") not in node_ids or str(edge.get("target") or "") not in node_ids:
            continue
        edges.append(edge)

    connected = {str(edge.get("source")) for edge in edges} | {str(edge.get("target")) for edge in edges}
    filtered_nodes = [node for node in nodes if str(node.get("id") or "") in connected or not edges]
    positions = _node_layout(filtered_nodes)
    return {
        "nodes": filtered_nodes,
        "edges": edges,
        "positions": positions,
        "summary": {
            "nodes": len(filtered_nodes),
            "edges": len(edges),
            "verified_valuechain_edges": sum(1 for edge in edges if edge.get("edge_kind") == "verified_valuechain"),
            "context_edges": sum(1 for edge in edges if edge.get("edge_kind") != "verified_valuechain"),
            "confidence_floor": float(confidence_floor),
        },
    }


def build_kis_theme_network_figure(plot_payload: Mapping[str, Any]) -> go.Figure:
    nodes = [dict(row) for row in (plot_payload.get("nodes") or []) if isinstance(row, Mapping)]
    edges = [dict(row) for row in (plot_payload.get("edges") or []) if isinstance(row, Mapping)]
    positions = plot_payload.get("positions") if isinstance(plot_payload.get("positions"), Mapping) else {}
    fig = go.Figure()

    for edge in edges:
        source_pos = positions.get(str(edge.get("source") or ""))
        target_pos = positions.get(str(edge.get("target") or ""))
        if not source_pos or not target_pos:
            continue
        edge_kind = str(edge.get("edge_kind") or "")
        width = 1.2 + min(5.0, _safe_float(edge.get("weight"), 1.0))
        fig.add_trace(
            go.Scatter(
                x=[source_pos[0], target_pos[0]],
                y=[source_pos[1], target_pos[1]],
                mode="lines",
                line=dict(color=EDGE_COLORS.get(edge_kind, "#98a2b3"), width=width),
                hoverinfo="text",
                text=(
                    f"{edge_kind}<br>{edge.get('relationship') or ''}"
                    f"<br>confidence {_safe_float(edge.get('confidence')):.2f}"
                ),
                showlegend=False,
            )
        )

    by_type: Dict[str, List[Mapping[str, Any]]] = {}
    for node in nodes:
        by_type.setdefault(str(node.get("type") or "unknown"), []).append(node)
    for node_type, group in by_type.items():
        x_values: List[float] = []
        y_values: List[float] = []
        labels: List[str] = []
        sizes: List[float] = []
        hover: List[str] = []
        for node in group:
            pos = positions.get(str(node.get("id") or ""))
            if not pos:
                continue
            x_values.append(pos[0])
            y_values.append(pos[1])
            labels.append(str(node.get("label") or ""))
            sizes.append(16.0 + min(24.0, _safe_float(node.get("weight"), 1.0) * 2.5))
            hover.append(
                f"{node.get('label') or ''}<br>type {node_type}"
                f"<br>weight {_safe_float(node.get('weight'), 0.0):.2f}"
                + (f"<br>theme {node.get('theme')}" if node.get("theme") else "")
                + (f"<br>sector {node.get('sector')}" if node.get("sector") else "")
            )
        if not x_values:
            continue
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="markers+text",
                text=labels,
                textposition="top center",
                marker=dict(size=sizes, color=NODE_COLORS.get(node_type, "#667085"), line=dict(width=1, color="#ffffff")),
                name=node_type,
                hovertext=hover,
                hoverinfo="text",
            )
        )

    fig.update_layout(
        height=640,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )
    return fig


def _timeline_frame(payload: Mapping[str, Any]) -> pd.DataFrame:
    rows = [dict(row) for row in (payload.get("theme_daily_state") or []) if isinstance(row, Mapping)]
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    keep = [
        "trade_date",
        "market",
        "theme_name",
        "symbol_count",
        "avg_day_return_pct",
        "positive_return_ratio",
        "total_value_traded",
        "news_count",
        "vi_triggered_count",
        "avg_kis_evidence_strength_score",
    ]
    return frame[[col for col in keep if col in frame.columns]].sort_values(["trade_date", "theme_name"])


def _load_or_build_payload(market: str) -> Dict[str, Any]:
    payload = load_kis_theme_valuechain_payload(market)
    if payload:
        return payload
    rows = load_local_scan_archive_rows(limit_runs=120)
    if not rows:
        return {}
    return build_kis_theme_valuechain_payload(rows, market=market)


def render_kis_theme_network_page() -> None:
    render_section_intro(
        "KIS Network",
        "KIS 테마 밸류체인 맵",
        "KIS 카테고리·뉴스·수급을 축적해 일별 테마 구조와 검증된 밸류체인 연결을 시각화합니다.",
        ["95% verified edges", "Timeline", "No dummy data"],
    )
    control_cols = st.columns([2, 2, 2])
    market = control_cols[0].selectbox("시장", ["KR", "KOSPI", "KOSDAQ"], key="kis_theme_network_market")
    include_context = control_cols[1].checkbox("컨텍스트 edge 포함", value=True, key="kis_theme_network_context")
    confidence_floor = control_cols[2].slider(
        "밸류체인 최소 신뢰도",
        min_value=0.8,
        max_value=1.0,
        value=float(VALUECHAIN_CONFIDENCE_FLOOR),
        step=0.01,
        key="kis_theme_network_confidence_floor",
    )
    payload = _load_or_build_payload(market)
    if not payload:
        st.info("아직 KIS 테마 네트워크를 만들 수 있는 스캔/sidecar 데이터가 없습니다.")
        return

    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    metric_cols = st.columns(5)
    metric_cols[0].metric("티커 카테고리", int(summary.get("ticker_category_records") or 0))
    metric_cols[1].metric("노드", int(summary.get("nodes") or 0))
    metric_cols[2].metric("전체 edge", int(summary.get("edges") or 0))
    metric_cols[3].metric("검증 밸류체인", int(summary.get("verified_valuechain_edges") or 0))
    metric_cols[4].metric("차단 edge", int(summary.get("blocked_valuechain_edges") or 0))

    if summary.get("verified_valuechain_edges", 0) == 0:
        render_status_banner(
            "검증 밸류체인 edge 없음",
            "95% 이상 공식 근거가 들어온 edge만 밸류체인으로 표시합니다. 현재는 KIS 카테고리/테마/뉴스 컨텍스트만 표시됩니다.",
            tone="caution",
            caption="뉴스 단독, 추정, 동시상승 edge는 production value-chain으로 승격되지 않습니다.",
        )

    plot_payload = build_kis_theme_network_plot_payload(
        payload,
        include_context_edges=bool(include_context),
        confidence_floor=float(confidence_floor),
    )
    st.plotly_chart(build_kis_theme_network_figure(plot_payload), use_container_width=True)

    timeline = _timeline_frame(payload)
    st.markdown("### 일별 테마 타임라인")
    if timeline.empty:
        st.caption("표시할 테마 타임라인이 없습니다.")
    else:
        st.dataframe(timeline, use_container_width=True, hide_index=True)

    blocked = [dict(row) for row in (payload.get("blocked_valuechain_edges") or []) if isinstance(row, Mapping)]
    if blocked:
        with st.expander("차단된 밸류체인 후보", expanded=False):
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "from": row.get("from_symbol"),
                            "to": row.get("to_symbol"),
                            "relationship": row.get("relationship"),
                            "confidence": row.get("confidence"),
                            "source_type": row.get("source_type"),
                            "blocked_reasons": ", ".join(row.get("blocked_reasons") or []),
                        }
                        for row in blocked
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )


__all__ = [
    "build_kis_theme_network_figure",
    "build_kis_theme_network_plot_payload",
    "render_kis_theme_network_page",
]
