"""
적응형 캘리브레이션

9포인트 초기 캘리브레이션 후
점진적으로 더 많은 포인트에서 캘리브레이션하며
실시간으로 모델을 재훈련하는 고급 캘리브레이션
"""

from __future__ import annotations

import random
import time
from typing import List, Tuple

import cv2
import numpy as np

from model.calibration.nine_point import run_9_point_calibration
from model.gaze import GazeEstimator
from model.utils.draw import draw_cursor
from model.utils.screen import get_screen_size


class BlueNoiseSampler:
    """
    Blue Noise 샘플링을 사용한 포인트 생성
    
    균등하게 분산된 포인트들을 생성합니다 (랜덤하지만 고르게 분포)
    화면 전체를 고르게 커버하기에 효과적입니다.
    """

    def __init__(self, w: int, h: int, margin: float = 0.08):
        """
        Blue Noise 샘플러 초기화
        
        Args:
            w (int): 화면 너비
            h (int): 화면 높이
            margin (float): 화면 가장자리 마진 비율 (기본값: 0.08 = 8%)
        """
        self.w, self.h = w, h
        self.mx, self.my = int(w * margin), int(h * margin)

    def sample(self, n: int, k: int = 30) -> List[Tuple[int, int]]:
        """
        균등하게 분산된 n개의 포인트를 생성합니다
        
        Poisson Disk Sampling 방식 사용:
        새로운 포인트는 기존 포인트들로부터 가장 먼 위치에 배치됩니다.
        
        Args:
            n (int): 생성할 포인트 개수
            k (int): 각 포인트마다 시도할 후보 개수 (기본값: 30)
                    클수록 더 좋은 배치, 느림
        
        Returns:
            list: (x, y) 포인트 좌표의 리스트
        """
        pts: List[Tuple[int, int]] = []
        for _ in range(n):
            best, best_d2 = None, -1
            # k번 후보를 시도해서 기존 포인트로부터 가장 먼 곳 선택
            for _ in range(k):
                x = random.randint(self.mx, self.w - self.mx)
                y = random.randint(self.my, self.h - self.my)
                # 기존 포인트들로부터의 최소 거리 제곱
                d2 = (
                    min((x - px) ** 2 + (y - py) ** 2 for px, py in pts) if pts else 1e9
                )
                # 가장 먼 위치 기록
                if d2 > best_d2:
                    best, best_d2 = (x, y), d2
            pts.append(best)
        return pts


def _draw_live_pred(canvas, frame, gaze_estimator):
    """
    프레임에서 시선을 추출하고 예측 결과를 캔버스에 그립니다
    
    Args:
        canvas: 그림을 그릴 numpy 배열 (이미지)
        frame: 입력 프레임
        gaze_estimator: 시선 추정기
    
    Returns:
        특징 배열 또는 None
    """
    ft, blink = gaze_estimator.extract_features(frame)
    if ft is None or blink:
        return None
    # 시선 위치 예측
    x_pred, y_pred = gaze_estimator.predict(np.array([ft]))[0]
    # 예측된 시선 위치를 커서로 표시
    draw_cursor(canvas, int(x_pred), int(y_pred), alpha=1.0)
    return ft


def _pulse_and_capture_live(
    gaze_estimator: GazeEstimator,
    cap: cv2.VideoCapture,
    pts: List[Tuple[int, int]],
    sw: int,
    sh: int,
):
    """
    적응형 캘리브레이션용 수행-캡처 루프
    
    각 포인트에서 1초간 펄스, 1초간 캡처
    실시간 시선 예측을 화면에 표시합니다
    
    Args:
        gaze_estimator: 시선 추정기
        cap: 비디오 캡처 객체
        pts: (x, y) 포인트 리스트
        sw: 화면 너비
        sh: 화면 높이
    
    Returns:
        tuple: (특징 리스트, 타겟 리스트) 또는 (None, None) 캔슬 시
    """
    feats, targs = [], []
    
    for x, y in pts:
        # === 펄스 단계 (1초) ===
        pulse_start = time.time()
        while time.time() - pulse_start < 1.0:
            ok, frame = cap.read()
            if not ok:
                continue
            canvas = np.zeros((sh, sw, 3), np.uint8)
            # 시간에 따라 원의 크기 변화 (펄스 효과)
            rad = 15 + int(15 * abs(np.sin((time.time() - pulse_start) * 6)))
            cv2.circle(canvas, (x, y), rad, (0, 255, 0), -1)
            # 실시간 시선 예측 표시
            _draw_live_pred(canvas, frame, gaze_estimator)
            cv2.imshow("Adaptive Calibration", canvas)
            if cv2.waitKey(1) == 27:
                # ESC 키로 캔슬
                return None, None

        # === 캡처 단계 (1초) ===
        cap_start = time.time()
        while time.time() - cap_start < 1.0:
            ok, frame = cap.read()
            if not ok:
                continue
            canvas = np.zeros((sh, sw, 3), np.uint8)
            cv2.circle(canvas, (x, y), 20, (0, 255, 0), -1)
            # 진행 원호 표시
            t = (time.time() - cap_start) / 1.0
            ang = 360 * (1 - (t * t * (3 - 2 * t)))
            cv2.ellipse(canvas, (x, y), (40, 40), 0, -90, -90 + ang, (255, 255, 255), 4)
            # 실시간 시선 예측 표시
            ft = _draw_live_pred(canvas, frame, gaze_estimator)
            cv2.imshow("Adaptive Calibration", canvas)
            if cv2.waitKey(1) == 27:
                # ESC 키로 캔슬
                return None, None
            # 유효한 시선 데이터 수집
            if ft is not None:
                feats.append(ft)
                targs.append([x, y])
    
    return feats, targs


def run_adaptive_calibration(
    gaze_estimator: GazeEstimator,
    *,
    num_random_points: int = 60,
    retrain_every: int = 10,
    show_predictions: bool = True,
    camera_index: int = 0,
) -> None:
    """
    적응형 캘리브레이션 실행
    
    1. 9포인트 초기 캘리브레이션 수행
    2. Blue Noise 샘플링으로 60개 포인트 생성
    3. 10개씩 묶어서 캘리브레이션 수행 (6번)
    4. 매번 데이터를 누적하고 모델 재훈련
    
    결과: 더 정확한 전체 화면 커버리지 캘리브레이션
    
    Args:
        gaze_estimator: 시선 추정기 인스턴스
        num_random_points (int): 생성할 랜덤 포인트 개수 (기본값: 60)
        retrain_every (int): 몇 개 포인트마다 모델 재훈련할지 (기본값: 10)
        show_predictions (bool): 실시간 예측 표시 여부 (기본값: True)
        camera_index (int): 웹캠 인덱스 (기본값: 0)
    """
    # 1단계: 기본 9포인트 캘리브레이션
    run_9_point_calibration(gaze_estimator, camera_index=camera_index)

    sw, sh = get_screen_size()
    # 2단계: 균등 분산 포인트 생성
    sampler = BlueNoiseSampler(sw, sh)
    points = sampler.sample(num_random_points)

    cap = cv2.VideoCapture(camera_index)
    cv2.namedWindow("Adaptive Calibration", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(
        "Adaptive Calibration", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
    )

    all_feats, all_targs = [], []

    # 3단계: 청크 단위로 캘리브레이션 및 재훈련
    for chunk_start in range(0, len(points), retrain_every):
        chunk = points[chunk_start : chunk_start + retrain_every]
        feats, targs = _pulse_and_capture_live(gaze_estimator, cap, chunk, sw, sh)
        if feats is None:
            # 사용자가 캔슬함
            break
        all_feats.extend(feats)
        all_targs.extend(targs)

        # 누적된 모든 데이터로 모델 재훈련
        gaze_estimator.train(np.asarray(all_feats), np.asarray(all_targs))

    cap.release()
    cv2.destroyWindow("Adaptive Calibration")
