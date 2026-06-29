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
