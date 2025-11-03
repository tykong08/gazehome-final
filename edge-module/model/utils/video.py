"""
비디오 처리 유틸리티

카메라 캡처, 전체화면 윈도우, 프레임 반복 등
context manager 기반의 리소스 관리 유틸리티
"""

from __future__ import annotations

from contextlib import contextmanager

import cv2


@contextmanager
def fullscreen(name: str):
    """
    전체화면 모드 윈도우 생성 및 정리
    
    with 문과 함께 사용하여 자동으로 윈도우를 생성하고 닫습니다.
    
    Args:
        name (str): 윈도우 이름
    
    Example:
        with fullscreen("Demo") as win:
            cv2.imshow("Demo", frame)
            cv2.waitKey(1)
    """
    cv2.namedWindow(name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    try:
        yield
    finally:
        cv2.destroyWindow(name)


@contextmanager
def camera(index: int = 0):
    """
    카메라 캡처 열기 및 정리
    
    with 문과 함께 사용하여 자동으로 카메라를 열고 닫습니다.
    
    Args:
        index (int): 카메라 인덱스 (기본값: 0 = 기본 카메라)
    
    Raises:
        RuntimeError: 카메라를 열 수 없는 경우
    
    Example:
        with camera() as cap:
            ret, frame = cap.read()
    """
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open camera {index}")
    try:
        yield cap
    finally:
        cap.release()


def iter_frames(cap: cv2.VideoCapture):
    """
    카메라에서 연속 프레임을 반환하는 무한 생성기
    
    읽기에 실패한 프레임은 건너뛰고 계속합니다.
    
    Args:
        cap (cv2.VideoCapture): 비디오 캡처 객체
    
    Yields:
        프레임 (numpy 배열)
    
    Example:
        with camera() as cap:
            for frame in iter_frames(cap):
                cv2.imshow("Video", frame)
                if cv2.waitKey(1) == 27:
                    break
    """
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        yield frame
