"""
sector_analysis.py
═══════════════════════════════════════════════════════
Pillar 4: Sector Rotation & Relative Strength Filter

목적:
  - 당일 시장에서 수급(돈)이 몰리는 상위 섹터만 추출
  - RS(Relative Strength) Momentum 기반 상위 3개 섹터 선별
  - Quality Gate에서 비주력 섹터 종목 자동 탈락

사용법:
  from sector_analysis import SectorRotation
  sr = SectorRotation()
  top_sectors = sr.get_top_sectors(n=3)  # ['반도체', '2차전지', '바이오']
  is_ok = sr.is_in_top_sector('005930.KS', n=3)  # True/False
"""

import warnings
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')


# ══════════════════════════════════════════════════════════
# 섹터 → ETF 매핑 (KOSPI/KOSDAQ 대표 ETF)
# ══════════════════════════════════════════════════════════
SECTOR_ETFS = {
    '반도체':    '091160.KS',  # KODEX 반도체
    '2차전지':   '305720.KS',  # KODEX 2차전지
    '바이오':    '244580.KS',  # KODEX 바이오 (KOSPI)
    '자동차':    '091180.KS',  # KODEX 자동차
    '은행':      '091170.KS',  # KODEX 은행
    '철강':      '117700.KS',  # KODEX 철강
    '건설':      '117680.KS',  # KODEX 건설
    '화학':      '117690.KS',  # KODEX 에너지화학
    'IT':        '139260.KS',  # TIGER 200 IT
    '기계':      '102970.KS',  # KODEX 기계장비
    '헬스케어':  '266420.KS',  # KODEX 헬스케어
    '미디어':    '261250.KS',  # KODEX K-미디어엔터테인먼트
}

# --- GLOBAL CACHE TO PREVENT PER-INSTANCE FETCH FLOODING ---
_GLOBAL_ETF_SERIES_CACHE = {}
_GLOBAL_RS_SCORES_CACHE = {}
_GLOBAL_CACHE_TIME = None

# 종목 → 섹터 매핑 (주요 종목)
TICKER_SECTOR = {
    # 반도체
    '005930.KS': '반도체', '000660.KS': '반도체', '042700.KS': '반도체',
    # 2차전지
    '051910.KS': '2차전지', '006400.KS': '2차전지', '373220.KS': '2차전지',
    # 바이오
    '068270.KS': '바이오', '207940.KS': '바이오', '214370.KQ': '바이오',
    '145020.KQ': '바이오', '293490.KQ': '바이오',
    # 자동차
    '005380.KS': '자동차', '012330.KS': '자동차', '018260.KS': '자동차',
    # 은행/금융
    '105560.KS': '은행', '055550.KS': '은행',
    # IT/인터넷
    '035720.KS': 'IT', '035420.KS': 'IT', '259960.KQ': 'IT',
    '035900.KQ': 'IT', '028300.KQ': 'IT', '086520.KQ': 'IT',
    # 화학
    '003670.KS': '화학', '011200.KS': '화학',
    # 건설/기계
    '000270.KS': '건설', '028260.KS': '기계',
    # 기타
    '095660.KQ': 'IT', '103140.KQ': 'IT', '112040.KQ': 'IT',
}


class SectorRotation:
    """섹터 RS Momentum 분석기"""

    def __init__(self, lookback_days: int = 20):
        self.lookback = lookback_days
        self._cache = {}
        self._rs_scores = {}
        self._last_computed = None

    def _fetch_etf_returns(self) -> dict:
        """각 섹터 ETF의 Lookback 기간 수익률 계산"""
        end   = datetime.now()
        start = end - timedelta(days=self.lookback + 30)

        results = {}
        for sector, etf in SECTOR_ETFS.items():
            try:
                df = yf.download(etf, start=start.strftime('%Y-%m-%d'),
                                 end=end.strftime('%Y-%m-%d'),
                                 progress=False, auto_adjust=True)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                if df.empty or len(df) < 10:
                    continue

                close = df['Close']
                # 최근 lookback 영업일 수익률
                n = min(self.lookback, len(close) - 1)
                ret = (close.iloc[-1] / close.iloc[-n-1] - 1) * 100
                volume_trend = df['Volume'].tail(5).mean() / df['Volume'].tail(20).mean()

                results[sector] = {
                    'return': round(float(ret), 2),
                    'vol_trend': round(float(volume_trend), 2),
                    'etf': etf,
                    # RS Score = 수익률 60% + 거래량 변동 40%
                    'rs_score': round(float(ret) * 0.6 + float(volume_trend - 1) * 100 * 0.4, 2)
                }
            except Exception:
                pass

        return results

    def compute_rs(self) -> dict:
        """RS 점수 계산 및 캐시"""
        global _GLOBAL_RS_SCORES_CACHE, _GLOBAL_CACHE_TIME
        now = datetime.now()
        
        # 1시간 캐시 (글로벌 캐시 사용)
        if _GLOBAL_CACHE_TIME and (now - _GLOBAL_CACHE_TIME).seconds < 3600 and _GLOBAL_RS_SCORES_CACHE:
            return _GLOBAL_RS_SCORES_CACHE

        raw = self._fetch_etf_returns()
        if not raw:
            return {}

        # RS Score 기준 정렬
        sorted_sectors = sorted(raw.items(), key=lambda x: x[1]['rs_score'], reverse=True)
        self._rs_scores = {s: d for s, d in sorted_sectors}
        
        # 글로벌 캐시 업데이트
        _GLOBAL_RS_SCORES_CACHE = self._rs_scores
        _GLOBAL_CACHE_TIME = now
        
        return self._rs_scores

    def get_top_sectors(self, n: int = 3) -> list:
        """상위 n개 섹터명 반환"""
        rs = self.compute_rs()
        return list(rs.keys())[:n]

    def get_sector_report(self) -> str:
        """섹터 RS 리포트 (UI 표시용)"""
        rs = self.compute_rs()
        if not rs:
            return "⚠️ 섹터 데이터 없음"

        lines = ["📊 섹터 RS Momentum (최근 20일):", "─" * 40]
        for i, (sector, info) in enumerate(rs.items()):
            rank = i + 1
            ret  = info['return']
            vol  = info['vol_trend']
            emoji = '🟢' if rank <= 3 else ('🟡' if rank <= 6 else '🔴')
            lines.append(f" {emoji} #{rank} {sector:6s} | 수익률 {ret:+.1f}% | 거래량 {vol:.1f}x")
        return "\n".join(lines)

    def _get_etf_close_series(self) -> dict:
        """Fetch and cache ETF closing price series for correlation"""
        global _GLOBAL_ETF_SERIES_CACHE, _GLOBAL_CACHE_TIME
        now = datetime.now()
        
        if _GLOBAL_CACHE_TIME and (now - _GLOBAL_CACHE_TIME).seconds < 3600 and _GLOBAL_ETF_SERIES_CACHE:
            return _GLOBAL_ETF_SERIES_CACHE

        end   = datetime.now()
        start = end - timedelta(days=self.lookback + 30)
        
        series_dict = {}
        for sector, etf in SECTOR_ETFS.items():
            try:
                df = yf.download(etf, start=start.strftime('%Y-%m-%d'),
                                 end=end.strftime('%Y-%m-%d'),
                                 progress=False, auto_adjust=True)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                if not df.empty and len(df) >= 10:
                    series_dict[sector] = df['Close']
            except Exception:
                pass
                
        _GLOBAL_ETF_SERIES_CACHE = series_dict
        _GLOBAL_CACHE_TIME = now
        return series_dict

    def get_ticker_sector_dynamic(self, ticker: str, ticker_df: pd.DataFrame = None) -> str:
        """
        [Dynamic Clustering] Determine a stock's sector based on price correlation with ETFs.
        If correlation is weak (< 0.5), defaults to '기타' (Other).
        """
        # Hardcoded overrides first
        if ticker in TICKER_SECTOR:
            return TICKER_SECTOR[ticker]
            
        if ticker_df is None or len(ticker_df) < 20:
            return '기타'
            
        try:
            etf_series = self._get_etf_close_series()
            stock_close = ticker_df['Close'].tail(self.lookback).pct_change().dropna()
            
            best_sector = '기타'
            best_corr = 0.4  # Minimum threshold for correlation
            
            for sector, etf_close in etf_series.items():
                ec = etf_close.tail(self.lookback).pct_change().dropna()
                
                # Align dates
                combined = pd.concat([stock_close, ec], axis=1).dropna()
                if len(combined) > 10:
                    corr = combined.iloc[:, 0].corr(combined.iloc[:, 1])
                    if corr > best_corr:
                        best_corr = corr
                        best_sector = sector
            
            return best_sector
        except Exception:
            return '기타'

    def is_in_top_sector(self, ticker: str, n: int = 3, ticker_df: pd.DataFrame = None) -> bool:
        """
        종목이 상위 n개 섹터에 속하는지 확인.
        상관관계(Correlation) 기반의 동적 클러스터링 적용.
        """
        sector = self.get_ticker_sector_dynamic(ticker, ticker_df)
        if sector == '기타':
            return True  # 테마를 특정할 수 없는 개별주는 패널티/혜택 미부여 (통과)
            
        tops = self.get_top_sectors(n)
        return sector in tops

    def get_ticker_sector(self, ticker: str) -> str:
        """Legacy static fallback"""
        return TICKER_SECTOR.get(ticker, '기타')


# ── CLI 테스트 ────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "🔥" * 20)
    print("  PILLAR 4: SECTOR ROTATION ANALYSIS")
    print("🔥" * 20 + "\n")

    sr = SectorRotation(lookback_days=20)
    print(sr.get_sector_report())

    print(f"\n상위 3개 섹터: {sr.get_top_sectors(3)}")
    print(f"\n삼성전자(005930) in Top3? {sr.is_in_top_sector('005930.KS', 3)}")
    print(f"LG화학(051910)  in Top3? {sr.is_in_top_sector('051910.KS', 3)}")
    print(f"카카오(035720)  in Top3? {sr.is_in_top_sector('035720.KS', 3)}")
