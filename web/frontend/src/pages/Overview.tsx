import { useEffect, useState } from "react";
import { api, Overview as OV } from "../api";
import { C, fmt } from "../theme";
import { Card, MarketBadge, LaneBadge, Term } from "../components/ui";

export function Overview() {
  const [ov, setOv] = useState<OV | null>(null);
  useEffect(() => { api.overview(6).then(setOv).catch(() => {}); }, []);
  if (!ov) return <div style={{ height: 200, background: C.surface, borderRadius: 12, opacity: .5 }} />;

  const fr = ov.freshness;
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Card>
        <div style={{ color: C.mut, fontSize: 12, marginBottom: 12, fontWeight: 600 }}>오늘의 핵심 픽 (A {ov.counts.A} · B {ov.counts.B})</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
          {ov.top_picks.map((p, i) => (
            <div key={p.code + p.lane} style={{ background: C.surface2, border: `1px solid ${C.line}`, borderRadius: 10, padding: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
                <span style={{ color: C.mut, fontSize: 12 }}>#{i + 1}</span>
                <b style={{ fontSize: 16 }}>{p.name}</b>
                <span style={{ color: C.mut, fontSize: 12 }}>{p.code}</span>
              </div>
              <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
                <MarketBadge market={p.market} />
                <LaneBadge kind={p.kind} badge={p.badge} label={p.lane_label} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
                <span style={{ color: C.mut }}>진입 {fmt(p.entry)}</span>
                <span>{p.prob != null ? `적중확률 ${p.prob}%` : "시장중립"}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <div style={{ color: C.mut, fontSize: 12, marginBottom: 10, fontWeight: 600 }}>데이터 신선도</div>
          {[["일봉", fr.daily], ["분봉", fr.minute], ["수급", fr.flow], ["공시", fr.dart], ["실적", fr.pead]].map(([k, v]) => (
            <div key={k as string} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", fontSize: 13 }}>
              <span style={{ color: C.mut }}>{k}</span><span>{v || "–"}</span>
            </div>
          ))}
        </Card>
        <Card>
          <div style={{ color: C.mut, fontSize: 12, marginBottom: 10, fontWeight: 600 }}>정직 안내</div>
          <div style={{ fontSize: 13, lineHeight: 1.7, color: C.text }}>
            절대수익 옆에는 항상 <Term k="알파">알파</Term>를 함께 봅니다. B엔진은 <Term k="시장중립">시장중립</Term>이며 아직 <Term k="forward-shadow">forward-shadow</Term> 관측 단계입니다.
            픽의 확률·수익은 <Term k="낙관치">낙관치</Term>일 수 있습니다.
          </div>
        </Card>
      </div>
    </div>
  );
}
