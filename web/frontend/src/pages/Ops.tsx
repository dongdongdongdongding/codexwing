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
