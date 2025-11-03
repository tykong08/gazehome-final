"""시선 추적 설정 및 상태 조회를 위한 REST API 엔드포인트."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter()


class FilterSettings(BaseModel):
    """시선 필터 설정."""
    filter_method: str = Field(description="필터 방식: 'noop' (필터링 비활성화)")


class FilterStatusResponse(BaseModel):
    """현재 필터 상태."""
    filter_method: str
    active: bool
    message: str


@router.get("/filter", response_model=FilterStatusResponse)
async def get_filter_status():
    """기능: 현재 필터 설정 및 상태 조회.
    
    args: 없음
    return: 필터 상태 정보 (filter_method, active, message)
    """
    try:
        from backend.api.main import gaze_tracker
        
        if gaze_tracker is None:
            raise HTTPException(status_code=500, detail="시선 추적기가 초기화되지 않았습니다")
        
        filter_method = gaze_tracker.filter_method
        
        return FilterStatusResponse(
            filter_method=filter_method,
            active=gaze_tracker.smoother is not None,
            message=f"NoOp 필터 (필터링 비활성화) 사용 중"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tracker-info")
async def get_tracker_info():
    """기능: 추적기 정보 조회.
    
    args: 없음
    return: 추적기 정보 (camera_index, model_name, filter_method, screen_size, calibrated, is_running, current_gaze, raw_gaze, blink, timestamp)
    """
    try:
        from backend.api.main import gaze_tracker
        
        if gaze_tracker is None:
            raise HTTPException(status_code=500, detail="시선 추적기가 초기화되지 않았습니다")
        
        state = gaze_tracker.get_current_state()
        
        return {
            "camera_index": gaze_tracker.camera_index,
            "model_name": gaze_tracker.model_name,
            "filter_method": gaze_tracker.filter_method,
            "screen_size": gaze_tracker.screen_size,
            "calibrated": state["calibrated"],
            "is_running": gaze_tracker.is_running,
            "current_gaze": state["gaze"],
            "raw_gaze": state["raw_gaze"],
            "blink": state["blink"],
            "timestamp": state["timestamp"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


