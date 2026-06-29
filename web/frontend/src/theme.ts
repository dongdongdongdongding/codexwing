// 디자인 토큰 — 기획 04_design_system "정직한 퀀트 터미널". 단일 진실원.
export const C = {
  bg: "#0B0E14",
  surface: "#141A24",
  surface2: "#1B2330",
  line: "#243044",
  text: "#E6EDF3",
  mut: "#8B98A9",
  up: "#26A269", // 상승/이익/통과
  down: "#E0526A", // 하락/손실
  accent: "#4C8DFF", // 브랜드/링크/장중
  warn: "#E3B341", // 주의/지연/낙관
  laneSwing: "#26A269",
  laneIntraday: "#4C8DFF",
  laneB: "#A371F7",
} as const;

export const RADIUS = { card: 10, panel: 12, pill: 999 };
export const FONT_NUM = "'Inter', ui-monospace, SFMono-Regular, Menlo, monospace";

// 의미 색: 부호 기반
export const signColor = (x?: number | null) =>
  x == null ? C.mut : x > 0 ? C.up : x < 0 ? C.down : C.mut;

export const fmt = (x?: number | null, d = 0) =>
  x == null ? "–" : Number(x).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });

export const pct = (x?: number | null, d = 2) =>
  x == null ? "–" : `${x > 0 ? "+" : ""}${fmt(x, d)}%`;
