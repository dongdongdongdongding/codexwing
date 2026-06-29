# 배포 가이드 — A 구조 (프론트=Vercel 공개 / 백엔드=로컬 + 터널)

```
[브라우저] → https://xxx.vercel.app (정적 프론트)
           → fetch(VITE_API_BASE) = https://yyy.trycloudflare.com (터널)
           → localhost:8800 (로컬 FastAPI 백엔드)
```
프론트는 정적 빌드라 Vercel이 서빙. 백엔드는 내 PC에서 돌고, 터널로만 공개. 데이터/키는 전부 로컬에 남음.

---

## 1. 로컬 백엔드 띄우기
```bash
# .env(.local)에 보안 변수 설정 후:
export TZ="Asia/Seoul"                                    # 서버시간 KST 고정(데이터 날짜/스캔 시각)
export WEB_API_TOKEN="<길고-랜덤한-토큰>"
export WEB_ALLOWED_ORIGINS="https://<당신>.vercel.app"   # 콤마로 여러개 가능
python3 -m uvicorn web.backend.main:app --host 127.0.0.1 --port 8800
```
> `TZ=Asia/Seoul`은 호스트(특히 UTC 기본인 클라우드)와 무관하게 naive `datetime.now()`를 KST로 고정합니다.
> launchd 운영잡(dailyops·auto-scan·premarket·learning·discord)엔 plist EnvironmentVariables로 이미 박혀 있음.
- `WEB_API_TOKEN` 설정 → 모든 `/api`가 `Authorization: Bearer <토큰>` 요구 (미설정시 무인증=로컬전용).
- `WEB_ALLOWED_ORIGINS` 설정 → CORS를 내 Vercel 도메인으로 제한 (미설정시 `*`).
- 터널이 외부 노출을 담당하므로 `--host 127.0.0.1`로 충분.

## 2. 터널 (localhost:8800 → 공개 HTTPS URL)
```bash
# Cloudflare Tunnel (설치: brew install cloudflared)
cloudflared tunnel --url http://localhost:8800
# → https://random-words.trycloudflare.com 출력 (이게 VITE_API_BASE)
```
> 빠른 임시 터널은 재시작마다 URL이 바뀜. 고정 URL은 named tunnel(도메인 연결) 사용.

## 3. Vercel 대시보드 설정 (코드 아님 — 직접)
- **Git → Production Branch**: `feat/b-engine-deploy`
- **Build & Development → Root Directory**: `web/frontend`
- **Framework Preset**: Vite (Build `npm run build`, Output `dist` 자동)
- **Environment Variables**:
  - `VITE_API_BASE` = 2번 터널 URL (끝 슬래시 없이)
  - `VITE_API_TOKEN` = 1번 `WEB_API_TOKEN`과 **동일 값**
- 위 변경 후 **Redeploy** (env는 빌드타임 주입이라 재배포 필요).

## 4. 동작 확인
- Vercel 사이트 접속 → 픽/차트/스캔 정상 로드.
- 백엔드/터널 꺼지면 데이터 안 뜸(프론트 껍데기만). 정상 — 백엔드는 내 PC에서만 돈다.

---

## ⚠️ 보안 한계 (정직)
- `VITE_API_TOKEN`은 프론트 번들에 박혀 **사이트 열람자에겐 보임**. 자동 봇/드라이브-바이는 막지만, 번들을 까보는 사람은 추출 가능.
- 진짜 비공개가 필요하면: **Cloudflare Access**(터널단 SSO/OTP 인증) 또는 Vercel Password Protection 사용. 그러면 토큰 게이트는 보조 수단.
- KIS/Gemini/Supabase 등 진짜 비밀키는 **백엔드 .env에만** — 절대 `VITE_` 변수로 두지 말 것.
