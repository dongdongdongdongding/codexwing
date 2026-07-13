// API 클라이언트 + 타입. /api → FastAPI(프록시).
export interface Pick {
  size_pct_total?: number | null; size_note?: string | null;
  code: string; ticker: string; name: string; market: string;
  lane: string; lane_label: string; kind: string; badge: string;
  signal_class: "A" | "B"; scan_date?: string; buy_date?: string;
  prob?: number | null; alpha?: number | null; entry?: number | null; target?: number | null; target_pct?: number;
  pred_alpha_5d?: number; smart5?: number; rsi14?: number; hold_days?: number;
  // 승격 계약(§7-E) 필드: 선별 티어 / 레짐 상태
  tier?: "PRIMARY" | "CANDIDATE"; tier_threshold?: number; rationale?: string;
  mkt_state?: "RISK_OFF" | "NORMAL" | "UNKNOWN"; mkt_dd20?: number; ev_pred?: number;
}
export interface ContractLane { label: string; n: number; ev_avg?: number; win_pct?: number; worst?: number; }
export interface ContractPerf {
  note: string; lanes: Record<string, ContractLane>;
  selective?: Record<string, { rank1?: { n: number; ev_avg?: number; win_pct?: number }; primary?: { n: number; ev_avg?: number; win_pct?: number } }> | null;
}
export interface Lane { key: string; label: string; kind: string; badge: string; }
export interface Freshness { daily?: string; minute?: string; flow?: string; dart?: string; pead?: string; }
export interface Overview {
  generated_at: string; top_picks: Pick[]; freshness: Freshness; counts: { A: number; B: number };
}
export interface Price { price?: number | null; change_pct?: number | null; status?: string; }
export interface ChartData {
  type: "candle" | "line"; tf: string;
  bars: Array<{ time: number | string; open?: number; high?: number; low?: number; close?: number; value?: number }>;
}
export interface PickDetail {
  code: string; name: string; market: string; in_picks: boolean; pick?: Pick;
  flow?: { frgn_5d: number; orgn_5d: number; asof: string };
  dart?: Array<{ ann: string; type: string }>;
  events?: Array<{ type: string; date: string; d_left: number; note: string }>;
}

// 운영(Vercel): 임시 터널 주소는 재시작마다 바뀌므로 빌드에 굽지 않고 런타임 발견 —
// 같은 오리진의 /tunnel.json(터널 감시 스크립트가 갱신·푸시)을 우선, 실패 시 빌드 env 폴백.
// 로컬 dev(vite)는 "" → /api 프록시 그대로.
const ENV_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");
const baseP: Promise<string> = (async () => {
  if (!import.meta.env.PROD) return "";
  try {
    const r = await fetch("/tunnel.json", { cache: "no-store" });
    if (r.ok) {
      const t = await r.json();
      const u = String(t.api || "").replace(/\/$/, "");
      if (u) return u;
    }
  } catch { /* fall through */ }
  return ENV_BASE;
})();
// 토큰: 백엔드 WEB_API_TOKEN과 일치해야 함. ⚠️ 프론트 번들에 포함되어 사이트 열람자에겐 노출됨
// (드라이브-바이 차단용 경량 게이트). 진짜 비공개는 터널단 인증(Cloudflare Access) 권장.
const TOKEN = (import.meta.env.VITE_API_TOKEN ?? "").trim();
const authHeaders: Record<string, string> = TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {};

const j = async <T>(u: string): Promise<T> => {
  const BASE = await baseP;
  const r = await fetch(BASE + u, { headers: authHeaders });
  if (!r.ok) throw new Error(`${u} ${r.status}`);
  return r.json();
};

export interface TimingTrailPt { d: string; headroom: number; left: number; }
export interface TimingPick { trail?: TimingTrailPt[]; today_best?: boolean; today_best_note?: string; code: string; ticker: string; name: string; lane: string; lane_label: string; kind: string; badge: string; scan_date: string; ref: number; target: number; tp_pct: number; age: number; sessions_left: number; touched: boolean; tier?: string | null; mkt_state?: string | null; prob?: number | null; entry_note: string; current?: number | null; change_pct?: number | null; pos_vs_ref?: number | null; headroom?: number | null; state: string; state_label: string; }
export interface ScanPost { scan_id: string; time: string; source: string; markets: string[]; lanes: string[]; pick_count: number; note?: string | null; }
export interface TickerCard { ticker: string; code: string; name: string; market: string; lane: string; prob?: number | null; score?: number | null; entry?: number | null; }

export interface Analysis {
  code: string; name: string; market: string; regime: string;
  model: { in_a: Pick | null; in_b: Pick | null };
  features: Record<string, number | string | null>;
  flow?: { frgn_5d: number; orgn_5d: number; frgn_20d: number; asof: string };
  events: { dart: Array<{ ann: string; type: string }>; pead: { ann: string; surp_eps: number } | null };
  verdict: { text: string; source: string };
}

export interface LaneAgg { n: number; alpha_mean?: number; alpha_win?: number; abs_mean?: number; abs_win?: number; immature?: number; pending?: number; }
export interface Performance {
  as_of: string; overall: LaneAgg; lanes: Record<string, LaneAgg>;
  b_shadow: { settled: number; open?: number; alpha_mean?: number; alpha_win?: number };
  rows: Array<{ lane: string; date: string; code: string; name: string; ret: number; alpha: number | null; days: number }>;
}
export interface ArchiveRow { date: string; run_id: string; code: string; name: string; market: string; lane: string; entry: number | null; prob: number | null; ret: number | null; result: string; }
export interface Archive { count: number; offset: number; limit: number; rows: ArchiveRow[]; note?: string; }

export const api = {
  overview: (top = 6) => j<Overview>(`/api/overview?top=${top}`),
  analyze: (code: string) => j<Analysis>(`/api/analyze/${code}`),
  performance: () => j<Performance>(`/api/performance`),
  contractPerformance: () => j<ContractPerf>(`/api/contract-performance`),
  opsStatus: () => j<any>(`/api/ops/status`),
  scanStatus: () => j<{ status: string; progress: number; current: string; target?: string; steps: Array<{ step: string; ok: boolean; note: string }>; finished_at?: string }>(`/api/ops/scan`),
  scanTargets: () => j<{ targets: Array<{ key: string; label: string }> }>(`/api/ops/scan-targets`),
  scanStart: async (target = "all") => fetch(`${await baseP}/api/ops/scan?target=${target}`, { method: "POST", headers: authHeaders }).then((r) => r.json()),
  market: () => j<any>(`/api/market`),
  theme: () => j<any>(`/api/theme`),
  scans: (source = "", market = "") => j<{ count: number; scans: ScanPost[] }>(`/api/scans?source=${source}&market=${market}&limit=60`),
  scanDetail: (id: string) => j<{ scan_id: string; time: string; cards: TickerCard[]; notes?: string[] }>(`/api/scans/${encodeURIComponent(id)}`),
  scanAnalyze: (id: string, ticker: string) => j<Analysis & { scan_id: string; cached_at: string }>(`/api/scans/${encodeURIComponent(id)}/analyze/${ticker}`),
  archive: (q: { from?: string; to?: string; market?: string; ticker?: string; limit?: number; offset?: number } = {}) =>
    j<Archive>(`/api/archive?date_from=${q.from || ""}&date_to=${q.to || ""}&market=${q.market || ""}&ticker=${q.ticker || ""}&limit=${q.limit || 100}&offset=${q.offset || 0}`),
  picks: (lane = "") => j<{ count: number; picks: Pick[] }>(`/api/picks?lane=${lane}`),
  lanes: () => j<{ lanes: Lane[] }>(`/api/lanes`),
  prices: (codes: string[]) => j<Record<string, Price>>(`/api/prices?codes=${codes.join(",")}`),
  chart: (code: string, tf: "day" | "minute") => j<ChartData>(`/api/chart?code=${code}&tf=${tf}`),
  buyTiming: (days = 5) => j<{ days: number; asof: string; picks: TimingPick[] }>(`/api/buy-timing?days=${days}`),
  detail: (code: string) => j<PickDetail>(`/api/picks/${code}`),
  freshness: () => j<Freshness>(`/api/health/freshness`),
};
