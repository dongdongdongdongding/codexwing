import { useEffect, useState } from "react";
import { api, Freshness } from "./api";
import { C } from "./theme";
import { Overview } from "./pages/Overview";
import { Picks } from "./pages/Picks";
import { Analyze } from "./pages/Analyze";
import { Performance } from "./pages/Performance";
import { Ops } from "./pages/Ops";
import { Market } from "./pages/Market";
import { Theme } from "./pages/Theme";

// IA 7섹션 (기획 R1). 1차: 개요·픽 구현, 나머지 준비중(정직).
const NAV = [
  { key: "overview", label: "개요", icon: "◆" },
  { key: "picks", label: "픽", icon: "◎" },
  { key: "analyze", label: "정밀분석", icon: "🔎" },
  { key: "performance", label: "성과", icon: "📈" },
  { key: "market", label: "시장·근거", icon: "🌐" },
  { key: "theme", label: "테마 네트워크", icon: "🕸" },
  { key: "ops", label: "운영", icon: "⚙", admin: true },
];

export default function App() {
  const [tab, setTab] = useState("overview");
  const [fr, setFr] = useState<Freshness>({});
  const [scan, setScan] = useState<{ status: string; progress: number; current: string } | null>(null);
  useEffect(() => { api.freshness().then(setFr).catch(() => {}); }, []);
  useEffect(() => { const t = setInterval(() => api.scanStatus().then(setScan).catch(() => {}), 3000); return () => clearInterval(t); }, []);

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: C.bg, color: C.text, fontFamily: "Pretendard, sans-serif" }}>
      {/* 좌측 네비 */}
      <nav style={{ width: 200, borderRight: `1px solid ${C.line}`, padding: "16px 10px", position: "sticky", top: 0, height: "100vh" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "0 8px 18px" }}>
          <span style={{ color: C.accent, fontSize: 20 }}>◆</span>
          <b style={{ fontSize: 18, letterSpacing: 1 }}>SWING</b>
        </div>
        {NAV.map((n) => (
          <button key={n.key} onClick={() => setTab(n.key)}
            style={{
              display: "flex", alignItems: "center", gap: 10, width: "100%", textAlign: "left",
              background: tab === n.key ? C.surface2 : "transparent", color: tab === n.key ? C.text : C.mut,
              border: "none", borderLeft: `2px solid ${tab === n.key ? C.accent : "transparent"}`,
              borderRadius: 8, padding: "10px 12px", fontSize: 14, cursor: "pointer", marginBottom: 2,
            }}>
            <span style={{ width: 18 }}>{n.icon}</span>{n.label}{n.admin && <span style={{ marginLeft: "auto", fontSize: 11 }}>🔒</span>}
          </button>
        ))}
      </nav>

      {/* 메인 */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {/* 상단바 */}
        <header style={{ height: 56, borderBottom: `1px solid ${C.line}`, display: "flex", alignItems: "center", gap: 16, padding: "0 22px", fontSize: 13 }}>
          <FreshChip label="일봉" v={fr.daily} />
          <FreshChip label="분봉" v={fr.minute} />
          <FreshChip label="수급" v={fr.flow} warnIf={fr.daily} />
          {scan && scan.status === "running" && (
            <span onClick={() => setTab("ops")} style={{ cursor: "pointer", color: C.accent, display: "inline-flex", gap: 6, alignItems: "center" }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: C.accent, display: "inline-block", animation: "none" }} />
              스캔 {scan.progress}% ({scan.current})
            </span>
          )}
          <span style={{ marginLeft: "auto", color: C.mut }}>운영자</span>
        </header>

        <main style={{ flex: 1, padding: 22, maxWidth: 1280, width: "100%", margin: "0 auto" }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 18px" }}>{NAV.find((n) => n.key === tab)?.label}</h1>
          {tab === "overview" && <Overview />}
          {tab === "picks" && <Picks />}
          {tab === "analyze" && <Analyze />}
          {tab === "performance" && <Performance />}
          {tab === "ops" && <Ops />}
          {tab === "market" && <Market />}
          {tab === "theme" && <Theme />}
        </main>
      </div>
    </div>
  );
}

function FreshChip({ label, v, warnIf }: { label: string; v?: string; warnIf?: string }) {
  const stale = warnIf && v && v < warnIf;
  const col = !v ? C.mut : stale ? C.warn : C.up;
  return (
    <span style={{ display: "inline-flex", gap: 5, alignItems: "center", color: col }}>
      <span style={{ color: C.mut }}>{label}</span>{v || "–"}{stale ? " ⚠" : ""}
    </span>
  );
}
