"""posture_guardian.processing.monitor
자세 모니터링 및 상태 업데이트
"""
import streamlit as st
from datetime import datetime, timedelta

# 주기 (초)
DECAY_INTERVAL = 5  # 감점 후 관측 중지 시간
from posture_guardian.processing.posture_evaluator import evaluate_posture
from posture_guardian.sensors.sensor_manager import sensor_manager


def monitor_posture():
    """자세 모니터링 및 상태 업데이트"""
    # 이미 게임이 종료되었다면 감지 중단
    if st.session_state.get("finished"):
        return

    # 센서 데이터 수집
    webcam_data = sensor_manager.get_webcam_data()
    foot_data = sensor_manager.get_foot_data()
    cushion_data = sensor_manager.get_cushion_data()
    
    # 자세 평가
    status, message, details = evaluate_posture(webcam_data, foot_data, cushion_data)
    
    # 상태 업데이트
    st.session_state.status = status
    st.session_state.message = message
    st.session_state.details = details
    
    # --------- 점수 및 쿨다운 로직 ---------
    now = datetime.now()

    # 쿨다운 체크: 감점 후 일정 시간 동안 추가 변동 금지
    cooldown_until = st.session_state.get("cooldown_until")

    if cooldown_until and now < cooldown_until:
        # 쿨다운 중에는 점수/알림 변화 없음
        return

    if status != "good":
        # 감점 및 쿨다운 설정
        st.session_state.score = max(0, st.session_state.score - 1)
        st.session_state.cooldown_until = now + timedelta(seconds=DECAY_INTERVAL)
        st.session_state.alert_audio = True  # 프론트에서 once 재생

        # 0점 도달 시 종료 처리
        if st.session_state.score == 0 and not st.session_state.get("finished"):
            st.session_state.finished = True
            # 최종 경과 시간 문자열 저장
            start_time_str = st.session_state.get("start_time")
            if start_time_str:
                try:
                    start_time_dt = datetime.fromisoformat(start_time_str)
                    elapsed = now - start_time_dt
                    m, s = elapsed.seconds // 60, elapsed.seconds % 60
                    st.session_state.final_elapsed = f"{m}분 {s}초"
                except:
                    st.session_state.final_elapsed = "0분 0초"
    else:
        # 좋은 자세 감지되었지만 점수는 회복하지 않음
        st.session_state.cooldown_until = None 