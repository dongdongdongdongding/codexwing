"""티커 → 종목명 해석기 (A/B 공용). 모델레인 픽 등 stock_name이 비어있을 때 폴백.

소스 우선순위: 1) 리포 번들 modules/data/ticker_names.json (FDR KRX 상장목록 스냅샷),
              2) ~/research_cache/names.parquet (있으면 최신값으로 병합).
KR 코드(6자리)만. .KS/.KQ 접미사·공백 제거 후 매칭.
"""
from __future__ import annotations
import os, json, re
from functools import lru_cache

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUNDLE = os.path.join(_HERE, "data", "ticker_names.json")


def _norm(ticker) -> str:
    s = str(ticker or "").strip().upper()
    s = s.split(".")[0]                # 489790.KS -> 489790
    s = re.sub(r"[^0-9A-Z]", "", s)
    if s.isdigit():
        s = s.zfill(6)
    return s


@lru_cache(maxsize=1)
def _name_map() -> dict:
    m: dict = {}
    try:
        with open(_BUNDLE, encoding="utf-8") as f:
            m.update({_norm(k): v for k, v in json.load(f).items()})
    except Exception:
        pass
    # 최신 캐시가 있으면 덮어쓰기(신규 상장 반영)
    cache = os.path.expanduser("~/research_cache/names.parquet")
    if os.path.exists(cache):
        try:
            import pandas as pd
            nm = pd.read_parquet(cache)
            nm["code"] = nm["code"].astype(str)
            for c, n in zip(nm["code"], nm["name"]):
                if isinstance(n, str) and n.strip():
                    m[_norm(c)] = n.strip()
        except Exception:
            pass
    return m


def resolve_name(ticker, default: str = "") -> str:
    """티커 코드 → 종목명. 못 찾으면 default(빈값이면 '')."""
    return _name_map().get(_norm(ticker), default)


def display_label(ticker, stock_name=None) -> str:
    """'종목명 (티커)' 표기. KR은 resolve_name 우선(저장 stock_name이 티커인 경우 보정),
    못 찾으면 stock_name(미국 영문명 등) 폴백, 둘 다 없으면 티커만."""
    tk = str(ticker or "-")
    name = resolve_name(ticker) or str(stock_name or "").strip()
    return f"{name} ({tk})" if name and name != tk else tk
