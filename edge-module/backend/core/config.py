"""백엔드 서버 설정."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정 - 라즈베리파이 4 & 7inch 디스플레이 최적화."""
    
    # ===== 서버 설정 =====
    host: str = "0.0.0.0"
    port: int = 8000  # 라즈베리파이 최적화: 표준 포트
    reload: bool = False  # 프로덕션: 디버그 모드 비활성화
    
    # ===== 시선 추적 설정 (라즈베리파이 4 최적화) =====
    camera_index: int = 0
    # 라즈베리파이 최적화 모델:
    # - ridge (권장): 선형 회귀, 최소 CPU/메모리, 매우 빠름 (~50ms)
    # - elastic_net: L1+L2 정규화, 약간 더 정확 (~60ms)
    # - svr: SVM 기반, 높은 정확도 (~100ms) - RPi4에는 무거움
    # - tiny_mlp: 신경망, 최고 정확도 (~200ms) - RPi4에는 너무 무거움
    model_name: str = "ridge"
    # 라즈베리파이 최적화 필터:
    # - noop (권장): 필터링 없음, 매우 빠름, 최소 메모리
    # - kde: 커널 밀도 추정, 약간의 오버헤드 (~10ms 추가)
    # - kalman: 칼만 필터, 노이즈 제거, 안정적 (~20ms 추가)
    filter_method: str = "noop"
    
    # ===== 디스플레이 설정 (7inch 1024x600 → 800x480 최적화) =====
    # 7inch 디스플레이 해상도: 800x480 (표준)
    # - 더 작은 해상도 = 더 빠른 렌더링, 더 적은 메모리 사용
    # - 더 큰 터치 타겟 = 시선 제어에 최적
    screen_width: int = 800
    screen_height: int = 480
    
    # 캘리브레이션 설정 (사용자 보정 데이터 저장 경로)
    calibration_dir: Path = Path.home() / ".gazehome" / "calibrations"
    
    # ===== CORS 설정 (라즈베리파이 네트워크) =====
    cors_origins: list[str] = [
        "http://localhost:3000",        # 개발용
        "http://localhost:5173",        # 개발용 (Vite)
        "http://localhost",             # 직접 접근
        "http://127.0.0.1:3000",        # 루프백
        "http://127.0.0.1:5173",        # 루프백 (Vite)
        "http://raspberrypi.local:3000", # 라즈베리파이 (mDNS)
        "http://raspberrypi.local:5173", # 라즈베리파이 (mDNS, Vite)
        "http://raspberrypi",            # 라즈베리파이 (호스트명)
    ]
    
    # ===== AI 서버 설정 (AWS 서버) =====
    # AWS EC2 인스턴스: http://34.227.8.172:8000
    ai_server_url: str = os.getenv("AI_SERVER_URL", "http://34.227.8.172:8000")
    # 라즈베리파이 네트워크 최적화:
    # - 응답 대기 시간: 10초 (인터넷 연결 불안정 대비)
    # - 최대 재시도: 3회 (네트워크 일시적 실패 대비)
    ai_request_timeout: int = int(os.getenv("AI_REQUEST_TIMEOUT", "10"))
    ai_max_retries: int = int(os.getenv("AI_MAX_RETRIES", "3"))
    
    # ===== Gateway 서버 설정 (AWS EC2 - 포트 8001) =====
    # Gateway는 AI-Services와 동일한 IP의 포트 8001에서 실행
    # http://34.227.8.172:8001
    gateway_url: str = os.getenv("GATEWAY_URL", "http://34.227.8.172:8001")
    gateway_devices_endpoint: str = os.getenv("GATEWAY_DEVICES_ENDPOINT", "http://34.227.8.172:8001/api/lg/devices")
    gateway_request_timeout: int = int(os.getenv("GATEWAY_REQUEST_TIMEOUT", "5"))
    
    # ===== 스마트 홈 통합 설정 (선택사항) =====
    home_assistant_url: str = ""
    home_assistant_token: str = ""
    
    @property
    def screen_size(self) -> Tuple[int, int]:
        """화면 크기를 튜플로 반환합니다."""
        return (self.screen_width, self.screen_height)
    
    class Config:
        """Pydantic 설정 - 라즈베리파이 최적화."""
        # 절대 경로로 .env 파일 명시
        # edge-module 루트의 .env 파일 로드
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
