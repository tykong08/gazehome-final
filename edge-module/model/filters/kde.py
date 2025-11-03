"""
커널 밀도 추정 필터 모듈

Kernel Density Estimation (KDE)을 사용한
적응형 시선 위치 스무더
"""

from __future__ import annotations

import time
from collections import deque
from typing import Deque, Tuple

import cv2
import numpy as np
from scipy.stats import gaussian_kde

from .base import BaseSmoother


class KDESmoother(BaseSmoother):
    """
    커널 밀도 추정 기반 시선 위치 스무더
    
    시간 윈도우 내의 시선 위치들을 가우시안 KDE로 모델링하고,
    확률 밀도 분포에서 신뢰도 높은 영역의 중심을 반환합니다.
    """

    def __init__(
        self,
        screen_w: int,
        screen_h: int,
        *,
        time_window: float = 0.5,
        confidence: float = 0.5,
        grid: Tuple[int, int] = (320, 200),
    ) -> None:
        """
        KDE 필터 초기화
        
        Args:
            screen_w (int): 화면 너비 (픽셀)
            screen_h (int): 화면 높이 (픽셀)
            time_window (float): 고려할 시선 히스토리 시간 윈도우 (초)
                                 기본값: 0.5초
            confidence (float): 신뢰도 임계값 (0~1)
                               1에 가까울수록 중심에 가까운 점들만 선택
                               기본값: 0.5
            grid (Tuple[int, int]): KDE 그리드 해상도 (너비, 높이)
                                   높을수록 정밀하지만 계산량 증가
                                   기본값: (320, 200)
        """
        super().__init__()
        self.sw, self.sh = screen_w, screen_h
        self.window = time_window
        self.conf = confidence
        self.grid = grid
        # 시선 히스토리: (timestamp, x, y) 튜플 저장
        self.hist: Deque[Tuple[float, int, int]] = deque()

    def step(self, x: int, y: int) -> Tuple[int, int]:
        """
        KDE를 사용하여 한 프레임의 시선 위치를 필터링합니다.
        
        Args:
            x (int): 측정된 X 좌표
            y (int): 측정된 Y 좌표
        
        Returns:
            Tuple[int, int]: 필터링된 (x, y) 좌표
        """
        now = time.time()

        # 새로운 시선 위치 추가
        self.hist.append((now, x, y))
        # 시간 윈도우를 벗어난 오래된 데이터 제거
        while self.hist and now - self.hist[0][0] > self.window:
            self.hist.popleft()

        # 히스토리를 numpy 배열로 변환
        pts = np.asarray([(hx, hy) for (_, hx, hy) in self.hist])
        if pts.shape[0] < 2:
            self.debug.clear()
            return x, y

        try:
            # 2D 가우시안 커널 밀도 추정
            kde = gaussian_kde(pts.T)
            # 그리드에서 KDE 값 계산
            xi, yi = np.mgrid[
                0 : self.sw : complex(self.grid[0]),
                0 : self.sh : complex(self.grid[1]),
            ]
            zi = kde(np.vstack([xi.ravel(), yi.ravel()])).reshape(xi.shape).T

            # 누적 분포 함수(CDF)로 신뢰도 임계값 계산
            flat = zi.ravel()
            idx = np.argsort(flat)[::-1]  # 내림차순 정렬
            cdf = np.cumsum(flat[idx]) / flat.sum()  # 누적 확률 계산
            thr = flat[idx[np.searchsorted(cdf, self.conf)]]  # 임계값 결정

            # 임계값 이상인 영역 마스크 생성
            mask = (zi >= thr).astype(np.uint8)
            # 마스크를 화면 크기로 리사이징
            mask = cv2.resize(mask, (self.sw, self.sh))

            # 신뢰 영역의 윤곽선 추출 (디버그용)
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            self.debug["mask"] = mask
            self.debug["contours"] = contours

            # 신뢰 영역 내 시선 위치들의 평균을 반환
            sx, sy = pts.mean(axis=0).astype(int)
            return int(sx), int(sy)

        except np.linalg.LinAlgError:
            # KDE 계산 실패 시 원본값 반환
            self.debug.clear()
            return x, y
