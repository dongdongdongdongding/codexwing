import { useState } from "react";
import { api, Analysis } from "../api";
import { C, fmt, pct, signColor } from "../theme";
import { Card, MarketBadge, LaneBadge, Term } from "../components/ui";
import { Chart } from "../components/Chart";

// ③ 정밀분석 — 우리 데이터로 한 종목 종합(yfinance 폐기). A모델·차트·수급·이벤트·레짐·Gemini 종합.
export function Analyze() {
  const [code, setCode] = useState("");
  const [data, setData] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const run = () => {
    const c = code.trim().replace(/\.(KS|KQ)$/i, "");
    if (!c) return;
    setLoading(true); setErr(""); setData(null);
    api.analyze(c).then((d) => { setData(d); setLoading(false); }).catch(() => { setErr("분석 실패 — 코드를 확인하세요."); setLoading(false); });
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 18, maxWidth: 460 }}>
        <input value={code} onChange={(e) => setCode(e.target.value)} onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="종목코드 입력 (예: 005930)"
          style={{ flex: 1, background: C.surface, border: `1px solid ${C.line}`, borderRadius: 8, padding: "10px 12px", color: C.text, fontSize: 14 }} />
        <button onClick={run} style={{ background: C.accent, color: "#fff", border: "none", borderRadius: 8, padding: "0 18px", fontWeight: 600, cursor: "pointer" }}>분석</button>
      </div>
      <div style={{ color: C.mut, fontSize: 12, marginBottom: 18 }}>
        yfinance가 아니라 우리 데이터(일봉·분봉·<Term k="수급">수급</Term>·공시·실적·모델)로 분석합니다. 결과는 정보이며 투자권유가 아닙니다.
      </div>

      {loading && <div style={{ height: 200, background: C.surface, borderRadius: 12, opacity: .5 }} />}
      {err && <div style={{ color: C.down }}>{err}</div>}

      {data && (
        <div style={{ display: "grid", gap: 16 }}>
          {/* 헤더 + 모델판정 */}
          <Card>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
              <b style={{ fontSize: 22 }}>{data.name}</b>
              <span style={{ color: C.mut }}>{data.code}</span>
              <MarketBadge market={data.market} />
              <span style={{ color: C.mut, fontSize: 13 }}>· <Term k="레짐">레짐</Term> {data.regime}</span>
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <ModelChip on={!!data.model.in_a} label={data.model.in_a ? `A 픽 · ${data.model.in_a.lane_label} ${data.model.in_a.prob}%` : "A 미픽"} pick={data.model.in_a} />
              <ModelChip on={!!data.model.in_b} label={data.model.in_b ? "B 시장중립 픽" : "B 미픽"} pick={data.model.in_b} />
            </div>
            {!data.model.in_a && !data.model.in_b && (
              <div style={{ color: C.warn, fontSize: 12, marginTop: 10 }}>※ 오늘 어느 모델도 이 종목을 고르지 않았습니다(웹이 임의 추천하지 않음).</div>
            )}
          </Card>

          {/* 종합 판정 (Gemini) */}
          <Card style={{ borderColor: C.accent + "55" }}>
            <div style={{ color: C.mut, fontSize: 12, marginBottom: 8, fontWeight: 600 }}>종합 판정 <span style={{ color: C.mut }}>({data.verdict.source})</span></div>
            <div style={{ fontSize: 14, lineHeight: 1.7 }}>{data.verdict.text}</div>
          </Card>

          {/* 차트 */}
          <Card><div style={{ color: C.mut, fontSize: 12, marginBottom: 8, fontWeight: 600 }}>가격 차트</div><Chart code={data.code} height={300} /></Card>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {/* 지표 */}
            <Card>
              <div style={{ color: C.mut, fontSize: 12, marginBottom: 10, fontWeight: 600 }}>가격·지표 ({data.features.asof})</div>
              <Kv k="RSI(14)" v={fmt(data.features.rsi14 as number, 1)} />
              <Kv k="20일 수익" v={pct(data.features.ret_20d as number, 1)} c={signColor(data.features.ret_20d as number)} />
              <Kv k={<>20일 고가이격</>} v={pct(data.features.dist_hi20 as number, 1)} />
              <Kv k="변동성(ATR%)" v={fmt(data.features.atr_pct as number, 1)} />
              <Kv k="볼린저 %B" v={fmt(data.features.bb_pctb as number, 2)} />
            </Card>
            {/* 수급·이벤트 */}
            <Card>
              <div style={{ color: C.mut, fontSize: 12, marginBottom: 10, fontWeight: 600 }}><Term k="수급">수급</Term> · 이벤트</div>
              {data.flow ? (<>
                <Kv k="외국인 5일" v={fmt(data.flow.frgn_5d)} c={signColor(data.flow.frgn_5d)} />
                <Kv k="기관 5일" v={fmt(data.flow.orgn_5d)} c={signColor(data.flow.orgn_5d)} />
                <Kv k="외국인 20일" v={fmt(data.flow.frgn_20d)} c={signColor(data.flow.frgn_20d)} />
                <div style={{ color: C.mut, fontSize: 11 }}>수급 기준 {data.flow.asof}</div>
              </>) : <div style={{ color: C.mut, fontSize: 13 }}>수급 데이터 없음</div>}
              <div style={{ height: 8 }} />
              {data.events.pead && <Kv k={<><Term k="PEAD">실적</Term> 서프라이즈</>} v={`${data.events.pead.surp_eps}% (${data.events.pead.ann})`} />}
              <Kv k="공시" v={data.events.dart.length ? data.events.dart.map((x) => x.type).join(", ") : "없음"} />
            </Card>
          </div>
          <div style={{ color: C.mut, fontSize: 11 }}>※ 확률·수익은 과거 기준이며 미래를 보장하지 않습니다. 데이터 신선도(특히 수급)를 확인하세요.</div>
        </div>
      )}
    </div>
  );
}

const ModelChip = ({ on, label }: { on: boolean; label: string; pick: any }) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, padding: "6px 12px", borderRadius: 8,
    color: on ? C.up : C.mut, background: on ? `${C.up}1A` : C.surface2, border: `1px solid ${on ? C.up + "55" : C.line}` }}>{label}</span>
);
const Kv = ({ k, v, c }: { k: React.ReactNode; v: React.ReactNode; c?: string }) => (
  <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", fontSize: 13 }}>
    <span style={{ color: C.mut }}>{k}</span><span style={{ color: c, fontVariantNumeric: "tabular-nums" }}>{v}</span>
  </div>
);
