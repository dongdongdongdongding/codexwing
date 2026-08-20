import { useEffect, useState } from "react";
import { api } from "../api";
import { C } from "../theme";
import { Card, Term } from "../components/ui";

// ⑦ 운영 [운영자] — 백그라운드 스캔(R4) + 스케줄러/신선도/모델 상태.
export function Ops() {
  const [status, setStatus] = useState<any>(null);
  const [scan, setScan] = useState<any>(null);
  const [target, setTarget] = useState("all");
  const [targets, setTargets] = useState<Array<{ key: string; label: string }>>([]);

  const refresh = () => { api.opsStatus().then(setStatus).catch(() => {}); api.scanStatus().then(setScan).catch(() => {}); };
  useEffect(() => { refresh(); api.scanTargets().then((d) => setTargets(d.targets)).catch(() => {}); const t = setInterval(() => api.scanStatus().then(setScan).catch(() => {}), 3000); return () => clearInterval(t); }, []);

  const running = scan?.status === "running";
  const start = async () => { await api.scanStart(target); setTimeout(refresh, 500); };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Card>
        <div style={{ color: C.mut, fontSize: 12, marginBottom: 12, fontWeight: 600 }}>스캔 제어 (백그라운드 — 탭 이동해도 계속)</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <select value={target} onChange={(e) => setTarget(e.target.value)} style={{ background: C.surface2, color: C.text, border: `1px solid ${C.line}`, borderRadius: 8, padding: "8px 12px" }}>
            {targets.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
          </select>
          <button onClick={start} disabled={running} style={{ background: running ? C.surface2 : C.accent, color: running ? C.mut : "#fff", border: "none", borderRadius: 8, padding: "8px 18px", fontWeight: 700, cursor: running ? "default" : "pointer" }}>
            {running ? "스캔 중…" : "▶ 스캔 실행"}
          </button>
          {scan && scan.status !== "idle" && (
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: C.mut, marginBottom: 4 }}>
                <span>{scan.current || scan.status}</span><span>{scan.progress}%</span>
              </div>
              <div style={{ height: 8, background: C.surface2, borderRadius: 4, overflow: "hidden" }}>
                <div style={{ width: `${scan.progress}%`, height: "100%", background: C.accent, transition: "width .3s" }} />
              </div>
            </div>
          )}
        </div>
        {scan?.steps?.length > 0 && (
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            {scan.steps.map((s: any, i: number) => (
              <span key={i} style={{ fontSize: 12, padding: "3px 10px", borderRadius: 999, color: s.ok ? C.up : C.down, background: `${s.ok ? C.up : C.down}1A`, border: `1px solid ${(s.ok ? C.up : C.down)}44` }}>
                {s.ok ? "✓" : "✗"} {s.step} {s.note}
              </span>
            ))}
          </div>
        )}
      </Card>

      {status && (
        <>
          {/* 에스컬레이션 — 판정기·경보 산출. 이 자리가 비어 있어서 매일 나오는
              critical 이 화면 어디에도 없었다. 경보를 만들어 놓고 아무도 읽지 않는
              파일에 쓰면 그것도 조용한 실패다. */}
          {(() => {
            const e = (status as any)?.escalations;
            if (!e) return null;
            if (e.note) return (
              <Card><div style={{ color: C.warn, fontSize: 13 }}>⚠ {e.note}</div></Card>
            );
            const items = e.items || [];
            return (
              <Card>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}>
                  <b style={{ fontSize: 13 }}>에스컬레이션</b>
                  <span style={{ fontSize: 11, color: items.length ? C.down : C.up }}>
                    {items.length ? `${items.length}건 · 최고 ${e.worst}` : "없음"}
                  </span>
                  <span style={{ fontSize: 11, color: C.mut, marginLeft: "auto" }}>{e.source} · {e.generated_at}</span>
                </div>
                {items.length === 0 ? (
                  <div style={{ color: C.mut, fontSize: 12 }}>판정기가 올린 건이 없다.</div>
                ) : items.map((it: any, i: number) => (
                  <div key={i} style={{ padding: "6px 0", borderTop: i ? `1px solid ${C.line}` : "none", fontSize: 12 }}>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "baseline" }}>
                      <span style={{ color: it.severity === "critical" ? "#ef4444" : "#f59e0b", fontWeight: 700, minWidth: 48 }}>
                        {it.severity === "critical" ? "CRIT" : "ALERT"}
                      </span>
                      <span style={{ color: C.mut, minWidth: 140 }}>{it.check}</span>
                      <b>{it.id}</b>
                      <span style={{ color: C.mut }}>{it.verdict}</span>
                      <span style={{ flex: 1, minWidth: 220 }}>{it.detail}</span>
                    </div>
                    {it.action && <div style={{ color: C.warn, fontSize: 11, marginTop: 2 }}>→ {it.action}</div>}
                  </div>
                ))}
              </Card>
            );
          })()}
          <Card>
            <div style={{ color: C.mut, fontSize: 12, marginBottom: 10, fontWeight: 600 }}>데이터 신선도</div>
            <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
              {Object.entries(status.freshness).map(([k, v]: any) => (
                <span key={k} style={{ fontSize: 13 }}><span style={{ color: C.mut }}>{({ daily: "일봉", minute: "분봉", flow: "수급", dart: "공시", pead: "실적" } as any)[k] || k}</span> {v || "–"}{k === "flow" && v && v < status.freshness.daily ? <span style={{ color: C.warn }}> ⚠지연</span> : ""}</span>
              ))}
            </div>
            <div style={{ color: C.mut, fontSize: 11, marginTop: 8 }}>※ 수급은 KIS API 시간제한(00:00~15:40)으로 09:35 아침세션이 갱신. 지연시 다음날 아침 최신화.</div>
          </Card>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Card>
              <div style={{ color: C.mut, fontSize: 12, marginBottom: 10, fontWeight: 600 }}>스케줄 (launchd 5분 폴링)</div>
              {status.schedule.map((s: any) => (
                <div key={s.id} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", fontSize: 13 }}>
                  <span>{s.time}</span><span style={{ color: C.mut }}>{s.desc}</span>
                </div>
              ))}
            </Card>
            <Card>
              <div style={{ color: C.mut, fontSize: 12, marginBottom: 10, fontWeight: 600 }}>모델</div>
              {status.models.B && <div style={{ fontSize: 13 }}>B 시장중립 · 학습~{status.models.B.trained_through}</div>}
              <div style={{ color: C.mut, fontSize: 12, marginTop: 6 }}>A 레인: 일일 ops에서 재학습</div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
