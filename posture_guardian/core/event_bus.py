"""
이벤트 버스 구현
"""
from typing import Dict, List, Callable, Any
import json
import os
from datetime import datetime
from pathlib import Path
import threading

_FILE_LOCK = threading.Lock()

class EventBus:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        # 상태 파일 경로를 절대 경로로 설정
        self._state_file = Path(__file__).parent.parent / "ui" / "state.json"
        self._state_file.parent.mkdir(exist_ok=True)
        self._subscribers: Dict[str, List[Callable]] = {}
        self._state = {
            "current_page": "home",
            "score": 10,
            "status": "unknown",
            "message": "준비 중...",
            "details": {},
            "calibration_complete": False,
            "start_time": None
        }
        self._save_state()
    
    def _save_state(self):
        """현재 상태를 파일에 저장 (원자적)"""
        try:
            with _FILE_LOCK:
                tmp_path = f"{self._state_file}.tmp"
                with open(tmp_path, "w") as f:
                    json.dump(self._state, f, ensure_ascii=False)
                os.replace(tmp_path, self._state_file)
        except Exception as e:
            print(f"상태 저장 오류: {e}")
    
    def _load_state(self) -> Dict:
        """파일에서 상태 로드 (실패 시 기본값 반환)"""
        if self._state_file.exists():
            try:
                with _FILE_LOCK:
                    with open(self._state_file, "r") as f:
                        return json.load(f)
            except Exception:
                # JSONDecodeError 등 발생 시 기본값 반환
                return self._state
        return self._state
    
    def publish(self, event_type: str, data: Any = None):
        """이벤트 발행"""
        if event_type == "state_change":
            self._state.update(data)
            self._save_state()
        
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                callback(data)
    
    def subscribe(self, event_type: str, callback: Callable):
        """이벤트 구독"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def get_state(self) -> Dict:
        """현재 상태 반환 (메모리)"""
        return self._state
    
    def reset_state(self):
        """상태 초기화"""
        self._state = {
            "current_page": "home",
            "score": 10,
            "status": "unknown",
            "message": "준비 중...",
            "details": {},
            "calibration_complete": False,
            "start_time": None
        }
        self._save_state()
        self.publish("state_change", self._state)

# 싱글톤 인스턴스
event_bus = EventBus() 