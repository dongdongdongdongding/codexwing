#!/usr/bin/env bash
# 백엔드(8800) Cloudflare 임시터널 + 자동 치유 (2026-07-13).
# 임시터널은 재시작마다 주소가 바뀜 → 새 주소를 web/frontend/public/tunnel.json에 쓰고
# git push → Vercel 자동 재배포 → 프론트가 런타임에 /tunnel.json으로 발견.
# launchd KeepAlive: 터널 죽으면 전체 재실행 → 새 주소도 자동 반영.
set -uo pipefail
REPO="/Users/dongdong/Projects/codex_swing/swing-main"
# 2026-08-14 수리: macOS mktemp는 접미사 템플릿(XXXX.log) 미지원 — 첫 실행이 만든 리터럴
# 파일과 충돌해 이후 모든 재시작에서 "File exists" 실패 → LOG="" → cloudflared 미기동
# 좀비 루프(163회, 7/13 터널 사망 후 한 달 복구 불능). 트레일링 X + 고정 경로 폴백 + 가드.
rm -f /tmp/cloudflared.XXXX.log
LOG="$(mktemp /tmp/cloudflared.XXXXXX 2>/dev/null || echo "/tmp/cloudflared.$$.log")"
: > "$LOG" || { echo "[tunnel] 로그 파일 생성 실패"; exit 1; }
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"

cloudflared tunnel --url http://127.0.0.1:8800 --no-autoupdate > "$LOG" 2>&1 &
CFPID=$!
# 자식 즉사 감지 — URL 루프 2분 낭비 방지
sleep 2
kill -0 "$CFPID" 2>/dev/null || { echo "[tunnel] cloudflared 즉시 종료"; tail -5 "$LOG"; exit 1; }
URL=""
for i in $(seq 1 60); do
  URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$LOG" | head -1 || true)
  [[ -n "$URL" ]] && break
  sleep 2
done
if [[ -n "$URL" ]]; then
  echo "[tunnel] $URL"
  CUR=$(python3 -c "import json;print(json.load(open('$REPO/web/frontend/public/tunnel.json')).get('api',''))" 2>/dev/null || echo "")
  if [[ "$URL" != "$CUR" ]]; then
    printf '{"api": "%s", "updated": "%s"}\n' "$URL" "$(date -u +%FT%TZ)" > "$REPO/web/frontend/public/tunnel.json"
    cd "$REPO"
    git pull --rebase --autostash -q origin "$(git rev-parse --abbrev-ref HEAD)" || true
    git add web/frontend/public/tunnel.json
    git commit -q -m "chore(tunnel): rotate api tunnel url [auto]" || true
    git push -q || echo "[tunnel] push 실패 — 수동 확인 필요"
    echo "[tunnel] tunnel.json 갱신·푸시 완료 → Vercel 재배포 대기"
  else
    echo "[tunnel] 주소 불변"
  fi
else
  # URL 미획득 = 비정상 — 자식 정리 후 실패 종료(launchd가 깨끗하게 재시작)
  echo "[tunnel] URL 파싱 실패"; tail -5 "$LOG"
  kill "$CFPID" 2>/dev/null
  exit 1
fi
wait $CFPID
