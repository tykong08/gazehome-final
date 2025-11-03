"""
GazeHome Model - 시선 추적 라이브러리

이 패키지는 MediaPipe와 머신러닝을 활용한 웹캠 기반 시선 추적을 제공합니다.

주요 기능:
- GazeEstimator: 실시간 시선 추적 엔진
- Kalman 필터: 시선 위치 스무딩
- 캘리브레이션: 9포인트, 5포인트, 리사주 곡선 방식
"""

from ._version import __version__

# 지연 로딩 맵
# 모듈을 실제로 사용할 때만 임포트하여 시작 시간을 단축합니다
_lazy_map = {
    # 시선 추적 엔진
    "GazeEstimator": ("model.gaze", "GazeEstimator"),
    # 필터 함수
    "make_kalman": ("model.filters", "make_kalman"),
    # 캘리브레이션 함수들
    "run_9_point_calibration": ("model.calibration", "run_9_point_calibration"),
    "run_5_point_calibration": ("model.calibration", "run_5_point_calibration"),
    "run_lissajous_calibration": ("model.calibration", "run_lissajous_calibration"),
}


def __getattr__(name: str):
    """
    요청된 심볼을 지연 로딩합니다.
    
    Args:
        name (str): 불러올 심볼의 이름
    
    Returns:
        요청된 심볼 (클래스, 함수, 객체 등)
    
    Raises:
        AttributeError: 심볼을 찾을 수 없는 경우
    """
    try:
        module_name, symbol = _lazy_map[name]
    except KeyError:
        raise AttributeError(name) from None

    import importlib

    # 모듈 임포트
    module = importlib.import_module(module_name)
    # 모듈에서 심볼 추출
    value = getattr(module, symbol)
    # 글로벌 네임스페이스에 캐싱 (이후 빠른 접근)
    globals()[name] = value
    return value


def __dir__():
    """
    패키지의 공개 인터페이스 목록을 반환합니다.
    
    Returns:
        list: 패키지에서 사용 가능한 모든 심볼 목록
    """
    std_attrs = set(globals()) | {"__getattr__", "__dir__"}
    return sorted(std_attrs | _lazy_map.keys())


# 공개 API 목록
__all__ = list(_lazy_map) + ["__version__"]
