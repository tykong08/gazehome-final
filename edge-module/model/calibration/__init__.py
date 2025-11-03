"""
시선 추적 캘리브레이션 모듈

시선 추적 모델을 사용자 환경에 맞게 조정하는 다양한 캘리브레이션 방식 제공

캘리브레이션 방식:
- 9-포인트: 화면의 9개 위치 (3x3 격자)
- 5-포인트: 화면의 5개 위치 (4 모서리 + 중앙)
- 리사주 곡선: 부드러운 곡선 따라가기
- 적응형: 자동 조정 캘리브레이션
"""

from .common import compute_grid_points, wait_for_face_and_countdown
from .five_point import run_5_point_calibration
from .lissajous import run_lissajous_calibration
from .nine_point import run_9_point_calibration

__all__ = [
    "wait_for_face_and_countdown",
    "compute_grid_points",
    "run_9_point_calibration",
    "run_5_point_calibration",
    "run_lissajous_calibration",
]
