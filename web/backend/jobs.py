"""백그라운드 스캔 잡 (기획 R4) — 탭 이동/이탈해도 서버에서 계속 실행. 동시 1개 락.

타깃별 모델 분리 실행:
  kospi_swing/kosdaq_swing/nasdaq_swing/kospi_intraday/kosdaq_intraday  = 단일 레인(모델)
  b = B 시장중립(b_engine)
  kospi_all/kosdaq_all = 시장별 스윙+장중
  all = 전체(B + KR 4레인 + 나스닥)
단계별 진행률·하트비트. /api/ops/scan 으로 어디서나 상태 조회. 완료시 picks 자동 최신화.
"""
from __future__ import annotations
import os, sys, threading, traceback
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

_LOCK = threading.Lock()
_STATE = {"status": "idle", "progress": 0, "steps": [], "started_at": None,
          "finished_at": None, "message": "", "current": "", "target": ""}

# 단일 스텝 정의: 라벨 → spec ("b" | (market, mode))
_STEP = {
    "kospi_swing": ("코스피 스윙", ("KOSPI", "SWING")),
    "kosdaq_swing": ("코스닥 스윙", ("KOSDAQ", "SWING")),
    "nasdaq_swing": ("나스닥 스윙", ("NASDAQ", "SWING")),
    "kospi_intraday": ("코스피 장중", ("KOSPI", "INTRADAY")),
    "kosdaq_intraday": ("코스닥 장중", ("KOSDAQ", "INTRADAY")),
    "b": ("B 시장중립", "b"),
}
# 타깃 → 실행할 스텝키 목록 (모델 분리)
TARGETS = {
    "kospi_swing": ["kospi_swing"],
    "kosdaq_swing": ["kosdaq_swing"],
    "nasdaq_swing": ["nasdaq_swing"],
    "kospi_intraday": ["kospi_intraday"],
    "kosdaq_intraday": ["kosdaq_intraday"],
    "b": ["b"],
    "kospi_all": ["kospi_swing", "kospi_intraday"],
    "kosdaq_all": ["kosdaq_swing", "kosdaq_intraday"],
    "all": ["b", "kospi_swing", "kospi_intraday", "kosdaq_swing", "kosdaq_intraday", "nasdaq_swing"],
}
TARGET_LABELS = {
    "kospi_swing": "코스피 스윙", "kosdaq_swing": "코스닥 스윙", "nasdaq_swing": "나스닥 스윙",
    "kospi_intraday": "코스피 장중", "kosdaq_intraday": "코스닥 장중", "b": "시장중립",
    "kospi_all": "코스피 전체", "kosdaq_all": "코스닥 전체", "all": "전체",
}


def status():
    return dict(_STATE)


def _set(**kw):
    _STATE.update(kw)


def _run_step(spec):
    """단일 스텝 실행 → (ok, note)."""
    try:
        if spec == "b":
            from b_engine import model_scan
            out = model_scan.scan()
            return True, (f"top{len(out['picks'])}" if out else "no-data")
        from modules.model_lane_scan import run_model_lane_scan
        res = run_model_lane_scan(spec[0], spec[1], route=True)
        if res.get("error"):
            return False, str(res.get("error"))[:80]
        try:
            from web.backend.scans import record_source
            record_source(res.get("run_id"), "manual")
        except Exception:
            pass
        return True, f"{len(res.get('picks', []))}픽"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:80]}"


def _run(target):
    keys = TARGETS.get(target, TARGETS["all"])
    steps = [_STEP[k] for k in keys]
    _set(status="running", progress=0, steps=[], started_at=datetime.now().isoformat(timespec="seconds"),
         finished_at=None, message="", current="", target=TARGET_LABELS.get(target, target))
    done = []
    for i, (label, spec) in enumerate(steps):
        _set(current=label, progress=int(i / len(steps) * 100))
        ok, note = _run_step(spec)
        done.append({"step": label, "ok": ok, "note": note})
        _set(steps=list(done))
    _set(status="done", progress=100, current="",
         finished_at=datetime.now().isoformat(timespec="seconds"), message="완료")


def start(target: str = "all"):
    """스캔 시작. 이미 실행중이면 거부(락). target=9종."""
    if target not in TARGETS:
        target = "all"
    if not _LOCK.acquire(blocking=False):
        return {"ok": False, "reason": "이미 스캔 실행중"}

    def runner():
        try:
            _run(target)
        except Exception:
            _set(status="error", message=traceback.format_exc()[-300:])
        finally:
            _LOCK.release()
    threading.Thread(target=runner, daemon=True).start()
    return {"ok": True, "started": True, "target": target}


def targets():
    """프론트 드롭다운용 타깃 목록(순서 보존)."""
    order = ["kospi_swing", "kosdaq_swing", "nasdaq_swing", "kospi_intraday", "kosdaq_intraday",
             "b", "kospi_all", "kosdaq_all", "all"]
    return [{"key": k, "label": TARGET_LABELS[k]} for k in order]
