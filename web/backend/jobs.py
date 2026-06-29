"""백그라운드 스캔 잡 (기획 R4) — 탭 이동/이탈해도 서버에서 계속 실행. 동시 1개 락.

스캔 = A 4레인(model_lane_scan) + B(b_engine model_scan). 단계별 진행률·하트비트.
상태는 어디서나 /api/ops/scan 으로 조회. 완료시 picks 자동 최신화.
"""
from __future__ import annotations
import os, sys, threading, time, traceback
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

_LOCK = threading.Lock()
_STATE = {"status": "idle", "progress": 0, "steps": [], "started_at": None,
          "finished_at": None, "message": "", "current": ""}


def status():
    return dict(_STATE)


def _set(**kw):
    _STATE.update(kw)


def _run(market_filter: str = ""):
    steps = [
        ("B 시장중립", "b"),
        ("코스피 스윙", ("KOSPI", "SWING")),
        ("코스피 장중", ("KOSPI", "INTRADAY")),
        ("코스닥 스윙", ("KOSDAQ", "SWING")),
        ("코스닥 장중", ("KOSDAQ", "INTRADAY")),
    ]
    if market_filter:
        steps = [s for s in steps if s[1] == "b" or s[1][0] == market_filter.upper()]
    _set(status="running", progress=0, steps=[], started_at=datetime.now().isoformat(timespec="seconds"),
         finished_at=None, message="", current="")
    done = []
    for i, (label, spec) in enumerate(steps):
        _set(current=label, progress=int(i / len(steps) * 100))
        ok, note = True, ""
        try:
            if spec == "b":
                from b_engine import model_scan
                out = model_scan.scan()
                note = f"top{len(out['picks'])}" if out else "no-data"
            else:
                from modules.model_lane_scan import run_model_lane_scan
                res = run_model_lane_scan(spec[0], spec[1], route=True)
                if res.get("error"):
                    ok, note = False, str(res.get("error"))[:80]
                else:
                    note = f"{len(res.get('picks', []))}픽"
                    try:   # 수동(웹) 스캔 소스 기록 → 스캔피드 게시물에 'manual' 표시
                        from web.backend.scans import record_source
                        record_source(res.get("run_id"), "manual")
                    except Exception:
                        pass
        except Exception as e:
            ok, note = False, f"{type(e).__name__}: {str(e)[:80]}"
        done.append({"step": label, "ok": ok, "note": note})
        _set(steps=list(done))
    _set(status="done", progress=100, current="", finished_at=datetime.now().isoformat(timespec="seconds"),
         message="완료")


def start(market_filter: str = ""):
    """스캔 시작. 이미 실행중이면 거부(락)."""
    if not _LOCK.acquire(blocking=False):
        return {"ok": False, "reason": "이미 스캔 실행중"}
    def runner():
        try:
            _run(market_filter)
        except Exception:
            _set(status="error", message=traceback.format_exc()[-300:])
        finally:
            _LOCK.release()
    threading.Thread(target=runner, daemon=True).start()
    return {"ok": True, "started": True}
