import { useEffect, useRef, useState } from "react";
import { createChart, ColorType, CrosshairMode, IChartApi } from "lightweight-charts";
import { api, ChartData } from "../api";
import { C } from "../theme";

// 토스급 분봉/일봉 차트 (기획 R6) — 미니멀·부드러운 크로스헤어·기간토글·견고.
export interface PriceLine { price: number; label: string; color: string; }
export function Chart({ code, height = 260, lines }: { code: string; height?: number; lines?: PriceLine[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [tf, setTf] = useState<"day" | "minute">("day");
  const [loading, setLoading] = useState(true);
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      height,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: C.mut, fontFamily: "Pretendard, sans-serif" },
      grid: { vertLines: { visible: false }, horzLines: { color: C.line, style: 1 } },
      rightPriceScale: { borderColor: C.line },
      timeScale: { borderColor: C.line, timeVisible: tf === "minute", secondsVisible: false },
      crosshair: { mode: CrosshairMode.Normal, vertLine: { color: C.mut, width: 1, style: 2 }, horzLine: { color: C.mut, width: 1, style: 2 } },
      handleScroll: true, handleScale: true,
    });
    chartRef.current = chart;
    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current!.clientWidth }));
    ro.observe(ref.current);

    setLoading(true); setEmpty(false);
    api.chart(code, tf).then((d: ChartData) => {
      if (!d.bars.length) { setEmpty(true); setLoading(false); return; }
      let series: any;
      if (d.type === "candle") {
        series = chart.addCandlestickSeries({ upColor: C.up, downColor: C.down, borderVisible: false, wickUpColor: C.up, wickDownColor: C.down });
        series.setData(d.bars as any);
      } else {
        series = chart.addAreaSeries({ lineColor: C.accent, topColor: `${C.accent}33`, bottomColor: `${C.accent}05`, lineWidth: 2 });
        series.setData(d.bars as any);
      }
      (lines || []).forEach((l) => series.createPriceLine({ price: l.price, color: l.color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: l.label }));
      chart.timeScale().fitContent();
      setLoading(false);
    }).catch(() => { setEmpty(true); setLoading(false); });

    return () => { ro.disconnect(); chart.remove(); };
  }, [code, tf, height, JSON.stringify(lines || [])]);

  return (
    <div>
      <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
        {(["day", "minute"] as const).map((t) => (
          <button key={t} onClick={() => setTf(t)} style={tfBtn(t === tf)}>{t === "day" ? "일봉" : "분봉"}</button>
        ))}
        {loading && <span style={{ color: C.mut, fontSize: 12, alignSelf: "center" }}>불러오는 중…</span>}
        {empty && <span style={{ color: C.warn, fontSize: 12, alignSelf: "center" }}>차트 데이터 없음</span>}
      </div>
      <div ref={ref} style={{ width: "100%", height }} />
    </div>
  );
}

const tfBtn = (on: boolean): React.CSSProperties => ({
  background: on ? C.accent : C.surface2, color: on ? "#fff" : C.mut,
  border: `1px solid ${on ? C.accent : C.line}`, borderRadius: 7, padding: "4px 12px",
  fontSize: 12, cursor: "pointer", fontWeight: 600,
});
