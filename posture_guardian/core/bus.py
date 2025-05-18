"""
이벤트 버스 구현
Pub-Sub 패턴을 사용하여 모듈 간 이벤트 통신을 위한 중앙 허브
"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set

from posture_guardian.utils.events import Event, EventType

logger = logging.getLogger(__name__)


class EventBus:
    """
    비동기 이벤트 버스 구현
    - 이벤트 발행 (publish)
    - 이벤트 구독 (subscribe)
    - 토픽 기반 구독
    """

    def __init__(self):
        """EventBus 초기화"""
        self._subscribers: Dict[EventType, Set[Callable]] = {}
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        logger.debug("EventBus 초기화됨")

    def subscribe(
        self, event_type: EventType, callback: Callable[[Event], Any]
    ) -> Callable[[], None]:
        """
        특정 이벤트 타입을 구독합니다.
        
        Args:
            event_type: 구독할 이벤트 타입
            callback: 이벤트 발생 시 호출할 콜백 함수
            
        Returns:
            Callable: 구독 취소 함수
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()
        
        self._subscribers[event_type].add(callback)
        logger.debug(f"이벤트 타입 '{event_type}' 구독 추가됨")
        
        # 구독 취소 함수 반환
        def unsubscribe() -> None:
            if event_type in self._subscribers and callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"이벤트 타입 '{event_type}' 구독 취소됨")
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]
        
        return unsubscribe

    async def publish(self, event: Event) -> None:
        """
        이벤트를 발행합니다.
        
        Args:
            event: 발행할 이벤트
        """
        await self._queue.put(event)
        logger.debug(f"이벤트 발행됨: {event.type}")

    async def start(self) -> None:
        """이벤트 버스 워커를 시작합니다."""
        if self._running:
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("EventBus 워커 시작됨")

    async def stop(self) -> None:
        """이벤트 버스 워커를 중지합니다."""
        if not self._running:
            return
        
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info("EventBus 워커 중지됨")

    async def _worker(self) -> None:
        """
        이벤트 큐를 모니터링하고 이벤트를 처리하는 워커
        """
        logger.debug("이벤트 워커 시작")
        while self._running:
            try:
                event = await self._queue.get()
                await self._process_event(event)
                self._queue.task_done()
            except asyncio.CancelledError:
                logger.debug("이벤트 워커 취소됨")
                break
            except Exception as e:
                logger.exception(f"이벤트 처리 중 오류 발생: {e}")
        logger.debug("이벤트 워커 종료")

    async def _process_event(self, event: Event) -> None:
        """
        이벤트를 처리하고 적절한 구독자에게 전달합니다.
        
        Args:
            event: 처리할 이벤트
        """
        if event.type not in self._subscribers:
            return
        
        # 모든 구독자에게 이벤트 전달
        # 리스트로 복사해서 콜백 중에 구독자가 변경될 수 있도록 함
        subscribers = list(self._subscribers[event.type])
        for callback in subscribers:
            try:
                result = callback(event)
                # 비동기 콜백 처리
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.exception(f"구독자 콜백 실행 중 오류 발생: {e}")


# 싱글톤 인스턴스
_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    전역 이벤트 버스 인스턴스를 반환합니다.
    
    Returns:
        EventBus: 싱글톤 이벤트 버스 인스턴스
    """
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
    return _bus_instance 