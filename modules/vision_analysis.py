import os

SYSTEM_PROMPT = """
Role: 당신은 20년 경력의 월스트리트 퀀트(Quant)이자 기술적 분석 전문가입니다. 업로드된 차트 이미지를 바탕으로 수학적 통계와 패턴 인식을 결합하여 최적의 매수 타점을 계산하고 종목의 승률을 평가합니다.

Analysis Process:

Visual Pattern Recognition: 차트에서 지지/저항선, 추세선, 주요 패턴(헤드앤숄더, 컵앤핸들, 더블 바텀 등)을 식별하세요.

Indicator Analysis: 이미지 상의 이동평균선(MA), RSI, MACD, 볼린저 밴드 상태를 수치적으로 추정하여 과매수/과매도 여부를 판단하세요.

Volume Profile: 거래량 변화를 분석하여 매집 혹은 분산 신호를 확인하세요.

Quantum Scoring: 위 지표들을 종합하여 1~100점 사이의 '상승 가능성 점수'를 산출하세요. (85점 이상일 때만 '강력 추천')

Output Format:

종목 요약: 현재 추세 및 핵심 패턴

매수 전략: 권장 진입가, 목표가(TP), 손절가(SL - 퀀트 기반 리스크 관리)

리스크 요인: 해당 차트에서 우려되는 기술적 결함

최종 등급: (Strong Buy / Buy / Hold / Sell)

Instruction: 감정에 휘둘리지 말고 오직 데이터와 기하학적 패턴에 근거하여 냉철하게 분석하세요.
"""


def _analyze_with_google_genai(img, api_key):
    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[SYSTEM_PROMPT, "Analyze this chart based on the system prompt instructions.", img],
    )
    return response.text


def _analyze_with_google_generativeai(img, api_key):
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        [SYSTEM_PROMPT, "Analyze this chart based on the system prompt instructions.", img]
    )
    text = getattr(response, "text", "")
    if text:
        return text
    try:
        return str(response.candidates[0].content.parts[0].text)
    except Exception:
        return str(response)


def analyze_chart_image(image_file, api_key):
    """
    Sends the image to Gemini for analysis using the expert system prompt.
    """
    if not api_key:
        return "Error: Gemini API Key is missing."

    try:
        from PIL import Image
        import io
        
        # Load the image
        img = Image.open(image_file)
        
        # Prefer new google-genai SDK, fallback to google-generativeai.
        try:
            return _analyze_with_google_genai(img=img, api_key=api_key)
        except Exception:
            return _analyze_with_google_generativeai(img=img, api_key=api_key)
    except Exception as e:
        return f"Error during analysis: {str(e)}"
