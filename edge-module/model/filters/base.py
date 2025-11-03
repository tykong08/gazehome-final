"""
필터 기본 클래스 모듈

모든 필터 구현이 상속해야 하는 추상 기본 클래스를 정의합니다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple


class BaseSmoother(ABC):
    """
    시선 위치 필터링을 위한 기본 추상 클래스
    
    모든 필터 구현은 이 클래스를 상속하고
    step() 메서드를 구현해야 합니다.
    """

    def __init__(self) -> None:
        """
        필터 초기화
        
        Attributes:
            debug (dict): 디버그 정보 저장소
                필터의 내부 상태나 중간 계산값 저장에 사용
        """
        self.debug: dict = {}

    @abstractmethod
    def step(self, x: int, y: int) -> Tuple[int, int]:
        """
        필터링 단계를 수행합니다.
        
        서브클래스에서 반드시 구현해야 합니다.
        
        Args:
            x (int): 입력 X 좌표 (필터링 전 원본 시선 위치)
            y (int): 입력 Y 좌표 (필터링 전 원본 시선 위치)
        
        Returns:
            Tuple[int, int]: 필터링된 (x, y) 좌표
        """
        ...

