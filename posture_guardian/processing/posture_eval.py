"""
자세 평가 모듈
- 프레임 및 압력 데이터 분석
- 자세 상태 판단 및 점수 관리
"""
import asyncio
import logging
import random
import time
from datetime import datetime
from typing import Dict, Optional

from posture_guardian.core.bus import get_event_bus
from posture_guardian.core.config import AppConfig
from posture_guardian.utils.events import (CalibrationData, Event, EventType,
                                          FrameData, PostureResult,
                                          PostureStatus, PressureData)

logger = logging.getLogger(__name__)


class PostureEvaluator:
    """자세 평가기"""
    
    def __init__(self, config: AppConfig):
        """
        자세 평가기 초기화
        
        Args:
            config: 애플리케이션 설정
        """
        self.config = config
        self.calibration: Optional[CalibrationData] = None
        self.latest_frame: Optional[FrameData] = None
        self.latest_pressure: Optional[PressureData] = None
        self.score: int = 10
        self.start_time: Optional[float] = None
        self.last_check_time: Optional[float] = None
        self.check_interval_min = config.processing.check_interval_min
        self.check_interval_max = config.processing.check_interval_max
        self.next_check_time: Optional[float] = None
    
    def set_calibration(self, calibration: CalibrationData) -> None:
        """
        보정 데이터 설정
        
        Args:
            calibration: 보정 데이터
        """
        self.calibration = calibration
        self.start_time = time.time()
        self.last_check_time = self.start_time
        self.next_check_time = self.start_time + self._get_random_interval()
        self.score = 10
        logger.info("자세 평가기 보정 데이터 설정됨")
    
    def update_frame(self, frame: FrameData) -> None:
        """
        최신 프레임 데이터 업데이트
        
        Args:
            frame: 프레임 데이터
        """
        self.latest_frame = frame
    
    def update_pressure(self, pressure: PressureData) -> None:
        """
        최신 압력 데이터 업데이트
        
        Args:
            pressure: 압력 데이터
        """
        self.latest_pressure = pressure
    
    def is_ready_for_evaluation(self) -> bool:
        """
        평가 준비 상태 확인
        
        Returns:
            bool: 평가 준비 완료 여부
        """
        current_time = time.time()
        
        # 보정 데이터, 프레임 데이터, 압력 데이터가 모두 있고, 체크 시간이 지났는지 확인
        return (self.calibration is not None and 
                self.latest_frame is not None and 
                self.latest_pressure is not None and
                self.next_check_time is not None and
                current_time >= self.next_check_time)
    
    def evaluate(self) -> Optional[PostureResult]:
        """
        자세 평가 수행
        
        Returns:
            Optional[PostureResult]: 평가 결과 또는 None (준비 미완료)
        """
        if not self.is_ready_for_evaluation():
            return None
        
        if self.calibration is None or self.latest_frame is None or self.latest_pressure is None:
            return None
        
        current_time = time.time()
        self.last_check_time = current_time
        self.next_check_time = current_time + self._get_random_interval()
        
        # 눈 거리 비율 체크
        eye_status = self._check_eye_distance()
        
        # 발받침대 압력 체크
        foot_status = self._check_foot_pressure()
        
        # 방석 압력 체크
        cushion_status = self._check_cushion_pressure()
        
        # 종합 상태 판단
        status = PostureStatus.GOOD
        if eye_status != PostureStatus.GOOD:
            status = eye_status
        elif foot_status != PostureStatus.GOOD:
            status = foot_status
        elif cushion_status != PostureStatus.GOOD:
            status = cushion_status
        
        # 점수 조정 - 나쁜 자세일 때 점수 감소
        if status != PostureStatus.GOOD:
            # 1점씩만 감소하도록 수정
            self.score = max(0, self.score - 1)
            logger.info(f"자세 평가: 나쁜 자세 감지 - 점수 감소: {self.score}")
        
        # 경과 시간 계산
        elapsed_time = 0.0
        if self.start_time is not None:
            elapsed_time = current_time - self.start_time
        
        # 세부 정보 수집
        details = {}
        if self.latest_frame.eye_distance_left is not None and self.latest_frame.eye_distance_right is not None:
            details["eye_distance_ratio"] = self.latest_frame.eye_distance_left / self.latest_frame.eye_distance_right
        details["foot_value"] = self.latest_pressure.foot_value
        details["cushion_value"] = self.latest_pressure.cushion_value
        
        # 결과 생성
        result = PostureResult(
            status=status,
            score=self.score,
            elapsed_time=elapsed_time,
            details=details
        )
        
        # 점수 0일 때 처리
        if self.score <= 0:
            logger.info("자세 평가: 실패 (점수 0)")
        
        return result
    
    def _check_eye_distance(self) -> PostureStatus:
        """
        눈 거리 비율 체크
        
        Returns:
            PostureStatus: 자세 상태
        """
        if self.calibration is None or self.latest_frame is None:
            return PostureStatus.UNKNOWN
        
        if self.latest_frame.eye_distance_left is None or self.latest_frame.eye_distance_right is None:
            return PostureStatus.UNKNOWN
        
        # 현재 눈 거리 비율 계산
        current_ratio = self.latest_frame.eye_distance_left / self.latest_frame.eye_distance_right
        baseline_ratio = self.calibration.baseline_eye_distance_ratio
        
        # 임계값 확인
        threshold = self.config.processing.eye_distance_threshold
        ratio_diff = abs(current_ratio - baseline_ratio) / baseline_ratio
        
        if ratio_diff > threshold:
            logger.info(f"눈 거리 비율 불균형: {ratio_diff:.4f} > {threshold:.4f} (기준값: {baseline_ratio:.4f})")
            return PostureStatus.BAD_EYES
        
        return PostureStatus.GOOD
    
    def _check_foot_pressure(self) -> PostureStatus:
        """
        발받침대 압력 체크
        
        Returns:
            PostureStatus: 자세 상태
        """
        if self.calibration is None or self.latest_pressure is None:
            return PostureStatus.UNKNOWN
        
        # 현재 압력 값 확인
        current_value = self.latest_pressure.foot_value
        baseline_value = self.calibration.baseline_foot
        
        # 임계값 확인
        threshold = self.config.processing.pressure_threshold
        pressure_diff = abs(current_value - baseline_value)
        
        if pressure_diff > threshold:
            logger.info(f"발받침대 압력 불균형: {pressure_diff:.2f} > {threshold} (기준값: {baseline_value:.2f})")
            return PostureStatus.BAD_FOOT
        
        return PostureStatus.GOOD
    
    def _check_cushion_pressure(self) -> PostureStatus:
        """
        방석 압력 체크
        
        Returns:
            PostureStatus: 자세 상태
        """
        if self.calibration is None or self.latest_pressure is None:
            return PostureStatus.UNKNOWN
        
        # 현재 압력 값 확인
        current_value = self.latest_pressure.cushion_value
        baseline_value = self.calibration.baseline_cushion
        
        # 임계값 확인
        threshold = self.config.processing.pressure_threshold
        pressure_diff = abs(current_value - baseline_value)
        
        if pressure_diff > threshold:
            logger.info(f"방석 압력 불균형: {pressure_diff:.2f} > {threshold} (기준값: {baseline_value:.2f})")
            return PostureStatus.BAD_CUSHION
        
        return PostureStatus.GOOD
    
    def _get_random_interval(self) -> float:
        """
        랜덤 체크 간격 생성
        
        Returns:
            float: 체크 간격 (초)
        """
        return random.uniform(self.check_interval_min, self.check_interval_max)


async def posture_processor(config: AppConfig) -> None:
    """
    자세 평가 처리 작업을 실행합니다.
    
    Args:
        config: 애플리케이션 설정
    """
    logger.info("자세 평가 처리기 시작")
    bus = get_event_bus()
    
    # 평가기 초기화
    evaluator = PostureEvaluator(config)
    
    # 보정 데이터 구독
    async def on_calibration(event: Event) -> None:
        calibration_data: CalibrationData = event.data
        evaluator.set_calibration(calibration_data)
        logger.info("자세 평가 처리기: 보정 데이터 수신")
    
    # 프레임 데이터 구독
    async def on_frame(event: Event) -> None:
        frame_data: FrameData = event.data
        evaluator.update_frame(frame_data)
        
        # 평가 수행
        if evaluator.is_ready_for_evaluation():
            result = evaluator.evaluate()
            if result is not None:
                # 결과 이벤트 발행
                result_event = Event(
                    type=EventType.POSTURE_RESULT,
                    data=result
                )
                await bus.publish(result_event)
    
    # 압력 데이터 구독
    async def on_pressure(event: Event) -> None:
        pressure_data: PressureData = event.data
        evaluator.update_pressure(pressure_data)
        
    # 이벤트 구독
    cal_unsub = bus.subscribe(EventType.CALIBRATION, on_calibration)
    frame_unsub = bus.subscribe(EventType.FRAME, on_frame)
    pressure_unsub = bus.subscribe(EventType.PRESSURE, on_pressure)
    
    try:
        # 계속 실행
        while True:
            await asyncio.sleep(0.1)
    
    except asyncio.CancelledError:
        logger.info("자세 평가 처리기 태스크 취소됨")
    except Exception as e:
        logger.exception(f"자세 평가 처리기 오류: {e}")
    finally:
        # 구독 해제
        cal_unsub()
        frame_unsub()
        pressure_unsub()
        logger.info("자세 평가 처리기 종료") 