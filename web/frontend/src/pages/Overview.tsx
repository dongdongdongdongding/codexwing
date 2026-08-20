import { useEffect, useState } from "react";
import { api, Overview as OV } from "../api";
import { C, fmt } from "../theme";
import { Card, MarketBadge, LaneBadge, Term, StatusChips } from "../components/ui";

export function Overview() {
  const [ov, setOv] = useState<OV | null>(null);
  useEffect(() => { api.overview(6).then(setOv).catch(() => {}); }, []);
  if (!ov) return <div style={{ height: 200, background: C.surface, borderRadius: 12, opacity: .5 }} />;

  const fr = ov.freshness;
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Compass />
      <Card>
        <div style={{ color: C.mut, fontSize: 12, marginBottom: 12, fontWeight: 600 }}>오늘의 핵심 픽 (A {ov.counts.A} · B {ov.counts.B})</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
          {ov.top_picks.map((p, i) => (
            <div key={p.code + p.lane} style={{ background: C.surface2, border: `1px solid ${C.line}`, borderRadius: 10, padding: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
                {/* 배열 인덱스를 순위처럼 보이면 안 된다 — 정렬 근거가 없는 숫자를
                    사용자가 1순위로 읽는다. 실제 당일 순위(레인 내 p 랭킹)를 쓴다. */}
                <span style={{ color: (p as any).is_top1 ? "#facc15" : C.mut, fontSize: 12,
                               fontWeight: (p as any).is_top1 ? 700 : 400 }}>
                  {(p as any).rank_in_day != null ? ((p as any).is_top1 ? "⭐1" : `${(p as any).rank_in_day}`) : "·"}
                </span>
                <b style={{ fontSize: 16 }}>{p.name}</b>
                <span style={{ color: C.mut, fontSize: 12 }}>{p.code}</span>
              </div>
              <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
                <MarketBadge market={p.market} />
                <LaneBadge kind={p.kind} badge={p.badge} label={p.lane_label} />
                <StatusChips p={p} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
                <span style={{ color: C.mut }}>진입 {fmt(p.entry)}</span>
                {/* 확률만 크게 보이면 폐기선 아래 레인도 좋아 보인다.
                    실측 forward EV 를 나란히 둔다 — 모델 점수와 실현 성적은 다른 것이다. */}
                <span>
                  {p.prob != null ? `적중확률 ${p.prob}%` : "시장중립"}
                  {(p as any).forward_ev != null && (
                    <span style={{ color: (p as any).forward_ev > 1 ? C.up : C.down, marginLeft: 6 }}>
                      · 실측 EV {(p as any).forward_ev}%
                    </span>
                  )}
                </span>
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


function Compass() {
  const [c, setC] = useState<Awaited<ReturnType<typeof api.compass>> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    // 실패를 삼키면 카드가 통째로 사라진다. 2026-08-20 에 실제로 그랬고, 콜드 스타트
    // 2초 지연을 "화면이 깨졌다"로 오인했다. 지연/실패를 각각 눈에 보이게 남긴다.
    const load = () => api.compass().then((d) => { setC(d); setErr(null); })
                                    .catch((e) => setErr(String(e?.message || e)));
    load(); const t = setInterval(load, 60000); return () => clearInterval(t);
  }, []);
  if (!c) return (
    <div style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 14,
                  padding: 14, color: err ? "#ef4444" : C.mut, fontSize: 12 }}>
      {err ? `국면 나침반 — 불러오지 못했다: ${err}` : "국면 나침반 — 불러오는 중…"}
    </div>
  );
  const JC: Record<string, string> = { LONG: "#22c55e", LEAN_LONG: "#eab308", NEUTRAL: "#94a3b8", WAIT: "#ef4444" };
  return (
    <div style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 14, padding: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <b>국면 나침반</b>
        <span style={{ fontSize: 11, color: C.mut }}>8y 검증 레짐 지도 · {c.asof} · 60초 갱신</span>
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        {c.markets.map((m) => (
          <div key={m.market} style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", fontSize: 13 }}>
            <b style={{ width: 70 }}>{m.market}</b>
            <span style={{ color: JC[m.judge], fontWeight: 700 }}>{m.judge_label}</span>
            <span style={{ color: C.mut }}>{m.phase} (dd20 {m.dd20}% · 5d {m.ret5}%)</span>
            <span style={{ color: C.mut, fontSize: 11 }}>{m.basis}{m.live ? " · 실시간" : ""}</span>
            {m.lane_note && <span style={{ color: "#818cf8", fontSize: 11 }}>{m.lane_note}</span>}
          </div>
        ))}
        {c.night && (
          <div style={{ display: "flex", gap: 10, fontSize: 12, color: C.mut, borderTop: `1px dashed ${C.line}`, paddingTop: 8, flexWrap: "wrap" }}>
            <b>🌙 {c.night.symbol}</b>
            <span style={{ color: c.night.change_pct >= 0 ? "#22c55e" : "#ef4444", fontWeight: 600 }}>{c.night.change_pct >= 0 ? "+" : ""}{c.night.change_pct}%</span>
            <span style={{ fontSize: 11 }}>{c.night.note}</span>
          </div>
        )}
        {/* §39 섹터 로테이션 (2026-08-04 운영자 승인): 20d 신 리더십 + 60d 진앙지(하위 1/4) */}
        {c.sector_rotation && (
          <div style={{ borderTop: `1px dashed ${C.line}`, paddingTop: 8, fontSize: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <b>🔄 섹터 로테이션</b>
              <span style={{ fontSize: 11, color: C.mut }}>{c.sector_rotation.note}</span>
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
              <span style={{ color: C.mut, fontSize: 11, width: 88 }}>리더십 20d</span>
              {c.sector_rotation.leadership_20d.slice(0, 5).map((s) => (
                <span key={s.industry} style={{ background: "rgba(34,197,94,.12)", color: "#22c55e", borderRadius: 6, padding: "1px 6px", fontSize: 11 }}>
                  {s.industry} {s.ret20 != null ? `${s.ret20 >= 0 ? "+" : ""}${s.ret20}%` : ""}
                </span>
              ))}
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <span style={{ color: C.mut, fontSize: 11, width: 88 }}>진앙지 60d</span>
              {c.sector_rotation.epicenter_60d.slice(0, 5).map((s) => (
                <span key={s.industry} style={{ background: "rgba(239,68,68,.12)", color: "#ef4444", borderRadius: 6, padding: "1px 6px", fontSize: 11 }}>
                  {s.industry} {s.ret60}%
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
