import { useEffect, useState } from "react";
import { api, ScanPost, TickerCard, Analysis } from "../api";
import { useIsMobile } from "../useIsMobile";
import { C, fmt, pct, signColor } from "../theme";
import { Card, MarketBadge, Term } from "../components/ui";
import { Chart } from "../components/Chart";

// ③ 스캔 피드 — 게시물(스캔)→티커카드→정밀분석 패널. 자동+수동+디스코드 누적.
export function ScanFeed() {
  const isMobile = useIsMobile();
  const [scans, setScans] = useState<ScanPost[]>([]);
  const [source, setSource] = useState("");
  const [sel, setSel] = useState<ScanPost | null>(null);
  const [cards, setCards] = useState<TickerCard[] | null>(null);
  const [ticker, setTicker] = useState<TickerCard | null>(null);
  const [notes, setNotes] = useState<string[]>([]);

  useEffect(() => { api.scans(source).then((d) => setScans(d.scans)).catch(() => {}); }, [source]);
  const openScan = (s: ScanPost) => { setSel(s); setCards(null); setTicker(null); setNotes([]); api.scanDetail(s.scan_id).then((d) => { setCards(d.cards); setNotes(d.notes || []); }).catch(() => setCards([])); };

  return (
    <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : ticker ? "300px 1fr" : sel ? "300px 1fr" : "1fr", gap: 16 }}>
      {/* 왼쪽: 게시물 목록 */}
      <div>
        <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
          {["", "auto", "manual", "discord"].map((s) => (
            <button key={s} onClick={() => setSource(s)} style={segBtn(source === s)}>{s === "" ? "전체" : s === "auto" ? "자동" : s === "manual" ? "수동" : "디스코드"}</button>
          ))}
        </div>
        <div style={{ display: isMobile && sel ? "none" : "grid", gap: 8, maxHeight: sel && !isMobile ? "78vh" : "none", overflowY: sel && !isMobile ? "auto" : "visible" }}>
          {scans.map((s) => (
            <div key={s.scan_id} onClick={() => openScan(s)}
              style={{ background: sel?.scan_id === s.scan_id ? C.surface2 : C.surface, border: `1px solid ${sel?.scan_id === s.scan_id ? C.accent : C.line}`, borderRadius: 10, padding: 12, cursor: "pointer" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontSize: 12, color: C.mut }}>{s.time}</span>
                <SourceBadge source={s.source} />
              </div>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{s.lanes.join(", ")}</div>
              <div style={{ fontSize: 12, color: C.mut, marginTop: 4 }}>{s.markets.join("·")} · {s.pick_count}픽</div>
              {s.note && <div style={{ fontSize: 11, color: C.mut, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>{s.note}</div>}
            </div>
          ))}
        </div>
      </div>

      {/* 오른쪽: 티커카드 그리드 또는 분석패널 */}
      {sel && (
        <div>
          {!ticker ? (
            <div>
              {isMobile && (
                <button onClick={() => setSel(null)} style={{ background: "none", border: "none", color: C.accent, fontSize: 14, padding: "0 0 10px", cursor: "pointer" }}>← 스캔 목록</button>
              )}
              <div style={{ marginBottom: 12, color: C.mut, fontSize: 13 }}>{sel.scan_id} · {cards?.length || 0} 종목 — 카드를 클릭하면 정밀분석</div>
              {notes.length > 0 && <div style={{ marginBottom: 12, padding: 10, background: C.surface2, borderRadius: 8, fontSize: 12, color: C.mut }}>{notes.map((n, i) => <div key={i}>{n}</div>)}</div>}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 10 }}>
                {(cards || []).map((c) => (
                  <div key={c.code} onClick={() => setTicker(c)} style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 10, padding: 12, cursor: "pointer" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
                      <b style={{ fontSize: 15 }}>{c.name}</b><span style={{ color: C.mut, fontSize: 11 }}>{c.code}</span>
                    </div>
                    <div style={{ marginBottom: 8 }}><MarketBadge market={c.market} /></div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
                      <span style={{ color: C.mut }}>진입 {fmt(c.entry)}</span>
                      <span>{c.prob != null ? `${c.prob}%` : ""}</span>
                    </div>
                  </div>
                ))}
                {cards && cards.length === 0 && <div style={{ color: C.mut }}>이 스캔의 픽 카드 없음</div>}
              </div>
            </div>
          ) : isMobile ? (
            <div onClick={() => setTicker(null)} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.5)", zIndex: 100, display: "flex", alignItems: "flex-end" }}>
              <div onClick={(e) => e.stopPropagation()}
                style={{ width: "100%", maxHeight: "86vh", overflowY: "auto", background: C.bg, borderTop: `1px solid ${C.line}`, borderRadius: "18px 18px 0 0", padding: "10px 14px calc(20px + env(safe-area-inset-bottom))" }}>
                <div style={{ width: 40, height: 4, borderRadius: 2, background: C.line, margin: "0 auto 10px" }} />
                <Panel scanId={sel.scan_id} card={ticker} onBack={() => setTicker(null)} />
              </div>
            </div>
          ) : (
            <Panel scanId={sel.scan_id} card={ticker} onBack={() => setTicker(null)} />
          )}
        </div>
      )}
    </div>
  );
}

function Panel({ scanId, card, onBack }: { scanId: string; card: TickerCard; onBack: () => void }) {
  const [a, setA] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { setLoading(true); api.scanAnalyze(scanId, card.code).then((d) => { setA(d); setLoading(false); }).catch(() => setLoading(false)); }, [scanId, card.code]);
  return (
    <div>
      <button onClick={onBack} style={{ ...segBtn(false), marginBottom: 12 }}>← 티커카드</button>
      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 10 }}>
          <b style={{ fontSize: 20 }}>{card.name}</b><span style={{ color: C.mut }}>{card.code}</span><MarketBadge market={card.market} />
          <span style={{ color: C.mut, fontSize: 12 }}>· {card.lane}</span>
        </div>
        {loading ? <div style={{ color: C.mut }}>정밀분석 생성 중… (최초 ~10초, 이후 캐시)</div> : a && (
          <div style={{ display: "grid", gap: 14 }}>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <Chip on={!!a.model.in_a}>{a.model.in_a ? `A 픽 ${a.model.in_a.prob}%` : "A 미픽"}</Chip>
              <Chip on={!!a.model.in_b}>{a.model.in_b ? `B 시장중립 ${a.model.in_b.prob ?? ""}% · 예측α ${fmt(a.model.in_b.pred_alpha_5d, 2)}` : "B 미픽"}</Chip>
              <span style={{ color: C.mut, fontSize: 13, alignSelf: "center" }}><Term k="레짐">레짐</Term> {a.regime}</span>
            </div>
            <div style={{ background: C.surface2, border: `1px solid ${C.accent}44`, borderRadius: 10, padding: 12 }}>
              <div style={{ color: C.mut, fontSize: 12, marginBottom: 6 }}>종합 판정 ({a.verdict.source})</div>
              <div style={{ fontSize: 14, lineHeight: 1.7 }}>{a.verdict.text}</div>
            </div>
            <Chart code={card.code} height={280} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <Mini title="지표">
                <Kv k="RSI" v={fmt(a.features.rsi14 as number, 1)} />
                <Kv k="20일수익" v={pct(a.features.ret_20d as number, 1)} c={signColor(a.features.ret_20d as number)} />
                <Kv k="고가이격" v={pct(a.features.dist_hi20 as number, 1)} />
              </Mini>
              <Mini title="수급·이벤트">
                {a.flow ? <><Kv k="외국인5d" v={fmt(a.flow.frgn_5d)} c={signColor(a.flow.frgn_5d)} /><Kv k="기관5d" v={fmt(a.flow.orgn_5d)} c={signColor(a.flow.orgn_5d)} /></> : <div style={{ color: C.mut, fontSize: 12 }}>수급 없음</div>}
                <Kv k="공시" v={a.events.dart.length ? a.events.dart.map((x) => x.type).join(",") : "없음"} />
              </Mini>
            </div>
            <div style={{ color: C.mut, fontSize: 11 }}>※ 지표·수급은 현재 기준, 차트는 라이브. 정보 제공이며 투자권유 아님.</div>
          </div>
        )}
      </Card>
    </div>
  );
}

const segBtn = (on: boolean): React.CSSProperties => ({ background: on ? C.accent : C.surface, color: on ? "#fff" : C.mut, border: `1px solid ${on ? C.accent : C.line}`, borderRadius: 8, padding: "6px 12px", fontSize: 13, cursor: "pointer", fontWeight: 600 });
const SourceBadge = ({ source }: { source: string }) => {
  const m: any = { auto: ["자동", C.accent], manual: ["수동", C.up], discord: ["디스코드", C.laneB] };
  const [label, col] = m[source] || [source, C.mut];
  return <span style={{ fontSize: 11, color: col, background: `${col}1A`, border: `1px solid ${col}44`, borderRadius: 999, padding: "1px 8px", fontWeight: 600 }}>{label}</span>;
};
const Chip = ({ on, children }: { on: boolean; children: React.ReactNode }) => <span style={{ fontSize: 13, fontWeight: 600, padding: "6px 12px", borderRadius: 8, color: on ? C.up : C.mut, background: on ? `${C.up}1A` : C.surface2, border: `1px solid ${on ? C.up + "55" : C.line}` }}>{children}</span>;
const Mini = ({ title, children }: { title: string; children: React.ReactNode }) => <div style={{ background: C.surface2, border: `1px solid ${C.line}`, borderRadius: 10, padding: 12 }}><div style={{ color: C.mut, fontSize: 12, marginBottom: 8, fontWeight: 600 }}>{title}</div>{children}</div>;
const Kv = ({ k, v, c }: { k: string; v: React.ReactNode; c?: string }) => <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 13 }}><span style={{ color: C.mut }}>{k}</span><span style={{ color: c, fontVariantNumeric: "tabular-nums" }}>{v}</span></div>;
