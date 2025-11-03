from __future__ import annotations

import pickle
from collections import deque
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from model.constants import LEFT_EYE_INDICES, MUTUAL_INDICES, RIGHT_EYE_INDICES
from model.models import BaseModel, create_model


class GazeEstimator:
    """
    시선 추적 추정기
    - MediaPipe를 사용한 얼굴 특징점 감지
    - 눈 영역의 특징점 추출 및 정규화
    - 깜빡임 감지 (Eye Aspect Ratio 기반)
    - 머신러닝 모델을 통한 시선 위치 예측
    """
    def __init__(
        self,
        model_name: str = "ridge",
        model_kwargs: dict | None = None,
        ear_history_len: int = 50,
        blink_threshold_ratio: float = 0.8,
        min_history: int = 15,
    ):
        """
        GazeEstimator 초기화
        
        @param model_name: 시선 추적 모델명 (ridge, svr, mlp 등)
        @param model_kwargs: 모델에 전달할 추가 인자
        @param ear_history_len: Eye Aspect Ratio 히스토리 길이
        @param blink_threshold_ratio: 깜빡임 감지 임계값
        @param min_history: 깜빡임 감지를 위한 최소 히스토리
        """
        # MediaPipe 얼굴 메시 감지기 초기화
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )
        # 시선 추적 모델 생성
        self.model: BaseModel = create_model(model_name, **(model_kwargs or {}))

        # 깜빡임 감지를 위한 EAR 히스토리
        self._ear_history = deque(maxlen=ear_history_len)
        self._blink_ratio = blink_threshold_ratio
        self._min_history = min_history

    def extract_features(self, image):
        """
        이미지에서 얼굴 특징점을 추출하고 정규화된 눈 영역 특징점 반환
        
        정규화 프로세스:
        1. 콧대(nose tip)를 기준점으로 설정
        2. 얼굴의 3D 좌표계 구성 (X: 양쪽 눈 방향, Y: 수직 방향, Z: 깊이 방향)
        3. 모든 포인트를 이 좌표계로 회전 및 스케일링
        4. 눈 사이 거리로 정규화
        5. 깜빡임 감지 (Eye Aspect Ratio 계산)
        
        @param image: 입력 이미지 (BGR 포맷)
        @return: (특징 벡터, 깜빡임 여부) 튜플, 또는 (None, False) 얼굴 미감지 시
        """
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(image_rgb)

        # 얼굴이 감지되지 않으면 반환
        if not results.multi_face_landmarks:
            return None, False

        face_landmarks = results.multi_face_landmarks[0]
        landmarks = face_landmarks.landmark

        # 모든 얼굴 포인트를 3D 좌표 배열로 변환
        all_points = np.array(
            [(lm.x, lm.y, lm.z) for lm in landmarks], dtype=np.float32
        )
        
        # 콧대를 기준점으로 설정
        nose_anchor = all_points[4]
        # 왼쪽 눈 모서리와 오른쪽 눈 모서리로 X축 구성
        left_corner = all_points[33]
        right_corner = all_points[263]
        # 머리 위쪽으로 Y축 구성 (대략적)
        top_of_head = all_points[10]

        # 모든 포인트를 콧대 기준으로 이동
        shifted_points = all_points - nose_anchor
        # X축 정규화 (양쪽 눈 방향)
        x_axis = right_corner - left_corner
        x_axis /= np.linalg.norm(x_axis) + 1e-9
        # Y축 정규화 (수직 방향)
        y_approx = top_of_head - nose_anchor
        y_approx /= np.linalg.norm(y_approx) + 1e-9
        # X축에 수직인 성분만 유지
        y_axis = y_approx - np.dot(y_approx, x_axis) * x_axis
        y_axis /= np.linalg.norm(y_axis) + 1e-9
        # Z축은 X와 Y의 외적 (깊이 방향)
        z_axis = np.cross(x_axis, y_axis)
        z_axis /= np.linalg.norm(z_axis) + 1e-9
        # 회전 행렬 구성
        R = np.column_stack((x_axis, y_axis, z_axis))
        # 모든 포인트를 새로운 좌표계로 회전
        rotated_points = (R.T @ shifted_points.T).T

        # 눈 사이 거리로 정규화
        left_corner_rot = R.T @ (left_corner - nose_anchor)
        right_corner_rot = R.T @ (right_corner - nose_anchor)
        inter_eye_dist = np.linalg.norm(right_corner_rot - left_corner_rot)
        if inter_eye_dist > 1e-7:
            rotated_points /= inter_eye_dist

        # 눈 영역 특징점 추출
        subset_indices = LEFT_EYE_INDICES + RIGHT_EYE_INDICES + MUTUAL_INDICES
        eye_landmarks = rotated_points[subset_indices]
        features = eye_landmarks.flatten()

        # 머리 자세 (Yaw, Pitch, Roll) 계산
        yaw = np.arctan2(R[1, 0], R[0, 0])
        pitch = np.arctan2(-R[2, 0], np.sqrt(R[2, 1] ** 2 + R[2, 2] ** 2))
        roll = np.arctan2(R[2, 1], R[2, 2])
        features = np.concatenate([features, [yaw, pitch, roll]])

        # 깜빡임 감지 (Eye Aspect Ratio 기반)
        # 왼쪽 눈의 특정 포인트들
        left_eye_inner = np.array([landmarks[133].x, landmarks[133].y])
        left_eye_outer = np.array([landmarks[33].x, landmarks[33].y])
        left_eye_top = np.array([landmarks[159].x, landmarks[159].y])
        left_eye_bottom = np.array([landmarks[145].x, landmarks[145].y])

        # 오른쪽 눈의 특정 포인트들
        right_eye_inner = np.array([landmarks[362].x, landmarks[362].y])
        right_eye_outer = np.array([landmarks[263].x, landmarks[263].y])
        right_eye_top = np.array([landmarks[386].x, landmarks[386].y])
        right_eye_bottom = np.array([landmarks[374].x, landmarks[374].y])

        # Eye Aspect Ratio (EAR) 계산: 높이 / 너비
        left_eye_width = np.linalg.norm(left_eye_outer - left_eye_inner)
        left_eye_height = np.linalg.norm(left_eye_top - left_eye_bottom)
        left_EAR = left_eye_height / (left_eye_width + 1e-9)

        right_eye_width = np.linalg.norm(right_eye_outer - right_eye_inner)
        right_eye_height = np.linalg.norm(right_eye_top - right_eye_bottom)
        right_EAR = right_eye_height / (right_eye_width + 1e-9)

        # 양쪽 눈의 EAR 평균
        EAR = (left_EAR + right_EAR) / 2

        # EAR 히스토리 업데이트
        self._ear_history.append(EAR)
        # 충분한 히스토리가 있으면 동적 임계값 설정
        if len(self._ear_history) >= self._min_history:
            thr = float(np.mean(self._ear_history)) * self._blink_ratio
        else:
            thr = 0.2
        # 깜빡임 감지 여부
        blink_detected = EAR < thr

        return features, blink_detected

    def save_model(self, path):
        """
        학습된 시선 추적 모델을 파일에 저장합니다.
        
        Args:
            path (str): 모델을 저장할 파일 경로
        """
        # BaseModel의 save() 메서드 사용 (전체 모델 객체 저장)
        self.model.save(path)

    def load_model(self, path):
        """
        저장된 시선 추적 모델을 파일에서 불러옵니다.
        
        Args:
            path (str): 저장된 모델 파일 경로
        """
        # BaseModel의 load() 클래스 메서드 사용 (전체 모델 객체 로드)
        from model.models.base import BaseModel
        self.model = BaseModel.load(path)

    def train(self, X, y, variable_scaling=False):
        """
        시선 추적 모델을 훈련 데이터로 학습합니다.
        
        Args:
            X (np.ndarray): 특징 데이터 (N x D 배열, N=샘플수, D=특징수)
            y (np.ndarray): 시선 위치 레이블 (N x 2 배열, x, y 좌표)
            variable_scaling (bool): 동적 스케일링 사용 여부 (기본값: False)
        """
        if variable_scaling:
            # 특징 데이터의 표준편차로 스케일링
            X_std = np.std(X, axis=0)
            # 0으로 나누지 않도록 방지
            X_std[X_std == 0] = 1
            X_scaled = X / X_std
            self.model.train(X_scaled, y, variable_scaling=None)
        else:
            # 표준 스케일링 없이 직접 학습
            self.model.train(X, y)

    def predict(self, X):
        """
        입력 특징에 대한 시선 위치를 예측합니다.
        
        Args:
            X (np.ndarray): 특징 데이터 (N x D 배열 또는 1D 배열)
        
        Returns:
            np.ndarray: 예측된 시선 위치 (x, y 좌표)
        """
        return self.model.predict(X)
