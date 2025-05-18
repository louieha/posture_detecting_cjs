"""posture_guardian.sensors.sensor_manager
센서 초기화 및 데이터 수집 로직을 관리하는 클래스

- WebcamSensor: 웹캠 연결 및 데이터 수집
- PressureSensor: 압력 센서 (발판, 방석) 데이터 수집
"""
import cv2
import numpy as np
import streamlit as st

from posture_guardian.sensors.webcam import calculate_distance
from posture_guardian.sensors.pressure_pad import PressurePadSimulator


class SensorManager:
    """센서 객체를 관리하고 데이터 수집 메서드 제공"""
    
    def __init__(self):
        """센서 관리자 초기화"""
        self.webcam = None
        self.pressure_simulator = PressurePadSimulator(
            foot_mean=500, foot_std=30,
            cushion_mean=500, cushion_std=30
        )
    
    def initialize(self):
        """모든 센서 초기화"""
        self._init_webcam()
    
    def _init_webcam(self):
        """웹캠 초기화 - 열리지 않으면 시뮬레이션 모드로 안내"""
        if self.webcam is None:
            try:
                self.webcam = cv2.VideoCapture(0)
                if not self.webcam.isOpened():
                    st.warning("웹캠을 열 수 없습니다. 시뮬레이션 모드로 동작합니다.")
            except Exception as e:
                st.warning(f"웹캠 초기화 오류: {e}")
    
    def get_webcam_data(self):
        """웹캠에서 데이터 수집
        
        Returns:
            dict: 눈 거리 (좌/우) 및 유효성 정보
        """
        import mediapipe as mp
        
        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        if self.webcam and self.webcam.isOpened():
            ret, frame = self.webcam.read()
            if ret:
                # 프레임 처리
                frame = cv2.flip(frame, 1)  # 좌우 반전 (거울 효과)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # MediaPipe Pose 처리
                results = pose.process(rgb_frame)
                
                if results.pose_landmarks:
                    # 키포인트 추출
                    landmarks = results.pose_landmarks.landmark
                    
                    # 눈 거리 계산
                    left_eye_inner = landmarks[1]
                    left_eye_outer = landmarks[3]
                    right_eye_inner = landmarks[4]
                    right_eye_outer = landmarks[6]
                    
                    left_eye_distance = calculate_distance(left_eye_inner, left_eye_outer)
                    right_eye_distance = calculate_distance(right_eye_inner, right_eye_outer)
                    
                    return {
                        "eye_distance_left": left_eye_distance,
                        "eye_distance_right": right_eye_distance,
                        "valid": True
                    }
        
        # 웹캠 데이터를 가져올 수 없는 경우 시뮬레이션 값 반환
        return {
            "eye_distance_left": np.random.normal(0.05, 0.01),
            "eye_distance_right": np.random.normal(0.05, 0.01),
            "valid": False
        }
    
    def get_pressure_data(self):
        """압력 센서에서 데이터 수집
        
        Returns:
            dict: 발판 및 방석 압력값
        """
        foot_value, cushion_value = self.pressure_simulator.read()
        return {
            "foot_value": foot_value,
            "cushion_value": cushion_value
        }
    
    def get_foot_data(self):
        """발판 압력 값만 반환"""
        return {"foot_value": self.get_pressure_data()["foot_value"]}

    def get_cushion_data(self):
        """방석 압력 값만 반환"""
        return {"cushion_value": self.get_pressure_data()["cushion_value"]}
    
    def get_all_sensor_data(self):
        """모든 센서 데이터를 한번에 수집
        
        Returns:
            dict: 모든 센서값 통합 데이터
        """
        webcam_data = self.get_webcam_data()
        pressure_data = self.get_pressure_data()
        
        return {
            "eye_distance_left": webcam_data["eye_distance_left"],
            "eye_distance_right": webcam_data["eye_distance_right"],
            "foot_value": pressure_data["foot_value"],
            "cushion_value": pressure_data["cushion_value"],
            "webcam_valid": webcam_data["valid"]
        }
    
    def cleanup(self):
        """센서 자원 정리"""
        if self.webcam:
            self.webcam.release()
            self.webcam = None


# 싱글톤 인스턴스
sensor_manager = SensorManager() 