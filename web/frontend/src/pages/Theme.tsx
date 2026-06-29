import { useEffect, useState } from "react";
import { api } from "../api";
import { C } from "../theme";
import { Card } from "../components/ui";

// ⑥ 테마 네트워크 — primary_theme 그룹. 오늘 픽이 겹친 '주도 테마' 상단. (가치사슬 그래프는 후속)
export function Theme() {
  const [d, setD] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => { api.theme().then(setD).catch(() => {}); }, []);
  if (!d) return <div style={{ height: 200, background: C.surface, borderRadius: 12, opacity: .5 }} />;
  const max = Math.max(...d.themes.map((t: any) => t.size), 1);
  return (
    <div>
      <div style={{ color: C.mut, fontSize: 13, marginBottom: 14 }}>
        총 {d.total_themes}개 테마 · <b style={{ color: C.text }}>오늘 픽이 겹친 테마(주도 테마)</b>가 위로. 막대=테마 규모, 강조=오늘 픽 수.
      </div>
      <div style={{ display: "grid", gap: 10 }}>
        {d.themes.map((t: any) => (
          <Card key={t.theme} style={{ padding: 14, cursor: "pointer", borderColor: t.pick_hits ? C.laneB + "66" : C.line }} >
            <div onClick={() => setOpen(open === t.theme ? null : t.theme)}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                <b style={{ fontSize: 15 }}>{t.theme}</b>
                {t.pick_hits > 0 && <span style={{ fontSize: 12, color: C.laneB, background: `${C.laneB}1A`, border: `1px solid ${C.laneB}44`, borderRadius: 999, padding: "1px 9px", fontWeight: 600 }}>오늘 픽 {t.pick_hits}</span>}
                <span style={{ marginLeft: "auto", color: C.mut, fontSize: 12 }}>{t.size}종목</span>
              </div>
              <div style={{ height: 6, background: C.surface2, borderRadius: 4, overflow: "hidden" }}>
                <div style={{ width: `${t.size / max * 100}%`, height: "100%", background: t.pick_hits ? C.laneB : C.line }} />
              </div>
            </div>
            {open === t.theme && (
              <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 6 }}>
                {t.members.map((mm: any) => (
                  <span key={mm.code} style={{ fontSize: 12, color: C.mut, background: C.surface2, borderRadius: 6, padding: "3px 8px" }}>{mm.name}</span>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
