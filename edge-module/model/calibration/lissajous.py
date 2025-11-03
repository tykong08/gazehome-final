"""
리사주 곡선 캘리브레이션

부드러운 리사주 곡선을 따라 이동하는 포인트를 사용
지속적인 캘리브레이션으로 더 자연스러운 사용자 경험
"""

import cv2
import numpy as np

from model.calibration.common import wait_for_face_and_countdown
from model.utils.screen import get_screen_size


def run_lissajous_calibration(gaze_estimator, camera_index: int = 0):
    """
    리사주 곡선을 따라 캘리브레이션 포인트를 이동시킵니다
    
    리사주 곡선은 두 개의 정현파를 조합한 매개변수 곡선입니다:
    x(t) = A * sin(at + d) + sw/2
    y(t) = B * sin(bt) + sh/2
    
    이를 사용하면 화면 전체를 부드럽게 스캔하면서 캘리브레이션할 수 있습니다.
    
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

    # 리사주 곡선 파라미터
    A, B = sw * 0.4, sh * 0.4    # 진폭
    a, b = 3, 2                   # 주파수
    d = 0                          # 위상 오프셋

    def curve(t):
        """
        리사주 곡선 계산
        
        Args:
            t (float): 매개변수 (0 ~ 2π)
        
        Returns:
            tuple: (x, y) 화면 좌표
        """
        return (A * np.sin(a * t + d) + sw / 2, B * np.sin(b * t) + sh / 2)

    # 캘리브레이션 타이밍
    total_time = 5.0  # 총 5초
    fps = 60           # 60 FPS
    frames = int(total_time * fps)
    feats, targs = [], []
    acc = 0

    # 변수 속도 계산 (부드러운 속도 프로필)
    # 시작과 끝에서 느리고 중간에 빠름
    for i in range(frames):
        frac = i / (frames - 1)
        spd = 0.3 + 0.7 * np.sin(np.pi * frac)  # 0.3 ~ 1.0 범위
        acc += spd / fps
    end = acc if acc >= 1e-6 else 1e-6
    acc = 0

    # 리사주 곡선을 따라 이동하며 캘리브레이션
    for i in range(frames):
        frac = i / (frames - 1)
        spd = 0.3 + 0.7 * np.sin(np.pi * frac)
        acc += spd / fps
        # 정규화된 매개변수를 0 ~ 2π 범위로 변환
        t = (acc / end) * (2 * np.pi)
        
        ret, f = cap.read()
        if not ret:
            continue
        
        # 곡선 상의 점 계산
        x, y = curve(t)
        
        # 포인트 표시
        c = np.zeros((sh, sw, 3), dtype=np.uint8)
        cv2.circle(c, (int(x), int(y)), 20, (0, 255, 0), -1)
        cv2.imshow("Calibration", c)
        
        if cv2.waitKey(1) == 27:
            # ESC 키로 캔슬
            break
        
        # 시선 데이터 수집 (깜빡이지 않을 때만)
        ft, blink = gaze_estimator.extract_features(f)
        if ft is not None and not blink:
            feats.append(ft)
            targs.append([x, y])

    cap.release()
    cv2.destroyAllWindows()
    
    # 수집된 데이터로 모델 훈련
    if feats:
        gaze_estimator.train(np.array(feats), np.array(targs))
