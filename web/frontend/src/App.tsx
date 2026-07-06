import { useEffect, useState } from "react";
import { useIsMobile } from "./useIsMobile";
import { api, Freshness } from "./api";
import { C } from "./theme";
import { Overview } from "./pages/Overview";
import { Picks } from "./pages/Picks";
import { ScanFeed } from "./pages/ScanFeed";
import { Performance } from "./pages/Performance";
import { Ops } from "./pages/Ops";
import { Market } from "./pages/Market";
import { Theme } from "./pages/Theme";

// IA 7섹션 (기획 R1). 1차: 개요·픽 구현, 나머지 준비중(정직).
const NAV = [
  { key: "overview", label: "개요", icon: "◆" },
  { key: "picks", label: "픽", icon: "◎" },
  { key: "analyze", label: "스캔·정밀분석", icon: "🔎" },
  { key: "performance", label: "성과", icon: "📈" },
  { key: "market", label: "시장·근거", icon: "🌐" },
  { key: "theme", label: "테마 네트워크", icon: "🕸" },
  { key: "ops", label: "운영", icon: "⚙", admin: true },
];

const MOBILE_MAIN = ["overview", "picks", "analyze", "performance"];

export default function App() {
  const isMobile = useIsMobile();
  const [more, setMore] = useState(false);
  const [tab, setTab] = useState("overview");
  const [fr, setFr] = useState<Freshness>({});
  const [scan, setScan] = useState<{ status: string; progress: number; current: string } | null>(null);
  useEffect(() => { api.freshness().then(setFr).catch(() => {}); }, []);
  useEffect(() => { const t = setInterval(() => api.scanStatus().then(setScan).catch(() => {}), 3000); return () => clearInterval(t); }, []);

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: C.bg, color: C.text, fontFamily: "Pretendard, sans-serif" }}>
      {/* 좌측 네비 (데스크톱) */}
      {!isMobile && <nav style={{ width: 200, borderRight: `1px solid ${C.line}`, padding: "16px 10px", position: "sticky", top: 0, height: "100vh" }}>
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
      </nav>}

      {/* 메인 */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {/* 상단바 */}
        <header style={{ height: isMobile ? 44 : 56, borderBottom: `1px solid ${C.line}`, display: "flex", alignItems: "center", gap: isMobile ? 10 : 16, padding: isMobile ? "0 12px" : "0 22px", fontSize: isMobile ? 11 : 13, overflowX: "auto", whiteSpace: "nowrap" }}>
          {isMobile && <b style={{ color: C.accent, marginRight: 2 }}>◆</b>}
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

        <main style={{ flex: 1, padding: isMobile ? "14px 12px calc(72px + env(safe-area-inset-bottom))" : 22, maxWidth: 1280, width: "100%", margin: "0 auto" }}>
          <h1 style={{ fontSize: isMobile ? 18 : 22, fontWeight: 700, margin: isMobile ? "0 0 12px" : "0 0 18px" }}>{NAV.find((n) => n.key === tab)?.label}</h1>
          {tab === "overview" && <Overview />}
          {tab === "picks" && <Picks />}
          {tab === "analyze" && <ScanFeed />}
          {tab === "performance" && <Performance />}
          {tab === "ops" && <Ops />}
          {tab === "market" && <Market />}
          {tab === "theme" && <Theme />}
        </main>
      </div>

      {/* 하단 탭바 (모바일 앱형) */}
      {isMobile && (
        <>
          {more && (
            <div onClick={() => setMore(false)} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", zIndex: 98 }}>
              <div onClick={(e) => e.stopPropagation()}
                style={{ position: "absolute", bottom: "calc(64px + env(safe-area-inset-bottom))", right: 10, background: C.surface, border: `1px solid ${C.line}`, borderRadius: 14, padding: 8, minWidth: 170 }}>
                {NAV.filter((n) => !MOBILE_MAIN.includes(n.key)).map((n) => (
                  <button key={n.key} onClick={() => { setTab(n.key); setMore(false); }}
                    style={{ display: "flex", gap: 10, alignItems: "center", width: "100%", background: tab === n.key ? C.surface2 : "transparent", color: C.text, border: "none", borderRadius: 10, padding: "12px 14px", fontSize: 14, cursor: "pointer" }}>
                    <span>{n.icon}</span>{n.label}
                  </button>
                ))}
              </div>
            </div>
          )}
          <nav style={{ position: "fixed", left: 0, right: 0, bottom: 0, zIndex: 99, display: "flex", background: C.surface, borderTop: `1px solid ${C.line}`, paddingBottom: "env(safe-area-inset-bottom)" }}>
            {NAV.filter((n) => MOBILE_MAIN.includes(n.key)).map((n) => (
              <button key={n.key} onClick={() => { setTab(n.key); setMore(false); }}
                style={{ flex: 1, background: "none", border: "none", padding: "9px 0 7px", cursor: "pointer", color: tab === n.key ? C.accent : C.mut, display: "flex", flexDirection: "column", alignItems: "center", gap: 3, fontSize: 10 }}>
                <span style={{ fontSize: 17 }}>{n.icon}</span>{n.label.split("·")[0]}
              </button>
            ))}
            <button onClick={() => setMore(!more)}
              style={{ flex: 1, background: "none", border: "none", padding: "9px 0 7px", cursor: "pointer", color: more || !MOBILE_MAIN.includes(tab) ? C.accent : C.mut, display: "flex", flexDirection: "column", alignItems: "center", gap: 3, fontSize: 10 }}>
              <span style={{ fontSize: 17 }}>☰</span>더보기
            </button>
          </nav>
        </>
      )}
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
