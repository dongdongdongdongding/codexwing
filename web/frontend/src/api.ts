// API 클라이언트 + 타입. /api → FastAPI(프록시).
export interface Pick {
  code: string; ticker: string; name: string; market: string;
  lane: string; lane_label: string; kind: string; badge: string;
  signal_class: "A" | "B"; scan_date?: string;
  prob?: number | null; entry?: number | null; target?: number | null; target_pct?: number;
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

export const api = {
  overview: (top = 6) => j<Overview>(`/api/overview?top=${top}`),
  picks: (lane = "") => j<{ count: number; picks: Pick[] }>(`/api/picks?lane=${lane}`),
  lanes: () => j<{ lanes: Lane[] }>(`/api/lanes`),
  prices: (codes: string[]) => j<Record<string, Price>>(`/api/prices?codes=${codes.join(",")}`),
  chart: (code: string, tf: "day" | "minute") => j<ChartData>(`/api/chart?code=${code}&tf=${tf}`),
  detail: (code: string) => j<PickDetail>(`/api/picks/${code}`),
  freshness: () => j<Freshness>(`/api/health/freshness`),
};
