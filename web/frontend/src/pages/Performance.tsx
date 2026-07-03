import { useEffect, useState } from "react";
import { api, Performance as PF, Archive as AR, ContractPerf } from "../api";
import { C, fmt, pct, signColor } from "../theme";
import { Card, Term, MarketBadge, WarnBadge } from "../components/ui";

// ④ 성과 — 알파(시장대비) 우선 + 절대수익 보조. 하위뷰: 집계 / 스캔아카이브.
export function Performance() {
  const [view, setView] = useState<"summary" | "archive">("summary");
  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <Seg on={view === "summary"} onClick={() => setView("summary")}>성과 집계</Seg>
        <Seg on={view === "archive"} onClick={() => setView("archive")}>스캔 아카이브</Seg>
      </div>
      {view === "summary" ? <Summary /> : <ArchiveView />}
    </div>
  );
}

function Summary() {
  const [pf, setPf] = useState<PF | null>(null);
  const [cp, setCp] = useState<ContractPerf | null>(null);
  const [basis, setBasis] = useState<"alpha" | "abs">("alpha");
  useEffect(() => { api.performance().then(setPf).catch(() => {}); api.contractPerformance().then(setCp).catch(() => {}); }, []);
  if (!pf) return <Sk />;
  const o = pf.overall;
  const mainVal = basis === "alpha" ? o.alpha_mean : o.abs_mean;
  const mainWin = basis === "alpha" ? o.alpha_win : o.abs_win;
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <span style={{ color: C.mut, fontSize: 13 }}>기준:</span>
        <Seg on={basis === "alpha"} onClick={() => setBasis("alpha")}><Term k="알파">알파(시장대비)</Term></Seg>
        <Seg on={basis === "abs"} onClick={() => setBasis("abs")}>절대수익</Seg>
        <span style={{ marginLeft: "auto", color: C.mut, fontSize: 12 }}>기준일 {pf.as_of}</span>
      </div>
      <div style={{ color: C.mut, fontSize: 12 }}>진입 기준 = <b style={{ color: C.text }}>다음 거래일 종가</b>(현실 매수 시점). 스캔일 종가가 아니라 실제 살 수 있는 가격으로 측정합니다.</div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 12 }}>
        <Stat label={basis === "alpha" ? "알파 평균" : "절대 평균"} value={pct(mainVal)} color={signColor(mainVal)} />
        <Stat label="승률" value={mainWin != null ? `${mainWin}%` : "–"} />
        <Stat label="표본" value={`${o.n}픽`} sub={o.immature ? `미성숙 ${o.immature}` : ""} />
        <Stat label="B forward-shadow" value={pf.b_shadow.settled ? `α ${pct(pf.b_shadow.alpha_mean)}` : "관측중"} sub={`채점 ${pf.b_shadow.settled}`} />
      </div>

      {basis === "abs" && (
        <div style={{ color: C.warn, fontSize: 12 }}>⚠ 절대수익엔 시장 베타가 포함됩니다(하락장엔 같이 빠짐). 모델 실력은 <Term k="알파">알파</Term>로 보세요.</div>
      )}
      {(o.immature || 0) > 0 && <div style={{ color: C.warn, fontSize: 12 }}>⚠ 일부 픽은 보유기간 미완료(평가 미성숙).</div>}

      <Card>
        <div style={{ color: C.mut, fontSize: 12, marginBottom: 10, fontWeight: 600 }}>레인별</div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead><tr style={{ color: C.mut, textAlign: "right" }}><th style={{ textAlign: "left", padding: 6 }}>레인</th><th style={{ padding: 6 }}>픽</th><th style={{ padding: 6 }}>알파</th><th style={{ padding: 6 }}>알파승</th><th style={{ padding: 6 }}>절대</th><th style={{ padding: 6 }}>대기</th></tr></thead>
          <tbody>
            {Object.entries(pf.lanes).filter(([, v]) => v.n || v.pending).map(([k, v]) => (
              <tr key={k} style={{ borderTop: `1px solid ${C.line}`, fontVariantNumeric: "tabular-nums" }}>
                <td style={{ textAlign: "left", padding: 6 }}>{k}</td>
                <td style={{ textAlign: "right", padding: 6 }}>{v.n}</td>
                <td style={{ textAlign: "right", padding: 6, color: signColor(v.alpha_mean) }}>{v.n ? pct(v.alpha_mean) : "–"}</td>
                <td style={{ textAlign: "right", padding: 6 }}>{v.n ? `${v.alpha_win}%` : "–"}</td>
                <td style={{ textAlign: "right", padding: 6, color: signColor(v.abs_mean) }}>{v.n ? pct(v.abs_mean) : "–"}</td>
                <td style={{ textAlign: "right", padding: 6, color: C.mut }}>{v.pending || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ color: C.mut, fontSize: 11, marginTop: 6 }}>대기 = 스캔 직후 아직 '다음 거래일 종가'가 없어 평가 보류 중인 픽 (다음 거래일 도래 시 자동 편입).</div>
      </Card>

      {cp && (
        <Card>
          <div style={{ color: C.mut, fontSize: 12, marginBottom: 4, fontWeight: 600 }}>계약 실현 성과 (터치익절 자동 채점)</div>
          <div style={{ color: C.mut, fontSize: 11, marginBottom: 10 }}>{cp.note} 위 표(마크투마켓: 익일종가→현재가)와 달리, 계약대로 익절/청산했을 때의 확정 수익입니다. 해상까지 ~9일 소요.</div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr style={{ color: C.mut, textAlign: "right" }}><th style={{ textAlign: "left", padding: 6 }}>레인 (계약)</th><th style={{ padding: 6 }}>해상</th><th style={{ padding: 6 }}>평균수익</th><th style={{ padding: 6 }}>승률</th><th style={{ padding: 6 }}>최악</th></tr></thead>
            <tbody>
              {Object.entries(cp.lanes).map(([k, v]) => (
                <tr key={k} style={{ borderTop: `1px solid ${C.line}`, fontVariantNumeric: "tabular-nums" }}>
                  <td style={{ textAlign: "left", padding: 6 }}>{v.label}</td>
                  <td style={{ textAlign: "right", padding: 6 }}>{v.n}</td>
                  <td style={{ textAlign: "right", padding: 6, color: signColor(v.ev_avg) }}>{v.n ? pct(v.ev_avg) : "관측중"}</td>
                  <td style={{ textAlign: "right", padding: 6 }}>{v.n ? `${v.win_pct}%` : "–"}</td>
                  <td style={{ textAlign: "right", padding: 6, color: signColor(v.worst) }}>{v.n ? pct(v.worst) : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {cp.selective && (
            <div style={{ color: C.mut, fontSize: 11, marginTop: 8 }}>
              선별 rank-1 트랙: {Object.entries(cp.selective).map(([m, v]) =>
                `${m} 전체 n=${v.rank1?.n ?? 0}${v.rank1?.n ? ` 평균 ${v.rank1?.ev_avg}%` : ""} · 주력 n=${v.primary?.n ?? 0}${v.primary?.n ? ` 평균 ${v.primary?.ev_avg}%` : ""}`).join("  |  ")}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function ArchiveView() {
  const [ar, setAr] = useState<AR | null>(null);
  const [ticker, setTicker] = useState("");
  const load = () => api.archive({ ticker, limit: 80 }).then(setAr).catch(() => {});
  useEffect(() => { load(); }, []);
  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input value={ticker} onChange={(e) => setTicker(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} placeholder="티커 필터"
          style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 8, padding: "8px 12px", color: C.text }} />
        <button onClick={load} style={{ background: C.surface2, color: C.text, border: `1px solid ${C.line}`, borderRadius: 8, padding: "0 14px", cursor: "pointer" }}>조회</button>
        {ar && <span style={{ color: C.mut, fontSize: 12, alignSelf: "center" }}>총 {ar.count.toLocaleString()}행 (과거 모든 스캔 이력)</span>}
      </div>
      {!ar ? <Sk /> : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, background: C.surface, border: `1px solid ${C.line}`, borderRadius: 12, overflow: "hidden" }}>
          <thead><tr style={{ color: C.mut, textAlign: "right", fontSize: 12 }}>
            <th style={{ textAlign: "left", padding: "10px" }}>일자</th><th style={{ textAlign: "left", padding: 10 }}>종목</th><th style={{ padding: 10 }}>레인</th><th style={{ padding: 10 }}>진입</th><th style={{ padding: 10 }}>수익</th><th style={{ padding: 10 }}>결과</th></tr></thead>
          <tbody>
            {ar.rows.map((r, i) => (
              <tr key={i} style={{ borderTop: `1px solid ${C.line}`, fontVariantNumeric: "tabular-nums" }}>
                <td style={{ textAlign: "left", padding: 10, color: C.mut }}>{r.date}</td>
                <td style={{ textAlign: "left", padding: 10 }}>{r.name} <span style={{ color: C.mut, fontSize: 11 }}>{r.code}</span></td>
                <td style={{ textAlign: "right", padding: 10, color: C.mut }}>{r.lane}</td>
                <td style={{ textAlign: "right", padding: 10 }}>{fmt(r.entry)}</td>
                <td style={{ textAlign: "right", padding: 10, color: signColor(r.ret) }}>{r.ret != null ? pct(r.ret, 1) : "–"}</td>
                <td style={{ textAlign: "right", padding: 10 }}>{r.result === "승" ? <span style={{ color: C.up }}>📈 승</span> : r.result === "패" ? <span style={{ color: C.down }}>📉 패</span> : <span style={{ color: C.mut }}>미해결</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const Stat = ({ label, value, color, sub }: { label: string; value: React.ReactNode; color?: string; sub?: string }) => (
  <Card><div style={{ color: C.mut, fontSize: 12, marginBottom: 6 }}>{label}</div><div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>{sub && <div style={{ color: C.mut, fontSize: 11, marginTop: 4 }}>{sub}</div>}</Card>
);
const Seg = ({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) => (
  <button onClick={onClick} style={{ background: on ? C.accent : C.surface, color: on ? "#fff" : C.mut, border: `1px solid ${on ? C.accent : C.line}`, borderRadius: 8, padding: "7px 14px", fontSize: 13, cursor: "pointer", fontWeight: 600 }}>{children}</button>
);
const Sk = () => <div style={{ height: 240, background: C.surface, borderRadius: 12, opacity: .5 }} />;
