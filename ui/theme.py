"""스윙 트레이딩 UI 테마.

기존 토스 스타일을 유지하면서 L0(컴팩트 상태바)·L1(요약 카드)·L2(상세 그리드) 3-depth
디자인 시스템에 필요한 토큰과 클래스를 추가합니다. 외부에서는 ``inject_theme()`` 만
부르면 됩니다.
"""

import streamlit as st


THEME_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

:root {
  --bg: #f2f4f6;
  --surface: rgba(255, 255, 255, 0.94);
  --surface-strong: #ffffff;
  --surface-soft: #f8fafc;
  --line: #e5e8eb;
  --text: #191f28;
  --muted: #8b95a1;
  --primary: #3182f6;
  --primary-deep: #1b64da;
  --primary-soft: #eaf2ff;
  --good: #17b26a;
  --good-deep: #118653;
  --warn: #ffb020;
  --warn-deep: #b86e00;
  --danger: #f04452;
  --danger-deep: #c2313d;
  --shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
  --shadow-soft: 0 10px 24px rgba(15, 23, 42, 0.05);
  --radius-card: 22px;
  --radius-pill: 999px;
  --radius-chip: 14px;
}

html, body, [class*="css"] {
  font-family: "Pretendard", "SUIT Variable", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
}

.stApp {
  background:
    radial-gradient(circle at top left, rgba(49, 130, 246, 0.10), transparent 28%),
    radial-gradient(circle at top right, rgba(35, 180, 120, 0.08), transparent 24%),
    linear-gradient(180deg, #f8fbff 0%, var(--bg) 18%, #eef2f6 100%);
  color: var(--text);
}

[data-testid="stHeader"] {
  background: rgba(248, 251, 255, 0.75);
  backdrop-filter: blur(14px);
}

.block-container {
  max-width: 1380px;
  padding-top: 1.6rem;
  padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #fbfdff 0%, #f4f7fb 100%);
  border-right: 1px solid rgba(229, 232, 235, 0.9);
}

[data-testid="collapsedControl"] {
  display: none;
}

h1, h2, h3, h4 {
  color: var(--text);
  letter-spacing: -0.03em;
}

p, li, label, .stCaption, .stMarkdown {
  color: var(--text);
}

div[data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid rgba(229, 232, 235, 0.92);
  border-radius: 22px;
  padding: 1rem 1.05rem;
  box-shadow: var(--shadow);
}

div[data-testid="stMetricLabel"] {
  color: var(--muted);
  font-weight: 600;
}

div[data-testid="stMetricValue"] {
  color: var(--text);
  letter-spacing: -0.03em;
}

div[data-baseweb="select"] > div,
.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid var(--line);
  border-radius: 16px;
  min-height: 3rem;
}

div[data-baseweb="select"] > div:focus-within,
.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {
  border-color: rgba(49, 130, 246, 0.9);
  box-shadow: 0 0 0 4px rgba(49, 130, 246, 0.14);
}

.stButton > button,
button[kind="primary"] {
  border-radius: 16px;
  min-height: 3rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.stButton > button:hover,
button[kind="primary"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 30px rgba(49, 130, 246, 0.18);
}

button[kind="primary"] {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-deep) 100%);
  border: 0;
}

.stButton > button {
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid var(--line);
  color: var(--text);
}

.stButton > button:hover {
  border-color: rgba(49, 130, 246, 0.45);
  color: var(--primary-deep);
}

div[data-testid="stTabs"] {
  margin-top: 0.75rem;
}

div[data-testid="stTabs"] button[role="tab"] {
  border-radius: 999px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.72);
  color: var(--muted);
  font-weight: 700;
  padding: 0.8rem 1.15rem;
}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  background: #ffffff;
  color: var(--primary-deep);
  border-color: rgba(49, 130, 246, 0.18);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

div[data-testid="stExpander"] {
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--surface);
  box-shadow: var(--shadow);
  overflow: hidden;
}

div[data-testid="stDataFrame"],
div[data-testid="stTable"] {
  border: 1px solid var(--line);
  border-radius: 22px;
  overflow: hidden;
  background: var(--surface-strong);
  box-shadow: var(--shadow);
}

.section-intro,
.status-banner,
.control-note {
  border: 1px solid rgba(229, 232, 235, 0.92);
  box-shadow: var(--shadow);
}

.section-kicker {
  color: var(--primary-deep);
  font-weight: 800;
  font-size: 0.82rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.section-title {
  color: var(--text);
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.08;
}

.section-title {
  margin: 0.28rem 0 0.55rem;
  font-size: clamp(1.45rem, 1.8vw, 2rem);
}

.section-body,
.status-body,
.status-caption {
  color: var(--muted);
  line-height: 1.65;
}

.section-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 1rem;
}

.section-chip {
  padding: 0.5rem 0.82rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(49, 130, 246, 0.12);
  color: var(--primary-deep);
  font-size: 0.88rem;
  font-weight: 700;
}

.section-intro {
  padding: 1.2rem 1.25rem;
  margin: 0.35rem 0 1rem;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.9);
}

.status-banner {
  padding: 1rem 1.15rem;
  margin: 0.5rem 0 0.85rem;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.92);
}

.status-banner.good {
  background: linear-gradient(135deg, rgba(236, 251, 243, 0.96), rgba(255, 255, 255, 0.95));
  border-color: rgba(23, 178, 106, 0.2);
}

.status-banner.caution {
  background: linear-gradient(135deg, rgba(255, 248, 230, 0.96), rgba(255, 255, 255, 0.95));
  border-color: rgba(255, 176, 32, 0.24);
}

.status-banner.risk,
.status-banner.danger {
  background: linear-gradient(135deg, rgba(255, 241, 242, 0.97), rgba(255, 255, 255, 0.95));
  border-color: rgba(240, 68, 82, 0.2);
}

.status-title {
  color: var(--text);
  font-size: 1rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin-bottom: 0.25rem;
}

.control-note {
  padding: 0.95rem 1.1rem;
  margin: 0.2rem 0 1rem;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.84);
}

.control-note strong {
  display: block;
  color: var(--text);
  margin-bottom: 0.2rem;
}

.control-note span {
  color: var(--muted);
  line-height: 1.6;
}

.intel-highlight-list {
  display: grid;
  gap: 0.7rem;
  margin: 0.55rem 0 1rem;
}

.intel-highlight-item {
  display: flex;
  gap: 0.7rem;
  align-items: flex-start;
  padding: 0.9rem 1rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(229, 232, 235, 0.9);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.intel-highlight-badge {
  flex-shrink: 0;
  min-width: 4.1rem;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  background: rgba(49, 130, 246, 0.1);
  color: var(--primary-deep);
  font-size: 0.78rem;
  font-weight: 700;
  text-align: center;
}

.intel-highlight-text {
  color: var(--text);
  line-height: 1.55;
  font-size: 0.95rem;
}

.intel-theme-card {
  padding: 1rem 1.05rem;
  margin-bottom: 0.8rem;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(229, 232, 235, 0.92);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
}

.intel-theme-card.good {
  background: linear-gradient(135deg, rgba(236, 251, 243, 0.98), rgba(255, 255, 255, 0.96));
  border-color: rgba(23, 178, 106, 0.18);
}

.intel-theme-card.risk {
  background: linear-gradient(135deg, rgba(255, 241, 242, 0.98), rgba(255, 255, 255, 0.96));
  border-color: rgba(240, 68, 82, 0.18);
}

.intel-theme-card.neutral {
  background: linear-gradient(135deg, rgba(246, 248, 251, 0.98), rgba(255, 255, 255, 0.96));
  border-color: rgba(139, 149, 161, 0.18);
}

.intel-theme-head {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  align-items: center;
  margin-bottom: 0.45rem;
}

.intel-theme-name {
  color: var(--text);
  font-size: 1rem;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.intel-theme-badge {
  flex-shrink: 0;
  border-radius: 999px;
  padding: 0.28rem 0.7rem;
  font-size: 0.78rem;
  font-weight: 800;
}

.intel-theme-badge.good {
  background: rgba(23, 178, 106, 0.12);
  color: #118653;
}

.intel-theme-badge.risk {
  background: rgba(240, 68, 82, 0.12);
  color: #c2313d;
}

.intel-theme-badge.neutral {
  background: rgba(139, 149, 161, 0.14);
  color: #5f6b76;
}

.intel-theme-meta {
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.55;
}

.intel-theme-evidence {
  margin-top: 0.65rem;
  color: var(--text);
  font-size: 0.9rem;
  line-height: 1.55;
}

.intel-theme-evidence strong {
  color: var(--primary-deep);
  margin-right: 0.3rem;
}

.intel-subtle-card {
  padding: 0.95rem 1rem;
  margin-bottom: 0.75rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(229, 232, 235, 0.92);
}

.intel-subtle-card strong {
  display: block;
  color: var(--text);
  margin-bottom: 0.3rem;
}

.intel-subtle-card span {
  color: var(--muted);
  line-height: 1.55;
}

.top-intel-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.9rem;
  margin: 0.45rem 0 1rem;
}

.top-intel-card {
  padding: 1rem 1.05rem;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(229, 232, 235, 0.92);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
}

.top-intel-kicker {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
  margin-bottom: 0.3rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.top-intel-title {
  color: var(--text);
  font-size: 1.02rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin-bottom: 0.35rem;
}

.top-intel-body {
  color: var(--text);
  font-size: 0.94rem;
  line-height: 1.6;
}

.top-intel-meta {
  color: var(--muted);
  font-size: 0.84rem;
  line-height: 1.55;
  margin-top: 0.5rem;
}

.intel-overview-shell {
  margin: 0.55rem 0 1rem;
}

.intel-scoreline {
  color: var(--text);
  font-size: 1.05rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  margin-bottom: 0.7rem;
}

.intel-scoreline .muted {
  color: var(--muted);
  font-weight: 700;
}

.intel-insight-box {
  padding: 1rem 1.1rem;
  margin-bottom: 0.9rem;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(229, 232, 235, 0.92);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
  color: var(--text);
  line-height: 1.65;
}

.intel-signal-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.9rem;
  margin: 0.6rem 0 1rem;
}

.intel-signal-card {
  padding: 1rem 1.05rem;
  border-radius: 22px;
  border: 1px solid rgba(229, 232, 235, 0.92);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
}

.intel-signal-card.good {
  background: linear-gradient(135deg, rgba(236, 251, 243, 0.98), rgba(255, 255, 255, 0.96));
  border-color: rgba(23, 178, 106, 0.18);
}

.intel-signal-card.risk {
  background: linear-gradient(135deg, rgba(255, 241, 242, 0.98), rgba(255, 255, 255, 0.96));
  border-color: rgba(240, 68, 82, 0.18);
}

.intel-signal-card.focus {
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.98), rgba(255, 255, 255, 0.96));
  border-color: rgba(49, 130, 246, 0.18);
}

.intel-signal-title {
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 700;
  margin-bottom: 0.35rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.intel-signal-body {
  color: var(--text);
  font-size: 1rem;
  font-weight: 800;
  line-height: 1.55;
}

.intel-signal-meta {
  margin-top: 0.35rem;
  color: var(--muted);
  font-size: 0.86rem;
  line-height: 1.55;
}

.intel-momentum-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.9rem;
  margin: 0.85rem 0 1rem;
}

.intel-momentum-card {
  padding: 1rem 1.05rem;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(229, 232, 235, 0.92);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
}

.intel-momentum-rank {
  color: var(--muted);
  font-size: 0.86rem;
  font-weight: 700;
  margin-bottom: 0.35rem;
}

.intel-momentum-theme {
  color: var(--text);
  font-size: 0.98rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  min-height: 2.4rem;
}

.intel-momentum-return {
  color: var(--text);
  font-size: 1.85rem;
  font-weight: 800;
  letter-spacing: -0.05em;
  margin: 0.35rem 0 0.55rem;
}

.intel-momentum-return.pos { color: #118653; }
.intel-momentum-return.neg { color: #c2313d; }
.intel-momentum-return.neu { color: var(--text); }

.intel-momentum-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  background: rgba(23, 178, 106, 0.1);
  color: #118653;
  font-size: 0.82rem;
  font-weight: 700;
}

.intel-momentum-meta {
  margin-top: 0.55rem;
  color: var(--muted);
  font-size: 0.85rem;
  line-height: 1.55;
}

.intel-catalyst-list {
  display: grid;
  gap: 0.7rem;
  margin: 0.65rem 0 0.9rem;
}

.intel-catalyst-item {
  padding: 0.95rem 1rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(229, 232, 235, 0.92);
  color: var(--text);
  line-height: 1.6;
}

.intel-headline-list {
  display: grid;
  gap: 0.7rem;
  margin: 0.65rem 0 0.8rem;
}

.intel-headline-item {
  padding: 0.95rem 1rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(229, 232, 235, 0.92);
  color: var(--text);
  line-height: 1.6;
}

.signal-list {
  display: grid;
  gap: 0.75rem;
  margin: 0.7rem 0 1rem;
}

.signal-card {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(0, 2.25fr) repeat(2, minmax(7.2rem, 0.75fr));
  gap: 0.85rem;
  align-items: center;
  padding: 0.95rem 1rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(229, 232, 235, 0.94);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.signal-identity {
  min-width: 0;
}

.signal-rank {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 800;
  margin-bottom: 0.2rem;
}

.signal-title {
  color: var(--text);
  font-size: 1rem;
  font-weight: 850;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.signal-subtitle {
  color: var(--muted);
  font-size: 0.84rem;
  line-height: 1.45;
  margin-top: 0.18rem;
  overflow-wrap: anywhere;
}

.signal-buy {
  min-width: 0;
  color: var(--text);
  font-size: 0.94rem;
  line-height: 1.45;
  font-weight: 750;
  overflow-wrap: anywhere;
}

.signal-metric {
  padding: 0.72rem 0.78rem;
  border-radius: 14px;
  background: rgba(246, 248, 251, 0.9);
  border: 1px solid rgba(229, 232, 235, 0.9);
  min-width: 0;
}

.signal-metric-label {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  margin-bottom: 0.18rem;
}

.signal-metric-value {
  color: var(--text);
  font-size: 1rem;
  font-weight: 850;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.signal-metric-value.pos { color: #118653; }
.signal-metric-value.neg { color: #c2313d; }
.signal-metric-value.neu { color: var(--text); }

/* === L0 컴팩트 상태바 (Macro + Gate + Market 통합 한 줄) === */
.compact-status {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  align-items: stretch;
  padding: 0.55rem 0.7rem;
  margin: 0.2rem 0 1rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(229, 232, 235, 0.92);
  box-shadow: var(--shadow-soft);
}

.compact-status-pill {
  display: inline-flex;
  flex-direction: column;
  gap: 0.05rem;
  padding: 0.45rem 0.85rem;
  border-radius: 14px;
  background: rgba(246, 248, 251, 0.95);
  border: 1px solid rgba(229, 232, 235, 0.85);
  min-width: 0;
}

.compact-status-pill.good {
  background: linear-gradient(135deg, rgba(236, 251, 243, 0.96), rgba(255, 255, 255, 0.95));
  border-color: rgba(23, 178, 106, 0.22);
}
.compact-status-pill.caution {
  background: linear-gradient(135deg, rgba(255, 248, 230, 0.96), rgba(255, 255, 255, 0.95));
  border-color: rgba(255, 176, 32, 0.26);
}
.compact-status-pill.risk,
.compact-status-pill.danger {
  background: linear-gradient(135deg, rgba(255, 241, 242, 0.97), rgba(255, 255, 255, 0.95));
  border-color: rgba(240, 68, 82, 0.22);
}
.compact-status-pill.focus {
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.98), rgba(255, 255, 255, 0.96));
  border-color: rgba(49, 130, 246, 0.22);
}

.compact-status-label {
  color: var(--muted);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.compact-status-value {
  color: var(--text);
  font-size: 0.96rem;
  font-weight: 850;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.compact-status-meta {
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.35;
  margin-top: 0.05rem;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* === L1 KPI 스트립 (탭 안에서 4~6 개 작은 지표 카드 가로 배치) === */
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.7rem;
  margin: 0.4rem 0 1rem;
}

.kpi-card {
  padding: 0.85rem 0.95rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(229, 232, 235, 0.92);
  box-shadow: var(--shadow-soft);
  min-width: 0;
}

.kpi-card.good { border-color: rgba(23, 178, 106, 0.22); }
.kpi-card.risk,
.kpi-card.danger { border-color: rgba(240, 68, 82, 0.22); }
.kpi-card.focus { border-color: rgba(49, 130, 246, 0.22); }

.kpi-label {
  color: var(--muted);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 0.3rem;
}

.kpi-value {
  color: var(--text);
  font-size: 1.35rem;
  font-weight: 900;
  letter-spacing: -0.04em;
  line-height: 1.1;
}

.kpi-value.pos { color: var(--good-deep); }
.kpi-value.neg { color: var(--danger-deep); }

.kpi-delta {
  margin-top: 0.25rem;
  color: var(--muted);
  font-size: 0.82rem;
  line-height: 1.4;
}

.kpi-delta.pos { color: var(--good-deep); }
.kpi-delta.neg { color: var(--danger-deep); }

/* === L2 디테일 그리드 표 안내 캡션 === */
.detail-grid-hint {
  color: var(--muted);
  font-size: 0.82rem;
  margin: 0.2rem 0 0.4rem;
}

@media (max-width: 980px) {
  .block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
  }

  .section-intro,
  .status-banner,
  .control-note,
  .top-intel-card,
  div[data-testid="stMetric"],
  div[data-testid="stExpander"],
  div[data-testid="stDataFrame"],
  div[data-testid="stTable"] {
    border-radius: 20px;
  }

  .top-intel-grid {
    grid-template-columns: 1fr;
  }

  .intel-signal-grid,
  .intel-momentum-grid,
  .signal-card {
    grid-template-columns: 1fr;
  }

  div[data-testid="stTabs"] button[role="tab"] {
    padding: 0.72rem 0.92rem;
  }

  .compact-status {
    padding: 0.45rem 0.55rem;
  }

  .kpi-strip {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  }
}
</style>
"""


def inject_theme() -> None:
    """글로벌 토스 스타일 테마 + L0/L1/L2 토큰을 주입한다."""

    st.markdown(THEME_CSS, unsafe_allow_html=True)
