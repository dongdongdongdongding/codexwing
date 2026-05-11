"""UI 모듈.

Streamlit UI 재사용 컴포넌트와 테마를 제공합니다. 진입점 ``app.py`` 는 여기서
필요한 함수를 import 해서 화면을 구성합니다.

* ``ui.theme.inject_theme`` — 글로벌 디자인 토큰/CSS
* ``ui.components`` — L0/L1 카드 / 컴팩트 상태바 / 디테일 그리드 헬퍼
"""

from . import theme, components

__all__ = ["theme", "components"]
