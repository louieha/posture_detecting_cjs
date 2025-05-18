"""
Streamlit 기반 UI 모듈
- 자세 상태 표시
- 점수 및 경과 시간 표시
- 알림 생성
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

from posture_guardian.core.bus import get_event_bus
from posture_guardian.core.config import AppConfig
from posture_guardian.utils.events import (CalibrationData, Command, CommandType,
                                          Event, EventType, PostureResult,
                                          PostureStatus)

logger = logging.getLogger(__name__)


async def start_ui() -> subprocess.Popen:
    """
    Streamlit UI를 별도 프로세스로 시작
    
    Returns:
        subprocess.Popen: Streamlit 프로세스
    """
    logger.info("Streamlit UI 프로세스 시작 중...")
    
    # 현재 스크립트 위치 찾기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    streamlit_script = os.path.join(current_dir, "streamlit_app.py")
    
    # Streamlit 앱이 없으면 생성
    if not os.path.exists(streamlit_script):
        await _create_streamlit_app(streamlit_script)
        
    # 상태 파일 존재 시 초기화
    state_file = os.path.join(current_dir, "temp_state.json")
    if os.path.exists(state_file):
        try:
            # 초기 상태 데이터 생성
            init_data = {
                "score": 10,
                "status": "unknown",
                "message": "준비 중...",
                "details": {},
                "calibration_complete": False,
                "start_time": None
            }
            
            # 파일에 초기 데이터 저장
            with open(state_file, "w") as f:
                import json
                json.dump(init_data, f)
                f.flush()
                os.fsync(f.fileno())
                
            logger.info(f"프로그램 시작 시 상태 파일 초기화: {state_file}")
        except Exception as e:
            logger.exception(f"상태 파일 초기화 오류: {e}")
    
    # Python 실행 경로 확인
    python_exe = sys.executable
    
    # Streamlit 실행 명령
    cmd = [
        python_exe, 
        "-m", 
        "streamlit", 
        "run", 
        streamlit_script, 
        "--server.port=8501",
        "--server.headless=false", 
        "--browser.serverAddress=127.0.0.1"
    ]
    
    logger.info(f"실행 명령: {' '.join(cmd)}")
    
    # Streamlit 프로세스 시작
    env = os.environ.copy()
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False
    )
    
    logger.info(f"Streamlit UI 프로세스 시작됨 (PID: {process.pid})")
    logger.info(f"Streamlit UI에 접속하려면 브라우저에서 http://127.0.0.1:8501 을 열어주세요")
    
    # SSE 서버 시작
    try:
        # SSE 서버 모듈 가져오기
        from posture_guardian.ui.sse_server import start_flask_server
        
        # SSE 서버 별도 스레드로 시작
        sse_thread = threading.Thread(
            target=start_flask_server,
            kwargs={"host": "127.0.0.1", "port": 5000},
            daemon=True
        )
        sse_thread.start()
        logger.info("SSE 서버 시작됨 - http://127.0.0.1:5000 에서 실시간 업데이트 활성화")
        
        # 브라우저를 SSE 서버로 열기
        import webbrowser
        await asyncio.sleep(2)  # 서버가 시작될 시간을 주기 위해 지연
        webbrowser.open_new_tab("http://127.0.0.1:5000")
        logger.info("브라우저가 SSE 서버로 자동으로 열렸습니다.")
    except Exception as e:
        logger.exception(f"SSE 서버 시작 오류: {e}")
        # 기존 Streamlit UI 브라우저 열기 코드 실행
        try:
            import webbrowser
            await asyncio.sleep(3)
            webbrowser.open_new_tab("http://127.0.0.1:8501")
            logger.info("Streamlit UI 브라우저가 자동으로 열렸습니다.")
        except Exception as e:
            logger.warning(f"브라우저를 자동으로 열지 못했습니다: {e}")
    
    return process


async def _create_streamlit_app(file_path: str) -> None:
    """
    Streamlit 앱 파일 생성
    
    Args:
        file_path: 파일 경로
    """
    content = """import os
import streamlit as st
import time
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="자세 교정 유도 장치",
    page_icon="🧘",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 세션 상태 초기화
if 'score' not in st.session_state:
    st.session_state.score = 10
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'status' not in st.session_state:
    st.session_state.status = "unknown"
if 'message' not in st.session_state:
    st.session_state.message = "준비 중..."
if 'details' not in st.session_state:
    st.session_state.details = {}
if 'calibration_complete' not in st.session_state:
    st.session_state.calibration_complete = False
if 'calibration_started' not in st.session_state:
    st.session_state.calibration_started = False

# CSS 스타일 적용
def local_css():
    st.markdown('''
    <style>
        .main-title {
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 2rem;
            text-align: center;
        }
        .score-container {
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 8rem;
            font-weight: bold;
            margin: 2rem 0;
            height: 12rem;
        }
        .good-score { color: #00b894; }
        .warning-score { color: #fdcb6e; }
        .bad-score { color: #d63031; }
        .status-message {
            font-size: 1.5rem;
            font-weight: bold;
            text-align: center;
            margin: 1rem 0;
            padding: 1rem;
            border-radius: 0.5rem;
        }
        .good-status { background-color: #55efc4; color: #2d3436; }
        .warning-status { background-color: #ffeaa7; color: #2d3436; }
        .bad-status { background-color: #fab1a0; color: #2d3436; }
        .timer-display {
            font-size: 1.5rem;
            text-align: center;
            margin: 1rem 0;
        }
        .start-button {
            display: flex;
            justify-content: center;
            margin: 2rem 0;
        }
        .details-section {
            margin-top: 2rem;
            border-top: 1px solid #dfe6e9;
            padding-top: 1rem;
        }
        .alert-animation {
            animation: blinker 1s linear infinite;
        }
        @keyframes blinker {
            50% { background-color: rgba(255, 0, 0, 0.2); }
        }
    </style>
    ''', unsafe_allow_html=True)

def main():
    local_css()
    
    # 페이지 제목
    st.markdown('<div class="main-title">자세 교정 유도 장치</div>', unsafe_allow_html=True)
    
    # 시작하기 화면
    if not st.session_state.calibration_started and not st.session_state.calibration_complete:
        st.info("바른 자세로 앉아주세요. '시작하기' 버튼을 누르면 3초간 기준 자세를 측정합니다.")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("시작하기", key="start_button"):
                st.session_state.calibration_started = True
                st.session_state.message = "보정 중... 바른 자세를 유지해주세요."
                st.rerun()
    
    # 보정 화면 - 프로그레스 바 표시
    elif st.session_state.calibration_started and not st.session_state.calibration_complete:
        # 다른 UI 요소 모두 제거하고 프로그레스 바만 표시
        st.empty()  # 이전 내용 지우기
        
        # 제목만 다시 표시
        st.markdown('<div class="main-title">자세 교정 유도 장치</div>', unsafe_allow_html=True)
        
        # 보정 상태 메시지
        st.markdown(f'<div class="status-message warning-status">{st.session_state.message}</div>', unsafe_allow_html=True)
        
        # 큰 프로그레스 바 표시
        progress_bar = st.progress(0)
        
        # 보정 진행 표시 - 3초 동안 진행
        for i in range(100):
            # 3초 동안 나누어 진행 (3초 / 100단계 = 0.03초)
            time.sleep(0.03)
            progress_bar.progress(i + 1, text=f"보정 중... {i+1}%")
        
        # 보정 완료 상태 업데이트
        st.session_state.calibration_complete = True
        st.session_state.start_time = datetime.now()
        st.session_state.message = "교정 완료! 바른 자세를 유지하세요."
        st.rerun()
    
    # 메인 화면 - 점수 표시
    else:
        # 점수 표시
        score_class = "good-score"
        if st.session_state.score <= 3:
            score_class = "bad-score"
        elif st.session_state.score <= 7:
            score_class = "warning-score"
            
        st.markdown(f'<div class="score-container {score_class}">{st.session_state.score}</div>', unsafe_allow_html=True)
        
        # 상태 메시지
        status_class = "good-status"
        if st.session_state.status == "bad_eyes":
            status_class = "bad-status"
            st.session_state.message = "자세가 바르지 않습니다! 앞으로 기울이지 마세요."
        elif st.session_state.status == "bad_foot":
            status_class = "bad-status"
            st.session_state.message = "발받침대에 압력이 불균형합니다!"
        elif st.session_state.status == "bad_cushion":
            status_class = "bad-status"
            st.session_state.message = "방석에 압력이 불균형합니다!"
        elif st.session_state.status == "good":
            status_class = "good-status"
            st.session_state.message = "좋은 자세를 유지하고 있습니다!"
        
        message_div = f'<div class="status-message {status_class}">{st.session_state.message}</div>'
        if st.session_state.status != "good":
            message_div = f'<div class="status-message {status_class} alert-animation">{st.session_state.message}</div>'
        
        st.markdown(message_div, unsafe_allow_html=True)
        
        # 경과 시간 표시
        if st.session_state.start_time:
            elapsed = datetime.now() - st.session_state.start_time
            minutes = elapsed.seconds // 60
            seconds = elapsed.seconds % 60
            st.markdown(f'<div class="timer-display">경과 시간: {minutes}분 {seconds}초</div>', unsafe_allow_html=True)
        
        # 실패 상태 (점수 0)
        if st.session_state.score <= 0:
            st.error("자세 유지에 실패하셨어요! 처음부터 다시 시작하세요!")
            elapsed = datetime.now() - st.session_state.start_time
            minutes = elapsed.seconds // 60
            seconds = elapsed.seconds % 60
            st.info(f"자세 유지 시간: {minutes}분 {seconds}초")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("다시 시작", key="restart_button"):
                    st.session_state.score = 10
                    st.session_state.start_time = None
                    st.session_state.calibration_started = False
                    st.session_state.calibration_complete = False
                    st.session_state.status = "unknown"
                    st.session_state.message = "준비 중..."
                    st.session_state.details = {}
                    st.rerun()
        
        # 세부 정보 영역 (접을 수 있는 섹션)
        with st.expander("세부 정보"):
            if st.session_state.details:
                for key, value in st.session_state.details.items():
                    st.text(f"{key}: {value}")
            else:
                st.text("세부 정보가 없습니다.")

# 메인 함수 실행
if __name__ == "__main__":
    main()
"""
    
    # 파일 쓰기
    with open(file_path, "w") as f:
        f.write(content)
    
    logger.info(f"Streamlit 앱 파일 생성됨: {file_path}")


async def play_alert_sound() -> None:
    """
    알림 소리 재생
    """
    try:
        if sys.platform == "darwin":  # macOS
            os.system("afplay /System/Library/Sounds/Tink.aiff")
        elif sys.platform == "win32":  # Windows
            os.system('powershell -c (New-Object Media.SoundPlayer "C:\\Windows\\Media\\chimes.wav").PlaySync()')
        else:  # Linux
            os.system("aplay /usr/share/sounds/sound-icons/glass-water.wav &>/dev/null || true")
    except Exception as e:
        logger.exception(f"알림 소리 재생 실패: {e}")


class UIState:
    """UI 상태 관리"""
    
    def __init__(self):
        self.score = 10
        self.status = PostureStatus.UNKNOWN
        self.message = "준비 중..."
        self.details: Dict[str, str] = {}
        self.last_update_time = datetime.now()
        self.calibration_complete = False
        self.start_time: Optional[datetime] = None
    
    def update_from_result(self, result: PostureResult) -> bool:
        """
        자세 평가 결과로 상태 업데이트
        
        Args:
            result: 자세 평가 결과
            
        Returns:
            bool: 상태 변경 여부
        """
        changed = False
        
        # 점수 업데이트
        if self.score != result.score:
            self.score = result.score
            changed = True
            logger.info(f"UI 상태 업데이트: 점수 변경 -> {self.score}")
        
        # 상태 업데이트
        if self.status != result.status:
            self.status = result.status
            changed = True
            logger.info(f"UI 상태 업데이트: 상태 변경 -> {self.status}")
            
            # 상태별 메시지 설정
            if result.status == PostureStatus.BAD_EYES:
                self.message = "자세가 바르지 않습니다! 앞으로 기울이지 마세요."
            elif result.status == PostureStatus.BAD_FOOT:
                self.message = "발받침대에 압력이 불균형합니다!"
            elif result.status == PostureStatus.BAD_CUSHION:
                self.message = "방석에 압력이 불균형합니다!"
            elif result.status == PostureStatus.GOOD:
                self.message = "좋은 자세를 유지하고 있습니다!"
            else:
                self.message = "자세 상태를 확인할 수 없습니다."
        
        # 세부 정보 업데이트
        if result.details:
            self.details = {k: f"{v:.4f}" if isinstance(v, float) else str(v) 
                           for k, v in result.details.items()}
            
        self.last_update_time = datetime.now()
        
        # 상태가 변경되었으면 상태 파일 업데이트
        if changed:
            self._save_state_to_file()
            
        return changed
    
    def update_from_calibration(self, calibration: CalibrationData) -> None:
        """
        보정 데이터로 상태 업데이트
        
        Args:
            calibration: 보정 데이터
        """
        self.calibration_complete = calibration.completed
        if self.calibration_complete:
            self.start_time = datetime.now()
            self.score = 10
            self.status = PostureStatus.GOOD
            self.message = "교정을 시작합니다! 자세가 뒤틀어질 때마다, 점수가 깎여요!"
            # 보정 완료시 상태 파일 업데이트
            self._save_state_to_file()
    
    def _save_state_to_file(self) -> None:
        """
        현재 UI 상태를 임시 파일에 저장
        """
        try:
            import json
            import os
            
            # 저장할 데이터 준비
            data = {
                "score": self.score,
                "status": self.status,
                "message": self.message,
                "details": self.details,
                "calibration_complete": self.calibration_complete,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "timestamp": datetime.now().isoformat()  # 파일 생성 시간 추가
            }
            
            # 임시 파일 경로 설정
            dir_path = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(dir_path, "temp_state.json")
            
            # 파일에 데이터 저장 (즉시 플러시)
            with open(file_path, "w") as f:
                json.dump(data, f, ensure_ascii=False)  # 한글 인코딩 보존
                f.flush()
                os.fsync(f.fileno())  # 파일 시스템에 즉시 반영
                
            logger.info(f"UI 상태를 파일에 저장했습니다: score={self.score}, status={self.status}")
        except Exception as e:
            logger.exception(f"UI 상태 파일 저장 오류: {e}")


# UI 상태 인스턴스
ui_state = UIState()


async def ui_processor(config: AppConfig) -> None:
    """
    UI 처리 작업을 실행합니다.
    
    Args:
        config: 애플리케이션 설정
    """
    logger.info("UI 처리기 시작")
    bus = get_event_bus()
    
    # 마지막 명령 처리 시간 추적
    last_command_check = datetime.now()
    
    # 이벤트 처리 함수들
    async def on_posture_result(event: Event) -> None:
        result: PostureResult = event.data
        # 결과를 받을 때마다 무조건 UI 상태 업데이트 (점수와 상태가 변경되지 않아도)
        ui_state.score = result.score
        ui_state.status = result.status
        
        # 상태별 메시지 설정
        if result.status == PostureStatus.BAD_EYES:
            ui_state.message = "자세가 바르지 않습니다! 앞으로 기울이지 마세요."
        elif result.status == PostureStatus.BAD_FOOT:
            ui_state.message = "발받침대에 압력이 불균형합니다!"
        elif result.status == PostureStatus.BAD_CUSHION:
            ui_state.message = "방석에 압력이 불균형합니다!"
        elif result.status == PostureStatus.GOOD:
            ui_state.message = "좋은 자세를 유지하고 있습니다!"
        else:
            ui_state.message = "자세 상태를 확인할 수 없습니다."
        
        # 세부 정보 업데이트
        if result.details:
            ui_state.details = {k: f"{v:.4f}" if isinstance(v, float) else str(v) 
                              for k, v in result.details.items()}
        
        # 항상 상태 파일 업데이트
        ui_state._save_state_to_file()
        
        # 로그 및 알림
        logger.info(f"자세 상태 갱신: {result.status}, 점수: {result.score}")
        
        # 나쁜 자세일 경우에만 알림 소리
        if result.status != PostureStatus.GOOD:
            await play_alert_sound()
    
    async def on_calibration(event: Event) -> None:
        calibration: CalibrationData = event.data
        ui_state.update_from_calibration(calibration)
        logger.info("UI 처리기: 보정 데이터 수신 완료")
    
    # 명령 파일 확인 함수
    async def check_command_file():
        try:
            # 명령 파일 경로
            dir_path = os.path.dirname(os.path.abspath(__file__))
            cmd_file = os.path.join(dir_path, "command.json")
            
            if os.path.exists(cmd_file):
                # 파일에서 명령 읽기
                with open(cmd_file, "r") as f:
                    data = json.load(f)
                
                cmd_type = data.get("command")
                
                # 파일 삭제 (한 번만 처리하기 위해)
                os.remove(cmd_file)
                
                # 명령 처리
                if cmd_type == "START":
                    logger.info("UI에서 시작 명령 수신")
                    
                    # START 명령 이벤트 발행
                    start_cmd = Event(
                        type=EventType.COMMAND,
                        data=Command(type=CommandType.START)
                    )
                    await bus.publish(start_cmd)
                    logger.info("시작 명령을 이벤트 버스에 발행했습니다.")
        except Exception as e:
            if os.path.exists(cmd_file):
                logger.exception(f"명령 파일 처리 오류: {e}")
    
    # 이벤트 구독
    result_unsub = bus.subscribe(EventType.POSTURE_RESULT, on_posture_result)
    cal_unsub = bus.subscribe(EventType.CALIBRATION, on_calibration)
    
    try:
        # 상태 업데이트 루프 - 더 자주 실행되도록 수정
        while True:
            # 명령 파일 확인 (0.5초마다)
            current_time = datetime.now()
            if (current_time - last_command_check).total_seconds() >= 0.5:
                await check_command_file()
                last_command_check = current_time
            
            # 짧은 간격으로 처리
            await asyncio.sleep(0.05)
    
    except asyncio.CancelledError:
        logger.info("UI 처리기 태스크 취소됨")
    except Exception as e:
        logger.exception(f"UI 처리기 오류: {e}")
    finally:
        # 구독 해제
        result_unsub()
        cal_unsub()
        logger.info("UI 처리기 종료") 