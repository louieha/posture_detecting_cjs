"""
애플리케이션 설정 관리
"""
import os
from pathlib import Path
from typing import Dict, Optional

import toml
from pydantic import BaseModel, Field
import streamlit as st
from datetime import datetime


class SensorConfig(BaseModel):
    """센서 설정"""
    arduino_connection: bool = Field(False, description="아두이노 연결 여부")
    webcam_device_id: int = Field(0, description="웹캠 장치 ID")
    simulation_foot_mean: int = Field(500, description="발받침대 시뮬레이션 평균값")
    simulation_foot_std: int = Field(30, description="발받침대 시뮬레이션 표준편차")
    simulation_cushion_mean: int = Field(500, description="방석 시뮬레이션 평균값")
    simulation_cushion_std: int = Field(30, description="방석 시뮬레이션 표준편차")


class ProcessingConfig(BaseModel):
    """처리 설정"""
    eye_distance_threshold: float = Field(0.1, description="눈 거리 불균형 임계값")
    pressure_threshold: int = Field(200, description="압력 불균형 임계값")
    check_interval_min: int = Field(2, description="검사 간격 최소값 (초)")
    check_interval_max: int = Field(10, description="검사 간격 최대값 (초)")
    calibration_time: int = Field(3, description="보정 시간 (초)")


class UIConfig(BaseModel):
    """UI 설정"""
    streamlit_port: int = Field(8501, description="Streamlit 포트")
    theme_color: str = Field("#ff4b4b", description="테마 색상")
    alert_sound_path: Optional[str] = Field(None, description="알림음 파일 경로")


class AppConfig(BaseModel):
    """애플리케이션 설정"""
    app_name: str = Field("자세 교정 유도 장치", description="애플리케이션 이름")
    version: str = Field("0.1.0", description="버전")
    debug: bool = Field(False, description="디버그 모드")
    sensors: SensorConfig = Field(default_factory=SensorConfig, description="센서 설정")
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig, description="처리 설정")
    ui: UIConfig = Field(default_factory=UIConfig, description="UI 설정")


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    설정 파일을 로드합니다.
    
    Args:
        config_path: 설정 파일 경로. 없으면 기본값 사용
        
    Returns:
        AppConfig: 로드된 애플리케이션 설정
    """
    # 기본 설정 경로
    if config_path is None:
        # 프로젝트 루트의 config 디렉토리
        base_dir = Path(__file__).parent.parent.parent
        config_path = os.path.join(base_dir, "config", "config.toml")
    
    # 설정 파일이 존재하는 경우 로드
    if os.path.exists(config_path):
        try:
            config_data = toml.load(config_path)
            return AppConfig(**config_data)
        except Exception as e:
            print(f"설정 파일 로드 실패: {e}, 기본 설정을 사용합니다.")
    
    # 기본 설정 반환
    return AppConfig() 

def reset_session_state():
    keys = list(st.session_state.keys())
    for key in keys:
        del st.session_state[key]
    st.session_state['app_initialized'] = True
    st.session_state['score'] = 10
    st.session_state['start_time'] = None
    st.session_state['status'] = "unknown"
    st.session_state['message'] = "준비 중..."
    st.session_state['details'] = {}
    st.session_state['calibration_complete'] = False
    st.session_state['calibration_started'] = False
    st.session_state['last_update_time'] = datetime.now() 