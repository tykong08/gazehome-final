"""
시선 추적 모델 모듈

다양한 회귀 모델을 사용한 시선 위치 예측
자동 모델 발견 및 팩토리 패턴 지원
"""

from importlib import import_module
from pathlib import Path
from typing import Dict, Type

from .base import BaseModel

__all__ = ["BaseModel", "create_model", "AVAILABLE_MODELS"]

# 등록된 모델들의 딕셔너리 (모델명 -> 모델 클래스)
AVAILABLE_MODELS: Dict[str, Type[BaseModel]] = {}


def register_model(name: str, cls: Type[BaseModel]) -> None:
    """
    새로운 모델을 레지스트리에 등록합니다.
    
    Args:
        name (str): 모델의 고유 이름
        cls (Type[BaseModel]): BaseModel을 상속한 모델 클래스
    
    Raises:
        ValueError: 같은 이름의 모델이 이미 등록되어 있는 경우
    """
    if name in AVAILABLE_MODELS:
        raise ValueError(f"Model name '{name}' already registered")
    AVAILABLE_MODELS[name] = cls


def _auto_discover() -> None:
    """
    models 디렉토리에서 모든 모델 모듈을 자동으로 발견하고 임포트합니다.
    
    각 .py 파일은 모듈 로드 시 register_model() 함수를 호출하여
    자신을 자동으로 등록해야 합니다.
    """
    pkg_dir = Path(__file__).resolve().parent
    for f in pkg_dir.iterdir():
        # __init__.py와 base.py는 제외, Python 파일만 처리
        if f.name in {"__init__.py", "base.py"} or f.suffix != ".py":
            continue
        mod_name = f"{__name__}.{f.stem}"
        import_module(mod_name)


def create_model(name: str, **kwargs) -> BaseModel:
    """
    주어진 이름의 모델을 생성합니다.
    
    이 함수는 지연 로딩 방식으로 모델들을 발견합니다.
    첫 호출 시에만 _auto_discover()를 실행합니다.
    
    Args:
        name (str): 생성할 모델의 이름
        **kwargs: 모델 클래스의 __init__에 전달할 인자들
    
    Returns:
        BaseModel: 생성된 모델 인스턴스
    
    Raises:
        ValueError: 요청한 모델이 등록되어 있지 않은 경우
    """
    if not AVAILABLE_MODELS:
        _auto_discover()
    try:
        cls = AVAILABLE_MODELS[name]
    except KeyError as e:
        raise ValueError(
            f"Unknown model '{name}'. Available: {sorted(AVAILABLE_MODELS)}"
        ) from e
    return cls(**kwargs)
