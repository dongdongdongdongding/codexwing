import { useState } from "react";
import { C, RADIUS } from "../theme";
import { TERMS } from "../terms";

// ⓘ 용어 툴팁 — 어려운 한국어 개념 설명 (기획 R3)
export function Term({ k, children }: { k: string; children?: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const desc = TERMS[k];
  return (
    <span style={{ position: "relative", whiteSpace: "nowrap" }}>
      {children ?? k}
      {desc && (
        <span
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
          style={{ marginLeft: 3, cursor: "help", color: C.mut, fontSize: 11, borderBottom: `1px dotted ${C.mut}` }}
        >
          ⓘ
          {open && (
            <span style={{
              position: "absolute", left: 0, top: "1.6em", zIndex: 50, width: 240,
              background: C.surface2, border: `1px solid ${C.line}`, borderRadius: 8,
              padding: "8px 10px", color: C.text, fontSize: 12, lineHeight: 1.5,
              whiteSpace: "normal", boxShadow: "0 6px 24px rgba(0,0,0,.5)", fontWeight: 400,
            }}>{desc}</span>
          )}
        </span>
      )}
    </span>
  );
}

// 시장 배지 (코스피/코스닥)
export function MarketBadge({ market }: { market?: string }) {
  const m = (market || "").toUpperCase();
  if (m.includes("NASDAQ")) return <span style={pillStyle("#7D5BD6")}>나스닥</span>;
  const isKospi = m.includes("KOSPI") || m === "KS";
  const label = isKospi ? "코스피" : m.includes("KOSDAQ") || m === "KQ" ? "코스닥" : m || "–";
  const col = isKospi ? "#2D7FF9" : "#E08A2B";
  return <span style={pillStyle(col)}>{label}</span>;
}

// 레인/신호 배지
export function LaneBadge({ kind, badge, label }: { kind?: string; badge?: string; label?: string }) {
  const col = kind === "SWING" ? C.laneSwing : kind === "INTRADAY" ? C.laneIntraday : C.laneB;
  return <span style={pillStyle(col)}>{badge} {label}</span>;
}

export function WarnBadge({ children }: { children: React.ReactNode }) {
  return <span style={pillStyle(C.warn)}>{children}</span>;
}

function pillStyle(color: string): React.CSSProperties {
  return {
    display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 600,
    color, background: `${color}1A`, border: `1px solid ${color}44`,
    borderRadius: RADIUS.pill, padding: "1px 8px", whiteSpace: "nowrap",
  };
}

export function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: RADIUS.panel, padding: 16, ...style }}>
      {children}
    </div>
  );
}

/** 픽 상태 칩 — **픽 페이지와 개요가 같은 것을 쓴다.**
 *  페이지마다 사본을 두면 한쪽만 고쳐진다. 실제로 그랬다: 픽 페이지엔 판정을 그렸는데
 *  개요(첫 화면)엔 아무것도 없어서, 사용자가 "적중확률 84.4%"만 보고 있었다 —
 *  그 레인은 forward EV +0.09% 로 폐기선 아래다. */
export function StatusChips({ p }: { p: any }) {
  const f = p.lane_frequency;
  const chip = (c: string, t: any) => (
    <span style={{ fontSize: 11, padding: "2px 7px", borderRadius: 999,
                   border: `1px solid ${c}55`, color: c, background: `${c}12`, whiteSpace: "nowrap" }}>{t}</span>
  );
  return (
    <>
      {/* 체결 가능성이 가장 먼저 온다 — 못 사는 픽은 나머지 정보가 의미 없다. */}
      {p.attainability === "LIMIT_UP" && chip("#ef4444", `⛔ 상한가 ${p.day_change?.toFixed(1)}% · 체결불가`)}
      {p.attainability === "LIMIT_DOWN" && chip("#ef4444", "⛔ 하한가 · 체결불가")}
      {p.attainability === "STALE_REFERENCE" && chip("#f59e0b", "⚠ 진입가=전일종가")}
      {p.is_top1 && chip("#facc15", "⭐ 1순위")}
      {p.rank_in_day != null && !p.is_top1 && chip("#64748b", `${p.rank_in_day}순위`)}
      {p.expired && chip("#ef4444", `⏱ 만료 ${p.stale_days}일`)}
      {p.operator_verdict === "KILL" && chip("#ef4444", `폐기선 EV ${p.forward_ev}%`)}
      {p.operator_verdict === "DEPLOY" && chip("#22c55e", "✅ 즉시적용")}
      {p.operator_verdict === "UNKNOWN" && chip("#f59e0b", "⚠ 근거없음")}
      {f && f.frequency_ok === false && chip("#f59e0b", `발화부족 ${f.median_gap}일간격`)}
      {p.stream_excluded && chip("#ef4444", "⛔ 관측전용")}
    </>
  );
}
