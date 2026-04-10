# 🚀 Swing Trading Bot - 워크스페이스 세팅 가이드 (다른 기기 연동용)

이 문서는 집, 회사, 노트북 등 **새로운 환경(기기)에서 이 프로젝트를 다운로드 받고, 기존 환경과 완벽하게 동일한 상태로 세팅하여 개발 및 구동을 이어가기 위한 상세 메뉴얼**입니다.

---

## 📌 1단계: GitHub에서 소스코드 가져오기 (Clone)

먼저 터미널을 열고, 프로젝트를 저장할 폴더로 이동한 뒤 코드를 다운로드 받습니다.

```bash
# 원하는 디렉토리로 이동 (예: 바탕화면)
cd ~/Desktop

# GitHub에서 프라이빗 레포지토리 복제 (Clone)
git clone https://github.com/dongdongdongdongding/swing.git

# 다운로드가 완료된 폴더로 진입
cd swing
```

*(참고: 프라이빗 레포지토리이므로 GitHub 연동/로그인이 안 되어 있다면 `gh auth login` 명령어를 통해 먼저 인증을 진행해야 합니다.)*

---

## 📌 2단계: 파이썬 가상환경(venv) 생성 및 활성화

운영체제에 설치된 기본 파이썬 환경이 꼬이는 것을 방지하기 위해 이 프로젝트 전용 격리 공간(가상환경)을 만듭니다. Python 3.9 이상을 권장합니다.

**✅ Mac / Linux 환경**
```bash
# 가상환경 생성 (폴더 안에 'venv'라는 폴더가 생김)
python3 -m venv venv

# 가상환경 활성화 (터미널 프롬프트 앞에 (venv)가 생기는지 확인!)
source venv/bin/activate
```

**✅ Windows 환경**
```cmd
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
.\venv\Scripts\activate
```

---

## 📌 3단계: 필수 라이브러리(Dependencies) 일괄 설치

가상환경이 활성화된 상태(`(venv)` 표시 확인)에서, 프로젝트 실행에 필요한 모든 파이썬 패키지를 설치합니다. `requirements.txt`에 명시되어 있어 한 번에 설치할 수 있습니다.

```bash
# 패키지 일괄 설치
pip install -r requirements.txt
```
*(수십 초에서 1분 정도 소요됩니다.)*

---

## 📌 4단계: 보안 환경변수(.env) 설정하기

GitHub에는 보안상 API 키나 비밀번호가 올라가지 않습니다. 따라서 새 기기에서는 **템플릿을 복사하여 본인의 API 키를 직접 다시 적어주어야 합니다.**

```bash
# 템플릿 파일을 복사하여 실제 환경변수 파일 생성
cp .env.example .env
```

복사된 `.env` 파일을 에디터(VS Code, PyCharm, 혹은 메모장)로 열고 아래 정보들을 본인의 키값으로 채워주세요.
*(기존 컴퓨터의 `.env` 내용을 그대로 복사해와도 됩니다.)*

```env
# 텔레그램 봇 토큰 (알림용 - 필수)
TELEGRAM_TOKEN=1234567890:ABCdef...
TELEGRAM_CHAT_ID=12345678

# Supabase (DB 연동 - 선택)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGci...

# OpenAI (종목 뉴스 요약 AI - 선택)
OPENAI_API_KEY=sk-proj-...
```

---

## 📌 5단계: [중요] AI 뇌(Model) 다시 굽기 (학습)

100MB가 넘는 모델 파일(`.pkl`)은 GitHub 용량 제한 정책으로 인해 올라오지 않았습니다. 따라서 **새 컴퓨터에서 AI 모델을 한 번 학습(생성)시켜 주어야 스캐너가 정상 작동**합니다.

```bash
# 모델 재학습 스크립트 실행
python train_global_brain.py
```

- **작동 방식:** 자동으로 야후 파이낸스에서 140개 글로벌/국내 주도주의 5년 치 데이터를 긁어옵니다.
- **소요 시간:** 컴퓨터 사양 및 인터넷 속도에 따라 **약 20분 ~ 30분** 정도 소요됩니다.
- **완료 확인:** `models/` 폴더 안에 `universal_rf_heavy.pkl` 파일(약 144MB)과 `optimal_threshold.pkl` 파일이 생성되면 성공입니다.

> 💡 **참고:** 한 번만 구워두면 다음부터는 이 단계를 생략해도 됩니다.

---

## 📌 6단계: 구동 및 테스트

이제 모든 세팅이 끝났습니다! 기존 컴퓨터에서 하던 것처럼 스캐너를 띄우거나 봇을 돌리면 됩니다. 똑같이 V2.5 버전의 고도화된 스캐너가 작동합니다.

**1. 수동 웹 스캐너 UI 실행하기**
```bash
streamlit run app.py
```
*(자동으로 브라우저가 열리며 스캐너 화면이 나옵니다.)*

**2. 자동 봇 실행하기 (터미널 백그라운드)**
```bash
python auto_bot.py
```

---

## 🔄 마무리: 작업 이어가기 & 동기화 (Sync)

새 기기에서 코드를 수정(개발)했다면, 기존 기기로 가기 전에 깃허브에 푸시(저장)해야 합니다.

**새 기기에서 작업 끝내고 저장할 때:**
```bash
git add .
git commit -m "작업 내용 요약"
git push
```

**기존 기기로 돌아와서 최신 코드 가져올 때:**
```bash
# (기존 기기의 터미널에서)
git pull
```

이 사이클을 반복하시면 기기가 몇 대든 상관없이 항상 최신 버전을 유지하며 개발할 수 있습니다! 🚀
