"""
웹캠 및 MediaPipe를 사용한 자세 감지 센서
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

from posture_guardian.core.bus import get_event_bus
from posture_guardian.core.config import AppConfig
from posture_guardian.utils.events import (Event, EventType, FrameData,
                                          PoseKeypoint)

logger = logging.getLogger(__name__)

# MediaPipe 초기화
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose


def calculate_distance(point1, point2) -> float:
    """
    두 키포인트 간의 유클리드 거리를 계산합니다.
    
    Args:
        point1: 첫 번째 키포인트
        point2: 두 번째 키포인트
        
    Returns:
        float: 두 점 사이의 거리
    """
    return np.sqrt((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2)


def extract_keypoints(landmarks) -> Dict[str, PoseKeypoint]:
    """
    MediaPipe 랜드마크에서 키포인트 정보를 추출합니다.
    
    Args:
        landmarks: MediaPipe 랜드마크 목록
        
    Returns:
        Dict[str, PoseKeypoint]: 키포인트 정보 사전
    """
    keypoint_map = {
        "left_eye_inner": 1,
        "left_eye_outer": 3,
        "right_eye_inner": 4,
        "right_eye_outer": 6,
        "nose": 0,
        "left_shoulder": 11,
        "right_shoulder": 12,
        "left_elbow": 13,
        "right_elbow": 14,
        "left_hip": 23,
        "right_hip": 24,
    }
    
    result = {}
    for name, idx in keypoint_map.items():
        landmark = landmarks.landmark[idx]
        result[name] = PoseKeypoint(
            x=landmark.x,
            y=landmark.y,
            z=landmark.z,
            visibility=landmark.visibility
        )
    
    return result


async def webcam_sensor(config: AppConfig) -> None:
    """
    웹캠 센서 작업을 실행합니다.
    
    Args:
        config: 애플리케이션 설정
    """
    logger.info("웹캠 센서 시작")
    bus = get_event_bus()
    
    # MediaPipe Pose 초기화
    pose = mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    cap = None
    frame_id = 0
    
    try:
        # 웹캠 초기화
        device_id = config.sensors.webcam_device_id
        cap = cv2.VideoCapture(device_id)
        
        if not cap.isOpened():
            logger.error(f"웹캠을 열 수 없습니다: 장치 ID {device_id}")
            return
        
        logger.info(f"웹캠 연결됨: 장치 ID {device_id}")
        
        # 웹캠 프레임 처리 루프
        while True:
            # CPU 부하 방지를 위한 지연
            await asyncio.sleep(0.03)  # 약 30 FPS
            
            # 프레임 읽기
            ret, frame = cap.read()
            if not ret:
                logger.warning("웹캠에서 프레임을 읽을 수 없습니다")
                await asyncio.sleep(1)
                continue
            
            # 프레임 처리
            frame = cv2.flip(frame, 1)  # 좌우 반전 (거울 효과)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # MediaPipe Pose 처리
            results = pose.process(rgb_frame)
            
            if results.pose_landmarks:
                # 키포인트 추출
                keypoints = extract_keypoints(results.pose_landmarks)
                
                # 눈 거리 계산
                landmarks = results.pose_landmarks.landmark
                left_eye_inner = landmarks[1]
                left_eye_outer = landmarks[3]
                right_eye_inner = landmarks[4]
                right_eye_outer = landmarks[6]
                
                left_eye_distance = calculate_distance(left_eye_inner, left_eye_outer)
                right_eye_distance = calculate_distance(right_eye_inner, right_eye_outer)
                
                # 이벤트 생성 및 발행
                frame_data = FrameData(
                    frame_id=frame_id,
                    keypoints=keypoints,
                    eye_distance_left=left_eye_distance,
                    eye_distance_right=right_eye_distance,
                    # 리소스 사용량을 줄이기 위해 원본 이미지 전송하지 않음
                    # raw_image=cv2.imencode('.jpg', frame)[1].tobytes()
                )
                
                event = Event(
                    type=EventType.FRAME,
                    data=frame_data
                )
                
                await bus.publish(event)
                frame_id += 1
            
    except asyncio.CancelledError:
        logger.info("웹캠 센서 태스크 취소됨")
    except Exception as e:
        logger.exception(f"웹캠 센서 오류: {e}")
    finally:
        # 자원 해제
        if cap is not None:
            cap.release()
        pose.close()
        logger.info("웹캠 센서 종료") 