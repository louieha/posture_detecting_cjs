"""
애플리케이션 내에서 사용되는 이벤트 데이터 모델
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """이벤트 타입 정의"""
    FRAME = "frame"                   # 웹캠 프레임 데이터
    PRESSURE = "pressure"             # 압력 센서 데이터
    POSTURE_RESULT = "posture_result" # 자세 평가 결과
    CALIBRATION = "calibration"       # 보정 데이터
    COMMAND = "command"               # 시스템 명령
    SYSTEM = "system"                 # 시스템 상태


class PoseKeypoint(BaseModel):
    """신체 키포인트 좌표"""
    x: float = Field(..., description="X 좌표 (0~1)")
    y: float = Field(..., description="Y 좌표 (0~1)")
    z: float = Field(..., description="Z 좌표 (깊이)")
    visibility: float = Field(..., description="가시성 (0~1)")


class FrameData(BaseModel):
    """웹캠에서 처리된 프레임 데이터"""
    timestamp: datetime = Field(default_factory=datetime.now, description="타임스탬프")
    frame_id: int = Field(..., description="프레임 ID")
    keypoints: Dict[str, PoseKeypoint] = Field(..., description="키포인트 정보")
    eye_distance_left: Optional[float] = Field(None, description="왼쪽 눈 내부-외부 거리")
    eye_distance_right: Optional[float] = Field(None, description="오른쪽 눈 내부-외부 거리")
    raw_image: Optional[bytes] = Field(None, description="원본 이미지 바이너리")


class PressureData(BaseModel):
    """압력 센서 데이터"""
    timestamp: datetime = Field(default_factory=datetime.now, description="타임스탬프")
    foot_value: int = Field(..., ge=1, le=1024, description="발받침대 압력값 (1-1024)")
    cushion_value: int = Field(..., ge=1, le=1024, description="방석 압력값 (1-1024)")
    source: str = Field("arduino", description="데이터 소스 (arduino 또는 simulation)")


class CalibrationData(BaseModel):
    """보정 데이터"""
    timestamp: datetime = Field(default_factory=datetime.now, description="타임스탬프")
    baseline_foot: float = Field(..., description="발받침대 기준값")
    baseline_cushion: float = Field(..., description="방석 기준값")
    baseline_eye_distance_ratio: float = Field(..., description="눈 거리 비율 기준값")
    completed: bool = Field(False, description="보정 완료 여부")


class PostureStatus(str, Enum):
    """자세 상태"""
    GOOD = "good"           # 올바른 자세
    BAD_EYES = "bad_eyes"   # 눈 거리 불균형 (앞으로 기울임)
    BAD_FOOT = "bad_foot"   # 발 압력 불균형
    BAD_CUSHION = "bad_cushion"  # 방석 압력 불균형
    UNKNOWN = "unknown"     # 알 수 없음


class PostureResult(BaseModel):
    """자세 평가 결과"""
    timestamp: datetime = Field(default_factory=datetime.now, description="타임스탬프")
    status: PostureStatus = Field(..., description="자세 상태")
    score: int = Field(..., ge=0, le=10, description="현재 점수 (0-10)")
    elapsed_time: float = Field(..., description="경과 시간 (초)")
    details: Dict[str, float] = Field(default_factory=dict, description="세부 측정값")


class CommandType(str, Enum):
    """명령 유형"""
    START = "start"         # 시작
    STOP = "stop"           # 종료
    RESTART = "restart"     # 재시작
    CALIBRATE = "calibrate" # 보정


class Command(BaseModel):
    """시스템 명령"""
    timestamp: datetime = Field(default_factory=datetime.now, description="타임스탬프")
    type: CommandType = Field(..., description="명령 유형")
    params: Dict = Field(default_factory=dict, description="명령 매개변수")


class Event(BaseModel):
    """통합 이벤트 모델"""
    type: EventType = Field(..., description="이벤트 유형")
    data: Union[FrameData, PressureData, PostureResult, CalibrationData, Command, Dict] = Field(
        ..., description="이벤트 데이터"
    ) 