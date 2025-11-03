"""
시선 추적 필터링 모듈

이 모듈은 시선 위치의 노이즈를 제거하고 스무딩하는
다양한 필터 알고리즘을 제공합니다.

필터 종류:
- Kalman 필터: 선형 칼만 필터를 사용한 스무딩
- KDE: 커널 밀도 추정을 사용한 적응형 필터
- NoOp: 필터링 없이 원본 데이터 반환
"""

from __future__ import annotations

import cv2
import numpy as np


def make_kalman(
    state_dim: int = 4,
    meas_dim: int = 2,
    dt: float = 1.0,
    process_var: float = 50.0,
    measurement_var: float = 0.2,
    init_state: np.ndarray | None = None,
) -> cv2.KalmanFilter:
    """
    칼만 필터를 생성하고 초기화합니다.
    
    칼만 필터는 시선 위치의 노이즈를 제거하고 스무딩합니다.
    상태 벡터: [x, y, vx, vy] (위치 및 속도)
    측정값: [x, y] (직접 관측되는 위치만)
    
    Args:
        state_dim (int): 상태 벡터의 차원 (기본값: 4 = x, y, vx, vy)
        meas_dim (int): 측정값의 차원 (기본값: 2 = x, y)
        dt (float): 시간 스텝 (프레임 간 시간 간격)
        process_var (float): 프로세스 노이즈 분산 (움직임 예측의 불확실성)
        measurement_var (float): 측정 노이즈 분산 (센서의 노이즈)
        init_state (np.ndarray | None): 초기 상태 벡터 (None이면 0으로 초기화)
    
    Returns:
        cv2.KalmanFilter: 초기화된 칼만 필터 객체
    """
    kf = cv2.KalmanFilter(state_dim, meas_dim)

    # 상태 전이 행렬: x' = x + vx*dt, y' = y + vy*dt
    kf.transitionMatrix = np.array(
        [[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float32
    )
    # 측정값 행렬: 위치만 직접 관측 가능
    kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float32)
    # 프로세스 노이즈 공분산
    kf.processNoiseCov = np.eye(state_dim, dtype=np.float32) * process_var
    # 측정 노이즈 공분산
    kf.measurementNoiseCov = np.eye(meas_dim, dtype=np.float32) * measurement_var
    # 초기 오류 공분산
    kf.errorCovPost = np.eye(state_dim, dtype=np.float32)

    # 상태 벡터 초기화
    kf.statePre = np.zeros((state_dim, 1), np.float32)
    kf.statePost = np.zeros((state_dim, 1), np.float32)

    # 초기 상태 설정 (제공된 경우)
    if init_state is not None:
        init_state = np.asarray(init_state, np.float32).reshape(state_dim, 1)
        kf.statePre[:] = init_state
        kf.statePost[:] = init_state

    return kf


# 필터 클래스들 임포트
from .base import BaseSmoother
from .kalman import KalmanSmoother
from .kde import KDESmoother
from .noop import NoSmoother

__all__ = [
    "make_kalman",
    "BaseSmoother",
    "KalmanSmoother",
    "KDESmoother",
    "NoSmoother",
]
