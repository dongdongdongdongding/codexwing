#!/usr/bin/env python3
"""KR swing CANDIDATE-pick producer (swing-main-zls0, RESEARCH_LOG §7-A). Observation-only.

Basis: 8y quarterly walk-forward, t5_5 LGBM ranker (rolling 2y train). 2026-08-21 운영자
  결정 "2026 관문 우선으로 가고 두 셀 배선해": 라벨을 ft_5_5 -> t5_5 (계약 라벨) 로 바꾸고
  진입기권 w60q0.7 을 건다. 근거 셀(보드 [H] §4 / [L] §1, [Q] 가 독립 재현):
  KOSPI 2026 net +1.35 · 최근3년 초과 +1.21 (CI 0 제외) · 발화 3.11일 · 승률 74.5%
  KOSDAQ 2026 net +1.13 · 최근3년 초과 +1.43 (CI 0 제외) · 발화 2.97일 · 승률 78.1%
  64칸 중 2026 net 양수는 7칸뿐이고, net·초과가 둘 다 양수인 5칸은 전부 TP5/H5 다.
  라벨 교체는 결함도 같이 고친다: ft_5_5 는 ±5% 양방향이라 둘 다 안 닿으면 NaN 이고
  dropna 가 유동성 통과 행의 19.7% 를 학습에서 버렸다. t5_5 는 결측이 없다.
  감쇠 기울기 ft_5_5 −0.451pp/년 (p=0.006) -> t5_5 +0.181 ([Q]).
  Honest tier: CANDIDATE. Fills "no-pick days" alongside the intraday PRIMARY lane.

Contract (TP5/H5, 불변): signal at close t -> BUY NEXT OPEN (t+1); exit +5% touch within
5 sessions (entry day counts) else 5d close. No stop. 계약부는 이미 TP5/H5 라 손대지 않았다.

기권 w60q0.7 (사양: research/SPEC_w60q0.7.md — 보드에서 복원. [Q] 는 재개 불가였다):
  그날 top-p 가 직전 60거래일 일별 top-p 의 0.7분위 미만이면 그날은 발행하지 않는다.
  🔴 **KOSPI 에만 건다** (`ABSTAIN_MARKETS`). KOSDAQ 에서는 이 기권이 좋은 날을 버린다 — 근거는 상수 옆에.
  인과적(당일 제외). 운영자 2026-08-21 결정 = **이중 모델**: 픽은 매일 재학습 모델 A 가 고르고,
  게이트는 분기 재학습 모델 B 가 판단한다(보드 하네스의 top-p 가 분기 WF 의 표본외 점수이므로
  매일 모델로 과거를 재채점하면 표본내가 되어 과잉기권이 된다). 게이트 이력은 런타임 파일에
  쌓지 않고 매 실행 직전 3분기를 재계산한다 — gitignore 된 파일에 의존하면 테스트가 오염된다.

2026-08-03 PKG-C ③ (§40, 사전등록): 랭킹 shadow 보드 — 유동 풀(≥30억/100억) 전수 스코어의
top-50/시장을 kr_ranking_shadow_ledger.jsonl에 관측 전용 축적, px_long 종가 기반 fwd5 자동 정산.
목적: "상승확률 최고 종목" 기능의 전제인 랭킹 심도(top1 vs top10 vs top50) 실측 차등 검증.
사전등록 킬 기준: forward n>=30/구간에서 심도 단조성(top1>top10>top50 EV) 부재 시 보드 폐기
(§25/§38/§11-B가 '셀 내 서열 무정보'로 부정적 사전확률 — 이 검증이 통과해야만 웹 노출 후보).
원시 p 표시 금지·발행/라우팅 금지. 비활성: AG_SWING_RANKING_SHADOW=0.

  python3 multi_agent/tools/report_kr_swing_candidate.py [--top-k 3]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
CACHE = Path(os.path.expanduser("~/research_cache"))
EXP = PROJECT_ROOT / "runtime_state" / "reports" / "experimental"
LEDGER = EXP / "kr_swing_candidate_ledger.jsonl"
RANK_LEDGER = EXP / "kr_ranking_shadow_ledger.jsonl"
RANK_TOP = 50
REPORT_JSON = EXP / "kr_swing_candidate_latest.json"
REPORT_MD = EXP / "kr_swing_candidate_latest.md"

FEATS = ["ret_1d","ret_3d","ret_5d","ret_10d","ret_20d","ret_60d","ma5_dist","ma20_dist","ma60_dist",
         "ma120_dist","ma20_slope","ma60_slope","rsi14","rsi_slope","accel","consec_up","dist_hi20",
         "dist_hi60","dist_hi120","dist_lo20","dist_lo60","pos20","bb_pctb","bb_bw","atr_pct","vol20",
         "close_loc","gap","vol_ratio","vol_trend","turn_z","obv_slope","cmf20","idx_mom20","idx_vol20"]
LIQ = {"KOSPI": 100e8, "KOSDAQ": 30e8}
TRAIN_YEARS = 2
from modules.trading_costs import KR_ROUNDTRIP_COST_PCT as COST  # 단일 출처(0.215)
LABEL = "t5_5"                     # P2 계약 라벨 (익일시가 진입 · +5% any-touch · 5세션 · 편측)
P2_LABEL = CACHE / "p2_label.parquet"   # (code,date) -> t5_5/r5_5. px_long 에는 t5_5 가 없다
GATE_W, GATE_Q, GATE_QUARTERS = 60, 0.7, 3   # 기권 창(거래일) · 분위 · 게이트 재계산 분기수
# 🔴 기권은 KOSPI 에만 건다. 운영자 결정 2026-08-22.
# w60q0.7 은 한 시장에서 도출돼 두 시장에 그대로 걸려 있었는데, 같은 시드·같은 랭커·같은 픽에서
# 기권만 켜고 끄면 두 시장의 부호가 반대다 (조정관이 [S] 발견을 독립 재계산해 확인):
#     KOSPI   순기여 8년 +0.270 · 2026H1 +0.747 · 기권이 버린 날 net -1.072  <- 버릴 만했다
#     KOSDAQ  순기여 8년 -0.019 · 2026H1 -0.736 · 기권이 버린 날 net +0.911  <- 좋은 날을 버렸다
# KOSDAQ 2026H1 음수 5/6 은 셀이 아니라 이 기권이 만들었다(빼면 2/6). [S] 측정으로 KOSDAQ 에서는
# 랜덤 기권이 96.8% 확률로 이보다 낫고 전기간 플라시보 p=0.557 로 무효다. EDGE_BOARD [조정관] 종합 §1.
ABSTAIN_MARKETS = ()   # 2026-08-23 비움. `gate_w60q07` 은 되돌릴 때를 위해 남겨 둔다
# KOSDAQ 은 대신 [U] 시장약세 게이트를 쓴다. 운영자 결정 2026-08-22.
# 유니버스(같은 유동성 필터)의 후행 5일 수익 평균이 자기 직전 250거래일 중앙값보다 **낮은** 날에만 산다.
# 인과적: 임계는 shift(1) 로 당일을 뺀다. 모델 p 가 아니라 가격 패널에 걸리므로 이중모델 문제가 없다.
# 근거 (6시드 · 조정관이 [U] 결과를 독립 재계산):
#   절대피처   8년 +0.361 -> +1.375  · 2026H1 음수 0/6 · 발화 2.01일 · 승률 82.1% · 종목 388/771픽
#   자기정규화B 8년 +0.338 -> +1.010  · 2026H1 +1.418 음수 0/6        <- 다른 랭커에서도 작동
#   [L] volume>0 정화 후 오히려 +1.375 -> +1.492 (2026H1 음수 여전히 0/6)
#   순환이동 플라시보 40,000회 z=+4.19 (본페로니 통과) · [T]/조정관이 각각 독립 재현
# 🔴 KOSPI 에는 걸지 않는다: 기여 +0.234 뿐이고 2026H1 이 음수 2/6 이다.
# 🔴 KOSDAQ 에 w60q0.7 과 **같이** 걸지 않는다: 발화가 5.35거래일로 운영자 3일 기준에 걸린다(규율 13).
# 🟩 2026-08-23: **KOSPI 도 시장약세 게이트로 옮긴다.** `w60q0.7` 은 더 이상 쓰이지 않는다.
# 근거([Y] 사다리, 현행 프로덕션 랭커 고정, 전기간 세션당 EV):
#     현행(w60q0.7·TP5/H5·top3) 0.1433  →  [U]Q0.40·TP5/H10·top3 **0.1898 (+32%)**
#     OOS23 0.2692 · 거래당 승률 최악시드 78.90% · net·초과 블록CI **6/6** · 버린날 초과 **-0.191**
#     시드별 `p_max` 0.00102(전기간) / **≤2e-5(OOS23)** — OOS23 은 [Y] 전체 탐색격자
#     1,838셀 본페로니(α=2.7e-5)를 **통과한다. 이 함대에서 처음이다.**
# 부수 효과: `w60q0.7` 이 요구하던 **이중모델(분기 재학습 B)이 통째로 사라진다** — 하루 4 fit -> 1 fit.
#
# 분위가 시장별로 다르다. **격자 최댓값이 아니다** — 세션당 EV 가 Q 에 **단조**라(0.374@Q0.25 ->
# 0.077@Q0.70) 봉우리가 없고, 선택 규칙이 **운영자의 기존 발화 기준**이다:
#     "세 창(전기간/OOS23/2026H1) 전부에서 발화 <=3거래일을 만족하는 가장 조인 0.05격자 분위"
#     Q0.30 -> 3.25/3.50/2.93 ✗ · Q0.35 -> 2.83/**3.04**/2.86 ✗ · **Q0.40 -> 2.52/2.66/2.67 ✅**
# KOSDAQ 은 [U] 사전지정값 0.50 을 유지한다 — Q 조임을 KOSDAQ 에서 **검정하지 않았고**,
# [V] §9 상 KOSDAQ 프론티어엔 무릎이 있어 같은 이득이 안 날 것으로 본다. 규율 3(옮기면 다시 검정).
MKT_WEAKNESS_MARKETS = ("KOSPI", "KOSDAQ")
MKT_WEAKNESS_Q = {"KOSPI": 0.40, "KOSDAQ": 0.50}
MKT_W, MKT_MINP = 250, 60
EMBARGO_DAYS = 17                  # 라벨이 H 세션 앞을 보므로 학습창 꼬리를 잘라낸다
# 계약 보유창이 시장별로 다르다. TP(+5%)는 공통이고 H 만 다르다.
# KOSPI H=10: [Y] 가 위 셀에서 검증한 계약. KOSDAQ H=5: [U] 게이트가 검증된 계약이고
# H 조임을 KOSDAQ 에서 다시 재지 않았다([V] 고원 TP4~7/H3~10 안이긴 하나 세션당으로는 미측정).
# **검증된 계약 밖으로 시장을 끌고 가지 않는다.**
CONTRACT_H = {"KOSPI": 10, "KOSDAQ": 5}
CONTRACT_TP = 0.05
# 발행 깊이도 **시장별**이다. 운영자 결정 2026-08-23.
# 깊이의 효과가 두 시장에서 정반대다([Z] 측정, 계약·게이트·유니버스·기간 고정하고 k 만 훑음):
#   KOSDAQ  k=3 -> k=1 : 세션당 +0.3388 -> **+0.6363 (+88%)** · 승률 77.9 -> 81.4% · 발화 1.99 -> 2.06일
#           사다리 분해로 이득의 **87% 가 깊이**다(Δ+0.2974, 블록CI (+0.157,+0.437) 0 제외).
#           계약 H 는 근거가 없다(H5->H3 Δ+0.0552, CI 0 포함, 게다가 승률을 72.8% 로 떨군다).
#   KOSPI   k=1 은 `p_max` **0.207 로 랜덤과 구별되지 않는다**. k=2 에서 0.00030, k=3 에서 0.00000.
#           **k=3 을 유지한다.**
# 집중도(규율 9) 확인 — KOSDAQ k=1 이 k=3 보다 나쁘지 않다:
#   최대단일 1.02%(보드 프로파일 2.3%/1.3%보다 낮다) · jackknife 최악1종목 제거 **−1.9%**(k=3 은 −2.3%) ·
#   최대연속손실 **3일/4건**(k=3 은 7일/9건) · 필요 슬롯 **13 -> 5개(자본 요구 −62%)**
# ⚠️ 미측정: **슬리피지.** k=1 은 하루 한 종목에 자본이 3배 몰린다. 라이브 원장 체결가로만 잴 수 있다.
# ⚠️ 대가: 판정 표본이 1/3 로 준다(13,312 -> 4,303픽).
TOP_K = {"KOSPI": 3, "KOSDAQ": 1}


def _fit(tr: pd.DataFrame):
    """LGBM ranker. 파라미터는 8y WF 하네스와 동일하게 유지한다(바꾸면 근거 셀과 끊긴다)."""
    import lightgbm as lgb
    # ⚠️ `subsample=0.8` 은 **무효다** — LightGBM 은 `subsample_freq=0`(기본값)이면 배깅을 아예
    #    안 돈다. 아래에 그 0 을 명시해 둔 것은 값을 바꾸려는 게 아니라, 다음 사람이 이 줄을
    #    「배깅이 켜져 있다」로 읽지 않게 하려는 것이다.
    #    **켜지 마라.** 8y WF 근거 셀이 전부 이 무효 상태에서 나왔다 — 켜면 셀과 끊긴다.
    #    바꾸려면 하네스와 함께 바꾸고 전 셀을 재검정해야 한다.
    m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                           subsample=0.8, subsample_freq=0, colsample_bytree=0.7, reg_lambda=5,
                           random_state=0, verbose=-1)
    m.fit(tr[FEATS].clip(-1e4, 1e4), tr[LABEL])
    return m


def gate_w60q07(d: pd.DataFrame, latest: pd.Timestamp) -> Dict[str, Any]:
    """진입기권 w60q0.7 — 게이트 전용 모델 B (분기 재학습, 전부 표본외).

    사양 research/SPEC_w60q0.7.md. 그날 top-p 가 직전 60거래일 일별 top-p 의 0.7분위 미만이면
    기권한다. 분위는 당일을 제외해 계산한다(인과). 직전 3분기(약 185거래일)를 매 실행 재계산하므로
    창 60 이 항상 차고, 런타임 파일에 의존하지 않는다. 창이 안 차면 보수적으로 기권한다."""
    q0 = pd.Timestamp(latest).to_period("Q").start_time
    tops: List[pd.Series] = []
    for k in range(GATE_QUARTERS - 1, -1, -1):
        qs = q0 - pd.DateOffset(months=3 * k)
        tr = d[(d["date"] < qs - pd.Timedelta(days=EMBARGO_DAYS))
               & (d["date"] >= qs - pd.DateOffset(years=TRAIN_YEARS))].dropna(subset=[LABEL])
        te = d[(d["date"] >= qs) & (d["date"] < qs + pd.DateOffset(months=3))
               & (d["date"] <= latest)].dropna(subset=FEATS[:6])
        if len(tr) < 20000 or te.empty:
            continue
        p = _fit(tr).predict_proba(te[FEATS].clip(-1e4, 1e4))[:, 1]
        tops.append(pd.DataFrame({"date": te["date"].values, "p": p}).groupby("date")["p"].max())
    if not tops:
        return {"gate": "NO_MODEL", "fire": False}
    ser = pd.concat(tops).sort_index()
    return _gate_decide(ser[~ser.index.duplicated(keep="last")], latest)


def _gate_decide(ser: pd.Series, latest: pd.Timestamp) -> Dict[str, Any]:
    """일별 top-p 계열 -> 발행/기권 판정. 순수 함수(모델·파일 없음)이므로 여기서 규칙을 검정한다.

    창은 **직전 60거래일**이고 당일은 제외한다. 창이 안 차면 기권한다(보수적)."""
    if latest not in ser.index:
        return {"gate": "NO_SCORE", "fire": False}
    hist = ser[ser.index < latest].iloc[-GATE_W:]          # 인과: 당일 제외
    if len(hist) < GATE_W:
        return {"gate": "WARMUP", "fire": False, "gate_history_days": int(len(hist))}
    thr = float(np.quantile(hist.values, GATE_Q))          # linear 보간 (사양 미확정 B, 고정 기록)
    top_p = float(ser.loc[latest])
    return {"gate": "FIRE" if top_p >= thr else "ABSTAIN", "fire": bool(top_p >= thr),
            "gate_top_p": round(top_p, 4), "gate_threshold": round(thr, 4),
            "gate_window": GATE_W, "gate_q": GATE_Q, "gate_history_days": int(len(hist))}


def gate_market_weakness(d: pd.DataFrame, latest: pd.Timestamp, q: float = 0.5) -> Dict[str, Any]:
    """[U] 시장약세 게이트 — 유니버스 후행 5일 수익이 자기 250거래일 중앙값보다 낮은 날에만 산다.

    `d` 는 이미 시장·유동성으로 걸러진 패널이다([U] 의 `inuniv` 와 같은 필터). 모델을 쓰지 않으므로
    적합 비용이 0 이고, 게이트가 가격 패널에만 걸려 `SPEC_w60q0.7.md` §C 의 표본내외 혼입 문제가 없다."""
    ser = d.groupby("date")["ret_5d"].mean().sort_index()
    return _mkt_weakness_decide(ser, latest, q=q)


def _mkt_weakness_decide(ser: pd.Series, latest: pd.Timestamp, q: float = 0.5) -> Dict[str, Any]:
    """일별 시장수익 계열 -> 발행/기권. 순수 함수이므로 여기서 규칙을 검정한다.

    임계는 **직전 250거래일 중앙값**이고 당일은 제외한다(인과). 창이 `MKT_MINP` 미만이면 기권한다."""
    if latest not in ser.index:
        return {"gate": "NO_SCORE", "fire": False}
    hist = ser[ser.index < latest].iloc[-MKT_W:]
    if len(hist) < MKT_MINP:
        return {"gate": "WARMUP", "fire": False, "gate_history_days": int(len(hist))}
    thr = float(np.nanquantile(hist.values, q))
    today = float(ser.loc[latest])
    weak = today < thr                       # 약할 때 산다 — 부호를 뒤집지 마라
    return {"gate": "FIRE" if weak else "ABSTAIN", "fire": bool(weak),
            "gate_kind": "mkt_weakness", "gate_mkt_ret5": round(today, 4),
            "gate_threshold": round(thr, 4), "gate_window": MKT_W, "gate_q": q,
            "gate_history_days": int(len(hist))}


KST = ZoneInfo("Asia/Seoul")
KRX_CLOSE = dt.time(15, 30)
# 종가 확정까지의 여유. 장 종료 직후 몇 분은 데이터가 아직 정리 중이다.
SETTLE_MINUTES = 10


def _drop_unconfirmed_session(px: pd.DataFrame, now=None) -> pd.DataFrame:
    """세션이 안 끝났으면 그 날 봉을 버린다.

    `px_long` 은 하루에도 여러 번 재구축되고(`PX_REBUILD=1`), 장중에 돌면 **오늘의
    미완성 봉**이 들어온다. 그걸 그대로 채점하면 아직 바뀔 종가로 픽을 낸다 —
    실측으로 정산 212건 중 48건(22.6%)이 그렇게 매겨졌고, 그 행들의 `close` 가
    확정 종가와 맞은 비율은 **5.8%** 였다.

    떨어뜨리는 것이 맞지 그 전날로 물러서는 것이 답이 아닌 이유: 이 레인의 계약은
    **신호봉 다음 시가 진입**이다. D-1 종가로 신호를 내면 진입은 D 시가여야 하는데
    장중 실행 시점에 그건 이미 지났다. 즉 **장중 실행은 원래 새 픽을 만들 수 없다.**
    미확정 봉을 버리면 마지막 확정 세션이 남고, 그 세션 픽이 이미 원장에 있으면
    중복 방지가 걸러 아무 일도 일어나지 않는다 — 그게 옳은 동작이다.
    """
    if px.empty:
        return px
    now = now or dt.datetime.now(KST)
    latest = px["date"].max()
    same_day = latest.date() == now.date()
    before_settle = (dt.datetime.combine(now.date(), KRX_CLOSE, tzinfo=KST)
                     + dt.timedelta(minutes=SETTLE_MINUTES)) > now
    if same_day and before_settle:
        return px[px["date"] < latest]
    return px


# 학습 라벨이 엠바고 너머로 얼마나 더 낡아도 되는가. 분기(약 63거래일)를 넘으면
# 가장 최근 폴드가 **새 데이터를 한 줄도 못 본 채** 적합된다 — walk-forward 재적합
# 주기가 분기이므로 그 지점이 「한 주기 통째로 뒤처졌다」는 선이다.
LABEL_STALENESS_HARD_DAYS = 63


def _label_staleness(label_max, as_of) -> int:
    """라벨이 **엠바고가 허용하는 것보다** 며칠 더 낡았나. 0 이면 정상이다.

    라벨은 계약이 끝나야 확정되므로 항상 `as_of - EMBARGO_DAYS` 근처에서 끝난다.
    그 너머의 지연은 **아무도 라벨을 다시 안 짓고 있다**는 뜻이다.

    실제로 그랬다(2026-08-26 발견): `px_long`(피처)은 일일 운영이 매일 재구축하는데
    `marcap → px_delisted → p2_label` 사슬은 **일일 운영 어디에도 없다.** 라벨이
    2026-07-24 에 멈춰 있었고 매일 하루씩 더 벌어지고 있었다. 아무것도 그걸 보지 않았다.
    """
    allowed = pd.Timestamp(as_of) - pd.Timedelta(days=EMBARGO_DAYS)
    return max(0, (allowed - pd.Timestamp(label_max)).days)


# 유니버스 무결성을 재는 창(거래일). 롤링 자기분위로 판정하므로 절대 임계가 없다.
UNIVERSE_CHECK_WINDOW = 60
# 「최근 수준」을 정하는 짧은 창. 오늘을 여기에 견준다.
UNIVERSE_REF_DAYS = 5


def _universe_integrity(px, latest) -> Dict[str, Any]:
    """오늘 패널에서 종목이 **갑자기** 사라졌는지 본다.

    왜 보는가: [W7] 이 파이프라인이 실제로 종목을 조용히 빠뜨리는 것을 관측했다
    (`build_px_long` 의 `pull()` 실패 → 로그상 2659↔2660). **입력이 말없이 줄어드는 것은
    그 자체로 알아야 할 사건이다** — 없는 데이터로 채점하게 된다.

    ⚠️ **EV 영향의 크기는 주장하지 않는다.** [W10] 이 한 종목 제거에서 −0.068 을 관측했으나
    [W11] 이 짝지은 부트스트랩으로 재니 **p=0.227** 로 잡음과 구별되지 않는다(56칸 중 유의 0).
    표본오차가 섭동 효과를 압도한다([W10] 성분분해: sd 0.073/0.155 vs 0.033/0.070).
    **이 가드의 근거는 「EV 가 얼마 움직인다」가 아니라 「데이터가 사라졌다」다.**

    🔴 **긴 창의 중앙값에 견주면 안 된다.** 첫 판을 그렇게 짰다가 실물에서 오탐이 났다:
    KOSPI 가 최근 5일 915·915·915·915·914 로 **안정적인데** 60일 중앙값이 931 이라
    「17종목 결손」으로 읽혔다. 몇 주 전 수준 이동(상폐·재분류 같은 정상 감소)을
    오늘의 사고로 오독한 것이고, 그러면 **매일 경고가 떠서 아무도 안 읽는다.**

    그래서 **최근 수준**(직전 {UNIVERSE_REF_DAYS}거래일 중앙)에 견주고, 문턱은
    **같은 모양으로 잰 전례의 최대 부족분**으로 잡는다 — 절대 임계를 발명하지 않는다.
    급락은 잡고 느린 정상 감소는 안 잡는다.

    **중단하지 않고 기록만 한다.** 대량 상폐나 휴장도 같은 모양이라 발행을 막으면
    오탐으로 레인을 죽인다. 목적은 **보이게 하는 것**이다.
    """
    out: Dict[str, Any] = {}
    hist = px[px["date"] > latest - pd.Timedelta(days=UNIVERSE_CHECK_WINDOW * 2)]
    for mkt in ("KOSPI", "KOSDAQ"):
        g = hist[hist["market"] == mkt].groupby("date")["code"].nunique().sort_index()
        if len(g) < UNIVERSE_REF_DAYS * 3 or latest not in g.index:
            continue
        # 각 날을 「그 날 직전 K일의 중앙」에 견준 부족분. 오늘도 과거도 같은 자로 잰다.
        ref = g.shift(1).rolling(UNIVERSE_REF_DAYS, min_periods=UNIVERSE_REF_DAYS).median()
        short = (ref - g).dropna()
        if latest not in short.index or len(short) < 10:
            continue
        today = float(short.loc[latest])
        worst_before = float(short[short.index < latest].max())
        rec = {"count": int(g.loc[latest]), "recent_level": float(ref.loc[latest]),
               "shortfall": round(today, 1), "worst_before": round(worst_before, 1),
               "anomalous": bool(today > worst_before)}
        out[mkt] = rec
        if rec["anomalous"]:
            print(f"[경고] {mkt} 유니버스에서 {today:.0f}종목이 갑자기 빠졌다 "
                  f"(최근 수준 {rec['recent_level']:.0f} → {rec['count']}). 직전 "
                  f"{UNIVERSE_CHECK_WINDOW}거래일에서 관측된 최대 급락은 {worst_before:.0f} 이었다 — "
                  f"전례 없는 폭이다. 입력이 말없이 줄었다는 뜻이다.", flush=True)
    return out


def score_today(top_k: Optional[int] = None) -> Dict[str, Any]:
    cols = list(dict.fromkeys(["code", "date", "market", "liq", "close", "volume"] + FEATS))
    px = pd.read_parquet(CACHE / "px_long.parquet", columns=cols)
    px["date"] = pd.to_datetime(px["date"])
    px = _drop_unconfirmed_session(px)
    latest = px["date"].max()
    lab = pd.read_parquet(P2_LABEL, columns=["code", "date", LABEL])
    lab["date"] = pd.to_datetime(lab["date"])
    _stale = _label_staleness(lab["date"].max(), latest)
    if _stale > LABEL_STALENESS_HARD_DAYS:
        raise SystemExit(
            f"[라벨 신선도] 학습 라벨이 엠바고 너머로 {_stale}일 더 낡았다"
            f"(라벨 최종 {lab['date'].max().date()} · 채점일 {latest.date()}).\n"
            f"  분기 재적합 주기({LABEL_STALENESS_HARD_DAYS}일)를 넘었다 — 가장 최근 폴드가\n"
            f"  새 데이터를 한 줄도 못 보고 적합된다. 픽을 내지 않는다.\n"
            f"  사슬을 다시 지어라: marcap → build_px_delisted.py → build_p2_label.py\n"
            f"  (일일 운영에 이 사슬이 없다. px_long 만 매일 돈다.)")
    if _stale:
        # 하드스톱이 **언제** 터지는지 매일 같이 말한다. 안 그러면 이 가드는 결함을
        # 고치지 않고 시한폭탄을 거는 것이 된다 — 어느 날 갑자기 레인이 죽는다.
        _deadline = (lab["date"].max() + pd.Timedelta(days=EMBARGO_DAYS)
                     + pd.Timedelta(days=LABEL_STALENESS_HARD_DAYS)).date()
        _left = (pd.Timestamp(_deadline) - latest).days
        print(f"[경고] 학습 라벨이 엠바고 너머로 {_stale}일 더 낡았다 "
              f"(라벨 최종 {lab['date'].max().date()}). "
              f"사슬(marcap → px_delisted → p2_label)이 일일 운영에 없다.\n"
              f"        재구축 없이 두면 {_deadline} 부터 이 도구가 픽을 아예 못 낸다 "
              f"(남은 {_left}일).", flush=True)
    out_deadline = None
    if _stale:
        out_deadline = str((lab["date"].max() + pd.Timedelta(days=EMBARGO_DAYS)
                            + pd.Timedelta(days=LABEL_STALENESS_HARD_DAYS)).date())
    # left join: 라벨은 H=5 세션 뒤에야 확정되므로 최근 행은 결측이다. 학습에서만 dropna 한다.
    px = px.merge(lab, on=["code", "date"], how="left")
    out: Dict[str, Any] = {"as_of": str(latest.date()), "picks": [], "gate": {},
                           "label_stale_days": _stale,
                           "label_max": str(lab["date"].max().date()),
                           "label_hard_stop_on": out_deadline,
                           "universe": _universe_integrity(px, latest)}
    for mkt in ("KOSPI", "KOSDAQ"):
        d = px[(px["market"] == mkt) & (px["liq"] >= LIQ[mkt])]
        tr = d[(d["date"] < latest - pd.Timedelta(days=EMBARGO_DAYS))
               & (d["date"] >= latest - pd.DateOffset(years=TRAIN_YEARS))].dropna(subset=[LABEL])
        te = d[d["date"] == latest].dropna(subset=FEATS[:6]).copy()
        # 신호일에 거래가 없던 종목은 **후보에서** 뺀다(학습에서는 안 뺀다 — 함정 3).
        # 유동성 필터가 롤링 `liq` 라 거래정지 시작 후에도 한참 통과한다. 실측([E4]·원장 검증):
        # 정지일 픽이 백테 4,632건 중 98건(거래당 −3.94 vs 정상 +1.57)이고 **라이브 원장에도
        # 이미 6건이 나가 평균 −5.75%** 였다. 신호일 거래량은 채점 시점에 관측 가능하므로
        # 미래정보가 아니다. `px_long` 은 정지일 open/high/low 를 종가로 평탄화하므로
        # 그 봉 위의 피처는 합성값이다 — 채점 대상이 아니라 학습 재료로만 쓴다.
        te = te[te["volume"].fillna(0) > 0]
        if len(tr) < 20000 or te.empty:
            continue
        te["p"] = _fit(tr).predict_proba(te[FEATS].clip(-1e4, 1e4))[:, 1]
        if mkt in ABSTAIN_MARKETS:
            verdict = gate_w60q07(d, latest)
        elif mkt in MKT_WEAKNESS_MARKETS:
            verdict = gate_market_weakness(d, latest, q=MKT_WEAKNESS_Q[mkt])
        else:
            verdict = {"gate": "OFF", "fire": True, "gate_note": "이 시장에는 게이트가 없다"}
        out["gate"][mkt] = verdict
        # RISK_OFF flag: swing ranker EV roughly doubles in drawdown states (8y: 0.85 vs
        # 0.49 KOSDAQ, 0.76 vs 0.50 KOSPI touch-exit) — complementary to the intraday lanes.
        try:
            from multi_agent.tools.report_kospi_intraday_swing import market_drawdown_state
            state = market_drawdown_state(mkt)
        except Exception:
            state = {"mkt_state": "UNKNOWN"}
        # PKG-C ③: 전수 스코어 top-50 랭킹 shadow (관측 전용 — 발행/라우팅 아님)
        for rank, (_, r) in enumerate(te.nlargest(RANK_TOP, "p").iterrows(), 1):
            out.setdefault("ranking", []).append(
                {"date": str(latest.date()), "market": mkt, "rank": rank,
                 "ticker": str(r["code"]) + (".KS" if mkt == "KOSPI" else ".KQ"),
                 "p": round(float(r["p"]), 4), "close": float(r["close"]),
                 "liq_eok": round(float(r["liq"]) / 1e8, 1)})
        if not verdict.get("fire"):
            continue          # 기권 w60q0.7: 그날은 사지 않는다 (순위 강등이 아니다)
        # `top_k` 가 명시되면 두 시장 다 그 값(수동 실행·검정용). 아니면 시장별 `TOP_K`.
        _k = top_k if top_k is not None else TOP_K.get(mkt, 3)
        for _, r in te.nlargest(_k, "p").iterrows():
            out["picks"].append({"date": str(latest.date()), "market": mkt, **state, **verdict,
                                 "ticker": str(r["code"]) + (".KS" if mkt == "KOSPI" else ".KQ"),
                                 "p": round(float(r["p"]), 4), "close": float(r["close"]),
                                 "ret_5d": round(float(r["ret_5d"]), 2) if pd.notna(r.get("ret_5d")) else None,
                                 "atr_pct": round(float(r["atr_pct"]), 2) if pd.notna(r.get("atr_pct")) else None,
                                 "liq_eok": round(float(r["liq"]) / 1e8, 1),
                                 "contract_h": CONTRACT_H.get(mkt, 5), "top_k": _k,
                                 "contract": f"buy next open; +{CONTRACT_TP*100:.0f}% touch exit within "
                                             f"{CONTRACT_H.get(mkt, 5)} sessions else close"})
    # §29 출구혼합 shadow: 당일 픽 내 ATR 3분위 밴드 → 출구 플랜 스탬프 (계약 불변, 병행채점용)
    atrs = [p["atr_pct"] for p in out["picks"] if p.get("atr_pct") is not None]
    if len(atrs) >= 3:
        lo_t, hi_t = float(np.quantile(atrs, 0.33)), float(np.quantile(atrs, 0.67))
        for p in out["picks"]:
            a = p.get("atr_pct")
            if a is None:
                continue
            if a > hi_t:
                p["exit_band"], p["exit_mix_plan"] = "HIGH", f"고ATR → +{1.5*a:.1f}%(1.5×ATR) 배리어 shadow"
            elif a <= lo_t:
                p["exit_band"], p["exit_mix_plan"] = "LOW", f"저ATR → 트레일링(고점-{1.5*a:.1f}%) shadow"
            else:
                p["exit_band"], p["exit_mix_plan"] = "MID", "중ATR → 현행 +5% 터치 (shadow 동일)"
    return out


def ranking_shadow(ranking: List[Dict[str, Any]], now_iso: str) -> Dict[str, Any]:
    """PKG-C ③: 랭킹 shadow 원장 append + px_long 종가 기반 fwd5 정산 (관측 전용).

    정산 근사: 익일 종가 진입 → +5세션 종가 (close-to-close; 터치 미반영 — 심도 비교는
    랭크 간 동일 기준이면 공정하므로 근사로 충분, 명시). 심도 요약: top1/2-10/11-50."""
    rows: List[Dict[str, Any]] = []
    if RANK_LEDGER.exists():
        rows = [json.loads(l) for l in RANK_LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    existing = {(r.get("date"), r.get("ticker")) for r in rows}
    for r in ranking:
        if (r["date"], r["ticker"]) not in existing:
            rows.append({**r, "fwd5_cc": None, "logged_at": now_iso})
    # 정산: 8일+ 경과 & 미정산 → px_long 종가 조인
    need = [r for r in rows if r.get("fwd5_cc") is None
            and (pd.Timestamp.utcnow().tz_localize(None) - pd.Timestamp(r["date"])).days >= 8]
    if need:
        try:
            px = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "date", "close"])
            px["date"] = pd.to_datetime(px["date"])
            by_code = {c: g.sort_values("date").reset_index(drop=True) for c, g in
                       px[px["code"].isin({str(r["ticker"]).split(".")[0] for r in need})].groupby("code")}
            for r in need:
                g = by_code.get(str(r["ticker"]).split(".")[0])
                if g is None:
                    continue
                after = g[g["date"] > pd.Timestamp(r["date"])]
                if len(after) < 6:
                    continue
                entry, exitc = float(after["close"].iloc[0]), float(after["close"].iloc[5])
                if entry > 0:
                    r["fwd5_cc"] = round((exitc / entry - 1) * 100, 2)
        except Exception:
            pass
    RANK_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    RANK_LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    # 심도 요약 (net, COST 차감)
    done = [r for r in rows if isinstance(r.get("fwd5_cc"), (int, float))]
    def _band(lo, hi):
        v = [r["fwd5_cc"] - COST for r in done if lo <= r["rank"] <= hi]
        return {"n": len(v), "ev": round(float(np.mean(v)), 2)} if v else {"n": 0}
    return {"ledger_rows": len(rows), "settled": len(done),
            "depth": {"top1": _band(1, 1), "r2_10": _band(2, 10), "r11_50": _band(11, 50)},
            "kill_rule": "n>=30/구간에서 top1>r2_10>r11_50 단조성 부재 시 보드 폐기 (사전등록)"}


def resolve_pending(today: pd.Timestamp) -> Dict[str, Any]:
    import FinanceDataReader as fdr
    if not LEDGER.exists():
        return {"resolved": 0}
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    changed = False
    for row in rows:
        if row.get("policy_ret") is not None:
            continue
        d = pd.to_datetime(row.get("date"), errors="coerce")
        # 🔴 **발행 당시 계약으로 채점한다.** 픽은 자기가 발행된 계약을 `contract_h` 로 들고 다닌다.
        # 계약을 바꾸면서 미정산 과거 픽까지 새 H 로 채점하면, 그 픽이 약속하지 않은 창으로 재는 것이고
        # 전진 기록이 소급 변조된다. `contract_h` 가 없는 행 = 2026-08-23 이전 발행 = H 5 계약이다.
        _H_row = int(row.get("contract_h") or 5)
        # 창이 끝나기 전에 정산하면 미완성 계약을 채점한다. H 가 픽별이므로 대기도 픽별이다.
        _wait = 10 if _H_row <= 5 else 18
        if pd.isna(d) or (today - d).days < _wait:
            continue
        try:
            bare = str(row["ticker"]).split(".")[0]
            h = fdr.DataReader(bare, str(d.date()))
            h = h[h.index > d]  # sessions after signal day
            if len(h) < 6:
                continue
            entry = float(h["Open"].iloc[0])
            if not np.isfinite(entry) or entry <= 0:
                continue
            _H = _H_row      # 발행 당시 계약 (위 참조)
            if len(h) < _H + 1:
                continue
            tgt = entry * (1.0 + CONTRACT_TP)
            win5 = h.iloc[:_H]
            ret = float((win5["Close"].iloc[-1] / entry - 1) * 100)
            touched = 0
            for k in range(_H):
                hi = float(win5["High"].iloc[k])
                if np.isfinite(hi) and hi >= tgt:
                    o = float(win5["Open"].iloc[k])
                    fill = max(tgt, o) if (k > 0 and np.isfinite(o) and o > 0) else tgt
                    ret = (fill / entry - 1) * 100
                    touched = 1
                    break
            row["entry_open"] = round(entry, 2)
            row["contract_h"] = _H
            row["ft_touch5"] = touched
            row["policy_ret"] = round(ret, 2)
            # §29 출구혼합 shadow 병행채점 (계약 불변): 밴드별 대체 출구의 실현수익
            a = row.get("atr_pct"); band = row.get("exit_band")
            if a is not None and band in ("HIGH", "LOW", "MID"):
                op5 = win5["Open"].astype(float); hi5v = win5["High"].astype(float)
                cl5 = win5["Close"].astype(float)
                if band == "HIGH":
                    mtg = entry * (1 + 0.015 * float(a))
                    mret = float((cl5.iloc[-1] / entry - 1) * 100)
                    for k in range(len(win5)):
                        if np.isfinite(hi5v.iloc[k]) and hi5v.iloc[k] >= mtg:
                            o = op5.iloc[k]
                            fill = max(mtg, float(o)) if (k > 0 and np.isfinite(o) and o > 0) else mtg
                            mret = (fill / entry - 1) * 100
                            break
                elif band == "LOW":
                    hh = entry
                    mret = float((cl5.iloc[-1] / entry - 1) * 100)
                    for k in range(len(win5)):
                        hh = max(hh, float(hi5v.iloc[k]) if np.isfinite(hi5v.iloc[k]) else hh)
                        if float(cl5.iloc[k]) <= hh * (1 - 0.015 * float(a)):
                            mret = (float(cl5.iloc[k]) / entry - 1) * 100
                            break
                else:
                    mret = ret
                row["exit_mix"] = round(float(mret), 2)
            changed = True
        except Exception:
            continue
    if changed:
        LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    res = [r for r in rows if r.get("policy_ret") is not None]
    if not res:
        return {"resolved": 0}
    rets = [float(r["policy_ret"]) - COST for r in res]
    mix = [float(r["exit_mix"]) - COST for r in res if isinstance(r.get("exit_mix"), (int, float))]
    return {"resolved": len(res),
            **({"exit_mix_n": len(mix), "exit_mix_ev": round(float(np.mean(mix)), 2)} if mix else {}),
            "touch5_pct": round(float(np.mean([r["ft_touch5"] for r in res])) * 100, 1),
            "ev_net_avg": round(float(np.mean(rets)), 2),
            "worst": round(float(np.min(rets)), 2)}


def main() -> None:
    ap = argparse.ArgumentParser(description="KR swing CANDIDATE producer (observation-only).")
    ap.add_argument("--top-k", type=int, default=None,
                    help="두 시장 공통 강제값. 생략하면 시장별 TOP_K (KOSPI 3 / KOSDAQ 1)")
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    scored = score_today(args.top_k)
    # append only new (date, ticker) rows
    existing = set()
    # 🔴 `(date,ticker)` 만으로는 계약 깊이가 안 지켜진다. 랭커는 실행마다 다른 종목을
    # 낼 수 있고(같은 레시피·시드로도 원장 top3 재현율 42.7%/54.4%), 그러면 재실행이
    # **같은 날에 픽을 더 얹는다.** 실측: 정산 212건 중 33건(15.6%)이 계약 깊이를
    # 넘었고 9개 일자는 실효 깊이가 5~6 이었다. EV 를 −0.128 끌었다.
    # 계약은 「(날짜, 시장)당 TOP_K 건」이므로 원장이 그 한도를 직접 지킨다.
    filled: Dict[Tuple[Any, Any], int] = {}
    if LEDGER.exists():
        for l in LEDGER.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                existing.add((r.get("date"), r.get("ticker")))
                k = (r.get("date"), r.get("market"))
                filled[k] = filled.get(k, 0) + 1
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        for p in scored["picks"]:
            slot = (p["date"], p.get("market"))
            quota = TOP_K.get(p.get("market"), 1)
            if filled.get(slot, 0) >= quota:
                continue          # 이 날·이 시장은 이미 계약만큼 찼다
            if (p["date"], p["ticker"]) not in existing:
                filled[slot] = filled.get(slot, 0) + 1
                fh.write(json.dumps({**p, "ft_touch5": None, "policy_ret": None,
                                     "logged_at": now.isoformat()}, ensure_ascii=False) + "\n")
    # P3 교체 스위치 (기본 OFF): AG_SWING_CANDIDATE_ROUTE=1이면 후보픽을 라이브 라우팅 —
    # 스윙 앙상블(fwd 45%/-0.5, DEGRADE 궤도) 교체 결정 시 env 플립 하나로 전환.
    # 근거: 8y walk-forward +0.65 CI>0 (§7-A) vs 앙상블 실측 미달 (§13/재귀게이트).
    routed = 0
    # 2026-07-06 운영자 결정(P3): 기본 ON — 스윙 앙상블(DEGRADE) 교체. 근거: 8y +0.65 CI>0 (§7-A).
    if os.getenv("AG_SWING_CANDIDATE_ROUTE", "1").strip() in ("1", "true", "True") and scored["picks"]:
        try:
            from report_swing_ensemble import _route_live
            rp = [{"ticker": p["ticker"], "market": p["market"], "p": p["p"] if p["p"] <= 1.5 else p["p"] / 100.0,
                   "entry_reference_price": p["close"]} for p in scored["picks"]]
            routed = _route_live(rp, "SWING-CAND-" + scored["as_of"].replace("-", ""), now.isoformat(),
                                 bucket="swing_candidate", decision="SWING_CANDIDATE_BUY", lane="SWING_CANDIDATE")
        except Exception as exc:
            routed = -1
            print(json.dumps({"route_error": repr(exc)[:200]}))
    summary = resolve_pending(pd.Timestamp(now.date()))
    rank_summary = None
    # 🔴 기본값 0 (2026-09-02). 사전등록 킬이 **2026-08-16 에 선언됐는데 기본값이 1 로 남아 있었다** —
    # 그 뒤로 1,304행이 더 쌓였고 센티넬 `kr_ranking_shadow_kill_enforced`(critical)가
    # 「죽은 보드가 생산을 재개했다」로 발동해 있었다. 킬은 선언만으로 집행되지 않는다.
    # 되살리려면 명시적으로 `AG_SWING_RANKING_SHADOW=1` 을 줘야 하고, 그건 킬을 되돌리는 결정이다.
    if os.getenv("AG_SWING_RANKING_SHADOW", "0").strip() in ("1", "true", "True") and scored.get("ranking"):
        try:
            rank_summary = ranking_shadow(scored["ranking"], now.isoformat())
        except Exception as exc:
            rank_summary = {"error": repr(exc)[:200]}
    report = {"generated_at": now.isoformat(), "as_of": scored["as_of"], "tier": "CANDIDATE",
              "label": LABEL, "abstention": f"w{GATE_W}q{GATE_Q}", "gate": scored.get("gate"),
              "expectation": "근거 셀은 분기 WF 단일모델 기준 2026 net KOSPI +1.35 / KOSDAQ +1.13. "
                             "운영자 결정(이중모델)은 게이트와 픽이 다른 모델이므로 그 수치를 그대로 "
                             "기대하면 안 된다 — 전진 실측으로 다시 잰다 (SPEC_w60q0.7.md)",
              "picks": scored["picks"], "forward_summary": summary, "routed": routed,
              "ranking_shadow": rank_summary}
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    gtxt = " / ".join(f"{k} {v.get('gate')}" for k, v in (scored.get("gate") or {}).items())
    # 데이터 건강 상태를 픽 **위에** 적는다. 아래에 적으면 안 읽는다.
    health = []
    if scored.get("label_stale_days"):
        health.append(f"🔴 학습 라벨이 엠바고 너머로 **{scored['label_stale_days']}일** 더 낡았다"
                      f"(최종 {scored.get('label_max')}). `marcap → px_delisted → p2_label` 사슬이"
                      f" 일일 운영에 없다 — 재구축이 필요하다."
                      f" **{scored.get('label_hard_stop_on')} 부터는 픽을 아예 못 낸다**")
    for _m, _u in (scored.get("universe") or {}).items():
        if _u.get("anomalous"):
            health.append(f"🔴 {_m} 유니버스에서 **{_u['shortfall']:.0f}종목**이 갑자기 빠졌다"
                          f"(최근 수준 {_u['recent_level']:.0f} → {_u['count']},"
                          f" 전례 최대 {_u['worst_before']:.0f}) — 입력이 말없이 줄었다")
    lines = [f"# KR swing CANDIDATE picks — {scored['as_of']}", ""]
    if health:
        lines += ["> **데이터 건강 경고**"] + [f"> - {h}" for h in health] + [""]
    lines += [f"- tier: CANDIDATE (후보픽) | label: {LABEL} | 기권 w{GATE_W}q{GATE_Q}: {gtxt or 'n/a'}",
              f"- forward: {summary}", "",
              "| Market | Ticker | p | liq(억) | close |", "|---|---|---:|---:|---:|"]
    for p in scored["picks"]:
        lines.append(f"| {p['market']} | {p['ticker']} | {p['p']} | {p['liq_eok']} | {p['close']} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # 일일 운영이 잡는 것은 이 한 줄뿐이다. 건강 필드를 여기 안 실으면 아무도 못 본다.
    print(json.dumps({"as_of": scored["as_of"], "picks": len(scored["picks"]), "forward": summary,
                      "label_stale_days": scored.get("label_stale_days"),
                      "universe_anomalous": sorted(m for m, u in (scored.get("universe") or {}).items()
                                                   if u.get("anomalous"))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
