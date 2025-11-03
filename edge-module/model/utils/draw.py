"""
화면 그리기 유틸리티

시선 커서, 썸네일 등을 그리는 함수들
"""

from __future__ import annotations

import cv2
import numpy as np


def draw_cursor(
    canvas,
    x: int,
    y: int,
    alpha: float,
    *,
    radius_outer: int = 30,
    radius_inner: int = 25,
    color_outer: tuple[int, int, int] = (0, 0, 255),
    color_inner: tuple[int, int, int] = (255, 255, 255),
):
    """
    시선 커서를 캔버스에 그립니다
    
    이중 원 구조로 시선 위치를 시각화합니다:
    - 외부 원: 빨강 (기본값)
    - 내부 원: 하양 (기본값)
    반투명하게 렌더링되어 배경이 보임
    
    Args:
        canvas: 그림을 그릴 numpy 배열 (이미지)
        x (int): X 좌표 (픽셀)
        y (int): Y 좌표 (픽셀)
        alpha (float): 불투명도 (0.0 ~ 1.0)
                      0 = 완전 투명 (그리지 않음)
                      1.0 = 완전 불투명
        radius_outer (int): 외부 원 반지름 (기본값: 30 픽셀)
        radius_inner (int): 내부 원 반지름 (기본값: 25 픽셀)
        color_outer (tuple): 외부 원 색상 BGR (기본값: 빨강)
        color_inner (tuple): 내부 원 색상 BGR (기본값: 하양)
    
    Returns:
        캔버스 (수정됨)
    """
    if alpha <= 0.0:
        return canvas

    # 오버레이 레이어 생성
    overlay = canvas.copy()
    # 외부 원 그리기
    cv2.circle(overlay, (int(x), int(y)), radius_outer, color_outer, -1)
    # 내부 원 그리기 (동공 표현)
    if radius_inner > 0:
        cv2.circle(overlay, (int(x), int(y)), radius_inner, color_inner, -1)

    # 오버레이와 원본 이미지 알파 블렌딩
    cv2.addWeighted(overlay, alpha * 0.6, canvas, 1 - alpha * 0.6, 0, canvas)
    return canvas


def make_thumbnail(
    frame,
    *,
    size: tuple[int, int] = (320, 240),
    border: int = 2,
    border_color: tuple[int, int, int] = (255, 255, 255),
):
    """
    프레임의 썸네일을 생성합니다
    
    화면 표시 또는 저장용으로 작은 크기의 이미지 생성
    선택적으로 보더(테두리) 추가 가능
    
    Args:
        frame: 입력 프레임 (numpy 배열)
        size (tuple): 썸네일 크기 (가로, 세로, 기본값: 320x240)
        border (int): 보더 두께 (픽셀, 기본값: 2)
        border_color (tuple): 보더 색상 BGR (기본값: 하양)
    
    Returns:
        thumbnail 이미지 (numpy 배열)
    """
    # 지정된 크기로 리사이징
    img = cv2.resize(frame, size)
    # 보더 추가
    return cv2.copyMakeBorder(
        img,
        border,
        border,
        border,
        border,
        cv2.BORDER_CONSTANT,
        value=border_color,
    )
