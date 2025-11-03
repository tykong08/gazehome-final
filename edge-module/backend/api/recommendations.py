"""
AI-Services 추천 수신 및 Frontend 브로드캐스트 엔드포인트.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)

# 현재 표시 중인 추천 저장 (Frontend에서 피드백할 때 사용)
current_recommendation: Optional[Dict[str, Any]] = None
# 최근 추천 ID와 응답 추적
pending_responses: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# 추천 상태 관리
# ============================================================================

def set_current_recommendation(recommendation: Dict[str, Any]) -> None:
    """현재 표시 중인 추천 저장.
    
    Args:
        recommendation (dict): 추천 정보 (title, contents, device_control 등 포함)
    """
    global current_recommendation
    current_recommendation = recommendation
    logger.info(f"[Recommendations] 📌 현재 추천 저장: {recommendation.get('title')}")


def get_current_recommendation() -> Optional[Dict[str, Any]]:
    """현재 표시 중인 추천 조회.
    
    Returns:
        dict: 추천 정보 또는 None
    """
    return current_recommendation


async def broadcast_recommendation_to_frontend(recommendation: Dict[str, Any]) -> bool:
    """모든 연결된 WebSocket 클라이언트에게 추천 브로드캐스트.
    
    Args:
        recommendation (dict): 추천 정보
        
    Returns:
        bool: 브로드캐스트 성공 여부
    """
    try:
        from backend.api.websocket import manager
        
        message = {
            "type": "recommendation",
            "data": recommendation
        }
        
        # 브로드캐스트 실행
        await manager.broadcast(message)
        
        logger.info(f"[Recommendations] 📢 추천 브로드캐스트: {len(manager.active_connections)}개 클라이언트")
        logger.info(f"  - 제목: {recommendation.get('title')}")
        logger.info(f"  - ID: {recommendation.get('recommendation_id')}")
        
        return True
        
    except Exception as e:
        logger.error(f"[Recommendations] ❌ 브로드캐스트 실패: {e}")
        return False


# ============================================================================
# Pydantic Models
# ============================================================================

class DeviceControl(BaseModel):
    """기기 제어 정보"""
    device_id: Optional[str] = Field(None, description="기기 ID")
    device_type: Optional[str] = Field(None, description="기기 타입")
    device_name: Optional[str] = Field(None, description="기기명")
    action: Optional[str] = Field(None, description="제어 액션")
    params: Optional[Dict[str, Any]] = Field(None, description="추가 파라미터")


class AIRecommendationRequest(BaseModel):
    """AI-Services에서 Edge-Module로 보내는 추천 요청."""
    recommendation_id: str = Field(..., description="추천 ID")
    title: str = Field(..., description="추천 제목")
    contents: str = Field(..., description="추천 내용")


class RecommendationFeedbackRequest(BaseModel):
    """Frontend에서 보내는 사용자 응답."""
    recommendation_id: str = Field(..., description="추천 ID")
    user_id: str = Field(..., description="사용자 ID")
    accepted: bool = Field(..., description="YES(true) / NO(false)")


class ConfirmRequest(BaseModel):
    """Frontend에서 사용자 YES/NO 응답을 받아 AI-Server로 전송.
    
    구조:
    - recommendation_id: 추천 ID
    - confirm: "YES" 또는 "NO"
    """
    recommendation_id: str = Field(..., description="추천 ID")
    confirm: str = Field(..., description="YES 또는 NO")


# ============================================================================
# API Endpoints: AI-Services ← → Edge-Module ← → Frontend
# ============================================================================

@router.post("/")
async def receive_recommendation(request: AIRecommendationRequest):
    """AI-Services에서 추천을 수신하고 Frontend로 브로드캐스트.
    
    Flow:
    1. AI-Services가 Edge-Module의 /api/recommendations/ 으로 POST
    2. Edge-Module이 WebSocket을 통해 모든 Frontend 클라이언트에게 브로드캐스트
    3. Frontend에서 사용자 응답 대기
    
    Args:
        request (AIRecommendationRequest): AI-Services의 추천 요청
            - recommendation_id: 추천 ID
            - title: 추천 제목
            - contents: 추천 내용
        
    Returns:
        dict: 추천 ID 및 성공/실패 상태
    """
    try:
        logger.info(f"[Recommendations] 📥 AI-Services에서 추천 수신:")
        logger.info(f"  - ID: {request.recommendation_id}")
        logger.info(f"  - 제목: {request.title}")
        logger.info(f"  - 내용: {request.contents[:100]}..." if len(request.contents) > 100 else f"  - 내용: {request.contents}")
        
        # AI-Server에서 받은 데이터를 그대로 사용 (캐시 저장)
        recommendation = {
            "recommendation_id": request.recommendation_id,
            "title": request.title,
            "contents": request.contents,
        }
        
        # 현재 추천 캐시 저장
        set_current_recommendation(recommendation)
        
        # Frontend에 브로드캐스트
        broadcast_success = await broadcast_recommendation_to_frontend(recommendation)
        
        if not broadcast_success:
            logger.warning(f"[Recommendations] ⚠️  브로드캐스트 실패 (클라이언트 없음 가능)")
        
        return {
            "success": True,
            "message": "추천을 Frontend에 전달했습니다",
            "recommendation_id": request.recommendation_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[Recommendations] ❌ 추천 수신 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"추천 수신 실패: {str(e)}"
        )


@router.post("/feedback")
async def submit_recommendation_feedback(feedback: RecommendationFeedbackRequest):
    """Frontend의 사용자 응답을 기록 (로컬 저장용).
    
    주의: 이 엔드포인트는 로컬 기록만 수행합니다.
    AI-Server로의 피드백은 /confirm 엔드포인트에서 수행합니다.
    
    Flow:
    1. Frontend가 사용자 응답 전송
    2. Edge-Module이 로컬에 기록
    3. /confirm 엔드포인트에서 AI-Server로 전송
    
    Args:
        feedback (RecommendationFeedbackRequest):
            - recommendation_id: 추천 ID
            - user_id: 사용자 ID
            - accepted: true(YES) / false(NO)
    
    Returns:
        dict: 기록 결과
    """
    try:
        response_text = "승인(YES)" if feedback.accepted else "거절(NO)"
        
        logger.info(f"[Recommendations] 📨 사용자 응답 기록:")
        logger.info(f"  - ID: {feedback.recommendation_id}")
        logger.info(f"  - 사용자: {feedback.user_id}")
        logger.info(f"  - 응답: {response_text}")
        
        # 응답 추적 업데이트
        if feedback.recommendation_id in pending_responses:
            pending_responses[feedback.recommendation_id]["accepted"] = feedback.accepted
            pending_responses[feedback.recommendation_id]["user_responded"] = True
            pending_responses[feedback.recommendation_id]["response_time"] = time.time()
            
            logger.info(f"[Recommendations] ✅ 응답 추적 업데이트: {feedback.recommendation_id}")
        
        return {
            "success": True,
            "message": f"피드백이 기록되었습니다: {response_text}",
            "recommendation_id": feedback.recommendation_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[Recommendations] ❌ 피드백 기록 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"피드백 기록 실패: {str(e)}"
        )


@router.get("/pending")
async def get_pending_recommendation():
    """대기 중인 추천 조회.
    
    Frontend가 연결되지 않았을 때 사용하거나, 
    현재 표시 중인 추천을 다시 조회할 때 사용.
    
    Returns:
        dict: 대기 중인 추천 정보 또는 없음 메시지
    """
    try:
        pending = get_current_recommendation()
        
        if pending:
            logger.info(f"[Recommendations] 📋 대기 중인 추천 조회: {pending.get('recommendation_id')}")
            return {
                "success": True,
                "recommendation": pending
            }
        else:
            logger.info(f"[Recommendations] ℹ️ 대기 중인 추천 없음")
            return {
                "success": False,
                "message": "대기 중인 추천이 없습니다"
            }
        
    except Exception as e:
        logger.error(f"[Recommendations] ❌ 추천 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"추천 조회 실패: {str(e)}"
        )


@router.get("/responses/{recommendation_id}")
async def get_recommendation_response(recommendation_id: str):
    """특정 추천에 대한 사용자 응답 조회 (Polling용).
    
    Frontend가 WebSocket이 아닌 HTTP 폴링으로 응답을 확인할 때 사용.
    
    Args:
        recommendation_id (str): 추천 ID
        
    Returns:
        dict: 사용자 응답 정보 (대기 중, 승인, 거절)
    """
    try:
        if recommendation_id not in pending_responses:
            return {
                "success": False,
                "message": "해당 추천을 찾을 수 없습니다"
            }
        
        response_info = pending_responses[recommendation_id]
        
        status = "pending"  # 기본값: 대기 중
        if response_info["user_responded"]:
            status = "accepted" if response_info["accepted"] else "rejected"
        
        logger.info(f"[Recommendations] 🔍 응답 상태 조회: {recommendation_id} → {status}")
        
        
        return {
            "success": True,
            "recommendation_id": recommendation_id,
            "status": status,
            "accepted": response_info["accepted"],
            "timestamp": response_info["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"[Recommendations] ❌ 응답 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"응답 조회 실패: {str(e)}"
        )


@router.post("/confirm")
async def confirm_recommendation(request: ConfirmRequest):
    """Frontend의 사용자 YES/NO 응답을 AI-Server로 전송.
    
    Flow:
    1. Frontend가 사용자의 YES/NO 선택을 Edge-Module로 전송 (POST /confirm)
    2. Edge-Module이 AI-Server의 /api/recommendations/feedback으로 전송
    3. AI-Server가 YES인 경우 기기 제어 수행
    
    Args:
        request:
            - recommendation_id: 추천 ID
            - confirm: "YES" 또는 "NO"
    
    Returns:
        dict: 처리 결과
        
    Example:
        POST /api/recommendations/confirm
        {
            "recommendation_id": "rec_abc123",
            "confirm": "YES"
        }
        
        Response:
        {
            "success": true,
            "recommendation_id": "rec_abc123",
            "confirm": "YES",
            "message": "AI-Server에 피드백을 전송했습니다"
        }
    """
    try:
        confirm = request.confirm.upper()
        
        # Validation
        if confirm not in ["YES", "NO"]:
            raise HTTPException(
                status_code=400,
                detail="confirm은 'YES' 또는 'NO'만 가능합니다"
            )
        
        logger.info(f"[Recommendations] 📤 사용자 응답 처리:")
        logger.info(f"  - ID: {request.recommendation_id}")
        logger.info(f"  - 응답: {confirm}")
        
        # AI-Server로 feedback 전송
        from backend.services.ai_client import ai_client
        
        logger.info(f"[Recommendations] 🚀 AI-Server로 피드백 전송 중...")
        feedback_result = await ai_client.send_recommendation_feedback(
            recommendation_id=request.recommendation_id,
            confirm=confirm
        )
        
        if feedback_result.get("success"):
            logger.info(f"✅ AI-Server 피드백 완료: {feedback_result.get('message', '성공')}")
            
            if confirm == "YES":
                logger.info(f"  → AI-Server가 기기 제어를 수행합니다")
            else:
                logger.info(f"  → 사용자가 거부했습니다")
        else:
            logger.warning(f"⚠️  AI-Server 응답 오류: {feedback_result.get('message')}")
        
        return {
            "success": True,
            "recommendation_id": request.recommendation_id,
            "confirm": confirm,
            "message": f"AI-Server에 {confirm} 피드백을 전송했습니다",
            "ai_server_response": feedback_result,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Recommendations] ❌ 피드백 전송 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"피드백 전송 실패: {str(e)}"
        )


