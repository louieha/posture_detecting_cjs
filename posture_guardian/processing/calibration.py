"""posture_guardian.processing.calibration
자세 보정(calibration) 로직을 담당하는 모듈

- 보정: 사용자의 기준 자세를 측정하고 저장
- 보정 데이터: 눈 거리, 발판/방석 압력 등의 기준값
"""
import time
import numpy as np
import streamlit as st

from posture_guardian.sensors.sensor_manager import sensor_manager


def perform_calibration() -> dict:
    """사용자의 '바른 자세' 보정 절차 실행
    
    여러 프레임의 센서 데이터를 수집해 평균값을 구하여 기준으로 삼습니다.
    * 눈 사이 거리: 사용자 머리와 화면의 기준 거리
    * 발판 압력: 발의 균형 있는 위치
    * 방석 압력: 앉은 자세의 균형
    
    Returns:
        dict: 보정된 센서 기준값 (eye_distance_left, eye_distance_right, foot_value, cushion_value)
    """
    # 여러 프레임의 데이터 수집
    eye_left_values = []
    eye_right_values = []
    foot_values = []
    cushion_values = []
    
    # 10개 샘플 수집 (1초 소요)
    for _ in range(10):  
        sensor_data = sensor_manager.get_all_sensor_data()
        
        eye_left_values.append(sensor_data["eye_distance_left"])
        eye_right_values.append(sensor_data["eye_distance_right"])
        foot_values.append(sensor_data["foot_value"])
        cushion_values.append(sensor_data["cushion_value"])
        
        time.sleep(0.1)  # 0.1초 간격
    
    # 평균값 계산으로 안정적인 기준 확보
    calibration_data = {
        "eye_distance_left": np.mean(eye_left_values),
        "eye_distance_right": np.mean(eye_right_values),
        "foot_value": np.mean(foot_values),
        "cushion_value": np.mean(cushion_values)
    }
    
    # 이벤트 버스에 상태 저장 (다른 모듈에서 접근 가능)
    st.session_state["calibration_reference"] = calibration_data
    st.session_state["details"] = {
        "눈 거리 (좌)": f"{calibration_data['eye_distance_left']:.4f}",
        "눈 거리 (우)": f"{calibration_data['eye_distance_right']:.4f}",
        "발판 압력": f"{calibration_data['foot_value']:.1f}",
        "방석 압력": f"{calibration_data['cushion_value']:.1f}"
    }
    
    return calibration_data 