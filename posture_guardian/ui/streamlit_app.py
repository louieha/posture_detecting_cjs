import os
import streamlit as st
import time
from datetime import datetime
import json
import threading

# 페이지 설정
st.set_page_config(
    page_title="자세 교정 유도 장치",
    page_icon="🧘",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 강제 새로고침을 위한 HTML 코드 삽입
st.markdown(
    """
    <meta http-equiv="refresh" content="0.5">
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

# 실시간 데이터 동기화를 위한 함수
def load_state_from_file():
    try:
        # 임시 파일에서 상태 불러오기
        temp_dir = os.path.dirname(os.path.abspath(__file__))
        state_file = os.path.join(temp_dir, "temp_state.json")
        
        if os.path.exists(state_file):
            # 파일 수정 시간 확인
            file_mtime = os.path.getmtime(state_file)
            last_file_check = getattr(st.session_state, 'last_file_check', 0)
            
            # 파일이 마지막 확인 이후 수정되었는지 확인
            if file_mtime > last_file_check:
                # 수정된 경우 파일 로드
                with open(state_file, "r") as f:
                    data = json.load(f)
                    
                    # 세션 상태 업데이트
                    st.session_state.score = data.get('score', 10)
                    st.session_state.status = data.get('status', "unknown")
                    st.session_state.message = data.get('message', "준비 중...")
                    st.session_state.details = data.get('details', {})
                    st.session_state.calibration_complete = data.get('calibration_complete', False)
                    
                    if 'start_time' in data and data['start_time']:
                        try:
                            st.session_state.start_time = datetime.fromisoformat(data['start_time'])
                        except:
                            pass
                
                # 마지막 확인 시간 업데이트
                st.session_state.last_file_check = file_mtime
                st.session_state.last_update_time = datetime.now()
                
                print(f"상태 파일이 업데이트됨: 점수={st.session_state.score}, 상태={st.session_state.status}")
    except Exception as e:
        print(f"상태 파일 로드 오류: {e}")
        # 오류 발생 시 콘솔에 자세한 정보 출력
        import traceback
        traceback.print_exc()

# 세션 상태 초기화
# 프로그램 시작 여부를 확인하는 플래그 추가
if 'app_initialized' not in st.session_state:
    # 최초 실행 시 모든 변수 초기화
    st.session_state.clear()
    st.session_state.app_initialized = True
    st.session_state.score = 10
    st.session_state.start_time = None
    st.session_state.status = "unknown"
    st.session_state.message = "준비 중..."
    st.session_state.details = {}
    st.session_state.calibration_complete = False
    st.session_state.calibration_started = False
    st.session_state.last_update_time = datetime.now()
    # 로그에 초기화 메시지 출력
    print("세션 상태가 초기화되었습니다.")
else:
    # 기존 세션 상태가 있다면 기본값 설정만 유지
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
    if 'last_update_time' not in st.session_state:
        st.session_state.last_update_time = datetime.now()

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
    
    # 세션 초기화 시 temp_state.json 파일도 초기화
    if 'app_initialized' in st.session_state and st.session_state.app_initialized:
        try:
            # temp_state.json 파일 초기화
            temp_dir = os.path.dirname(os.path.abspath(__file__))
            state_file = os.path.join(temp_dir, "temp_state.json")
            
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
                json.dump(init_data, f)
                f.flush()
                os.fsync(f.fileno())
                
            print(f"상태 파일이 초기화되었습니다: {state_file}")
            # 초기화 완료 후 플래그 해제
            st.session_state.app_initialized = False
        except Exception as e:
            print(f"상태 파일 초기화 오류: {e}")
    
    # 상태 업데이트를 더 자주 실행 (매번 호출 시)
    load_state_from_file()
    
    # 페이지 제목
    st.markdown('<div class="main-title">자세 교정 유도 장치</div>', unsafe_allow_html=True)
    
    # 자동 새로고침 및 상태 로드 자바스크립트 (보정이 완료된 경우에만)
    if st.session_state.calibration_complete:
        st.markdown("""
        <script>
            // 디버깅 메시지 출력
            console.log("자동 새로고침 작동 중");
        </script>
        """, unsafe_allow_html=True)

    # 시작 시간 데이터 요소 (경과 시간 계산용)
    if st.session_state.start_time:
        current_time = datetime.now()
        elapsed = current_time - st.session_state.start_time
        minutes = elapsed.seconds // 60
        seconds = elapsed.seconds % 60
        elapsed_str = f"{minutes}분 {seconds}초"
    else:
        elapsed_str = "0분 0초"
    
    # 시작하기 화면
    if not st.session_state.calibration_started and not st.session_state.calibration_complete:
        st.info("바른 자세로 앉아주세요. '시작하기' 버튼을 누르면 3초간 기준 자세를 측정합니다.")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("시작하기", key="start_button"):
                st.session_state.calibration_started = True
                st.session_state.message = "보정 중... 바른 자세를 유지해주세요."
                
                # 서버에 START 명령 보내기
                try:
                    # 시작 명령 파일 생성
                    temp_dir = os.path.dirname(os.path.abspath(__file__))
                    cmd_file = os.path.join(temp_dir, "command.json")
                    
                    cmd_data = {
                        "command": "START",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    with open(cmd_file, "w") as f:
                        json.dump(cmd_data, f)
                        f.flush()
                        os.fsync(f.fileno())
                        
                    print("시작 명령이 서버로 전송되었습니다.")
                except Exception as e:
                    print(f"시작 명령 전송 오류: {e}")
                
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
        st.markdown(f'<div class="timer-display">경과 시간: {elapsed_str}</div>', unsafe_allow_html=True)
        
        # 실패 상태 (점수 0)
        if st.session_state.score <= 0:
            st.error("자세 유지에 실패하셨어요! 처음부터 다시 시작하세요!")
            st.info(f"자세 유지 시간: {elapsed_str}")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("다시 시작", key="restart_button"):
                    # 세션 상태 완전 초기화
                    st.session_state.clear()
                    st.session_state.app_initialized = True
                    st.session_state.score = 10
                    st.session_state.start_time = None
                    st.session_state.calibration_started = False
                    st.session_state.calibration_complete = False
                    st.session_state.status = "unknown"
                    st.session_state.message = "준비 중..."
                    st.session_state.details = {}
                    
                    # 상태 파일도 초기화
                    try:
                        temp_dir = os.path.dirname(os.path.abspath(__file__))
                        state_file = os.path.join(temp_dir, "temp_state.json")
                        
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
                            json.dump(init_data, f)
                            f.flush()
                            os.fsync(f.fileno())
                    except Exception as e:
                        print(f"재시작 시 상태 파일 초기화 오류: {e}")
                    
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
