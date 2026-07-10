import { useEffect, useMemo, useState } from "react";
import { api, TimingPick } from "../api";
import { useIsMobile } from "../useIsMobile";
import { C, fmt } from "../theme";
import { MarketBadge } from "../components/ui";
import { Chart } from "../components/Chart";

// 매수 타이밍 — "지금 가격에 사도 되나"를 계약 오버레이(기준가/목표가/잔여세션)로 답한다.
// 신호등: GREEN 기준가권 / YELLOW 여력 절반 / RED 추격 비추천 / DONE 터치완료 / EXPIRED 만기.
const STATE_META: Record<string, { color: string; icon: string }> = {
  GREEN: { color: "#22c55e", icon: "🟢" },
  YELLOW: { color: "#eab308", icon: "🟡" },
  RED: { color: "#ef4444", icon: "🔴" },
  DONE: { color: "#94a3b8", icon: "✅" },
  EXPIRED: { color: "#64748b", icon: "⏳" },
  UNKNOWN: { color: "#64748b", icon: "·" },
};

export function Timing() {
  const isMobile = useIsMobile();
  const [picks, setPicks] = useState<TimingPick[]>([]);
  const [asof, setAsof] = useState("");
  const [dateSel, setDateSel] = useState("");
  const [laneSel, setLaneSel] = useState("");
  const [sel, setSel] = useState<TimingPick | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.buyTiming(5).then((d) => {
      setPicks(d.picks); setAsof(d.asof); setLoading(false);
      const first = d.picks.find((p) => p.state === "GREEN" || p.state === "YELLOW") || d.picks[0];
      if (first) { setSel(first); setDateSel(first.scan_date); }
    }).catch(() => setLoading(false));
  }, []);

  const dates = useMemo(() => Array.from(new Set(picks.map((p) => p.scan_date))).sort().reverse(), [picks]);
  const lanes = useMemo(() => Array.from(new Set(picks.map((p) => p.lane_label))), [picks]);
  const shown = picks.filter((p) => (!dateSel || p.scan_date === dateSel) && (!laneSel || p.lane_label === laneSel));

  if (loading) return <div style={{ color: C.mut, padding: 40, textAlign: "center" }}>계약 대비 시세 계산 중…</div>;
  if (!picks.length) return <div style={{ color: C.mut, padding: 40, textAlign: "center" }}>최근 5거래일 발행 픽이 없습니다.</div>;

  return (
    <div>
      {/* 차트 + 선택 픽 판단 */}
      {sel && (
        <div style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 14, padding: 14, marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
            <b style={{ fontSize: 16 }}>{sel.name}</b>
            <span style={{ color: C.mut, fontSize: 12 }}>{sel.code}</span>
            <MarketBadge market={sel.ticker.endsWith(".KQ") ? "KOSDAQ" : "KOSPI"} />
            <span style={{ fontSize: 12, color: C.mut }}>{sel.badge} {sel.lane_label} · {sel.scan_date} 발행 (D+{sel.age})</span>
            <span style={{ marginLeft: "auto", fontWeight: 700, color: STATE_META[sel.state]?.color }}>
              {STATE_META[sel.state]?.icon} {sel.state_label}
            </span>
          </div>
          <Chart code={sel.code} height={isMobile ? 220 : 300}
            lines={[
              { price: sel.ref, label: `기준가 ${fmt(sel.ref)}`, color: "#818cf8" },
              { price: sel.target, label: `목표 +${sel.tp_pct}% ${fmt(sel.target)}`, color: "#22c55e" },
            ]} />
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginTop: 8, fontSize: 13 }}>
            <span>현재 <b>{sel.current != null ? fmt(sel.current) : "-"}</b>{sel.pos_vs_ref != null && <span style={{ color: STATE_META[sel.state]?.color }}> (기준가 {sel.pos_vs_ref >= 0 ? "+" : ""}{sel.pos_vs_ref}%)</span>}</span>
            {sel.headroom != null && <span>목표까지 <b>{sel.headroom >= 0 ? "+" : ""}{sel.headroom}%</b></span>}
            <span>잔여 <b>{sel.sessions_left}</b>세션</span>
            <span style={{ color: C.mut }}>{sel.entry_note} · 미터치 시 5일 종가청산 · 손절 없음 · 비중 2%</span>
          </div>
        </div>
      )}

      {/* 필터: 날짜(최근 5거래일) × 레인 */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
        <button onClick={() => setDateSel("")} style={chip(dateSel === "")}>전체일</button>
        {dates.map((d) => <button key={d} onClick={() => setDateSel(d)} style={chip(dateSel === d)}>{d.slice(5)}</button>)}
        <span style={{ width: 8 }} />
        <button onClick={() => setLaneSel("")} style={chip(laneSel === "")}>전레인</button>
        {lanes.map((l) => <button key={l} onClick={() => setLaneSel(l)} style={chip(laneSel === l)}>{l}</button>)}
        <span style={{ marginLeft: "auto", color: C.mut, fontSize: 11, alignSelf: "center" }}>{asof} 기준</span>
      </div>

      {/* 픽 리스트 (신호등) */}
      <div style={{ display: "grid", gap: 8 }}>
        {shown.map((p) => (
          <div key={p.code + p.scan_date + p.lane} onClick={() => setSel(p)}
            style={{ display: "flex", alignItems: "center", gap: 10, background: sel?.code === p.code && sel?.scan_date === p.scan_date ? C.surface2 : C.surface, border: `1px solid ${sel?.code === p.code && sel?.scan_date === p.scan_date ? C.accent : C.line}`, borderRadius: 12, padding: "10px 14px", cursor: "pointer", flexWrap: "wrap" }}>
            <span style={{ fontSize: 16 }}>{STATE_META[p.state]?.icon}</span>
            <b style={{ fontSize: 14 }}>{p.name}</b>
            <span style={{ fontSize: 11, color: C.mut }}>{p.badge} {p.lane_label} · {p.scan_date.slice(5)} D+{p.age}</span>
            <span style={{ marginLeft: "auto", fontSize: 12, color: STATE_META[p.state]?.color, fontWeight: 600 }}>{p.state_label}</span>
            <span style={{ fontSize: 12, color: C.mut }}>
              {p.current != null ? fmt(p.current) : "-"}{p.headroom != null && p.state !== "DONE" && p.state !== "EXPIRED" ? ` · 여력 ${p.headroom >= 0 ? "+" : ""}${p.headroom}%` : ""} · 잔여{p.sessions_left}
            </span>
          </div>
        ))}
        {shown.length === 0 && <div style={{ color: C.mut, padding: 20, textAlign: "center" }}>조건에 맞는 픽 없음</div>}
      </div>
    </div>
  );
}

const chip = (on: boolean): React.CSSProperties => ({
  background: on ? C.surface2 : "transparent", color: on ? C.text : C.mut,
  border: `1px solid ${on ? C.accent : C.line}`, borderRadius: 999, padding: "5px 12px", fontSize: 12, cursor: "pointer",
});
