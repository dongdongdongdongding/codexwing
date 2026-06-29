// API 클라이언트 + 타입. /api → FastAPI(프록시).
export interface Pick {
  code: string; ticker: string; name: string; market: string;
  lane: string; lane_label: string; kind: string; badge: string;
  signal_class: "A" | "B"; scan_date?: string; buy_date?: string;
  prob?: number | null; alpha?: number | null; entry?: number | null; target?: number | null; target_pct?: number;
  pred_alpha_5d?: number; smart5?: number; rsi14?: number; hold_days?: number;
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
}

const j = async <T>(u: string): Promise<T> => {
  const r = await fetch(u);
  if (!r.ok) throw new Error(`${u} ${r.status}`);
  return r.json();
};

export interface Analysis {
  code: string; name: string; market: string; regime: string;
  model: { in_a: Pick | null; in_b: Pick | null };
  features: Record<string, number | string | null>;
  flow?: { frgn_5d: number; orgn_5d: number; frgn_20d: number; asof: string };
  events: { dart: Array<{ ann: string; type: string }>; pead: { ann: string; surp_eps: number } | null };
  verdict: { text: string; source: string };
}

export interface LaneAgg { n: number; alpha_mean?: number; alpha_win?: number; abs_mean?: number; abs_win?: number; immature?: number; }
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
  archive: (q: { from?: string; to?: string; market?: string; ticker?: string; limit?: number; offset?: number } = {}) =>
    j<Archive>(`/api/archive?date_from=${q.from || ""}&date_to=${q.to || ""}&market=${q.market || ""}&ticker=${q.ticker || ""}&limit=${q.limit || 100}&offset=${q.offset || 0}`),
  picks: (lane = "") => j<{ count: number; picks: Pick[] }>(`/api/picks?lane=${lane}`),
  lanes: () => j<{ lanes: Lane[] }>(`/api/lanes`),
  prices: (codes: string[]) => j<Record<string, Price>>(`/api/prices?codes=${codes.join(",")}`),
  chart: (code: string, tf: "day" | "minute") => j<ChartData>(`/api/chart?code=${code}&tf=${tf}`),
  detail: (code: string) => j<PickDetail>(`/api/picks/${code}`),
  freshness: () => j<Freshness>(`/api/health/freshness`),
};
