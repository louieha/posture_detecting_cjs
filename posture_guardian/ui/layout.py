"""posture_guardian.ui.layout
Streamlit 페이지 레이아웃 및 렌더링 함수
"""
from datetime import datetime
import time
import streamlit as st

# main 모듈을 직접 참조하지 않고 필요한 기능만 개별 임포트하여 순환 참조를 방지합니다.
from posture_guardian.sensors.sensor_manager import sensor_manager
from posture_guardian.processing.calibration import perform_calibration
from posture_guardian.processing.monitor import monitor_posture


def init_session_state():
    """세션 상태 초기화"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "home"
    if 'calibration_started' not in st.session_state:
        st.session_state.calibration_started = False
    if 'calibration_complete' not in st.session_state:
        st.session_state.calibration_complete = False
    if 'score' not in st.session_state:
        st.session_state.score = 10
    if 'status' not in st.session_state:
        st.session_state.status = "unknown"
    if 'message' not in st.session_state:
        st.session_state.message = "준비 중..."
    if 'details' not in st.session_state:
        st.session_state.details = {}
    if 'start_time' not in st.session_state:
        st.session_state.start_time = None


def render_home_page(config):
    """홈 페이지 렌더링 - 시작하기 버튼과 기본 정보 표시
    
    Args:
        config: 앱 설정 객체 (앱 이름, 버전 등 포함)
    """
    init_session_state()
    
    # 시작하기 버튼
    st.markdown('<div class="start-button">', unsafe_allow_html=True)
    if st.button("시작하기", key="start_button", use_container_width=True):
        # 상태 초기화 및 페이지 전환
        st.session_state.current_page = "calibration"
        st.session_state.calibration_started = False
        st.session_state.calibration_complete = False
        st.session_state.start_time = None
        st.session_state.score = 10
        st.session_state.status = "unknown"
        st.session_state.message = "준비 중..."
        st.session_state.details = {}
        
        # 센서 초기화
        sensor_manager.initialize()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 앱 정보
    with st.expander("앱 정보"):
        st.write(f"버전: {config.version}")
        st.write("이 앱은 사용자의 자세를 실시간으로 모니터링하고 교정을 유도합니다.")
        st.write("1. 시작하기: 앱을 시작합니다.")
        st.write("2. 보정: 기준 자세를 측정합니다.")
        st.write("3. 관측: 실시간으로 자세를 모니터링합니다.")


def render_calibration_page():
    """보정 페이지 렌더링 - 3초간 사용자의 '바른 자세'를 측정"""
    init_session_state()
    
    # 1단계: 보정 시작 전 안내
    if not st.session_state.calibration_started:
        st.info("바른 자세로 앉아주세요. '보정 시작' 버튼을 누르면 3초간 기준 자세를 측정합니다.")
        
        if st.button("보정 시작", key="calibration_start", use_container_width=True):
            st.session_state.calibration_started = True
            st.session_state.message = "보정 중... 바른 자세를 유지해주세요."
            st.rerun()
    
    # 2단계: 보정 진행 중 (프로그레스 바 + 측정)
    elif not st.session_state.calibration_complete:
        st.markdown(f'<div class="status-message warning-status">{st.session_state.message}</div>', unsafe_allow_html=True)
        
        # 프로그레스 바
        progress_bar = st.progress(0)
        
        # 보정 진행 (3초)
        for i in range(100):
            time.sleep(0.03)
            progress_bar.progress(i + 1, text=f"보정 중... {i+1}%")
            if i == 50:  # 중간에 보정 수행
                perform_calibration()
        
        # 보정 완료 및 모니터링 페이지로 전환
        st.session_state.current_page = "monitoring"
        st.session_state.calibration_complete = True
        st.session_state.start_time = datetime.now().isoformat()
        st.session_state.message = "교정 완료! 바른 자세를 유지하세요."
        st.rerun()


def render_monitoring_page():
    """관측 페이지 렌더링 - 실시간 점수와 자세 상태 표시"""
    init_session_state()
    
    finished = st.session_state.get("finished", False)

    # 1) 센서 데이터 평가 및 상태/점수 업데이트 (종료 시 건너뜀)
    if not finished:
        monitor_posture()

    # 2) 최신 세션 상태 읽기
    # 보정 완료 여부 확인 전까지 상태 초기화를 보장합니다.
    # 세션 상태는 monitor_posture에서 업데이트합니다.
    # render_monitoring_page 시작 시점에 항상 최신 데이터가 반영됩니다.
    
    # -------- 세션 상태 참조 --------
    state = st.session_state
    
    # 보정 완료 여부 확인
    if not state.get("calibration_complete"):
        st.warning("보정이 필요합니다.")
        time.sleep(1)
        state.current_page = "home"
        st.rerun()
        return
    
    # --------- 점수 표시 (10~0) ---------
    score = state.get("score")
    score_class = "good-score"
    if score <= 3:
        score_class = "bad-score"  # 빨간색 (위험)
    elif score <= 7:
        score_class = "warning-score"  # 노란색 (주의)
    
    st.markdown(f'<div class="score-container {score_class}">{score}</div>', unsafe_allow_html=True)
    
    # --------- 상태 메시지 ---------
    status = state.get("status")
    status_class = "good-status"
    message = state.get("message")
    
    # 상태별 스타일 및 메시지 설정
    if status == "bad_eyes":
        status_class = "bad-status"
        message = "자세가 바르지 않습니다! 앞으로 기울이지 마세요."
    elif status == "bad_foot":
        status_class = "bad-status"
        message = "발판에 압력이 불균형합니다!"
    elif status == "bad_cushion":
        status_class = "bad-status"
        message = "방석에 압력이 불균형합니다!"
    elif status == "good":
        status_class = "good-status"
        message = "좋은 자세를 유지하고 있습니다!"
    
    # 경고 상태에서는 깜빡임 효과 추가
    message_div = f'<div class="status-message {status_class}">{message}</div>'
    if status != "good":
        message_div = f'<div class="status-message {status_class} alert-animation">{message}</div>'
    
    st.markdown(message_div, unsafe_allow_html=True)
    
    # ---- 오디오 알림 (1회) ----
    if state.get("alert_audio"):
        st.audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg", format="audio/ogg", start_time=0)
        state.alert_audio = False
    
    # --------- 경과 시간 ---------
    if finished and state.get("final_elapsed"):
        elapsed_str = state.final_elapsed
    else:
        start_time = state.get("start_time")
        if start_time:
            try:
                start_time = datetime.fromisoformat(start_time)
                elapsed = datetime.now() - start_time
                minutes = elapsed.seconds // 60
                seconds = elapsed.seconds % 60
                elapsed_str = f"{minutes}분 {seconds}초"
            except:
                elapsed_str = "0분 0초"
        else:
            elapsed_str = "0분 0초"
    
    st.markdown(f'<div class="timer-display">경과 시간: {elapsed_str}</div>', unsafe_allow_html=True)
    
    # --------- 실패 상태 (점수 0점) ---------
    if score <= 0:
        st.error("자세 유지에 실패하셨어요! 다시 도전해 보세요!")
        st.info(f"자세 유지 시간: {elapsed_str}. 상위 20%입니다.")
        
        if st.button("다시 시작", key="restart_button", use_container_width=True):
            st.session_state.clear()
            st.session_state.current_page = "home"
            st.rerun()
    
    # --------- 세부 정보 확장 패널 ---------
    with st.expander("세부 정보"):
        details = state.get("details", {})
        if details:
            for key, value in details.items():
                st.text(f"{key}: {value}")
        else:
            st.text("세부 정보가 없습니다.")
    
    # 자동 새로고침 (0.5초) - 종료 시 중단
    if not finished:
        time.sleep(0.5)
        st.rerun() 