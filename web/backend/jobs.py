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


def _norm_picks(picks):
    out = []
    for p in picks or []:
        t = p.get("ticker") or p.get("code")
        if not t:
            continue
        prob = p.get("p") if p.get("p") is not None else p.get("prob_win")
        out.append({"ticker": str(t), "name": p.get("name"), "prob": prob,
                    "entry": p.get("entry_reference_price") or p.get("close") or p.get("entry_price"),
                    "market": str(p.get("market") or "")})
    return out


def _run_step(label, spec):
    """단일 스텝 실행 → 저널 레코드. 결과가 무엇이든(0픽/저장픽/세션블록/에러) 사유와 함께 남긴다 —
    스캔 피드가 이 레코드를 게시물로 보장 표시한다 (swing-main-bbe9)."""
    rec = {"label": label, "ok": False, "note": "", "run_id": "", "picks": [], "stale": False,
           "market": "B시장중립" if spec == "b" else spec[0]}
    try:
        if spec == "b":
            from b_engine import model_scan
            # 강제는 엔진(model_scan.suspension)이 한다. 여기서는 실행자가 화면에서
            # 사유를 볼 수 있도록 저널·진행표시에 정지 사실을 남긴다 — 이번 사고의
            # 핵심 피해가 "자기가 뭘 기록했는지 몰랐다"였기 때문이다 (trace-b-lane-f7).
            susp = model_scan.suspension()
            if susp:
                rec.update(ok=False, suspended=True,
                           note=f"정지됨 (since {susp.get('since') or '?'}) — 신규 픽 미발행")
                return rec
            out = model_scan.scan()
            rec.update(ok=bool(out), run_id=f"B-{(out or {}).get('scan_date', '')}",
                       picks=_norm_picks((out or {}).get("picks")),
                       note=f"top{len((out or {}).get('picks') or [])}" if out else "no-data")
            return rec
        from modules.model_lane_scan import run_model_lane_scan
        res = run_model_lane_scan(spec[0], spec[1], route=True)
        rec.update(run_id=str(res.get("run_id") or ""), picks=_norm_picks(res.get("picks")),
                   stale=bool(res.get("stale_session")))
        if res.get("error"):
            rec["note"] = str(res["error"])[:120]
            return rec
        rec["ok"] = True
        if res.get("session_blocked"):
            rec["note"] = f"세션 블록: {str(res.get('session_block_reason'))[:100]}"
        elif res.get("stale_session"):
            rec["note"] = str(res.get("note") or "장중 창 미완성 — 최신 세션 저장픽 표시")[:160]
        elif not rec["picks"]:
            rec["note"] = "0픽 (모델 기권)"
        else:
            rec["note"] = f"{len(rec['picks'])}픽"
        try:
            from web.backend.scans import record_source
            record_source(rec["run_id"], "manual")
        except Exception:
            pass
    except Exception as e:
        rec["note"] = f"{type(e).__name__}: {str(e)[:100]}"
    return rec


def _write_journal(target, details, requester=None):
    """스캔 버튼 1회 = 저널 1행 (피드 게시물 1건).

    2026-08-15: `requester`(origin IP·UA) 추가. 정지 이후 B 픽 30건의 생성 주체를
    추적할 때 저널에 신원 필드가 없어 접근로그·원장 logged_at·프로세스 stdout을
    나흘치 대조해 재구성해야 했다 (trace-b-lane-f7.md §4).
    """
    try:
        import json
        from datetime import timezone
        d = os.path.join(REPO, "runtime_state", "local_short_term")
        os.makedirs(d, exist_ok=True)
        row = {"scan_id": "MANUAL-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
               "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "target": TARGET_LABELS.get(target, target), "steps": details,
               "requester": requester}
        with open(os.path.join(d, "scan_runs.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _run(target, requester=None):
    keys = TARGETS.get(target, TARGETS["all"])
    steps = [_STEP[k] for k in keys]
    _set(status="running", progress=0, steps=[], started_at=datetime.now().isoformat(timespec="seconds"),
         finished_at=None, message="", current="", target=TARGET_LABELS.get(target, target))
    done = []
    details = []
    for i, (label, spec) in enumerate(steps):
        _set(current=label, progress=int(i / len(steps) * 100))
        rec = _run_step(label, spec)
        details.append(rec)
        done.append({"step": label, "ok": rec["ok"], "note": rec["note"]})
        _set(steps=list(done))
    _write_journal(target, details, requester)
    # 스캔 결과가 픽·개요·피드에 즉시 반영되도록 캐시 무효화
    try:
        from web.backend import services as _S
        _S.invalidate_pick_caches()
        from web.backend import scans as _SC
        _SC._LIST_CACHE.update(ts=0.0, data=None)
    except Exception:
        pass
    _set(status="done", progress=100, current="",
         finished_at=datetime.now().isoformat(timespec="seconds"), message="완료")


def start(target: str = "all", requester=None):
    """스캔 시작. 이미 실행중이면 거부(락). target=9종."""
    if target not in TARGETS:
        target = "all"
    if not _LOCK.acquire(blocking=False):
        return {"ok": False, "reason": "이미 스캔 실행중"}

    def runner():
        try:
            _run(target, requester)
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
