"""Posture Guardian - 웹캠과 압력센서 기반 자세 교정 유도 장치

이 모듈은 앱의 진입점으로 다음 책임을 갖습니다:
1. Streamlit 페이지 설정
2. 센서 초기화
3. 감시 스레드 시작
4. UI 렌더링

처음 실행하는 경우 순서는 다음과 같습니다:
1. 시작하기 버튼 클릭
2. 보정 화면으로 이동해 바른 자세 측정
3. 자세 모니터링 화면 표시
4. 10점에서 시작해 나쁜 자세 시 점수 감소
"""
import streamlit as st
from pathlib import Path

# 이후 모듈 import
from posture_guardian.core.config import load_config

# 추가 표준 라이브러리
import time  # (monitor_posture에서 사용)

# 리팩터링된 모듈 import
from posture_guardian.ui.layout import render_home_page, render_calibration_page, render_monitoring_page
from posture_guardian.ui.utils import load_css
from posture_guardian.sensors.sensor_manager import sensor_manager
# from posture_guardian.processing.calibration import perform_calibration  # 보정 페이지 내부 사용


def init_session_state():
    """세션 상태 초기화"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "home"


# 센서 초기화 함수
def init_sensors():
    """모든 센서를 초기화하고 준비합니다."""
    sensor_manager.initialize()


def main():
    """메인 애플리케이션 진입점"""
    # 설정 로드
    config = load_config()
    
    # 페이지 설정 (첫 Streamlit 명령)
    st.set_page_config(
        page_title=config.app_name,
        page_icon="🪑",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # 세션 상태 초기화
    init_session_state()
    
    # CSS 스타일 적용 (없으면 경고 표시)
    load_css()
    
    # 현재 페이지에 따라 적절한 UI 렌더링
    if st.session_state.current_page == "home":
        render_home_page(config)
    elif st.session_state.current_page == "calibration":
        render_calibration_page()
    elif st.session_state.current_page == "monitoring":
        render_monitoring_page()


# 앱 실행 진입점
if __name__ == "__main__":
    # 리소스 초기화 (센서 등)
    try:
        init_sensors()
    except Exception as e:
        st.error(f"센서 초기화 중 오류: {e}")

    # 메인 UI 루프
    main() 