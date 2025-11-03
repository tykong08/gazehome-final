"""
No-Op (아무 작업도 하지 않는) 필터 모듈

필터링을 하지 않고 입력된 시선 위치를 그대로 반환하는
필터 (주로 디버깅이나 필터 비교용)
"""

from __future__ import annotations

from typing import Tuple

from .base import BaseSmoother


class NoSmoother(BaseSmoother):
    """
    필터링을 수행하지 않는 스무더
    
    입력받은 시선 위치를 그대로 반환합니다.
    필터 효과를 비교하거나 원본 데이터가 필요할 때 사용합니다.
    """

    def step(self, x: int, y: int) -> Tuple[int, int]:
        """
        필터링 없이 입력 좌표를 그대로 반환합니다.
        
        Args:
            x (int): X 좌표
            y (int): Y 좌표
        
        Returns:
            Tuple[int, int]: 입력과 동일한 (x, y)
        """
        return x, y
