"""
작은 다층 퍼셉트론 모델

경량 신경망을 사용한 시선 위치 예측
선형 모델보다 복잡한 관계를 학습 가능
"""

from __future__ import annotations

from sklearn.neural_network import MLPRegressor

from . import register_model
from .base import BaseModel


class TinyMLPModel(BaseModel):
    """
    MLP (Multi-Layer Perceptron)를 사용한 시선 위치 예측 모델
    
    작은 신경망으로 선형 모델보다 복잡한 시선-화면 매핑을 학습합니다.
    기본 구조: 입력 → 64개 뉴런 → 32개 뉴런 → 출력
    """

    def __init__(
        self,
        *,
        hidden_layer_sizes: tuple[int, ...] = (64, 32),
        activation: str = "relu",
        alpha: float = 1e-4,
        learning_rate_init: float = 1e-3,
        max_iter: int = 500,
        early_stopping: bool = True,
    ) -> None:
        """
        TinyMLP 모델 초기화
        
        Args:
            hidden_layer_sizes (tuple): 은닉층 크기 (기본값: (64, 32))
                                       3개의 예: (64, 32, 16)
            activation (str): 활성화 함수 (기본값: "relu")
                             "relu", "tanh", "logistic" 등
            alpha (float): L2 정규화 강도 (기본값: 1e-4)
            learning_rate_init (float): 초기 학습률 (기본값: 1e-3)
            max_iter (int): 최대 반복 횟수 (기본값: 500)
            early_stopping (bool): 조기 종료 사용 여부 (기본값: True)
        """
        super().__init__()
        self._init_native(
            hidden_layer_sizes=hidden_layer_sizes,
            activation=activation,
            alpha=alpha,
            learning_rate_init=learning_rate_init,
            max_iter=max_iter,
            early_stopping=early_stopping,
        )

    def _init_native(self, **kw):
        """scikit-learn MLPRegressor 생성"""
        self.model = MLPRegressor(
            solver="adam",        # Adam 최적화 알고리즘
            batch_size="auto",    # 배치 크기 자동 설정
            random_state=0,       # 재현성 보장
            verbose=False,        # 상세 출력 비활성화
            **kw,
        )

    def _native_train(self, X, y):
        """모델 훈련"""
        self.model.fit(X, y)

    def _native_predict(self, X):
        """시선 위치 예측"""
        return self.model.predict(X)


# 모델 레지스트리에 등록
register_model("tiny_mlp", TinyMLPModel)
