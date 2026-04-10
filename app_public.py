"""
AI Quant Pro — Public Edition
================================
Clean, premium web scanner for public use.
Features: Market Scanner + Deep Analysis
"""
import concurrent.futures
import streamlit as st
import os
from dotenv import load_dotenv
load_dotenv()
load_dotenv(".env.local")

from modules import quant_analysis, news_analysis, market_intelligence
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import traceback

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="AI Quant Pro",
    layout="wide",
    page_icon="🧠",
    initial_sidebar_state="collapsed"
)

# ============================================================
# PREMIUM CSS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
}
.main .block-container {
    padding: 1.5rem 2rem;
    max-width: 1400px;
}

/* Header */
.hero-header {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 24px;
    border: 1px solid rgba(255,255,255,0.08);
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
    pointer-events: none;
}
.hero-header h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 800;
    background: linear-gradient(90deg, #a78bfa, #818cf8, #6366f1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
}
.hero-header .subtitle {
    color: rgba(255,255,255,0.55);
    font-size: 14px;
    margin-top: 6px;
    font-weight: 400;
}

/* Regime Badge */
.regime-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 600;
    margin-top: 12px;
}
.regime-risk-on {
    background: rgba(52,211,153,0.12);
    color: #34d399;
    border: 1px solid rgba(52,211,153,0.25);
}
.regime-risk-off {
    background: rgba(248,113,113,0.12);
    color: #f87171;
    border: 1px solid rgba(248,113,113,0.25);
}
.regime-neutral {
    background: rgba(251,191,36,0.12);
    color: #fbbf24;
    border: 1px solid rgba(251,191,36,0.25);
}
.regime-crash {
    background: rgba(239,68,68,0.2);
    color: #ef4444;
    border: 1px solid rgba(239,68,68,0.4);
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

/* Result Cards */
.result-card {
    background: rgba(30,30,46,0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
}
.result-card:hover {
    border-color: rgba(99,102,241,0.3);
    transform: translateY(-1px);
}

/* Metric Cards */
.metric-card {
    background: linear-gradient(135deg, rgba(30,30,50,0.8), rgba(20,20,40,0.9));
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
}
.metric-card .label {
    color: rgba(255,255,255,0.45);
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.metric-card .value {
    font-size: 28px;
    font-weight: 700;
    margin-top: 4px;
}
.metric-card .delta {
    font-size: 12px;
    margin-top: 2px;
}

/* Verdict Colors */
.verdict-strong-buy { color: #34d399; }
.verdict-buy { color: #60a5fa; }
.verdict-neutral { color: #fbbf24; }
.verdict-sell { color: #f87171; }
.verdict-strong-sell { color: #ef4444; }

/* Alpha Score Ring */
.alpha-ring {
    width: 100px;
    height: 100px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    font-weight: 800;
    margin: 0 auto;
}

/* Clean table */
.stDataFrame { border-radius: 12px; overflow: hidden; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 600;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Signal tag */
.signal-tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}
.signal-strong-buy { background: rgba(52,211,153,0.15); color: #34d399; }
.signal-buy { background: rgba(96,165,250,0.15); color: #60a5fa; }
.signal-neutral { background: rgba(251,191,36,0.15); color: #fbbf24; }
.signal-sell { background: rgba(248,113,113,0.15); color: #f87171; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER + MARKET REGIME
# ============================================================
if 'market_regime' not in st.session_state:
    with st.spinner(""):
        try:
            q_r = quant_analysis.QuantStrategy("^GSPC")
            st.session_state['market_regime'] = q_r.get_market_regime()
        except:
            st.session_state['market_regime'] = {'status': 'NEUTRAL', 'score': 50, 'vix': 0}

regime = st.session_state['market_regime']
r_status = regime['status']
r_map = {
    'RISK_ON': ('☀️ Risk-On', 'regime-risk-on', '강세장 — 공격적 전략 활성'),
    'RISK_OFF': ('⛈️ Risk-Off', 'regime-risk-off', '약세장 — 방어적 전략 활성'),
    'CRASH': ('🚨 Crash Alert', 'regime-crash', '급락장 — 현금 비중 확대 권고'),
    'NEUTRAL': ('⚖️ Neutral', 'regime-neutral', '보합장 — 균형 전략'),
}
r_label, r_class, r_desc = r_map.get(r_status, r_map['NEUTRAL'])

st.markdown(f"""
<div class="hero-header">
    <h1>🧠 AI Quant Pro</h1>
    <div class="subtitle">ML 기반 실시간 주식 스캐너 · V5.1 Voting Ensemble</div>
    <div class="regime-badge {r_class}">{r_label} · VIX {regime.get('vix', 0):.1f} · {r_desc}</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# TABS
# ============================================================
tab1, tab2 = st.tabs(["📡 마켓 스캐너", "🔬 심층 분석"])

# ============================================================
# TAB 1: MARKET SCANNER
# ============================================================
with tab1:
    col1, col2, col3 = st.columns([2, 1, 1])
    market = col1.selectbox("시장", ["KOSPI", "KOSDAQ", "NASDAQ", "S&P500"], label_visibility="collapsed")
    max_scan = col2.number_input("스캔 수", 10, 3500, 50, step=10, label_visibility="collapsed")
    strength = col3.selectbox("필터", ["표준", "엄격", "느슨"], label_visibility="collapsed")
    
    if st.button("🚀 스캔 시작", type="primary", width='stretch'):
        progress = st.progress(0)
        status = st.empty()
        
        tickers_dict = quant_analysis.QuantStrategy.get_market_tickers(market)
        ticker_list = list(tickers_dict.keys())
        status.markdown(f"<div style='color:rgba(255,255,255,0.5);font-size:13px;'>📡 {len(ticker_list)}개 종목 로드 완료</div>", unsafe_allow_html=True)
        
        # Market Intelligence
        gemini_key = os.environ.get('GEMINI_API_KEY', '')
        intel_data = market_intelligence.get_market_intelligence(market, gemini_key)
        
        if intel_data and intel_data.get('source') == 'gemini':
            with st.expander(f"🧠 AI 시장 인텔리전스", expanded=True):
                sent = intel_data.get('market_sentiment', 'NEUTRAL')
                sent_icon = {'BULLISH': '🟢', 'BEARISH': '🔴', 'MIXED': '🟡', 'NEUTRAL': '⚪'}.get(sent, '⚪')
                st.markdown(f"**{sent_icon} {sent}** — {intel_data.get('key_insight', '')}")
                
                themes = intel_data.get('themes', [])
                if themes:
                    for t in themes[:3]:
                        impact = {'POSITIVE': '📈', 'NEGATIVE': '📉', 'MIXED': '↔️'}.get(t.get('impact', ''), '📌')
                        st.caption(f"{impact} {t.get('theme', '')}: {t.get('description', '')}")
        
        results = []
        
        def scan_worker(sym):
            try:
                stock_name = tickers_dict.get(sym, sym)
                qs = quant_analysis.QuantStrategy(sym)
                if not qs.fetch_data(period="5y"):
                    return None
                qs.calculate_indicators()
                qs.check_signals()
                
                if qs.df is not None and 'Signal' in qs.df.columns:
                    recent = qs.df['Signal'].tail(10)
                    if recent.sum() > 0:
                        stats = qs.backtest()
                        
                        surge = qs.detect_pre_surge_signals()
                        strategy_type = surge.get('strategy_type', 'Wait')
                        
                        try:
                            wr = float(stats.get("Win Rate", "0").strip('%'))
                            pf = float(stats.get("Profit Factor", "0"))
                            
                            if strength == "엄격":
                                if strategy_type != 'REVERSAL' and (wr < 60 or pf < 1.5):
                                    return None
                            elif strength == "표준":
                                if strategy_type != 'REVERSAL' and (wr < 40 and pf < 0.8):
                                    return None
                        except:
                            wr, pf = 0, 0
                        
                        ml_pred = qs.get_ml_prediction()
                        ml_prob = ml_pred.get('prob', 50)
                        signal = ml_pred.get('signal', 'NEUTRAL')
                        raw_prob = ml_pred.get('raw_prob', ml_prob)
                        
                        whale_data = qs.get_investor_flows()
                        whale_score = whale_data.get('whale_score', 0)
                        
                        alpha = qs.calculate_alpha_score_v30(
                            wr/100, pf, 0,
                            whale_score=whale_score,
                            macro_status=r_status,
                            ml_prob=ml_prob
                        )
                        
                        # News adjustment
                        news_adj = market_intelligence.calculate_news_adjustment(
                            stock_name, sym, '', intel_data
                        )
                        alpha = min(100, max(0, alpha + news_adj['score_adjustment']))
                        
                        position = qs.get_price_position()
                        latest = qs.df.iloc[-1]
                        
                        # Verdict
                        ml_threshold = ml_pred.get('threshold', 50.0)
                        if alpha >= 80 and ml_prob >= 60:
                            verdict = "🟢 강력매수"
                        elif alpha >= 60 and ml_prob >= 50:
                            verdict = "🔵 매수"
                        elif alpha >= 50 or signal == "NEUTRAL":
                            verdict = "🟡 관망"
                        elif signal in ("SELL", "STRONG_SELL"):
                            verdict = "🔴 매도"
                        else:
                            verdict = "🟡 관망"
                        
                        strategy_tag = "📈 모멘텀"
                        if surge.get('is_pre_surge'):
                            strategy_tag = f"🎣 {surge.get('type', 'Reversal')}"
                        
                        news_tag = ""
                        if news_adj['is_beneficiary']:
                            news_tag = "🔥 수혜"
                        elif news_adj['is_victim']:
                            news_tag = "⚠️ 피해"
                        
                        return {
                            "종목": f"{stock_name}",
                            "티커": sym,
                            "판정": verdict,
                            "Alpha": int(alpha),
                            "AI신호": signal,
                            "AI확률": f"{ml_prob:.0f}%",
                            "수급": f"{whale_score}",
                            "승률": f"{wr:.0f}%",
                            "전략": strategy_tag,
                            "뉴스": news_tag,
                            "위치": position,
                            "가격": f"{latest['Close']:,.0f}" if '.KS' in sym or '.KQ' in sym else f"${latest['Close']:,.2f}",
                        }
            except Exception as e:
                return None
            return None
        
        # Parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(scan_worker, t): t for t in ticker_list[:max_scan]}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                sym = futures[future]
                try:
                    data = future.result()
                    if data:
                        results.append(data)
                except:
                    pass
                progress.progress((i + 1) / max_scan)
                name = tickers_dict.get(sym, sym)
                status.markdown(f"<div style='color:rgba(255,255,255,0.4);font-size:12px;'>스캔 중 [{i+1}/{max_scan}] {name}</div>", unsafe_allow_html=True)
        
        progress.empty()
        status.empty()
        
        if results:
            df_r = pd.DataFrame(results)
            try:
                df_r = df_r.sort_values('Alpha', ascending=False)
            except:
                pass
            
            # Summary stats
            buy_count = sum(1 for r in results if '매수' in r['판정'])
            sell_count = sum(1 for r in results if '매도' in r['판정'])
            watch_count = sum(1 for r in results if '관망' in r['판정'])
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("발견 종목", f"{len(results)}개")
            c2.metric("매수 신호", f"{buy_count}개", delta=None)
            c3.metric("관망", f"{watch_count}개")
            c4.metric("매도 신호", f"{sell_count}개")
            
            st.dataframe(
                df_r,
                width='stretch',
                height=min(600, 40 + len(df_r) * 35),
                column_config={
                    "Alpha": st.column_config.ProgressColumn("Alpha", min_value=0, max_value=100, format="%d"),
                    "수급": st.column_config.NumberColumn("수급", format="%d점"),
                }
            )
            
            # CSV Download
            csv = df_r.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 결과 다운로드 (CSV)", csv, "scan_results.csv", "text/csv", width='stretch')
        else:
            st.info("조건에 맞는 종목을 찾지 못했습니다.")

# ============================================================
# TAB 2: DEEP ANALYSIS
# ============================================================
with tab2:
    col_in, col_btn = st.columns([4, 1])
    ticker_input = col_in.text_input("종목 코드", value="", placeholder="예: AAPL, NVDA, 005930", label_visibility="collapsed")
    run_analysis = col_btn.button("🔬 분석", type="primary", width='stretch')
    
    if ticker_input and run_analysis:
        ticker = ticker_input.strip().upper()
        if ticker.isdigit() and len(ticker) == 6:
            ticker = f"{ticker}.KS"
        
        with st.spinner(f"'{ticker}' 심층 분석 중..."):
            # Get name
            stock_name = ticker
            try:
                t_info = quant_analysis.yf.Ticker(ticker).info
                stock_name = t_info.get('shortName') or t_info.get('longName') or ticker
            except:
                pass
            
            qs = quant_analysis.QuantStrategy(ticker)
            if qs.fetch_data(period="max"):
                qs.calculate_indicators()
                qs.check_signals()
                stats = qs.backtest()
                setup = qs.get_trade_setup()
                latest = qs.df.iloc[-1]
                
                is_kr = ".KS" in ticker or ".KQ" in ticker
                cur = "₩" if is_kr else "$"
                fmt = "{:,.0f}" if is_kr else "{:,.2f}"
                
                # ML Prediction
                ml_pred = qs.get_ml_prediction()
                ml_prob = ml_pred.get('prob', 50)
                signal = ml_pred.get('signal', 'NEUTRAL')
                raw_prob = ml_pred.get('raw_prob', ml_prob)
                
                # Whale + Macro + News
                whale = qs.get_investor_flows()
                try:
                    macro = qs.get_macro_metrics()
                except:
                    macro = {'status': r_status}
                
                n_score = 0
                try:
                    na = news_analysis.NewsAnalyzer(ticker)
                    nr = na.get_news_sentiment()
                    n_score = nr.get('score', 0)
                except:
                    pass
                
                sector = qs.get_sector_performance()
                
                # Parse stats
                try: wr_val = float(stats.get("Win Rate", "0").strip('%')) / 100
                except: wr_val = 0
                try: pf_val = float(stats.get("Profit Factor", "0"))
                except: pf_val = 0
                
                curr_price = float(qs.df['Close'].iloc[-1])
                target_price = setup.get('Target Price', 0)
                ai_ret = ((target_price - curr_price) / curr_price * 100) if curr_price > 0 else 0
                
                alpha = qs.calculate_alpha_score_v30(
                    wr_val, pf_val, ai_ret,
                    whale_score=whale.get('whale_score', 0),
                    sector_data=sector,
                    macro_status=macro.get('status', 'NEUTRAL'),
                    ml_prob=ml_prob
                )
                
                # ==========================
                # HEADER + ALPHA RING
                # ==========================
                st.markdown(f"## {stock_name}")
                st.caption(f"{ticker} · {cur}{fmt.format(curr_price)}")
                
                # Signal color
                signal_colors = {
                    'STRONG_BUY': ('#34d399', '강력매수'),
                    'BUY': ('#60a5fa', '매수'),
                    'NEUTRAL': ('#fbbf24', '관망'),
                    'SELL': ('#f87171', '매도'),
                    'STRONG_SELL': ('#ef4444', '강력매도'),
                }
                sig_color, sig_label = signal_colors.get(signal, ('#fbbf24', '관망'))
                
                alpha_color = '#34d399' if alpha >= 70 else '#60a5fa' if alpha >= 50 else '#fbbf24' if alpha >= 35 else '#f87171'
                
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.markdown(f"""<div class="metric-card">
                    <div class="label">Alpha Score</div>
                    <div class="value" style="color:{alpha_color}">{alpha}</div>
                    <div class="delta">/ 100</div>
                </div>""", unsafe_allow_html=True)
                
                m2.markdown(f"""<div class="metric-card">
                    <div class="label">AI 신호</div>
                    <div class="value" style="color:{sig_color};font-size:20px">{sig_label}</div>
                    <div class="delta">{ml_prob:.1f}% (raw: {raw_prob:.1f}%)</div>
                </div>""", unsafe_allow_html=True)
                
                m3.markdown(f"""<div class="metric-card">
                    <div class="label">수급 점수</div>
                    <div class="value">{whale.get('whale_score', 0)}</div>
                    <div class="delta">외국인/기관</div>
                </div>""", unsafe_allow_html=True)
                
                m4.markdown(f"""<div class="metric-card">
                    <div class="label">승률</div>
                    <div class="value">{wr_val*100:.0f}%</div>
                    <div class="delta">PF {pf_val:.1f}</div>
                </div>""", unsafe_allow_html=True)
                
                quad = sector.get('quadrant', 'N/A')
                quad_color = '#34d399' if quad == 'Leading' else '#60a5fa' if quad == 'Improving' else '#fbbf24' if quad == 'Weakening' else '#f87171'
                m5.markdown(f"""<div class="metric-card">
                    <div class="label">섹터 위치</div>
                    <div class="value" style="color:{quad_color};font-size:16px">{quad}</div>
                    <div class="delta">RRG 기준</div>
                </div>""", unsafe_allow_html=True)
                
                st.divider()
                
                # ==========================
                # TRADE SETUP
                # ==========================
                st.markdown("### ⚡ 매매 전략")
                
                entry_min = setup.get('Entry Min', setup.get('Entry Price', 0))
                entry_max = setup.get('Entry Max', entry_min)
                stop_loss = setup.get('Stop Loss', 0)
                
                upside = ((target_price - curr_price) / curr_price * 100) if curr_price > 0 else 0
                downside = ((curr_price - stop_loss) / curr_price * 100) if curr_price > 0 and stop_loss > 0 else 0
                rr = upside / downside if downside > 0 else 0
                
                t1, t2, t3, t4 = st.columns(4)
                
                entry_str = f"{cur}{fmt.format(entry_min)}~{fmt.format(entry_max)}" if entry_max > entry_min * 1.001 else f"{cur}{fmt.format(entry_min)}"
                t1.metric("진입가", entry_str)
                t2.metric("목표가", f"{cur}{fmt.format(target_price)}", f"+{upside:.1f}%")
                t3.metric("손절가", f"{cur}{fmt.format(stop_loss)}", f"-{downside:.1f}%", delta_color="inverse")
                t4.metric("손익비", f"{rr:.2f}", delta_color="normal" if rr > 1.5 else "off")
                
                st.divider()
                
                # ==========================
                # CANDLESTICK CHART
                # ==========================
                st.markdown("### 📊 차트")
                
                chart_df = qs.df.tail(120)
                
                fig = make_subplots(
                    rows=2, cols=1, shared_xaxes=True,
                    vertical_spacing=0.03,
                    row_heights=[0.7, 0.3]
                )
                
                fig.add_trace(go.Candlestick(
                    x=chart_df.index,
                    open=chart_df['Open'],
                    high=chart_df['High'],
                    low=chart_df['Low'],
                    close=chart_df['Close'],
                    name='Price',
                    increasing_line_color='#34d399',
                    decreasing_line_color='#f87171',
                ), row=1, col=1)
                
                # MAs
                for ma, color in [('MA20', '#60a5fa'), ('MA50', '#fbbf24'), ('MA200', '#a78bfa')]:
                    if ma in chart_df.columns:
                        fig.add_trace(go.Scatter(
                            x=chart_df.index, y=chart_df[ma],
                            name=ma, line=dict(width=1, color=color),
                            opacity=0.7
                        ), row=1, col=1)
                
                # Bollinger Bands
                if 'BB_Upper' in chart_df.columns:
                    fig.add_trace(go.Scatter(
                        x=chart_df.index, y=chart_df['BB_Upper'],
                        name='BB Upper', line=dict(width=0.5, color='rgba(147,197,253,0.3)'),
                        showlegend=False
                    ), row=1, col=1)
                    fig.add_trace(go.Scatter(
                        x=chart_df.index, y=chart_df['BB_Lower'],
                        name='BB Lower', line=dict(width=0.5, color='rgba(147,197,253,0.3)'),
                        fill='tonexty', fillcolor='rgba(147,197,253,0.04)',
                        showlegend=False
                    ), row=1, col=1)
                
                # Entry/Target/SL lines
                fig.add_hline(y=target_price, line_dash="dot", line_color="#34d399", annotation_text="목표가", row=1, col=1)
                fig.add_hline(y=stop_loss, line_dash="dot", line_color="#f87171", annotation_text="손절가", row=1, col=1)
                
                # Volume
                colors = ['#34d399' if c >= o else '#f87171' for o, c in zip(chart_df['Open'], chart_df['Close'])]
                fig.add_trace(go.Bar(
                    x=chart_df.index, y=chart_df['Volume'],
                    name='Volume', marker_color=colors, opacity=0.5
                ), row=2, col=1)
                
                fig.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis_rangeslider_visible=False,
                    height=550,
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"),
                    font=dict(family="Inter", size=11),
                )
                fig.update_xaxes(gridcolor='rgba(255,255,255,0.04)')
                fig.update_yaxes(gridcolor='rgba(255,255,255,0.04)')
                
                st.plotly_chart(fig, width='stretch')
                
                # ==========================
                # NEWS SENTIMENT
                # ==========================
                st.divider()
                st.markdown("### 📰 뉴스 감성")
                
                try:
                    na = news_analysis.NewsAnalyzer(ticker, stock_name)
                    news_result = na.get_news_sentiment()
                    
                    n_score = news_result.get('score', 0)
                    score_pct = (n_score + 1) / 2 * 100 # -1~1 → 0~100
                    
                    n_color = '#34d399' if n_score > 0.2 else '#f87171' if n_score < -0.2 else '#fbbf24'
                    n_label = '긍정' if n_score > 0.2 else '부정' if n_score < -0.2 else '중립'
                    
                    st.markdown(f"**감성 점수**: <span style='color:{n_color};font-weight:700'>{n_score:.2f} ({n_label})</span>", unsafe_allow_html=True)
                    
                    headlines = news_result.get('headlines', [])
                    if headlines:
                        for h in headlines[:5]:
                            title = h.get('title', h) if isinstance(h, dict) else str(h)
                            st.caption(f"• {title}")
                    else:
                        st.caption("최근 뉴스 없음")
                except:
                    st.caption("뉴스 데이터를 불러올 수 없습니다.")
                
                # ==========================
                # BACKTEST SUMMARY
                # ==========================
                st.divider()
                st.markdown("### 📊 백테스트")
                
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("총 수익", stats.get('Total Return', 'N/A'))
                b2.metric("최대 손실률", stats.get('Max Drawdown', 'N/A'))
                b3.metric("수익 계수", stats.get('Profit Factor', 'N/A'))
                b4.metric("Kelly 비중", stats.get('Kelly Allocation', 'N/A'))
                
            else:
                st.error(f"'{ticker}' 데이터를 불러올 수 없습니다. 종목 코드를 확인해주세요.")
