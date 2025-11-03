"""
릿지 회귀 모델

L2 정규화를 사용한 선형 회귀 모델
시선 위치 예측용 가벼운 모델
"""

from __future__ import annotations

from sklearn.linear_model import Ridge

from . import register_model
from .base import BaseModel


class RidgeModel(BaseModel):
    """
    Ridge 회귀를 사용한 시선 위치 예측 모델
    
    Ridge 회귀는 L2 정규화를 통해 과적합을 방지하는
    간단하면서도 효과적인 선형 모델입니다.
    """

    def __init__(self, alpha: float = 1.0) -> None:
        """
        Ridge 모델 초기화
        
        Args:
            alpha (float): 정규화 강도 (기본값: 1.0)
                          값이 클수록 정규화가 강함
        """
        super().__init__()
        self._init_native(alpha=alpha)

    def _init_native(self, **kw):
        """scikit-learn Ridge 모델 생성"""
        self.model = Ridge(**kw)

    def _native_train(self, X, y):
        """모델 훈련"""
        self.model.fit(X, y)

    def _native_predict(self, X):
        """시선 위치 예측"""
        return self.model.predict(X)


# 모델 레지스트리에 등록
register_model("ridge", RidgeModel)
