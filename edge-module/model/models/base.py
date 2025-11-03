"""
시선 예측 모델 기본 클래스

모든 회귀 모델이 구현해야 하는 공통 인터페이스 정의
"""

from __future__ import annotations

import pickle
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
from sklearn.preprocessing import StandardScaler


class BaseModel(ABC):
    """
    모든 시선 예측 모델이 구현해야 하는 추상 기본 클래스
    
    특징: 자동 특징 스케일링, 저장/로드, 다양한 회귀 모델 지원
    """

    def __init__(self) -> None:
        """
        기본 모델 초기화
        
        Attributes:
            scaler (StandardScaler): 특징 정규화용 스케일러
                                    입력 특징을 표준정규분포로 변환
            variable_scaling (np.ndarray | None): 특징별 가변 스케일링 계수
        """
        self.scaler = StandardScaler()

    @abstractmethod
    def _init_native(self, **kwargs):
        """
        네이티브 모델 구현 초기화 (서브클래스에서 구현 필수)
        
        예: scikit-learn 모델 생성, 하이퍼파라미터 설정
        """
        ...

    @abstractmethod
    def _native_train(self, X: np.ndarray, y: np.ndarray):
        """
        네이티브 모델 훈련 (서브클래스에서 구현 필수)
        
        Args:
            X (np.ndarray): 정규화된 입력 특징 (N x D)
            y (np.ndarray): 타겟 값 (N x 2) - 시선 위치
        """
        ...

    @abstractmethod
    def _native_predict(self, X: np.ndarray) -> np.ndarray:
        """
        네이티브 모델로 예측 (서브클래스에서 구현 필수)
        
        Args:
            X (np.ndarray): 정규화된 입력 특징 (N x D 또는 D)
        
        Returns:
            np.ndarray: 예측된 시선 위치 (N x 2 또는 2)
        """
        ...

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        variable_scaling: np.ndarray | None = None,
    ) -> None:
        """
        공개 훈련 인터페이스 (자동 정규화 포함)
        
        Args:
            X (np.ndarray): 입력 특징 (N x D)
            y (np.ndarray): 타겟 값 (N x 2) - 시선 위치
            variable_scaling (np.ndarray | None): 특징별 가변 스케일링 계수
                                                 None이면 사용 안함
        """
        self.variable_scaling = variable_scaling
        # 특징 정규화 (평균=0, 표준편차=1)
        Xs = self.scaler.fit_transform(X)
        # 가변 스케일링 적용 (있으면)
        if variable_scaling is not None:
            Xs *= variable_scaling
        # 네이티브 모델 훈련
        self._native_train(Xs, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        공개 예측 인터페이스 (자동 정규화 포함)
        
        Args:
            X (np.ndarray): 입력 특징 (N x D 또는 D)
        
        Returns:
            np.ndarray: 예측된 시선 위치 (N x 2 또는 2)
        """
        # 입력 특징 정규화 (훈련 때의 통계 사용)
        Xs = self.scaler.transform(X)
        # 가변 스케일링 적용 (훈련 때 설정되었으면)
        if getattr(self, "variable_scaling", None) is not None:
            Xs *= self.variable_scaling
        # 네이티브 모델로 예측
        return self._native_predict(Xs)

    def save(self, path: str | Path) -> None:
        """
        학습된 모델을 파일에 저장합니다 (Pickle 포맷)
        
        Args:
            path (str | Path): 저장할 파일 경로
        """
        with Path(path).open("wb") as fh:
            pickle.dump(self, fh)

    @classmethod
    def load(cls, path: str | Path) -> "BaseModel":
        """
        저장된 모델을 파일에서 불러옵니다
        
        Args:
            path (str | Path): 저장된 모델 파일 경로
        
        Returns:
            BaseModel: 로드된 모델 인스턴스
        """
        with Path(path).open("rb") as fh:
            return pickle.load(fh)
