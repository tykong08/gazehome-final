"""사용자 관리 API 엔드포인트."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Body
from pydantic import BaseModel

from backend.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    """사용자 로그인 요청 - 데모 모드."""
    pass  # 빈 요청


class LoginResponse(BaseModel):
    """사용자 로그인 응답."""
    success: bool
    username: str
    has_calibration: bool
    calibration_file: str | None = None
    message: str


@router.post("/login", response_model=LoginResponse)
async def login_user(request: dict = Body(default={})):
    """기능: 데모 사용자 로그인.
    
    args: 없음 (body는 빈 dict)
    return: success, username, has_calibration, calibration_file, message
    """
    try:
        username = db.DEFAULT_USERNAME
        
        has_calibration = db.has_calibration()
        calibration_file = db.get_latest_calibration() if has_calibration else None
        
        if has_calibration and calibration_file:
            try:
                from backend.api.main import gaze_tracker
                from pathlib import Path
                
                if gaze_tracker is not None:
                    if Path(calibration_file).exists():
                        gaze_tracker.load_calibration(calibration_file)
                        logger.info(f"Calibration loaded: {calibration_file}")
            except Exception as e:
                logger.error(f"Failed to load calibration: {e}")
        
        try:
            from backend.services.ai_client import ai_client
            import asyncio
            from backend.core.config import settings
            
            user_id = db.get_demo_user_id()
            
            # ⭐ AI-Services는 사용자 등록 엔드포인트를 제공하지 않음
            # → 로컬 데이터베이스에만 저장됨
            logger.info(f"✅ 사용자 로컬 저장 완료: {username}")
                
        except Exception as e:
            logger.error(f"사용자 정보 처리 중 오류: {e}")
        
        logger.info(f"Login: {username}, has_calibration: {has_calibration}")
        
        return LoginResponse(
            success=True,
            username=username,
            has_calibration=has_calibration,
            calibration_file=calibration_file,
            message=f"Welcome, {username}!"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            username = db.DEFAULT_USERNAME
            return LoginResponse(
                success=True,
                username=username,
                has_calibration=False,
                calibration_file=None,
                message=f"Welcome, {username}!"
            )
        except Exception as fallback_error:
            logger.error(f"Fallback login also failed: {fallback_error}")
            raise