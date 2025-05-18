"""posture_guardian.processing.posture_evaluator
자세 데이터 평가 모듈

센서로부터 수집한 데이터(웹캠·압력값)를 분석해 자세 상태를 판단합니다.
- status : good, bad_eyes, bad_foot, bad_cushion, unknown
- message : 사용자에게 보여줄 메시지
- details : 센서 수치 상세 정보(dict)
"""
from typing import Dict, Tuple


# ----- 임계값 설정 (간단한 휴리스틱) -----
EYE_DISTANCE_MIN = 0.03  # 너무 가까우면 고개 숙임으로 판단
EYE_DISTANCE_MAX = 0.08  # 너무 멀면 화면에서 멀어짐
FOOT_PRESSURE_MIN = 450  # 발판 압력 정상 범위 (시뮬레이션 값 기준)
FOOT_PRESSURE_MAX = 550
CUSHION_PRESSURE_MIN = 450  # 방석 압력 정상 범위 (시뮬레이션 값 기준)
CUSHION_PRESSURE_MAX = 550


def _evaluate_single(data: Dict[str, float]) -> Tuple[str, str, Dict[str, float]]:
    """통합 데이터(dict) 기반 평가"""
    details = {
        "eye_distance_left": data.get("eye_distance_left"),
        "eye_distance_right": data.get("eye_distance_right"),
        "foot_value": data.get("foot_value"),
        "cushion_value": data.get("cushion_value"),
    }

    # ----- 눈 거리 평가 -----
    eye_left = data.get("eye_distance_left", 0.0)
    eye_right = data.get("eye_distance_right", 0.0)
    eye_avg = (eye_left + eye_right) / 2

    if not (EYE_DISTANCE_MIN <= eye_avg <= EYE_DISTANCE_MAX):
        status = "bad_eyes"
        message = "자세가 바르지 않습니다! 앞으로 기울이지 마세요."
        return status, message, details

    # ----- 발판 압력 평가 -----
    foot_val = data.get("foot_value", 500)
    if not (FOOT_PRESSURE_MIN <= foot_val <= FOOT_PRESSURE_MAX):
        status = "bad_foot"
        message = "발판에 압력이 불균형합니다!"
        return status, message, details

    # ----- 방석 압력 평가 -----
    cushion_val = data.get("cushion_value", 500)
    if not (CUSHION_PRESSURE_MIN <= cushion_val <= CUSHION_PRESSURE_MAX):
        status = "bad_cushion"
        message = "방석에 압력이 불균형합니다!"
        return status, message, details

    # ----- 모두 정상 -----
    status = "good"
    message = "좋은 자세를 유지하고 있습니다!"
    return status, message, details


def evaluate_posture(*args):
    """자세 평가 함수 (가변 인자 지원)

    사용 예시:
        1) 하나의 dict 통합 데이터를 전달
            status, message, details = evaluate_posture(data_dict)
        2) 개별 센서 데이터를 전달 (웹캠 dict, 발판 dict, 방석 dict)
            status, message, details = evaluate_posture(webcam_dict, foot_dict, cushion_dict)
    """
    if len(args) == 1 and isinstance(args[0], dict):
        return _evaluate_single(args[0])

    if len(args) == 3:
        webcam_data, foot_data, cushion_data = args
        merged = {
            "eye_distance_left": webcam_data.get("eye_distance_left"),
            "eye_distance_right": webcam_data.get("eye_distance_right"),
            "foot_value": foot_data.get("foot_value"),
            "cushion_value": cushion_data.get("cushion_value"),
        }
        return _evaluate_single(merged)

    # 예외: 지원하지 않는 인자 형태
    raise ValueError("evaluate_posture() 인자 형식이 잘못되었습니다.")
