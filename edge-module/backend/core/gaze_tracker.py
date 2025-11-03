"""Gaze tracking wrapper for web application."""
from __future__ import annotations

import asyncio
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from model.gaze import GazeEstimator
from model.filters import NoSmoother


class WebGazeTracker:
    """Async wrapper for gaze estimation suitable for web streaming."""
    
    def __init__(
        self,
        camera_index: int = 0,
        model_name: str = "ridge",
        filter_method: str = "noop",
        screen_size: Tuple[int, int] = (1024, 600)
    ):
        self.camera_index = camera_index
        self.model_name = model_name
        self.filter_method = filter_method
        self.screen_size = screen_size
        
        self.gaze_estimator = GazeEstimator(model_name=model_name)
        self.cap: Optional[cv2.VideoCapture] = None
        self.smoother = None
        self.is_running = False
        self.current_gaze: Optional[Tuple[int, int]] = None
        self.raw_gaze: Optional[Tuple[int, int]] = None
        self.current_blink = False
        self.calibrated = False
        self._lock = asyncio.Lock()
        
        # 👁️ 눈깜빡임 추적 (1초 이상 = 클릭 인식)
        self.blink_start_time: Optional[float] = None
        self.blink_duration: float = 0.0
        self.prolonged_blink_triggered: bool = False
        self.PROLONGED_BLINK_DURATION = 1.0  # 👁️ 1초 이상 눈깜빡임 = 클릭
        
    async def initialize(self):
        """기능: 카메라 및 필터 초기화.
        
        args: 없음
        return: 없음
        """
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_index}")
        
        # ⭐ Kalman 필터 활성화 (노이즈 제거, 안정성 향상)
        if self.filter_method == "kalman":
            from model.filters import KalmanSmoother
            self.smoother = KalmanSmoother(
                process_noise=0.001,      # 낮음 = 더 안정적 (덜 민감)
                measurement_noise=10.0    # 높음 = 노이즈 제거 강화
            )
            print(f"[GazeTracker] Initialized with Kalman filter (high stability)")
        else:
            self.smoother = NoSmoother()
            print(f"[GazeTracker] Initialized with NoOp filter (no smoothing)")

            
    def load_calibration(self, model_path: str):
        """기능: 캘리브레이션 모델 로드.
        
        args: model_path
        return: 없음
        """
        self.gaze_estimator.load_model(model_path)
        self.calibrated = True
        
    def save_calibration(self, model_path: str):
        """기능: 캘리브레이션 모델 저장.
        
        args: model_path
        return: 없음
        """
        self.gaze_estimator.save_model(model_path)
    
    # ⭐ Kalman 필터 튜닝 제거됨 (NoOp 필터 사용)
    # tune_kalman_filter(), get_kalman_params(), set_kalman_measurement_noise() 
    # 메서드들은 필터링이 비활성화되어 있으므로 필요 없음
    
    async def start_tracking(self):
        """기능: 시선 추적 시작.
        
        args: 없음
        return: 없음 (연속 프레임 처리)
        """
        self.is_running = True
        while self.is_running:
            await self._process_frame()
            await asyncio.sleep(0.016)  # ~60 FPS
            
    async def _process_frame(self):
        """기능: 단일 프레임 처리 및 시선 추정.
        
        args: 없음
        return: 없음
        """
        if self.cap is None:
            return
            
        ret, frame = self.cap.read()
        if not ret:
            return
            
        # Extract features and detect blink
        features, blink_detected = self.gaze_estimator.extract_features(frame)
        
        async with self._lock:
            # 👁️ 눈깜빡임 추적 로직
            if blink_detected:
                # 눈깜빡임 시작
                if self.blink_start_time is None:
                    self.blink_start_time = time.time()
                    self.prolonged_blink_triggered = False
                    print("[GazeTracker] Blink detected - starting timer")
                
                # 눈깜빡임 지속 시간 계산
                self.blink_duration = time.time() - self.blink_start_time
                
                # 0.5초 이상 눈깜빡임 감지
                if self.blink_duration >= self.PROLONGED_BLINK_DURATION and not self.prolonged_blink_triggered:
                    self.prolonged_blink_triggered = True
                    print(f"[GazeTracker] PROLONGED BLINK DETECTED: {self.blink_duration:.2f}s - Click triggered!")
            else:
                # 눈깜빡임 종료
                if self.blink_start_time is not None:
                    self.blink_duration = time.time() - self.blink_start_time
                    print(f"[GazeTracker] Blink ended: duration {self.blink_duration:.2f}s (threshold: {self.PROLONGED_BLINK_DURATION}s)")
                
                self.blink_start_time = None
                self.prolonged_blink_triggered = False
            
            self.current_blink = blink_detected
            
            if features is not None and not blink_detected and self.calibrated:
                # Predict gaze point
                gaze_point = self.gaze_estimator.predict(np.array([features]))[0]
                x, y = map(int, gaze_point)
                self.raw_gaze = (x, y)
                
                # Apply smoothing
                x_pred, y_pred = self.smoother.step(x, y)
                self.current_gaze = (x_pred, y_pred)
            elif self.current_gaze is None:
                # Initialize with screen center if no gaze yet
                self.current_gaze = (self.screen_size[0] // 2, self.screen_size[1] // 2)
                self.raw_gaze = self.current_gaze
                
    def get_current_state(self) -> dict:
        """기능: 현재 시선 상태 조회.
        
        args: 없음
        return: 현재 상태 (gaze, raw_gaze, blink, blink_duration, prolonged_blink, calibrated, timestamp)
        """
        return {
            "gaze": self.current_gaze,
            "raw_gaze": self.raw_gaze,
            "blink": self.current_blink,
            "blink_duration": self.blink_duration,
            "prolonged_blink": self.prolonged_blink_triggered,  # 👁️ 0.5초 이상 눈깜빡임 = 클릭
            "calibrated": self.calibrated,
            "timestamp": time.time()
        }
            
    async def stop_tracking(self):
        """기능: 시선 추적 중지.
        
        args: 없음
        return: 없음
        """
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
            
    def __del__(self):
        """Cleanup on deletion."""
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
