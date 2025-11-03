"""FastAPI 애플리케이션."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.gaze_tracker import WebGazeTracker
from backend.api import websocket, devices, recommendations, calibration, settings as settings_api, users

logger = logging.getLogger(__name__)

# 전역 시선 추적기 인스턴스
gaze_tracker: WebGazeTracker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 및 종료 이벤트."""
    global gaze_tracker
    
    # 🚀 시작 - 시선 추적기 초기화 및 기기 동기화
    logger.info(f"[Backend] GazeHome 웹 서버 시작: {settings.host}:{settings.port}")
    
    # ✅ 기기 동기화 (Gateway → Local DB)
    try:
        from backend.services.gateway_client import gateway_client
        logger.info("[Backend] 🔄 Gateway 기기 동기화 시작...")
        sync_success = await gateway_client.sync_all_devices_to_db()
        if sync_success:
            logger.info("[Backend] ✅ 기기 동기화 완료")
        else:
            logger.warning("[Backend] ⚠️  기기 동기화 실패 (계속 진행)")
    except Exception as e:
        logger.warning(f"[Backend] ⚠️  기기 동기화 중 오류: {e}")
    
    try:
        gaze_tracker = WebGazeTracker(
            camera_index=settings.camera_index,
            model_name=settings.model_name,
            filter_method=settings.filter_method,
            screen_size=settings.screen_size
        )
        
        await gaze_tracker.initialize()
        logger.info("[Backend] ✅ 시선 추적기 초기화됨")
        
        # ⭐ 최신 보정 파일 자동 로드 (DB에서 조회)
        from pathlib import Path
        from backend.core.database import db
        
        latest_calibration = db.get_latest_calibration()
        if latest_calibration:
            try:
                gaze_tracker.load_calibration(latest_calibration)
                logger.info(f"[Backend] ✅ 보정 파일 로드됨: {latest_calibration}")
            except Exception as e:
                logger.warning(f"[Backend] ⚠️  보정 파일 로드 실패: {e}")
                logger.info("[Backend] → 보정이 필요합니다. /calibration 페이지로 이동하세요.")
        else:
            logger.info("[Backend] ℹ️  보정 파일이 없습니다. 신규 보정이 필요합니다.")
        
        # 백그라운드에서 추적 시작
        asyncio.create_task(gaze_tracker.start_tracking())
        logger.info("[Backend] ✅ 시선 추적 시작됨")
        
    except Exception as e:
        logger.error(f"[Backend] ⚠️  시선 추적기 초기화 실패: {e}")
        logger.warning("[Backend] ⚠️  DEMO 모드로 실행 중 (시선 추적 비활성화)")
        # gaze_tracker = None으로 유지하여 WebSocket에서 더미 데이터 제공
        gaze_tracker = None
    
    yield
    
    # 🛑 종료 - 시선 추적기 정지
    logger.info("[Backend] 🛑 종료 중...")
    if gaze_tracker:
        await gaze_tracker.stop_tracking()
    logger.info("[Backend] ✅ 시선 추적기 중지됨")


# FastAPI 앱 생성
app = FastAPI(
    title="GazeHome 스마트 홈 API",
    description="시선 제어 스마트 홈 백엔드",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 포함
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(devices.router, prefix="/api/devices", tags=["Devices"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"])
app.include_router(calibration.router, prefix="/api/calibration", tags=["Calibration"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["Settings"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])


@app.get("/")
async def root():
    """루트 엔드포인트."""
    return {
        "app": "GazeHome 스마트 홈",
        "version": "1.0.0",
        "status": "실행 중"
    }


@app.get("/health")
async def health():
    """헬스 체크 엔드포인트."""
    if gaze_tracker is None:
        return {"status": "초기화 중", "tracker_active": False}
    
    return {
        "status": "건강함",
        "tracker_active": gaze_tracker.is_running,
        "calibrated": gaze_tracker.calibrated
    }


def get_gaze_tracker() -> WebGazeTracker:
    """시선 추적기 인스턴스를 가져오는 의존성.
    
    Returns:
        시선 추적기 인스턴스
        
    Raises:
        RuntimeError: 시선 추적기가 초기화되지 않은 경우
    """
    if gaze_tracker is None:
        raise RuntimeError("시선 추적기가 초기화되지 않았습니다")
    return gaze_tracker
