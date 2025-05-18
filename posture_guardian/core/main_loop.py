"""
애플리케이션 메인 이벤트 루프 관리
"""
import asyncio
import logging
from typing import List

from posture_guardian.core.bus import get_event_bus
from posture_guardian.core.config import AppConfig
from posture_guardian.processing.calibration import calibration_processor
from posture_guardian.processing.posture_eval import posture_processor
from posture_guardian.sensors.pressure_pad import pressure_pad_sensor
from posture_guardian.sensors.webcam import webcam_sensor
from posture_guardian.ui.streamlit_ui import start_ui, ui_processor
from posture_guardian.utils.events import Command, CommandType, Event, EventType

logger = logging.getLogger(__name__)


async def start_all(config: AppConfig) -> None:
    """
    모든 시스템 모듈을 시작합니다.
    
    Args:
        config: 애플리케이션 설정
    """
    # 이벤트 버스 초기화
    bus = get_event_bus()
    await bus.start()
    
    # 시스템 태스크 목록
    tasks: List[asyncio.Task] = []
    
    try:
        # UI 시작 - 별도 프로세스로 실행
        ui_process = await start_ui()
        
        # 센서 모듈 태스크 시작
        tasks.append(asyncio.create_task(webcam_sensor(config)))
        tasks.append(asyncio.create_task(pressure_pad_sensor(config)))
        
        # 처리 모듈 태스크 시작
        tasks.append(asyncio.create_task(calibration_processor(config)))
        tasks.append(asyncio.create_task(posture_processor(config)))
        
        # UI 프로세서 태스크 시작
        tasks.append(asyncio.create_task(ui_processor(config)))
        
        # 모든 태스크 완료될 때까지 대기
        logger.info("모든 시스템 모듈이 시작되었습니다")
        await asyncio.gather(*tasks)
    
    except asyncio.CancelledError:
        logger.info("메인 루프 취소 요청 - 태스크 정리 중")
    except Exception as e:
        logger.exception(f"메인 루프 오류: {e}")
    finally:
        # 모든 남은 태스크 취소
        for task in tasks:
            if not task.done():
                task.cancel()
        
        # 취소된 태스크 대기
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 이벤트 버스 중지
        await bus.stop()
        
        logger.info("모든 시스템 모듈이 종료되었습니다") 