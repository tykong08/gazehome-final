"""
9포인트 캘리브레이션

표준 9포인트 캘리브레이션 (3x3 격자)
가장 일반적이고 효과적인 캘리브레이션 방식
"""

import cv2
import numpy as np

from model.calibration.common import (
    _pulse_and_capture,
    compute_grid_points,
    wait_for_face_and_countdown,
)
from model.utils.screen import get_screen_size


def run_9_point_calibration(gaze_estimator, camera_index: int = 0):
    """
    표준 9포인트 캘리브레이션 실행
    
    화면의 3x3 격자 (9개 위치)에서 시선 데이터를 수집합니다.
    순서:
    1. 중앙 → 좌상단 → 우상단 → 좌하단 → 우하단 (모서리)
    2. 상단 중앙 → 좌측 중앙 → 하단 중앙 → 우측 중앙 (가장자리)
    
    Args:
        gaze_estimator: 시선 추정기 인스턴스
        camera_index (int): 웹캠 인덱스 (기본값: 0)
    """
    sw, sh = get_screen_size()

    cap = cv2.VideoCapture(camera_index)
    # 사용자가 준비될 때까지 대기
    if not wait_for_face_and_countdown(cap, gaze_estimator, sw, sh, 2):
        cap.release()
        cv2.destroyAllWindows()
        return

    # 9개 포인트의 그리드 위치 (행, 열) 순서
    order = [
        (1, 1),  # 1. 중앙
        (0, 0),  # 2. 좌상단
        (2, 0),  # 3. 우상단
        (0, 2),  # 4. 좌하단
        (2, 2),  # 5. 우하단
        (1, 0),  # 6. 상단 중앙
        (0, 1),  # 7. 좌측 중앙
        (2, 1),  # 8. 하단 중앙
        (1, 2),  # 9. 우측 중앙
    ]
    # 격자 좌표를 픽셀 좌표로 변환
    pts = compute_grid_points(order, sw, sh)

    # 모든 포인트에서 시선 데이터 수집
    res = _pulse_and_capture(gaze_estimator, cap, pts, sw, sh)
    cap.release()
    cv2.destroyAllWindows()
    
    if res is None:
        # 사용자가 캔슬함
        return
    
    feats, targs = res
    # 수집된 데이터로 모델 훈련
    if feats:
        gaze_estimator.train(np.array(feats), np.array(targs))
