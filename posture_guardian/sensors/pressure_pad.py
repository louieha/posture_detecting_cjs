"""
압력 센서(발받침대, 방석) 데이터 수집 모듈
- 실제 아두이노 연동
- 시뮬레이션 모드 지원
"""
import asyncio
import logging
import random
import time
from typing import Optional, Tuple

import numpy as np
import serial
import serial.tools.list_ports

from posture_guardian.core.bus import get_event_bus
from posture_guardian.core.config import AppConfig
from posture_guardian.utils.events import Event, EventType, PressureData

logger = logging.getLogger(__name__)


class PressurePadSimulator:
    """압력 센서 시뮬레이터"""
    
    def __init__(
        self, 
        foot_mean: int = 500, 
        foot_std: int = 30,
        cushion_mean: int = 500, 
        cushion_std: int = 30
    ):
        """
        압력 센서 시뮬레이터 초기화
        
        Args:
            foot_mean: 발받침대 평균값
            foot_std: 발받침대 표준편차
            cushion_mean: 방석 평균값
            cushion_std: 방석 표준편차
        """
        self.foot_mean = foot_mean
        self.foot_std = foot_std
        self.cushion_mean = cushion_mean
        self.cushion_std = cushion_std
    
    def read(self) -> Tuple[int, int]:
        """
        시뮬레이션된 압력 센서 값을 읽습니다.
        
        Returns:
            Tuple[int, int]: (발받침대 값, 방석 값)
        """
        # 정규분포로 값 생성
        foot_value = int(np.random.normal(self.foot_mean, self.foot_std))
        cushion_value = int(np.random.normal(self.cushion_mean, self.cushion_std))
        
        # 1~1024 범위 제한
        foot_value = max(1, min(1024, foot_value))
        cushion_value = max(1, min(1024, cushion_value))
        
        return foot_value, cushion_value


def get_arduino_port() -> Optional[str]:
    """
    아두이노 시리얼 포트를 자동으로 찾습니다.
    
    Returns:
        Optional[str]: 아두이노 포트, 찾지 못한 경우 None
    """
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if "Arduino" in port.description or "CH340" in port.description:
            return port.device
    return None


async def pressure_pad_sensor(config: AppConfig) -> None:
    """
    압력 센서 데이터 수집 작업을 실행합니다.
    
    Args:
        config: 애플리케이션 설정
    """
    logger.info("압력 센서 시작")
    bus = get_event_bus()
    
    # 아두이노 연결 시도 (또는 시뮬레이터 초기화)
    arduino_mode = config.sensors.arduino_connection
    arduino_port = None
    ser = None
    simulator = None
    
    try:
        if arduino_mode:
            # 아두이노 연결 시도
            arduino_port = get_arduino_port()
            if arduino_port:
                ser = serial.Serial(arduino_port, 9600, timeout=1)
                logger.info(f"아두이노 연결됨: {arduino_port}")
            else:
                logger.warning("아두이노 포트를 찾을 수 없음, 시뮬레이션 모드로 전환")
                arduino_mode = False
        
        if not arduino_mode:
            # 시뮬레이터 초기화
            simulator = PressurePadSimulator(
                foot_mean=config.sensors.simulation_foot_mean,
                foot_std=config.sensors.simulation_foot_std,
                cushion_mean=config.sensors.simulation_cushion_mean,
                cushion_std=config.sensors.simulation_cushion_std
            )
            logger.info("압력 센서 시뮬레이션 모드 활성화됨")
        
        # 데이터 수집 루프
        while True:
            # 압력 센서 값 읽기
            foot_value = None
            cushion_value = None
            
            if arduino_mode and ser:
                try:
                    if ser.in_waiting:
                        line = ser.readline().decode("utf-8").strip()
                        values = line.split(",")
                        if len(values) == 2:
                            foot_value = int(values[0])
                            cushion_value = int(values[1])
                except Exception as e:
                    logger.error(f"아두이노 읽기 오류: {e}")
                    arduino_mode = False
                    simulator = PressurePadSimulator(
                        foot_mean=config.sensors.simulation_foot_mean,
                        foot_std=config.sensors.simulation_foot_std,
                        cushion_mean=config.sensors.simulation_cushion_mean,
                        cushion_std=config.sensors.simulation_cushion_std
                    )
                    logger.info("오류로 인해 시뮬레이션 모드로 전환")
            
            if foot_value is None or cushion_value is None:
                if simulator:
                    foot_value, cushion_value = simulator.read()
                else:
                    await asyncio.sleep(0.1)
                    continue
            
            # 이벤트 생성 및 발행
            pressure_data = PressureData(
                foot_value=foot_value,
                cushion_value=cushion_value,
                source="arduino" if arduino_mode else "simulation"
            )
            
            event = Event(
                type=EventType.PRESSURE,
                data=pressure_data
            )
            
            await bus.publish(event)
            
            # 다음 읽기까지 대기
            await asyncio.sleep(0.1)  # 약 10Hz 샘플링
    
    except asyncio.CancelledError:
        logger.info("압력 센서 태스크 취소됨")
    except Exception as e:
        logger.exception(f"압력 센서 오류: {e}")
    finally:
        # 자원 해제
        if ser:
            ser.close()
        logger.info("압력 센서 종료") 