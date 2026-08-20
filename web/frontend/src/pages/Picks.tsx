import { useEffect, useState } from "react";
import { useIsMobile } from "../useIsMobile";
import { api, Pick, Lane, Price } from "../api";
import { C, fmt, pct, signColor } from "../theme";
import { MarketBadge, LaneBadge, Term, WarnBadge, StatusChips } from "../components/ui";
import { Chart } from "../components/Chart";

export function Picks() {
  const isMobile = useIsMobile();
  const [lanes, setLanes] = useState<Lane[]>([]);
  const [lane, setLane] = useState("");
  const [picks, setPicks] = useState<Pick[]>([]);
  const [prices, setPrices] = useState<Record<string, Price>>({});
  const [sel, setSel] = useState<Pick | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.lanes().then((d) => setLanes(d.lanes)).catch(() => {}); }, []);
  useEffect(() => {
    setLoading(true);
    api.picks(lane).then((d) => { setPicks(d.picks); setLoading(false); loadPrices(d.picks); }).catch(() => setLoading(false));
  }, [lane]);

  const loadPrices = (ps: Pick[]) => {
    const codes = ps.map((p) => p.code);
    if (codes.length) api.prices(codes).then(setPrices).catch(() => {});
  };
  useEffect(() => {
    const t = setInterval(() => loadPrices(picks), 15000);
    return () => clearInterval(t);
  }, [picks]);

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <Tab on={lane === ""} onClick={() => setLane("")}>전체</Tab>
        {lanes.map((l) => <Tab key={l.key} on={lane === l.key} onClick={() => setLane(l.key)}>{l.badge} {l.label}</Tab>)}
      </div>

      {loading ? <Skeleton /> : picks.length === 0 ? (
        <div style={{ color: C.mut, padding: 40, textAlign: "center" }}>
          표시할 픽이 없습니다 — 스캔이 아직 돌지 않았거나 조건을 통과한 종목이 없습니다.
        </div>
      ) : isMobile ? (
        <div style={{ display: "grid", gap: 10 }}>
          {picks.map((p) => {
            const pr = prices[p.code];
            const live = pr?.price ?? p.entry;
            return (
              <div key={p.code + p.lane} onClick={() => setSel(p)}
                style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 14, padding: "12px 14px", cursor: "pointer" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <b style={{ fontSize: 15 }}>{p.name}</b>
                  <span style={{ color: C.mut, fontSize: 11 }}>{p.code}</span>
                  <MarketBadge market={p.market} />
                  <span style={{ marginLeft: "auto", fontVariantNumeric: "tabular-nums", fontWeight: 700, color: pr?.change_pct != null ? signColor(pr.change_pct) : C.text }}>
                    {fmt(live)} {pr?.change_pct != null ? pct(pr.change_pct) : ""}
                  </span>
                </div>
                <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>
                  <LaneBadge kind={p.kind} badge={p.badge} label={p.lane_label} />
                  {p.tier === "PRIMARY" && <Chip color="#22c55e">주력</Chip>}
                  {p.mkt_state === "RISK_OFF" && <Chip color="#f59e0b">약세장</Chip>}
                  {p.size_pct_total != null && <Chip color="#818cf8">비중 {p.size_pct_total}%</Chip>}
                                    <StatusChips p={p} />
                  {p.sector_capitulation === "epicenter" && <Chip color="#22c55e">섹터동반↑</Chip>}
                  {p.sector_capitulation === "resilient" && <Chip color="#f59e0b">비진앙 단독항복</Chip>}
                  {p.tail_warn && <Chip color="#f59e0b">⚠tail</Chip>}
                  <span style={{ marginLeft: "auto", color: C.mut, fontSize: 12 }}>
                    {(p as any).measured_win != null ? `승률 ${(p as any).measured_win}%` : p.prob != null ? `확률 ${p.prob}%` : ""} · 목표 {p.signal_class === "B" ? "α" : fmt(p.target)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", background: C.surface, border: `1px solid ${C.line}`, borderRadius: 12, overflow: "hidden" }}>
          <thead>
            <tr style={{ color: C.mut, fontSize: 12, textAlign: "right" }}>
              <Th style={{ textAlign: "left" }}>#</Th>
              <Th style={{ textAlign: "left" }}>종목</Th>
              <Th>실시간</Th><Th>등락</Th>
              <Th><Term k="진입">진입</Term></Th>
              <Th><Term k="목표">목표</Term></Th>
              <Th><Term k="확률">확률</Term></Th>
              <Th><Term k="알파">알파</Term></Th>
              <Th style={{ textAlign: "left" }}>신호</Th>
            </tr>
          </thead>
          <tbody>
            {picks.map((p, i) => {
              const pr = prices[p.code];
              const live = pr?.price ?? p.entry;
              return (
                <tr key={p.code + p.lane} onClick={() => setSel(p)}
                  style={{ borderTop: `1px solid ${C.line}`, cursor: "pointer", fontVariantNumeric: "tabular-nums" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = C.surface2)}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                  {/* 배열 인덱스를 순위처럼 보여주면 안 된다 — 정렬 근거가 없는 숫자를
                      사용자가 1순위로 읽는다. 실제 당일 순위가 있으면 그것을 쓴다. */}
                  <Td style={{ textAlign: "left", color: p.is_top1 ? "#facc15" : C.mut,
                               fontWeight: p.is_top1 ? 700 : 400 }}>
                    {p.rank_in_day != null ? (p.is_top1 ? "⭐1" : p.rank_in_day) : "·"}
                  </Td>
                  <Td style={{ textAlign: "left" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <b style={{ fontSize: 15 }}>{p.name}</b>
                      <span style={{ color: C.mut, fontSize: 12 }}>{p.code}</span>
                      <MarketBadge market={p.market} />
                    </div>
                  </Td>
                  <Td style={{ color: live && p.entry && live > p.entry ? C.up : live && p.entry && live < p.entry ? C.down : C.text }}>{fmt(live)}</Td>
                  <Td style={{ color: signColor(pr?.change_pct) }}>{pr?.change_pct != null ? pct(pr.change_pct) : "–"}</Td>
                  <Td>{fmt(p.entry)}</Td>
                  <Td style={{ color: C.mut }}>{p.signal_class === "B" ? "α기준" : fmt(p.target)}</Td>
                  <Td>{p.prob != null ? `${p.prob}%` : "–"}</Td>
                  <Td style={{ color: signColor(p.alpha) }}>{p.alpha != null ? pct(p.alpha) : "–"}</Td>
                  <Td style={{ textAlign: "left" }}>
                    <div style={{ display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap" }}>
                      <LaneBadge kind={p.kind} badge={p.badge} label={p.lane_label} />
                      {p.tier === "PRIMARY" && <Chip color="#22c55e">주력</Chip>}
                      {p.tier === "CANDIDATE" && <Chip color="#94a3b8">후보</Chip>}
                      {p.mkt_state === "RISK_OFF" && <Chip color="#f59e0b">약세장</Chip>}
                      {p.size_pct_total != null && <Chip color="#818cf8">비중 {p.size_pct_total}%</Chip>}
                                    <StatusChips p={p} />
                  {p.sector_capitulation === "epicenter" && <Chip color="#22c55e">섹터동반↑</Chip>}
                  {p.sector_capitulation === "resilient" && <Chip color="#f59e0b">비진앙 단독항복</Chip>}
                  {p.tail_warn && <Chip color="#f59e0b">⚠tail</Chip>}
                    </div>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <div style={{ color: C.mut, fontSize: 12, marginTop: 10, lineHeight: 1.7 }}>
        🗓 <b style={{ color: C.text }}>픽 = 다음 거래일 매수 대상</b> (스캔은 장마감 후 <Term k="진입">종가</Term> 기준 산출 → 그 다음 거래일 진입). 행의 매수일은 상세에서 확인.<br />
        확률 = A 모델 적중확률 · <Term k="시장중립">B</Term>는 시장대비 초과 확률(보정). 알파 = B 예측 초과수익(A는 확률형이라 –).<br />
        픽은 저장된 스캔과 동일(재계산 아님). 실시간 시세 15초 자동갱신(장외=종가). 순서는 개요와 동일(확률순).
      </div>

      {sel && <Drawer pick={sel} live={prices[sel.code]} onClose={() => setSel(null)} />}
    </div>
  );
}

function Chip({ color, children }: { color: string; children: any }) {
  return <span style={{ fontSize: 11, padding: "1px 7px", borderRadius: 999, border: `1px solid ${color}`, color }}>{children}</span>;
}

function Drawer({ pick, live, onClose }: { pick: Pick; live?: Price; onClose: () => void }) {
  const [detail, setDetail] = useState<any>(null);
  useEffect(() => { api.detail(pick.code).then(setDetail).catch(() => {}); }, [pick.code]);
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 100, display: "flex", justifyContent: "flex-end" }}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: 560, maxWidth: "100vw", height: "100%", background: C.bg, borderLeft: `1px solid ${C.line}`, padding: 20, overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <b style={{ fontSize: 20 }}>{pick.name}</b>
            <span style={{ color: C.mut }}>{pick.code}</span>
            <MarketBadge market={pick.market} />
            <LaneBadge kind={pick.kind} badge={pick.badge} label={pick.lane_label} />
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: C.mut, fontSize: 22, cursor: "pointer" }}>×</button>
        </div>
        <div style={{ color: signColor(live?.change_pct), fontSize: 22, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>
          {fmt(live?.price ?? pick.entry)} <span style={{ fontSize: 14 }}>{live?.change_pct != null ? pct(live.change_pct) : ""}</span>
        </div>

        <div style={{ margin: "16px 0" }}><Chart code={pick.code} /></div>

        <Section title="매매 계획">
          <Row k="매수 대상일" v={pick.buy_date ? `${pick.buy_date} (다음 거래일)` : "다음 거래일"} />
          <Row k={`진입 (${pick.scan_date || ""} 종가)`} v={fmt(pick.entry)} />
          <Row k={`목표(+${pick.target_pct ?? 5}%)`} v={pick.signal_class === "B" ? "α기준(시장중립)" : fmt(pick.target)} />
          <Row k="보유" v={`${pick.hold_days ?? 5}거래일 (목표 터치시 익절, 아니면 종가 청산)`} />
          {pick.tier && <Row k="발행 티어" v={pick.tier === "PRIMARY" ? "주력(고확신 선별)" : "후보(관측용 — 매수 판단 참고만)"} />}
          {pick.mkt_state === "RISK_OFF" && <Row k="시장 상태" v={`약세 구간 (20일 낙폭 ${pick.mkt_dd20 ?? "-"}%) — 모멘텀 픽 주의`} />}
          <Row k="적중확률" v={pick.prob != null ? `${pick.prob}%` : "–"} />
        </Section>

        <Section title="근거">
          {pick.rationale && <Row k="모델 근거" v={pick.rationale} />}
          {pick.size_note && <Row k="권장 비중" v={pick.size_note} />}
          {/* 왜 이 상태인지를 상세에서 숫자로 보인다 — 칩만으론 근거가 안 남는다. */}
          {pick.rank_note && <Row k="당일 순위" v={pick.rank_note} />}
          {pick.forward_ev != null && (
            <Row k="실측 forward" v={`EV ${pick.forward_ev}%${pick.forward_win != null ? ` · 승률 ${pick.forward_win}%` : ""}${pick.forward_n != null ? ` (n=${pick.forward_n})` : ""}`} />
          )}
          {pick.lane_frequency?.last_fired && (
            <Row k="레인 발화" v={`마지막 ${pick.lane_frequency.last_fired} · ${pick.lane_frequency.days_since}거래일 전 · 통상 ${pick.lane_frequency.median_gap}거래일 간격${pick.lane_frequency.frequency_ok === false ? " — 기준(3거래일) 미달" : ""}`} />
          )}
          {pick.expired && <Row k="신선도" v={`매수일 ${pick.buy_date} 이 ${pick.stale_days}일 지났다 — 지금 진입가가 다르다`} />}
          {(pick as any).exit_mix_plan && <Row k="출구 shadow" v={`${(pick as any).exit_mix_plan} — 실매도는 현행 계약(+5% 터치) 기준, 혼합안은 §29 검증중`} />}
          {detail?.events?.map((e: { type: string; date: string; d_left: number; note: string }, i: number) => (
            <Row key={"ev" + i} k={`⚠ ${e.type} D-${e.d_left}`} v={`${e.date} — ${e.note}`} />
          ))}
          {detail?.flow && <Row k="수급(5일)" v={`외국인 ${fmt(detail.flow.frgn_5d)} · 기관 ${fmt(detail.flow.orgn_5d)} (${detail.flow.asof})`} />}
          {detail?.dart?.length ? detail.dart.map((d: any, i: number) => <Row key={i} k="공시" v={`${d.ann} ${d.type}`} />) : <Row k="공시" v="없음" />}
          {pick.signal_class === "B" && <Row k="스마트머니5d" v={fmt(pick.smart5, 1)} />}
        </Section>

        <div style={{ marginTop: 14, display: "flex", gap: 6, flexWrap: "wrap" }}>
          <WarnBadge>⚠ 낙관치</WarnBadge>
          {pick.signal_class === "B" && <WarnBadge>🔬 forward-shadow</WarnBadge>}
        </div>
        <div style={{ color: C.mut, fontSize: 11, marginTop: 12 }}>
          ※ 근거는 정보 제공이며 투자 권유가 아닙니다. 확률·수익은 과거 기준이고 미래를 보장하지 않습니다.
        </div>
      </div>
    </div>
  );
}

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div style={{ marginTop: 16 }}>
    <div style={{ color: C.mut, fontSize: 12, marginBottom: 8, fontWeight: 600 }}>{title}</div>
    <div style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 10, padding: 12 }}>{children}</div>
  </div>
);
const Row = ({ k, v }: { k: string; v: React.ReactNode }) => (
  <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", fontSize: 13 }}>
    <span style={{ color: C.mut }}>{k}</span><span style={{ fontVariantNumeric: "tabular-nums" }}>{v}</span>
  </div>
);
const Tab = ({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) => (
  <button onClick={onClick} style={{ background: on ? C.accent : C.surface, color: on ? "#fff" : C.mut, border: `1px solid ${on ? C.accent : C.line}`, borderRadius: 8, padding: "7px 14px", fontSize: 13, cursor: "pointer", fontWeight: 600 }}>{children}</button>
);
const Th = ({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) => (
  <th style={{ padding: "11px 13px", fontWeight: 600, textAlign: "right", ...style }}>{children}</th>
);
const Td = ({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) => (
  <td style={{ padding: "11px 13px", textAlign: "right", ...style }}>{children}</td>
);
const Skeleton = () => <div style={{ height: 300, background: C.surface, borderRadius: 12, opacity: 0.5 }} />;
