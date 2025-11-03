"""
5포인트 캘리브레이션

빠른 5포인트 캘리브레이션 (4개 모서리 + 중앙)
9포인트보다 빠르지만 정확도는 약간 낮음
"""

import cv2
import numpy as np

from model.calibration.common import (
    _pulse_and_capture,
    compute_grid_points,
    wait_for_face_and_countdown,
)
from model.utils.screen import get_screen_size


def run_5_point_calibration(gaze_estimator, camera_index: int = 0):
    """
    빠른 5포인트 캘리브레이션 실행
    
    화면의 4개 모서리와 중앙에서 시선 데이터를 수집합니다.
    순서: 중앙 → 좌상단 → 우상단 → 좌하단 → 우하단
    
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

    # 5개 포인트의 그리드 위치 (행, 열) 순서
    order = [
        (1, 1),  # 1. 중앙
        (0, 0),  # 2. 좌상단
        (2, 0),  # 3. 우상단
        (0, 2),  # 4. 좌하단
        (2, 2),  # 5. 우하단
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
