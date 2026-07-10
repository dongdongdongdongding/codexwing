import { useEffect, useMemo, useState } from "react";
import { api, TimingPick } from "../api";
import { useIsMobile } from "../useIsMobile";
import { C, fmt } from "../theme";
import { MarketBadge } from "../components/ui";
import { Chart } from "../components/Chart";

// 매수 타이밍 — ant.wiki 사분면 맵을 우리 계약 의미론으로 번안:
//   X축 = 목표까지 여력(%) · Y축 = 잔여 세션 · 크기 = 적중확률 · 색 = 신호등
//   사분면: 매수적기(여력+시간) / 마지막 기회(여력, 만기임박) / 관망(소진) / 종료권
// 차트(계약 오버레이)는 버블/리스트 클릭 시 상세로만 표시.
const SM: Record<string, { color: string; icon: string }> = {
  GREEN: { color: "#22c55e", icon: "🟢" },
  YELLOW: { color: "#eab308", icon: "🟡" },
  RED: { color: "#ef4444", icon: "🔴" },
  DONE: { color: "#64748b", icon: "✅" },
  EXPIRED: { color: "#475569", icon: "⏳" },
  UNKNOWN: { color: "#64748b", icon: "·" },
};

function BubbleMap({ picks, sel, onSel, isMobile }: { picks: TimingPick[]; sel: TimingPick | null; onSel: (p: TimingPick) => void; isMobile: boolean }) {
  const W = 900, H = 360, PAD = { l: 46, r: 16, t: 26, b: 34 };
  const xs = picks.map((p) => p.headroom ?? 0);
  const xMin = Math.min(-6, ...xs) - 1, xMax = Math.max(8, ...xs) + 1;
  const X = (v: number) => PAD.l + ((v - xMin) / (xMax - xMin)) * (W - PAD.l - PAD.r);
  const Y = (v: number) => PAD.t + ((5.5 - v) / 6) * (H - PAD.t - PAD.b);
  const x0 = X(0), yMid = Y(2.5);
  // 같은 잔여세션(정수) 버블 겹침 방지: 인덱스 기반 미세 오프셋
  const seen: Record<string, number> = {};
  const jit = (p: TimingPick) => {
    const k = `${p.sessions_left}:${Math.round((p.headroom ?? 0) * 2)}`;
    seen[k] = (seen[k] || 0) + 1;
    return (seen[k] - 1) * 0.22 * (seen[k] % 2 ? 1 : -1);
  };
  return (
    <div style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 14, padding: "8px 4px 0", marginBottom: 12, overflow: "hidden" }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", display: "block" }}>
        {/* 사분면 배경 */}
        <rect x={x0} y={PAD.t} width={W - PAD.r - x0} height={yMid - PAD.t} fill="#22c55e08" />
        <rect x={x0} y={yMid} width={W - PAD.r - x0} height={H - PAD.b - yMid} fill="#eab30808" />
        <rect x={PAD.l} y={PAD.t} width={x0 - PAD.l} height={H - PAD.t - PAD.b} fill="#64748b0a" />
        {/* 축/구분선 */}
        <line x1={x0} y1={PAD.t} x2={x0} y2={H - PAD.b} stroke={C.line} strokeDasharray="4 3" />
        <line x1={PAD.l} y1={yMid} x2={W - PAD.r} y2={yMid} stroke={C.line} strokeDasharray="4 3" />
        {/* 사분면 라벨 */}
        <text x={W - PAD.r - 8} y={PAD.t + 16} textAnchor="end" fill="#22c55e" fontSize="13" fontWeight="700">매수적기</text>
        <text x={W - PAD.r - 8} y={PAD.t + 30} textAnchor="end" fill={C.mut} fontSize="10">여력·시간 충분</text>
        <text x={W - PAD.r - 8} y={H - PAD.b - 20} textAnchor="end" fill="#eab308" fontSize="13" fontWeight="700">마지막 기회</text>
        <text x={W - PAD.r - 8} y={H - PAD.b - 6} textAnchor="end" fill={C.mut} fontSize="10">여력 있으나 만기 임박</text>
        <text x={PAD.l + 8} y={PAD.t + 16} fill="#94a3b8" fontSize="13" fontWeight="700">관망</text>
        <text x={PAD.l + 8} y={PAD.t + 30} fill={C.mut} fontSize="10">여력 소진 · 추격 금지</text>
        <text x={PAD.l + 8} y={H - PAD.b - 6} fill={C.mut} fontSize="11">종료권 (터치완료·만기)</text>
        {/* 축 라벨 */}
        <text x={(PAD.l + W - PAD.r) / 2} y={H - 6} textAnchor="middle" fill={C.mut} fontSize="11">← 여력 소진 · 목표까지 남은 수익률(%) · 여력 큼 →</text>
        <text x={12} y={(PAD.t + H - PAD.b) / 2} fill={C.mut} fontSize="11" transform={`rotate(-90 12 ${(PAD.t + H - PAD.b) / 2})`} textAnchor="middle">잔여 세션</text>
        {[0, 5].map((v) => <text key={v} x={PAD.l - 8} y={Y(v) + 4} textAnchor="end" fill={C.mut} fontSize="10">{v}</text>)}
        {/* 버블 */}
        {picks.map((p, i) => {
          const hx = p.headroom ?? 0;
          const dead = p.state === "DONE" || p.state === "EXPIRED";
          const r = Math.max(9, Math.min(22, ((p.prob ?? 0.6) as number) * (p.prob && p.prob > 1.5 ? 0.22 : 22)));
          const cx = X(Math.max(xMin, Math.min(xMax, hx)));
          const cy = Y(Math.max(0, Math.min(5, p.sessions_left + jit(p))));
          const on = sel && sel.code === p.code && sel.scan_date === p.scan_date;
          return (
            <g key={p.code + p.scan_date + i} onClick={() => onSel(p)} style={{ cursor: "pointer" }} opacity={dead ? 0.35 : 1}>
              <circle cx={cx} cy={cy} r={r} fill={`${SM[p.state]?.color}55`} stroke={on ? C.accent : SM[p.state]?.color} strokeWidth={on ? 2.5 : 1.2} />
              <text x={cx} y={cy - r - 4} textAnchor="middle" fill={on ? C.text : C.mut} fontSize={isMobile ? 10 : 11} fontWeight={on ? 700 : 500}>{p.name}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function Timing() {
  const isMobile = useIsMobile();
  const [picks, setPicks] = useState<TimingPick[]>([]);
  const [asof, setAsof] = useState("");
  const [dateSel, setDateSel] = useState("");
  const [laneSel, setLaneSel] = useState("");
  const [sel, setSel] = useState<TimingPick | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.buyTiming(5).then((d) => { setPicks(d.picks); setAsof(d.asof); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const dates = useMemo(() => Array.from(new Set(picks.map((p) => p.scan_date))).sort().reverse(), [picks]);
  const lanes = useMemo(() => Array.from(new Set(picks.map((p) => p.lane_label))), [picks]);
  const shown = picks.filter((p) => (!dateSel || p.scan_date === dateSel) && (!laneSel || p.lane_label === laneSel));

  if (loading) return <div style={{ color: C.mut, padding: 40, textAlign: "center" }}>계약 대비 시세 계산 중…</div>;
  if (!picks.length) return <div style={{ color: C.mut, padding: 40, textAlign: "center" }}>최근 5거래일 발행 픽이 없습니다.</div>;

  return (
    <div>
      {/* 필터 */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
        <button onClick={() => setDateSel("")} style={chip(dateSel === "")}>전체일</button>
        {dates.map((d) => <button key={d} onClick={() => setDateSel(d)} style={chip(dateSel === d)}>{d.slice(5)}</button>)}
        <span style={{ width: 8 }} />
        <button onClick={() => setLaneSel("")} style={chip(laneSel === "")}>전레인</button>
        {lanes.map((l) => <button key={l} onClick={() => setLaneSel(l)} style={chip(laneSel === l)}>{l}</button>)}
        <span style={{ marginLeft: "auto", color: C.mut, fontSize: 11, alignSelf: "center" }}>{asof} 기준 · 버블크기=적중확률</span>
      </div>

      {/* 사분면 버블 맵 */}
      <BubbleMap picks={shown} sel={sel} onSel={setSel} isMobile={isMobile} />

      {/* 상세 (클릭 시에만): 차트 + 계약 오버레이 */}
      {sel && (
        <div style={{ background: C.surface, border: `1px solid ${C.accent}`, borderRadius: 14, padding: 14, marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
            <b style={{ fontSize: 16 }}>{sel.name}</b>
            <span style={{ color: C.mut, fontSize: 12 }}>{sel.code}</span>
            <MarketBadge market={sel.ticker.endsWith(".KQ") ? "KOSDAQ" : "KOSPI"} />
            <span style={{ fontSize: 12, color: C.mut }}>{sel.badge} {sel.lane_label} · {sel.scan_date} 발행 (D+{sel.age})</span>
            <span style={{ marginLeft: "auto", fontWeight: 700, color: SM[sel.state]?.color }}>{SM[sel.state]?.icon} {sel.state_label}</span>
            <button onClick={() => setSel(null)} style={{ background: "transparent", border: "none", color: C.mut, cursor: "pointer", fontSize: 16 }}>✕</button>
          </div>
          <Chart code={sel.code} height={isMobile ? 220 : 300}
            lines={[
              { price: sel.ref, label: `기준가 ${fmt(sel.ref)}`, color: "#818cf8" },
              { price: sel.target, label: `목표 +${sel.tp_pct}% ${fmt(sel.target)}`, color: "#22c55e" },
            ]} />
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginTop: 8, fontSize: 13 }}>
            <span>현재 <b>{sel.current != null ? fmt(sel.current) : "-"}</b>{sel.pos_vs_ref != null && <span style={{ color: SM[sel.state]?.color }}> (기준가 {sel.pos_vs_ref >= 0 ? "+" : ""}{sel.pos_vs_ref}%)</span>}</span>
            {sel.headroom != null && <span>목표까지 <b>{sel.headroom >= 0 ? "+" : ""}{sel.headroom}%</b></span>}
            <span>잔여 <b>{sel.sessions_left}</b>세션</span>
            <span style={{ color: C.mut }}>{sel.entry_note} · 미터치 시 5일 종가청산 · 손절 없음 · 비중 2%</span>
          </div>
        </div>
      )}

      {/* 리스트 (맵과 연동) */}
      <div style={{ display: "grid", gap: 8 }}>
        {shown.map((p) => (
          <div key={p.code + p.scan_date + p.lane} onClick={() => setSel(p)}
            style={{ display: "flex", alignItems: "center", gap: 10, background: sel?.code === p.code && sel?.scan_date === p.scan_date ? C.surface2 : C.surface, border: `1px solid ${sel?.code === p.code && sel?.scan_date === p.scan_date ? C.accent : C.line}`, borderRadius: 12, padding: "10px 14px", cursor: "pointer", flexWrap: "wrap" }}>
            <span style={{ fontSize: 16 }}>{SM[p.state]?.icon}</span>
            <b style={{ fontSize: 14 }}>{p.name}</b>
            <span style={{ fontSize: 11, color: C.mut }}>{p.badge} {p.lane_label} · {p.scan_date.slice(5)} D+{p.age}</span>
            <span style={{ marginLeft: "auto", fontSize: 12, color: SM[p.state]?.color, fontWeight: 600 }}>{p.state_label}</span>
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
