"""
캘리브레이션 공통 유틸리티

모든 캘리브레이션 방식에서 사용되는 공유 함수들
"""

import time

import cv2
import numpy as np


def compute_grid_points(order, sw: int, sh: int, margin_ratio: float = 0.10):
    """
    격자 (행, 열) 인덱스를 절대 픽셀 위치로 변환합니다.
    
    화면 가장자리에 마진을 둔 상태로 포인트들을 배치합니다.
    
    Args:
        order (list): (행, 열) 튜플의 리스트
                     예: [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)]
        sw (int): 화면 너비 (픽셀)
        sh (int): 화면 높이 (픽셀)
        margin_ratio (float): 화면 가장자리 마진 비율 (기본값: 0.10 = 10%)
    
    Returns:
        list: (x, y) 픽셀 좌표의 리스트
    """
    if not order:
        return []

    # 격자의 최대 행, 열 계산
    max_r = max(r for r, _ in order)
    max_c = max(c for _, c in order)

    # 마진 계산
    mx, my = int(sw * margin_ratio), int(sh * margin_ratio)
    gw, gh = sw - 2 * mx, sh - 2 * my

    # 각 칸의 크기 계산
    step_x = 0 if max_c == 0 else gw / max_c
    step_y = 0 if max_r == 0 else gh / max_r

    # 픽셀 좌표로 변환
    return [(mx + int(c * step_x), my + int(r * step_y)) for r, c in order]


def wait_for_face_and_countdown(cap, gaze_estimator, sw, sh, dur: int = 2) -> bool:
    """
    얼굴이 감지되고 깜빡임이 없을 때까지 대기한 후 카운트다운을 표시합니다.
    
    사용자가 카메라를 보도록 대기하고, 준비가 되면 카운트다운 시작.
    ESC 키로 캔슬 가능.
    
    Args:
        cap (cv2.VideoCapture): 비디오 캡처 객체
        gaze_estimator: 시선 특징 추출기
        sw (int): 화면 너비
        sh (int): 화면 높이
        dur (int): 카운트다운 시간 (초, 기본값: 2)
    
    Returns:
        bool: 카운트다운 완료 (True), 캔슬됨 (False)
    """
    cv2.namedWindow("Calibration", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Calibration", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    fd_start = None
    countdown = False
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        # 얼굴과 깜빡임 감지
        f, blink = gaze_estimator.extract_features(frame)
        face = f is not None and not blink
        canvas = np.zeros((sh, sw, 3), dtype=np.uint8)
        now = time.time()
        
        if face:
            # 얼굴이 감지됨 - 카운트다운 시작
            if not countdown:
                fd_start = now
                countdown = True
            elapsed = now - fd_start
            
            if elapsed >= dur:
                # 카운트다운 완료
                return True
            
            # 부드러운 카운트다운 이징
            t = elapsed / dur
            e = t * t * (3 - 2 * t)  # 스무딩 이징
            ang = 360 * (1 - e)
            # 원호로 진행 상황 표시
            cv2.ellipse(
                canvas,
                (sw // 2, sh // 2),
                (50, 50),
                0,
                -90,
                -90 + ang,
                (0, 255, 0),
                -1,
            )
        else:
            # 얼굴이 감지되지 않음
            countdown = False
            fd_start = None
            txt = "Face not detected"
            fs = 2
            thick = 3
            size, _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, fs, thick)
            tx = (sw - size[0]) // 2
            ty = (sh + size[1]) // 2
            cv2.putText(
                canvas, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 255), thick
            )
        cv2.imshow("Calibration", canvas)
        if cv2.waitKey(1) == 27:
            # ESC 키로 캔슬
            return False


def _pulse_and_capture(
    gaze_estimator,
    cap,
    pts,
    sw: int,
    sh: int,
    pulse_d: float = 1.0,
    cd_d: float = 1.0,
):
    """
    각 캘리브레이션 포인트에서 공유되는 수행-캡처 루프
    
    1. 포인트에서 대상을 맥박처럼 움직임 (펄스 단계)
    2. 사용자의 시선이 포인트를 따라올 때까지 대기하고 데이터 수집 (캡처 단계)
    
    Args:
        gaze_estimator: 시선 특징 추출기
        cap (cv2.VideoCapture): 비디오 캡처 객체
        pts (list): (x, y) 포인트 리스트
        sw (int): 화면 너비
        sh (int): 화면 높이
        pulse_d (float): 펄스 지속 시간 (초, 기본값: 1.0)
        cd_d (float): 캡처 지속 시간 (초, 기본값: 1.0)
    
    Returns:
        tuple | None: (특징 리스트, 타겟 좌표 리스트) 또는 캔슬 시 None
    """
    feats, targs = [], []

    for x, y in pts:
        # === 펄스 단계 ===
        # 포인트가 주기적으로 커졌다 작아졌다를 반복
        ps = time.time()
        final_radius = 20
        while True:
            e = time.time() - ps
            if e > pulse_d:
                break
            ok, frame = cap.read()
            if not ok:
                continue
            canvas = np.zeros((sh, sw, 3), dtype=np.uint8)
            # 사인파 사용해서 부드럽게 크기 변화
            radius = 15 + int(15 * abs(np.sin(2 * np.pi * e)))
            final_radius = radius
            cv2.circle(canvas, (x, y), radius, (0, 255, 0), -1)
            cv2.imshow("Calibration", canvas)
            if cv2.waitKey(1) == 27:
                # ESC 키로 캔슬
                return None
        
        # === 캡처 단계 ===
        # 포인트가 고정되고 카운트다운 진행
        cs = time.time()
        while True:
            e = time.time() - cs
            if e > cd_d:
                break
            ok, frame = cap.read()
            if not ok:
                continue
            canvas = np.zeros((sh, sw, 3), dtype=np.uint8)
            # 포인트 표시
            cv2.circle(canvas, (x, y), final_radius, (0, 255, 0), -1)
            # 진행 원호 표시
            t = e / cd_d
            ease = t * t * (3 - 2 * t)  # 스무딩 이징
            ang = 360 * (1 - ease)
            cv2.ellipse(canvas, (x, y), (40, 40), 0, -90, -90 + ang, (255, 255, 255), 4)
            cv2.imshow("Calibration", canvas)
            if cv2.waitKey(1) == 27:
                # ESC 키로 캔슬
                return None
            # 시선 데이터 수집 (깜빡이지 않을 때만)
            ft, blink = gaze_estimator.extract_features(frame)
            if ft is not None and not blink:
                feats.append(ft)
                targs.append([x, y])

    return feats, targs
