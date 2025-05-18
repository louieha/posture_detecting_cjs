# Posture-Guardian 🪑

웹캠과 발판·방석 압력센서를 이용해 **올바른 자세**를 지켜주는 학습용 프로젝트입니다.  
코드는 Streamlit(front-end) + 파이썬 모듈화(back-end) 구조이며, 센서가 없더라도 **시뮬레이션 모드**로 바로 실행해 볼 수 있습니다.

---
## 1. 개발 환경 세팅 ‑ 상세
```bash
./setup_env.sh
# 스크립트가 venv 생성 → 활성화 → requirements 설치까지 자동 수행
source venv_new/bin/activate
```

#### Windows 수동
```powershell
.\venv_new\Scripts\Activate.ps1
pip install -r requirements.txt
```

가상환경이 열린 이후 아래 명령어 실행
```
streamlit run posture_guardian/main.py
```
---

---
## 2. 프로젝트 아키텍처 한눈에 보기
```
posture_guardian/
│
├── main.py                 # Streamlit 진입점 – 페이지 라우팅/설정
│
├── ui/                     # 프론트엔드(UI) 계층
│   ├── layout.py           # 각 페이지(Home/Calibration/Monitoring) 렌더링
│   ├── utils.py            # CSS 로더 등
│   └── style.css           # (선택) 사용자 정의 스타일
│
├── processing/             # 도메인-로직 계층
│   ├── calibration.py      # 3초간 기준 자세 측정
│   ├── monitor.py          # 주기적 센서 평가 & 점수/알림 업데이트
│   └── posture_evaluator.py# '좋음/나쁨' 판단 휴리스틱
│
├── sensors/                # 인프라(센서 I/O) 계층
│   ├── sensor_manager.py   # 센서 통합 관리 (웹캠 + 압력)
│   ├── webcam.py           # MediaPipe 기반 얼굴 키포인트 검출
│   ├── pressure_pad.py     # 아두이노→시리얼 or 시뮬레이터
│   └── …
└── core/…                  # 설정, 이벤트버스(구버전) 등
```
흐름 순서
1. 사용자가 **시작하기** 버튼 클릭 → `ui/layout.py` 가 `sensor_manager.initialize()` 호출하며 페이지를 `calibration` 으로 전환
2. **보정 시작** 버튼 → `processing/calibration.py` 가 1 초 동안 10 프레임을 모아 평균을 얻고 `session_state` 에 기준값 저장
3. `monitoring` 페이지가 반복적으로 `processing/monitor.py -> posture_evaluator.py` 를 호출해 센서 데이터를 평가
   * '나쁜 자세' → 점수 1 감점 + 5 초‐쿨다운 + 경고 (beep)
   * 점수 0 도달 → `finished` 플래그, 타이머 고정, 감지 중지

---
### 2-1. 센서(아두이노) 연결 지침
현재 `pressure_pad.py` 안의 `PressurePadSimulator` 가 무작위 값을 생성해 **발판/방석** 센서값을 대신합니다.
실제 HX711 + 로드셀 or FSR 을 연결하려면 다음 단계를 따라 주세요.
1. 아두이노 스케치 예시(`arduino/pressure_sender.ino`)를 업로드합니다.  
   – 두 센서를 A0, A1 에 연결해 아날로그 값(0-1023)을 `Serial.println("{foot},{cushion}")` 형식으로 전송합니다.
2. `sensors/pressure_pad.py` 의 `PressurePadSimulator` 클래스를 **`PressurePadSerial`** 로 교체하고, 시리얼 포트(`/dev/ttyACM0` 또는 COM3 등) 를 지정합니다.
```python
# pressure_pad.py (발췌)
import serial
class PressurePadSerial:
    def __init__(self, port='/dev/ttyACM0', baud=9600):
        self.ser = serial.Serial(port, baud)
    def read(self):
        line = self.ser.readline().decode().strip()
        foot, cushion = map(int, line.split(','))
        return foot, cushion
```
3. `SensorManager.__init__` 에서 `self.pressure_simulator = PressurePadSerial('/dev/ttyACM0')` 로 변경
4. 나머지 코드는 동일하게 동작합니다.

---
## 3. Github 협업 가이드
> 팀원이 코드를 망칠까 걱정하지 마세요. **Branch → Pull Request → Review → Merge** 순서만 지키면 안전합니다.

1. 본 저장소를 Fork 한 뒤 `git clone`
2. 기능 단위로 브랜치 생성
```bash
git checkout -b feature/<설명>
```
3. 개발 & 커밋 (자주, 의미 있게!)
```bash
git add .
git commit -m "feat: 웹캠 거리계산 개선"
```
4. 원격 동일 브랜치로 push
```bash
git push origin feature/<설명>
```
5. GitHub 에서 **Pull Request** 생성 → 리뷰어 지정 → 코드리뷰 받고 Merge
6. 팀원은 `main` 브랜치를 주기적으로 pull 하여 최신화
```bash
git checkout main
git pull upstream main   # 원본 저장소가 upstream 이라고 가정
```

협업 팁
* 커밋 메시지는 영어 present tense or 한글 서술형 권장
* 큰 기능을 한 번에 넣기보다, 작게 쪼개어 PR
* PR 설명란에 **변경 이유 / 주요 구현 / 테스트 방법 / 스크린샷** 포함

---
## 4. 자주 묻는 질문(FAQ)
| 질문 | 해결 |
|---|---|
| 실행했는데 빈 페이지만 나와요 | 터미널 로그에 에러가 없는지 확인 → 브라우저 새로고침(F5) |
| 웹캠이 열리지 않습니다 | 다른 앱이 카메라 사용 중인지 확인, macOS '카메라 권한' 허용 |
| 센서 값이 계속 10점인데요? | 현재 시뮬레이터 범위가 정상값만 내보내는 중 – `sensors/pressure_pad.py` 의 평균·표준편차를 수정해 테스트 |

즐거운 개발 되세요! 🎉

Git이 꼬인 것 같을 때
✅ 1. 기존 Git 설정 완전히 제거
현재 디렉토리에서 Git 관련 설정을 모두 삭제하려면 .git 폴더를 제거해야 합니다:

✅ 2. 새로운 Git 저장소 초기화
Git 저장소를 새로 초기화합니다:

bash
코드 복사
git init
이 명령어는 현재 디렉토리에 새로운 Git 저장소를 생성합니다