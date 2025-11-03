"""
칼만 필터 스무더 모듈

cv2.KalmanFilter를 래핑한 시선 위치 스무딩 필터
"""

from __future__ import annotations

import time
from typing import Callable, Optional, Tuple

import cv2
import numpy as np

from model.utils.screen import get_screen_size

from . import make_kalman
from .base import BaseSmoother


class KalmanSmoother(BaseSmoother):
    """
    칼만 필터를 사용한 시선 위치 스무더
    
    시선 추적의 노이즈를 제거하고 움직임을 예측하여
    더 부드러운 시선 위치 시퀀스를 생성합니다.
    """

    def __init__(self, kf=None) -> None:
        """
        칼만 필터 스무더 초기화
        
        Args:
            kf (cv2.KalmanFilter | None): 기존 칼만 필터 인스턴스
                                          None이면 기본값으로 생성
        """
        super().__init__()

        try:
            import cv2

            self.kf = kf if isinstance(kf, cv2.KalmanFilter) else make_kalman()
        except ImportError:
            self.kf = make_kalman()

    def step(self, x: int, y: int) -> Tuple[int, int]:
        """
        한 프레임의 시선 위치를 필터링합니다.
        
        Args:
            x (int): 측정된 X 좌표 (필터링 전)
            y (int): 측정된 Y 좌표 (필터링 전)
        
        Returns:
            Tuple[int, int]: 필터링된 (x, y) 좌표
        """
        # 측정값 벡터 생성
        meas = np.array([[float(x)], [float(y)]], dtype=np.float32)

        # 첫 측정값인 경우 칼만 필터 상태 초기화
        if not np.any(self.kf.statePost):
            self.kf.statePre[:2] = meas
            self.kf.statePost[:2] = meas

        # 다음 상태 예측
        pred = self.kf.predict()
        # 측정값 기반으로 예측값 보정
        self.kf.correct(meas)

        return int(pred[0, 0]), int(pred[1, 0])

    def tune(
        self,
        gaze_estimator,
        *,
        camera_index: int = 0,
        capture: Optional["cv2.VideoCapture"] = None,
        display_callback: Optional[Callable[[np.ndarray], None]] = None,
        abort_callback: Optional[Callable[[], bool]] = None,
        event_callback: Optional[Callable[[], None]] = None,
    ):
        """
        칼만 필터의 측정 노이즈 공분산을 자동으로 조정합니다.
        
        사용자가 세 개의 화면 위치를 봄으로써 칼만 필터를
        실시간 환경에 맞게 보정합니다.
        
        Args:
            gaze_estimator: 시선 위치를 추출하는 GazeEstimator 인스턴스
            camera_index (int): 웹캠 인덱스 (기본값: 0)
            capture (cv2.VideoCapture | None): 기존 비디오 캡처 객체
                                               None이면 새로 생성
            display_callback (Callable | None): 화면 업데이트 콜백
                                                None이면 OpenCV 윈도우 사용
            abort_callback (Callable | None): 중단 여부 확인 콜백
            event_callback (Callable | None): 이벤트 처리 콜백
        """

        screen_width, screen_height = get_screen_size()

        # 캘리브레이션 포인트: 화면의 세 위치
        points_tpl = [
            (screen_width // 2, screen_height // 4),           # 상단 중앙
            (screen_width // 4, 3 * screen_height // 4),      # 좌측 하단
            (3 * screen_width // 4, 3 * screen_height // 4),  # 우측 하단
        ]

        # 각 포인트의 상태 추적
        points = [
            dict(
                position=pos,
                start_time=None,
                data_collection_started=False,
                collection_start_time=None,
                collected_gaze=[],
            )
            for pos in points_tpl
        ]

        # 시선이 포인트 근처에 있는지 판단하는 거리 임계값
        proximity_threshold = screen_width / 5
        # 사용자가 포인트를 봐야 하는 초기 지연 시간 (초)
        initial_delay = 0.5
        # 각 포인트에서 데이터를 수집하는 시간 (초)
        data_collection_duration = 0.5

        # 카메라 캡처 객체 관리
        owns_capture = capture is None
        if owns_capture:
            cap = cv2.VideoCapture(camera_index)
        else:
            cap = capture

        # 디스플레이 윈도우 생성
        if display_callback is None:
            cv2.namedWindow("Fine Tuning", cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty(
                "Fine Tuning", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
            )

        gaze_positions = []
        aborted = False

        # 모든 포인트가 수집될 때까지 반복
        while points:
            if abort_callback is not None and abort_callback():
                aborted = True
                break
            if event_callback is not None:
                event_callback()

            ret, frame = cap.read()
            if not ret:
                continue

            # 프레임에서 시선 특징 추출
            features, blink_detected = gaze_estimator.extract_features(frame)
            # 검은 배경 캔버스 생성
            canvas = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)

            # 모든 포인트를 녹색 원으로 그리기
            for point in points:
                cv2.circle(canvas, point["position"], 20, (0, 255, 0), -1)

            # 안내 텍스트 추가
            font = cv2.FONT_HERSHEY_SIMPLEX
            text = "Look at the points until they disappear"
            size, _ = cv2.getTextSize(text, font, 1.5, 2)
            cv2.putText(
                canvas,
                text,
                ((screen_width - size[0]) // 2, screen_height - 50),
                font,
                1.5,
                (255, 255, 255),
                2,
            )

            now = time.time()

            # 유효한 시선 데이터가 있으면 처리
            if features is not None and not blink_detected:
                # 시선 위치 예측
                gaze_point = gaze_estimator.predict(np.array([features]))[0]
                gaze_x, gaze_y = map(int, gaze_point)
                # 예측된 시선 위치를 파란 원으로 표시
                cv2.circle(canvas, (gaze_x, gaze_y), 10, (255, 0, 0), -1)

                # 각 포인트에 대해 시선 위치 확인
                for point in points[:]:
                    dx, dy = (
                        gaze_x - point["position"][0],
                        gaze_y - point["position"][1],
                    )
                    distance = np.hypot(dx, dy)
                    
                    if distance <= proximity_threshold:
                        # 시선이 포인트 근처에 있음
                        if point["start_time"] is None:
                            point["start_time"] = now
                        elapsed = now - point["start_time"]

                        # 초기 지연 시간 이후 데이터 수집 시작
                        if (
                            not point["data_collection_started"]
                            and elapsed >= initial_delay
                        ):
                            point["data_collection_started"] = True
                            point["collection_start_time"] = now

                        # 데이터 수집 중
                        if point["data_collection_started"]:
                            data_elapsed = now - point["collection_start_time"]
                            # 시선 위치 기록
                            point["collected_gaze"].append([gaze_x, gaze_y])
                            # 포인트 흔들림 (진행 상황 시각화)
                            shake = int(
                                5 + (data_elapsed / data_collection_duration) * 20
                            )
                            shaken = (
                                point["position"][0]
                                + int(np.random.uniform(-shake, shake)),
                                point["position"][1]
                                + int(np.random.uniform(-shake, shake)),
                            )
                            cv2.circle(canvas, shaken, 20, (0, 255, 0), -1)
                            # 데이터 수집 완료
                            if data_elapsed >= data_collection_duration:
                                gaze_positions.extend(point["collected_gaze"])
                                points.remove(point)
                        else:
                            # 초기 지연 중 포인트를 청색으로 표시
                            cv2.circle(canvas, point["position"], 25, (0, 255, 255), 2)
                    else:
                        # 시선이 포인트에서 벗어남 - 상태 리셋
                        point.update(
                            start_time=None,
                            data_collection_started=False,
                            collection_start_time=None,
                            collected_gaze=[],
                        )

            # 캔버스 표시
            if display_callback is not None:
                display_callback(canvas)
            else:
                cv2.imshow("Fine Tuning", canvas)
                # ESC 키로 중단 가능
                if cv2.waitKey(1) == 27:
                    aborted = True
                    break

        # 리소스 정리
        if owns_capture:
            cap.release()
        if display_callback is None:
            cv2.destroyWindow("Fine Tuning")

        # 중단된 경우 반환
        if aborted:
            return

        # 수집된 데이터로 측정 노이즈 공분산 계산
        gaze_positions = np.array(gaze_positions)
        if gaze_positions.shape[0] < 2:
            return

        # 분산 계산 및 칼만 필터 업데이트
        var = np.var(gaze_positions, axis=0)
        var[var == 0] = 1e-4
        self.kf.measurementNoiseCov = np.array(
            [[var[0], 0], [0, var[1]]], dtype=np.float32
        )
