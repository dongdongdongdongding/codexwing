# Antigravity Quant Explorer (Global Brain V2.5 & Phase 25 Edition)

🔥 **[최신 업데이트] Phase 25: 데이터 기반 스코어링 교정 및 머신러닝 앙상블 시스템 도입**
- **스코어링 로직 반전:** 과거 휴리스틱 로직에서 '단기과열' 및 '거래량 폭증(>2.5배)'에 부여하던 감점(-10점)을, 2.8만 건의 백테스트 결과를 근거로 **가장 강력한 긍정 시그널**로 전환했습니다 (실제 탑 20 평균수익 +3.44%, 승률 70% 달성 입증).
- **실시간 하이브리드 블렌딩 (Phase 18.2 + Phase 25):** 기존의 시장 레짐(거시경제) 모델에 실시간 종목 스캔 데이터(추세, 순간 거래량, 위치)를 학습시킨 **RandomForest** 앙상블 엔진을 추가 결합했습니다 (60:40 비율).
- **Mac/OSX 라이브러리 호환성 강화:** LightGBM 및 XGBoost의 의존성(libomp) 문제를 자동으로 감지하고 안전하게 RandomForest로 Fallback 하는 강건성을 확보했습니다.

---

A comprehensive Python-based automated trading scanner and bot with an integrated ML model.

### 🌟 Key Core Features (V32 Flawless System)
- **Hyper-Realistic Backtesting Engine:** Overcomes traditional static quant pitfalls with enforced T+1 Open Execution logic, 0.4% default slippage/tax deduction, and strict penalties against small-sample and recency biases. Built and tested over 2,500 KRX tickers seamlessly.
- **U-Shaped Intraday Volume:** Intelligently projects daily volume dynamically mapping real-life morning/afternoon market peaks rather than naive linear scaling, heavily reducing False Positive momentum traps.
- **System Robustness & Multithreading:** Completely refactored to process massive, full-market API requests natively bypassing legacy `ZeroDivisionError`, Streamlit `NoneType` UI crashes, and API JSON decoding errors with parallel processing efficiency.
- **Dual Filtering Architectures & Live AI Target:** 
  - *Strict Mode (🟢):* Pure quantitative historical edge (Win Rate > 60%, Profit Factor > 1.5x) strictly evaluated under realistic T+1 conditions.
  - *Extreme Mode (🔥):* Overrides historical metrics to deeply execute Real-Time AI Machine Learning logic targeting absolute `+5% Surge` probability flags on robust chart patterns like Pre-Surge or OBV Div.
- **Live GUI Engine Toggle:** Effortlessly switch between Legacy (T+0 historical fantasy) and Advanced (T+1 harsh reality) inside the UI to clearly evaluate algorithm realities vs theoretical illusions.

## 🚀 Setup in a New Environment

To download and run this repository in another environment, follow these steps:

### 1. Clone the Repository
```bash
git clone https://github.com/dongdongdongdongding/swing.git
cd swing
```

### 2. Install Dependencies
Make sure you have Python 3.9+ installed. It is highly recommended to use a virtual environment.
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Setup Environment Variables
Secure keys (like API tokens) shouldn't be added to version control.
1. Copy `.env.example` to `.env`
2. Open `.env` and fill in your actual API keys (Telegram, OpenAI, etc.)
```bash
cp .env.example .env
```

### 4. Generate the ML Model (Important!)
To bypass GitHub's strict 100MB file limit, the large Global Brain model files (`models/*.pkl`) are **excluded** from this repository. Before running the scanner, you must generate the models locally:

```bash
# Phase 18.2 레짐 기반 확률 모델 생성
python3 train_ml_targets.py

# Universal fallback model 생성
python3 train_global_brain.py

# Phase 25 실전 스캔 데이터 최적화 모델 생성
# (충분한 market_scan_results 이력 데이터가 있을 때 권장)
python3 retrain_ml.py
```
*(This process fetches historical/scan data and runs TimeSeriesSplit cross-validation. It typically takes minutes to finish and save `.pkl` files into the `models/` directory).*

KR 시장 스캔 안정화를 위해 기본적으로 아래 유니버스 위생 필터를 권장합니다.
- `AG_KRX_MIN_LISTING_DAYS=330`
- `AG_KRX_EXCLUDE_SPACS=1`
- `AG_KRX_EXCLUDE_NON_NUMERIC_CODES=1`

이 설정은 신규상장, 스팩, 비정형 코드가 스캔 선두를 차지하면서 `MISSING_ANTIGRAV_SCORE` 또는 데이터 부족으로 0건이 되는 현상을 줄이는 데 목적이 있습니다.

### 5. Run the Application
Once the model is successfully generated, you can run the bot or the web app!

**Run the Streamlit Web Scanner UI:**
```bash
python3 -m streamlit run app.py --server.port 8513
```

**Run the Auto Telegram Bot:**
```bash
python auto_bot.py
```
