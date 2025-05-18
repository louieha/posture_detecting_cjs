"""
SSE(Server-Sent Events)를 사용한 실시간 업데이트 서버
- Flask와 flask-sse를 사용하여 자세 상태를 실시간으로 브라우저에 전송
"""
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, render_template, send_from_directory
from flask_sse import sse

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Redis 구성
if "REDIS_URL" not in os.environ:
    os.environ["REDIS_URL"] = "redis://localhost:6379"

# Flask 앱 생성
app = Flask(__name__, template_folder="templates")
app.config["REDIS_URL"] = os.environ["REDIS_URL"]
app.register_blueprint(sse, url_prefix='/stream')

# 현재 디렉토리 경로
current_dir = Path(__file__).parent

# 마지막으로 처리한 상태 파일 수정 시간
last_state_file_mtime = 0
last_score = 10

# HTML 템플릿 디렉토리 생성
templates_dir = current_dir / "templates"
if not templates_dir.exists():
    templates_dir.mkdir(parents=True)

# 정적 파일 디렉토리 생성
static_dir = current_dir / "static"
if not static_dir.exists():
    static_dir.mkdir(parents=True)

# HTML 템플릿 생성
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>자세 교정 유도 장치 - 실시간 업데이트</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            padding: 20px;
        }
        .score-container {
            font-size: 72px;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
        }
        .good-score { color: #00b894; }
        .warning-score { color: #fdcb6e; }
        .bad-score { color: #d63031; }
        .status-message {
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
            padding: 10px;
            border-radius: 5px;
        }
        .good-status { background-color: #55efc4; color: #2d3436; }
        .warning-status { background-color: #ffeaa7; color: #2d3436; }
        .bad-status { background-color: #fab1a0; color: #2d3436; }
        .timer-display {
            font-size: 24px;
            text-align: center;
            margin: 20px 0;
        }
        .alert-animation {
            animation: blinker 1s linear infinite;
        }
        @keyframes blinker {
            50% { background-color: rgba(255, 0, 0, 0.2); }
        }
    </style>
</head>
<body>
    <h1 style="text-align: center;">자세 교정 유도 장치</h1>
    
    <div class="score-container" id="score">10</div>
    
    <div class="status-message good-status" id="status-message">준비 중...</div>
    
    <div class="timer-display" id="timer">경과 시간: 0분 0초</div>
    
    <div id="details" style="margin-top: 30px; border-top: 1px solid #ddd; padding-top: 10px;">
        <h3>세부 정보</h3>
        <div id="details-content">세부 정보가 없습니다.</div>
    </div>

    <script>
        // SSE 연결 설정
        const eventSource = new EventSource("/stream");
        
        // 시작 시간
        let startTime = null;
        
        // 상태 업데이트 이벤트 수신
        eventSource.addEventListener('posture-update', function(e) {
            const data = JSON.parse(e.data);
            console.log('상태 업데이트 수신:', data);
            
            // 점수 업데이트
            const scoreElement = document.getElementById('score');
            scoreElement.textContent = data.score;
            
            // 점수에 따른 클래스 설정
            scoreElement.className = 'score-container';
            if (data.score <= 3) {
                scoreElement.classList.add('bad-score');
            } else if (data.score <= 7) {
                scoreElement.classList.add('warning-score');
            } else {
                scoreElement.classList.add('good-score');
            }
            
            // 상태 메시지 업데이트
            const statusElement = document.getElementById('status-message');
            statusElement.textContent = data.message;
            
            // 상태에 따른 클래스 설정
            statusElement.className = 'status-message';
            if (data.status === 'good') {
                statusElement.classList.add('good-status');
            } else if (data.status.startsWith('bad_')) {
                statusElement.classList.add('bad-status');
                statusElement.classList.add('alert-animation');
            } else {
                statusElement.classList.add('warning-status');
            }
            
            // 시작 시간 설정 (처음 한 번만)
            if (data.start_time && !startTime) {
                startTime = new Date(data.start_time);
                // 타이머 시작
                updateTimer();
            }
            
            // 세부 정보 업데이트
            const detailsContent = document.getElementById('details-content');
            if (data.details && Object.keys(data.details).length > 0) {
                let detailsHtml = '';
                for (const [key, value] of Object.entries(data.details)) {
                    detailsHtml += `<p>${key}: ${value}</p>`;
                }
                detailsContent.innerHTML = detailsHtml;
            } else {
                detailsContent.textContent = '세부 정보가 없습니다.';
            }
        });
        
        // 경과 시간 업데이트 함수
        function updateTimer() {
            if (!startTime) return;
            
            const now = new Date();
            const elapsedSeconds = Math.floor((now - startTime) / 1000);
            const minutes = Math.floor(elapsedSeconds / 60);
            const seconds = elapsedSeconds % 60;
            
            document.getElementById('timer').textContent = 
                `경과 시간: ${minutes}분 ${seconds}초`;
            
            // 1초마다 업데이트
            setTimeout(updateTimer, 1000);
        }
        
        // 연결 오류 처리
        eventSource.onerror = function(e) {
            console.error('SSE 연결 오류:', e);
            // 5초 후 재연결 시도
            setTimeout(() => {
                eventSource.close();
                window.location.reload();
            }, 5000);
        };
    </script>
</body>
</html>
"""

# HTML 템플릿 파일 저장
with open(templates_dir / "index.html", "w", encoding="utf-8") as f:
    f.write(html_template)

@app.route('/')
def index():
    """인덱스 페이지"""
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """정적 파일 제공"""
    return send_from_directory(static_dir, path)

def read_state_file():
    """상태 파일 읽기"""
    global last_state_file_mtime, last_score
    
    try:
        state_file = current_dir / "temp_state.json"
        
        if not state_file.exists():
            return
        
        # 파일 수정 시간 확인
        current_mtime = state_file.stat().st_mtime
        
        # 파일이 변경되었는지 확인
        if current_mtime > last_state_file_mtime:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 점수가 변경되었는지 확인
            if data.get("score", 10) != last_score:
                logger.info(f"상태 변경 감지: 점수={data.get('score', 10)}, 상태={data.get('status', 'unknown')}")
                last_score = data.get("score", 10)
                
                # SSE 이벤트 발행
                sse.publish(data, type="posture-update")
            
            # 수정 시간 업데이트
            last_state_file_mtime = current_mtime
    except Exception as e:
        logger.exception(f"상태 파일 읽기 오류: {e}")

def monitor_state_file():
    """상태 파일을 주기적으로 모니터링"""
    while True:
        read_state_file()
        time.sleep(0.1)  # 100ms마다 확인

def start_flask_server(host="127.0.0.1", port=5000):
    """Flask 서버 시작"""
    logger.info(f"SSE 서버 시작: http://{host}:{port}")
    
    # 상태 파일 모니터링 스레드 시작
    monitor_thread = threading.Thread(target=monitor_state_file, daemon=True)
    monitor_thread.start()
    
    # Flask 서버 실행
    return app.run(host=host, port=port, debug=False, threaded=True)

if __name__ == "__main__":
    start_flask_server() 