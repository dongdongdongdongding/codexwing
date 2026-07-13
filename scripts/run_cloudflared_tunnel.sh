#!/usr/bin/env bash
# 백엔드(8800) Cloudflare 임시터널 + 자동 치유 (2026-07-13).
# 임시터널은 재시작마다 주소가 바뀜 → 새 주소를 web/frontend/public/tunnel.json에 쓰고
# git push → Vercel 자동 재배포 → 프론트가 런타임에 /tunnel.json으로 발견.
# launchd KeepAlive: 터널 죽으면 전체 재실행 → 새 주소도 자동 반영.
set -uo pipefail
REPO="/Users/dongdong/Projects/codex_swing/swing-main"
LOG="$(mktemp /tmp/cloudflared.XXXX.log)"
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"

cloudflared tunnel --url http://127.0.0.1:8800 --no-autoupdate > "$LOG" 2>&1 &
CFPID=$!
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
  echo "[tunnel] URL 파싱 실패"; cat "$LOG" | tail -5
fi
wait $CFPID
