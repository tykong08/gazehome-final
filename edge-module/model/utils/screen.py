"""
화면 정보 유틸리티

현재 모니터의 해상도 등 화면 정보 조회
"""

from screeninfo import get_monitors


def get_screen_size():
    """
    현재 주 모니터(첫 번째 모니터)의 해상도를 반환합니다
    
    Returns:
        tuple: (가로, 세로) 해상도 (픽셀 단위)
    """
    m = get_monitors()[0]
    return m.width, m.height
