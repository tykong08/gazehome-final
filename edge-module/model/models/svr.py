"""
선형 서포트 벡터 회귀 모델

SVM 기반의 비선형 시선 위치 예측
복잡한 시선-화면 매핑 관계 모델링 가능
"""

from __future__ import annotations

import numpy as np
from sklearn.svm import LinearSVR

from . import register_model
from .base import BaseModel


class LinearSVRModel(BaseModel):
    """
    LinearSVR을 사용한 시선 위치 예측 모델
    
    Support Vector Regression (SVR)는 비선형 데이터 관계를 
    효과적으로 모델링할 수 있습니다.
    X, Y 좌표를 별도의 SVR 모델로 학습합니다.
    """

    def __init__(
        self,
        *,
        C: float = 5.0,
        epsilon: float = 5.0,
        loss: str = "epsilon_insensitive",
        fit_intercept: bool = True,
    ) -> None:
        """
        LinearSVR 모델 초기화
        
        Args:
            C (float): 정규화 파라미터 (기본값: 5.0)
                      값이 클수록 훈련 데이터에 더 정확함
            epsilon (float): 오차 여유 (기본값: 5.0)
                           이 범위 내의 오차는 무시
            loss (str): 손실 함수 (기본값: "epsilon_insensitive")
            fit_intercept (bool): 절편 학습 여부 (기본값: True)
        """
        super().__init__()
        self._init_native(
            C=C,
            epsilon=epsilon,
            loss=loss,
            fit_intercept=fit_intercept,
        )

    def _init_native(self, **kwargs):
        """LinearSVR 모델 템플릿 생성 (X, Y 좌표용으로 복사됨)"""
        self._template = LinearSVR(**kwargs)

    def _native_train(self, X: np.ndarray, y: np.ndarray):
        """
        X, Y 좌표를 각각 별도의 SVR 모델로 훈련합니다
        
        Args:
            X (np.ndarray): 입력 특징 (N x D)
            y (np.ndarray): 시선 위치 (N x 2)
        """
        y = y.reshape(-1, 2)

        # X 좌표 예측용 SVR 모델
        self.model_x = LinearSVR(**self._template.get_params())
        # Y 좌표 예측용 SVR 모델
        self.model_y = LinearSVR(**self._template.get_params())

        # X 좌표 훈련
        self.model_x.fit(X, y[:, 0])
        # Y 좌표 훈련
        self.model_y.fit(X, y[:, 1])

    def _native_predict(self, X: np.ndarray) -> np.ndarray:
        """
        X, Y 좌표를 각각 예측하고 병합합니다
        
        Args:
            X (np.ndarray): 입력 특징 (N x D 또는 D)
        
        Returns:
            np.ndarray: 예측된 시선 위치 (N x 2 또는 2)
        """
        x_pred = self.model_x.predict(X)
        y_pred = self.model_y.predict(X)
        return np.column_stack((x_pred, y_pred))


# 모델 레지스트리에 등록
register_model("linear_svr", LinearSVRModel)
register_model("svr", LinearSVRModel)  # 기본 별칭
