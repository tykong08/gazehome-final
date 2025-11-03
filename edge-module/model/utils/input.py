"""
시스템 입력 유틸리티

OS 수준의 마우스 클릭 등 입력 제어
"""

from __future__ import annotations

import importlib
from typing import Any


class ClickActionUnavailable(RuntimeError):
    """
    시스템 입력 작업을 수행할 수 없을 때 발생하는 예외
    
    주로 pynput이 설치되지 않았을 때 발생합니다
    """


class MouseClicker:
    """
    pynput을 사용하여 OS 수준의 마우스 클릭 발생
    
    예: 시선 기반 클릭 (깜빡임으로 클릭 등)
    """

    def __init__(self) -> None:
        """
        MouseClicker 초기화
        
        pynput 모듈 임포트를 시도합니다.
        임포트 실패 시 ClickActionUnavailable 예외 발생
        
        Raises:
            ClickActionUnavailable: pynput이 설치되지 않은 경우
        """
        try:
            module = importlib.import_module("pynput.mouse")
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ClickActionUnavailable(
                "pynput is required for blink-to-click. Install it via 'pip install pynput'."
            ) from exc

        # pynput 모듈에서 필요한 클래스 추출
        Button: Any = getattr(module, "Button")
        Controller: Any = getattr(module, "Controller")

        self._controller = Controller()
        self._button = Button.left

    def click(self) -> None:
        """
        왼쪽 마우스 버튼 클릭 발생
        
        현재 마우스 위치에서 클릭이 발생합니다
        """
        self._controller.click(self._button)
