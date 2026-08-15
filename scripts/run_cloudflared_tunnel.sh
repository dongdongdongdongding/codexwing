#!/usr/bin/env bash
# 백엔드(8800) Cloudflare 임시터널 + 자동 치유 (2026-07-13).
# 임시터널은 재시작마다 주소가 바뀜 → 새 주소를 web/frontend/public/tunnel.json 에 담은
# 커밋을 origin 에 push → Vercel 자동 재배포 → 프론트가 런타임에 /tunnel.json 으로 발견.
# launchd KeepAlive: 터널 죽으면 전체 재실행 → 새 주소도 자동 반영.
#
# 2026-08-14 수리: macOS mktemp 는 접미사 템플릿(XXXX.log)을 지원하지 않아 첫 실행이 만든
#   리터럴 파일과 충돌 → 이후 모든 재시작이 "File exists" → LOG="" → cloudflared 미기동
#   좀비 루프(162회, 7/13 터널 사망 후 한 달 복구 불능).
#
# 2026-08-15 수리 (검증보고 orca/reports/verify-tunnel.md 의 E·B·G·C·D·F):
#   이 래퍼는 dailyops·kr-daily-auto-scan·learning 이 함께 쓰는 **공용 운영 리포**에서
#   무인으로 돈다. 그 전제 위에서 다음을 계약으로 고정한다.
#   E) 워킹트리·인덱스·HEAD·stash 를 일절 건드리지 않는다. 예전 `git pull --rebase
#      --autostash` 는 상시 갱신되는 runtime_state/*.jsonl 과 충돌해 UU 를 방치하고
#      충돌 마커(<<<<<<<)를 JSONL 에 물리적으로 기록했다 — 같은 리포를 파싱하는 다른
#      launchd 잡들이 그 지점에서 깨진다. 발행은 임시 인덱스에서 origin 팁 위에 커밋을
#      만들어 곧장 push 하므로, 그 실패 모드가 원천적으로 존재할 수 없다.
#   B) 발행이 실패하면 "완료"를 찍지 않고 exit 1 한다. 조용한 실패·거짓 성공 금지.
#   G) 리포 경로를 하드코딩하지 않는다. 스크립트 위치에서 유도하고 검증에 실패하면 중단.
#   C) /tmp 로그는 trap 으로 반드시 지운다(재시작 1회당 1개 영구 누적이던 회귀).
#   D) 정상 종료·SIGTERM 어느 경로에서도 cloudflared 자식을 고아로 남기지 않는다.
#   F) mktemp 실패 시 예측 가능한 고정 경로로 폴백하지 않는다(심링크 추종) — 즉시 중단.
set -uo pipefail

TUNNEL_JSON_REL="web/frontend/public/tunnel.json"
CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-cloudflared}"
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"

# --- G: 리포 위치 유도 -------------------------------------------------------
# launchd 는 절대경로로 이 스크립트를 호출한다. 자기 위치의 git 최상위가 곧 리포다.
# 이주 중인 경로(~/Projects → /Volumes/ORICO)를 하드코딩하지 않기 위한 것.
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" >/dev/null 2>&1 && pwd -P)"
REPO="${TUNNEL_REPO:-}"
if [[ -z "$REPO" ]]; then
  REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
fi
if [[ -z "$REPO" ]] || ! git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1; then
  echo "[tunnel] 실패: 발행 리포를 찾을 수 없다 (REPO='${REPO}', script='${SCRIPT_DIR}')." >&2
  echo "[tunnel] TUNNEL_REPO 환경변수로 명시하라. 발행 없이 터널만 띄우는 것은 무의미하므로 중단." >&2
  exit 1
fi
if [[ ! -d "$REPO/$(dirname "$TUNNEL_JSON_REL")" ]]; then
  echo "[tunnel] 실패: '$REPO' 는 발행 리포가 아니다 ($TUNNEL_JSON_REL 경로 없음). 엉뚱한 리포에 커밋하지 않고 중단." >&2
  exit 1
fi

# --- C/F: 로그 파일 ----------------------------------------------------------
LOG="$(mktemp /tmp/cloudflared.XXXXXX)" || {
  echo "[tunnel] 실패: 로그 파일 생성 실패 (mktemp)" >&2; exit 1; }
IDX=""
CFPID=""

cleanup() {
  if [[ -n "$CFPID" ]]; then
    kill "$CFPID" 2>/dev/null || true   # D: 정상·TERM 어느 경로에서도 고아 금지
  fi
  [[ -n "$LOG" ]] && rm -f "$LOG"       # C: /tmp 무제한 누적 방지
  [[ -n "$IDX" ]] && rm -f "$IDX"
  return 0
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

# --- 발행 --------------------------------------------------------------------
# 워킹트리를 건드리지 않고 origin/<branch> 위에 tunnel.json 만 바꾼 커밋을 만들어 push.
# 성공 0 / 실패 non-zero. "완료" 줄은 실제 push 가 성공한 경로에서만 출력한다(B).
publish_url() {
  local url="$1"
  local branch="" remote="" cur="" blob="" tree="" commit="" attempt=""

  branch="$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [[ -z "$branch" || "$branch" == "HEAD" ]]; then
    echo "[tunnel] 발행 실패: 브랜치를 확인할 수 없다 (detached HEAD?)" >&2
    return 1
  fi

  # 이 래퍼가 만든 것이든 아니든, 미해결 충돌은 다른 잡을 깨뜨린다 — 크게 알린다.
  if [[ -n "$(git -C "$REPO" ls-files -u 2>/dev/null | head -1)" ]]; then
    echo "[tunnel] 경고: 리포에 미해결 충돌(UU)이 남아 있다 — dailyops/auto-scan/learning 이 깨질 수 있다. 수동 정리 필요." >&2
  fi

  for attempt in 1 2 3; do
    if ! git -C "$REPO" fetch -q origin "$branch"; then
      echo "[tunnel] 발행 시도 ${attempt}/3 실패: origin fetch 불가 ($branch)" >&2
      sleep 3; continue
    fi
    remote="$(git -C "$REPO" rev-parse FETCH_HEAD 2>/dev/null || true)"
    if [[ -z "$remote" ]]; then
      echo "[tunnel] 발행 시도 ${attempt}/3 실패: FETCH_HEAD 확인 불가" >&2
      sleep 3; continue
    fi

    # 비교 대상은 로컬 워킹트리가 아니라 **origin 이 실제로 서빙하는 값**이다.
    cur="$(git -C "$REPO" show "${remote}:${TUNNEL_JSON_REL}" 2>/dev/null \
           | python3 -c 'import json,sys; print(json.load(sys.stdin).get("api",""))' 2>/dev/null || true)"
    if [[ "$url" == "$cur" ]]; then
      echo "[tunnel] 주소 불변 — 발행 생략"
      return 0
    fi

    blob="$(printf '{"api": "%s", "updated": "%s"}\n' "$url" "$(date -u +%FT%TZ)" \
            | git -C "$REPO" hash-object -w --stdin 2>/dev/null || true)"
    if [[ -z "$blob" ]]; then
      echo "[tunnel] 발행 시도 ${attempt}/3 실패: blob 생성 불가" >&2
      sleep 3; continue
    fi

    IDX="$(mktemp /tmp/tunnelidx.XXXXXX)" || {
      echo "[tunnel] 발행 실패: 임시 인덱스 생성 불가" >&2; return 1; }
    if ! GIT_INDEX_FILE="$IDX" git -C "$REPO" read-tree "$remote" \
      || ! GIT_INDEX_FILE="$IDX" git -C "$REPO" update-index --add \
             --cacheinfo "100644,${blob},${TUNNEL_JSON_REL}"; then
      echo "[tunnel] 발행 시도 ${attempt}/3 실패: 임시 인덱스 구성 불가" >&2
      rm -f "$IDX"; IDX=""; sleep 3; continue
    fi
    tree="$(GIT_INDEX_FILE="$IDX" git -C "$REPO" write-tree 2>/dev/null || true)"
    rm -f "$IDX"; IDX=""
    if [[ -z "$tree" ]]; then
      echo "[tunnel] 발행 시도 ${attempt}/3 실패: write-tree 불가" >&2
      sleep 3; continue
    fi

    commit="$(git -C "$REPO" commit-tree "$tree" -p "$remote" \
              -m "chore(tunnel): rotate api tunnel url [auto]" 2>/dev/null || true)"
    if [[ -z "$commit" ]]; then
      echo "[tunnel] 발행 시도 ${attempt}/3 실패: commit-tree 불가 (git identity 미설정?)" >&2
      sleep 3; continue
    fi

    if git -C "$REPO" push -q origin "${commit}:refs/heads/${branch}"; then
      echo "[tunnel] tunnel.json 발행 완료 (${branch} ${commit}) → Vercel 재배포 대기"
      return 0
    fi
    echo "[tunnel] 발행 시도 ${attempt}/3 실패: push 거절 (원격이 앞섰거나 도달 불가)" >&2
    sleep 3
  done
  return 1
}

# --- 터널 기동 ---------------------------------------------------------------
"$CLOUDFLARED_BIN" tunnel --url http://127.0.0.1:8800 --no-autoupdate > "$LOG" 2>&1 &
CFPID=$!
# 자식 즉사 감지 — URL 루프 2분 낭비 방지
sleep 2
kill -0 "$CFPID" 2>/dev/null || {
  echo "[tunnel] cloudflared 즉시 종료" >&2; tail -5 "$LOG" >&2; CFPID=""; exit 1; }

URL=""
for i in $(seq 1 60); do
  URL="$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$LOG" | head -1 || true)"
  [[ -n "$URL" ]] && break
  sleep 2
done

if [[ -z "$URL" ]]; then
  # URL 미획득 = 비정상 — trap 이 자식 정리, 실패 종료로 launchd 가 깨끗하게 재시작
  echo "[tunnel] URL 파싱 실패" >&2; tail -5 "$LOG" >&2
  exit 1
fi

echo "[tunnel] $URL"
if ! publish_url "$URL"; then
  echo "[tunnel] 발행 실패 — 공개 사이트는 여전히 옛 주소를 서빙한다. 터널을 내리고 종료(launchd 재시작)." >&2
  exit 1
fi

wait "$CFPID"
RC=$?
CFPID=""      # 이미 회수된 PID 를 trap 이 다시 kill 하지 않도록(PID 재사용 방지)
exit "$RC"
