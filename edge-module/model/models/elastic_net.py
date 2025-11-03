"""
엘라스틱 넷 회귀 모델

L1 + L2 정규화 결합 모델
릿지와 라쏘의 장점을 결합한 선형 회귀 모델
"""

from __future__ import annotations

from sklearn.linear_model import ElasticNet

from . import register_model
from .base import BaseModel


class ElasticNetModel(BaseModel):
    """
    ElasticNet 회귀를 사용한 시선 위치 예측 모델
    
    L1 (라쏘) + L2 (릿지) 정규화를 결합하여
    특성 선택과 과적합 방지를 동시에 수행합니다.
    """

    def __init__(self, *, alpha: float = 1.0, l1_ratio: float = 0.5) -> None:
        """
        ElasticNet 모델 초기화
        
        Args:
            alpha (float): 정규화 강도 (기본값: 1.0)
                          값이 클수록 정규화가 강함
            l1_ratio (float): L1/L2 정규화 비율 (기본값: 0.5)
                             0 = 순수 L2 (릿지), 1 = 순수 L1 (라쏘)
        """
        super().__init__()
        self._init_native(alpha=alpha, l1_ratio=l1_ratio)

    def _init_native(self, **kw):
        """scikit-learn ElasticNet 모델 생성"""
        self.model = ElasticNet(**kw)

    def _native_train(self, X, y):
        """모델 훈련"""
        self.model.fit(X, y)

    def _native_predict(self, X):
        """시선 위치 예측"""
        return self.model.predict(X)


# 모델 레지스트리에 등록
register_model("elastic_net", ElasticNetModel)
