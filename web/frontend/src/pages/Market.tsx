import { useEffect, useState } from "react";
import { api } from "../api";
import { C, fmt, pct, signColor } from "../theme";
import { Card, Term, MarketBadge } from "../components/ui";

// ⑤ 시장·근거 — 지수/레짐 + 공시(DART)·수급(flow) 근거 피드.
export function Market() {
  const [m, setM] = useState<any>(null);
  useEffect(() => { api.market().then(setM).catch(() => {}); }, []);
  if (!m) return <div style={{ height: 200, background: C.surface, borderRadius: 12, opacity: .5 }} />;
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 12 }}>
        {["KOSPI", "KOSDAQ"].map((k) => (
          <Card key={k}>
            <div style={{ color: C.mut, fontSize: 12 }}>{k}</div>
            <div style={{ fontSize: 24, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{fmt(m.index?.[k]?.level, 2)}</div>
            <div style={{ color: signColor(m.index?.[k]?.change_pct), fontSize: 14 }}>{pct(m.index?.[k]?.change_pct)}</div>
          </Card>
        ))}
        <Card><div style={{ color: C.mut, fontSize: 12 }}><Term k="레짐">레짐</Term></div><div style={{ fontSize: 24, fontWeight: 700 }}>{m.regime}</div></Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <div style={{ color: C.mut, fontSize: 12, marginBottom: 10, fontWeight: 600 }}>공시 (DART)</div>
          {m.dart?.length ? m.dart.map((d: any, i: number) => (
            <div key={i} style={{ display: "flex", gap: 8, padding: "5px 0", fontSize: 13, borderTop: i ? `1px solid ${C.line}` : "none" }}>
              <span style={{ color: C.mut, minWidth: 70 }}>{d.ann}</span><b>{d.name}</b><span style={{ color: C.mut }}>{d.type}</span>
            </div>
          )) : <div style={{ color: C.mut }}>없음</div>}
        </Card>
        <Card>
          <div style={{ color: C.mut, fontSize: 12, marginBottom: 10, fontWeight: 600 }}><Term k="수급">수급</Term> 상위 (외국인 순매수) <span style={{ color: C.mut }}>{m.flow_asof}</span></div>
          {m.flow_top?.length ? m.flow_top.map((f: any, i: number) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", fontSize: 13, borderTop: i ? `1px solid ${C.line}` : "none" }}>
              <span><b>{f.name}</b> <span style={{ color: C.mut, fontSize: 11 }}>{f.code}</span></span>
              <span style={{ color: C.up, fontVariantNumeric: "tabular-nums" }}>+{fmt(f.frgn)}</span>
            </div>
          )) : <div style={{ color: C.mut }}>없음</div>}
        </Card>
      </div>
      <div style={{ color: C.mut, fontSize: 11 }}>※ 수급 데이터는 KIS 시간제한으로 지연될 수 있습니다(09:35 아침세션 갱신).</div>
    </div>
  );
}
