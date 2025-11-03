"""AI 서버와의 HTTP 통신을 담당하는 클라이언트."""
from __future__ import annotations

import logging
import asyncio
import httpx
import pytz
from typing import Dict, Any, Optional
from datetime import datetime

from backend.core.config import settings

logger = logging.getLogger(__name__)
KST = pytz.timezone('Asia/Seoul')


class AIServiceClient:
    """AI Server HTTP 클라이언트."""
    
    def __init__(self):
        """AI Server 클라이언트 초기화."""
        self.base_url = settings.ai_server_url.rstrip('/')
        self.timeout = settings.ai_request_timeout
        self.max_retries = settings.ai_max_retries
        
        logger.info(f"AIServiceClient initialized: {self.base_url}")
    
    # =========================================================================
    # Device Control
    # =========================================================================
    
    async def send_device_control(
        self,
        user_id: str,
        device_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """기능: 기기 제어 명령을 AI Server로 전송.
        
        AI Server의 /api/lg/control 엔드포인트 호출
        → Gateway의 /api/lg/control 호출
        → LG ThinQ API 제어
        
        args: user_id, device_id, action, params
        return: 제어 결과 (message)
        
        응답 형식:
        {
            "message": "[GATEWAY] 스마트 기기(공기청정기) 제어 완료"
        }
        """
        url = f"{self.base_url}/api/lg/control"
        
        # AI-Services의 /api/lg/control 엔드포인트 요청 형식
        # (Gateway와 동일한 형식)
        payload = {
            "device_id": device_id,
            "action": action
        }
        
        try:
            logger.info(f"🚀 AI Server로 기기 제어 요청:")
            logger.info(f"  - URL: {url}")
            logger.info(f"  - 기기: {device_id}")
            logger.info(f"  - 액션: {action}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                message = result.get("message", "기기 제어 완료")
                
                logger.info(f"✅ 기기 제어 성공: {message}")
                logger.info(f"   AI-Server → Gateway → LG Device 제어 완료")
                
                return {
                    "success": True,
                    "message": message,
                    "device_id": device_id,
                    "action": action
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ AI Server 기기 제어 실패:")
            logger.error(f"   Status: {e.response.status_code}")
            logger.error(f"   Detail: {e.response.text}")
            return {
                "success": False,
                "message": f"기기 제어 실패: {e.response.text}",
                "device_id": device_id,
                "action": action
            }
        except httpx.TimeoutException:
            logger.error(f"❌ AI Server 통신 타임아웃: {device_id}")
            return {
                "success": False,
                "message": f"AI Server 통신 타임아웃 ({self.timeout}초)",
                "device_id": device_id,
                "action": action
            }
        except Exception as e:
            logger.error(f"❌ 기기 제어 중 오류: {e}")
            return {
                "success": False,
                "message": f"기기 제어 실패: {str(e)}",
                "device_id": device_id,
                "action": action
            }
    
    # =========================================================================
    # Get User Devices
    # =========================================================================
    
    async def get_user_devices(self, user_id: str) -> list[Dict[str, Any]]:
        """기능: 기기 목록 조회 (로컬 Mock 데이터 사용).
        
        ⭐ AI-Services는 기기 목록 조회 엔드포인트를 제공하지 않으므로
           Edge-Module에서 로컬 MOCK_DEVICES를 사용합니다.
        
        기기 제어만 AI-Services를 통해 진행합니다:
        AI-Services (POST /api/lg/control) → Gateway → LG ThinQ API
        
        args: user_id
        return: 기기 목록 (로컬 Mock 데이터)
        """
        logger.info(f"📋 기기 목록 조회: AI-Services를 통하지 않고 로컬 Mock 데이터 사용")
        logger.warning(f"⚠️  AI-Services는 기기 조회 엔드포인트를 제공하지 않음")
        logger.info(f"   → 기기 제어는 AI-Services POST /api/lg/control을 통해 수행")
        
        # 로컬 Mock 기기 데이터 반환 (AI-Services 엔드포인트 부재)
        return []
    
    # =========================================================================
    # Register User
    # =========================================================================
    
    async def register_user_async(
        self, 
        user_id: str,
        username: str,
        has_calibration: bool,
    ) -> Dict[str, Any]:
        """기능: 사용자 정보를 로컬에 기록 (AI Server 미지원).
        
        ⭐ AI-Services는 사용자 등록 엔드포인트를 제공하지 않으므로
           로컬 데이터베이스에만 기록합니다.
        
        args: user_id, username, has_calibration
        return: 로컬 기록 결과
        """
        logger.info(f"👤 사용자 정보 로컬 기록: {username}")
        logger.warning(f"⚠️  AI-Services는 사용자 등록 엔드포인트를 제공하지 않음")
        logger.info(f"   → 로컬 데이터베이스에만 저장됨 (AI-Services 연동 불필요)")
        
        # 로컬 데이터베이스에 저장됨 (database.py에서 처리)
        return {
            "success": True,
            "message": f"User registered locally: {username}",
            "user_id": user_id
        }
    
    # =========================================================================
    # AI Recommendation
    # =========================================================================
    
    async def send_recommendation(
        self,
        title: str,
        contents: str
    ) -> Dict[str, Any]:
        """기능: AI 추천을 하드웨어(Frontend)에 전송.
        
        AI Service가 생성한 추천을 사용자에게 보여주고 확인 대기.
        사용자가 YES 선택시 기기 제어 정보 포함.
        
        args: title (추천 제목), contents (추천 내용)
        return: 응답 (message, confirm: YES/NO, device_control)
        """
        url = f"{self.base_url}/api/recommendations"
        
        payload = {
            "title": title,
            "contents": contents
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Send recommendation: title={title}")
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                
                # 응답 형식 검증
                confirm = result.get("confirm", "NO")
                device_control = result.get("device_control")
                
                logger.info(f"Recommendation response: confirm={confirm}")
                
                if confirm == "YES" and device_control:
                    logger.info(f"User confirmed recommendation, device_control: {device_control}")
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to send recommendation: {e}")
            return {
                "success": False,
                "message": f"Failed to send recommendation: {str(e)}",
                "confirm": "NO"
            }
    
    # =========================================================================
    # Device Click Event
    # =========================================================================
    
    async def send_device_click(
        self,
        user_id: str,
        device_id: str,
        device_name: str,
        device_type: str,
        action: str
    ) -> Dict[str, Any]:
        """기능: 기기 클릭 이벤트를 AI Server로 전송.
        
        args: user_id, device_id, device_name, device_type, action
        return: 결과 (success, message, recommendation)
        """
        url = f"{self.base_url}/api/gaze/click"
        
        payload = {
            "user_id": user_id,
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "action": action,
            "timestamp": datetime.now(KST).isoformat()
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(
                    f"Send device click: user_id={user_id}, device_id={device_id}, "
                    f"action={action}"
                )
                
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Device click processed: {device_id}, action: {action}")
                
                return result
                
        except Exception as e:
            logger.warning(f"Failed to send device click: {e}")
            return {
                "success": False,
                "message": f"Failed to send device click: {str(e)}"
            }
    
    # =========================================================================
    # Recommendation Feedback (사용자 YES/NO 응답을 AI-Server로 전송)
    # =========================================================================
    
    async def send_recommendation_feedback(
        self,
        recommendation_id: str,
        confirm: str
    ) -> Dict[str, Any]:
        """기능: 사용자의 추천 응답(YES/NO)을 AI-Server로 전송.
        
        AI-Server의 POST /api/recommendations/feedback 엔드포인트 호출.
        YES인 경우 AI-Server가 자동으로 기기 제어를 수행합니다.
        
        args:
            recommendation_id: 추천 ID
            confirm: "YES" 또는 "NO"
        
        return: AI-Server 응답
        """
        url = f"{self.base_url}/api/recommendations/feedback"
        
        payload = {
            "recommendation_id": recommendation_id,
            "confirm": confirm,
        }
        
        try:
            logger.info(f"📤 AI-Server로 피드백 전송:")
            logger.info(f"  - URL: {url}")
            logger.info(f"  - recommendation_id: {recommendation_id}")
            logger.info(f"  - confirm: {confirm}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                result = response.json()
                message = result.get("message", "피드백 전송 완료")
                
                logger.info(f"✅ AI-Server 응답: {message}")
                
                if confirm == "YES":
                    logger.info(f"  → AI-Server가 기기 제어를 수행합니다")
                else:
                    logger.info(f"  → 사용자가 거부했으므로 기기 제어 없음")
                
                return {
                    "success": True,
                    "message": message,
                    "recommendation_id": recommendation_id,
                    "confirm": confirm
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ AI-Server 피드백 전송 실패:")
            logger.error(f"   Status: {e.response.status_code}")
            logger.error(f"   Detail: {e.response.text}")
            return {
                "success": False,
                "message": f"피드백 전송 실패: {e.response.text}",
                "recommendation_id": recommendation_id,
                "confirm": confirm
            }
        except httpx.TimeoutException:
            logger.error(f"❌ AI-Server 통신 타임아웃")
            return {
                "success": False,
                "message": f"AI-Server 통신 타임아웃 ({self.timeout}초)",
                "recommendation_id": recommendation_id,
                "confirm": confirm
            }
        except Exception as e:
            logger.error(f"❌ 피드백 전송 중 오류: {e}")
            return {
                "success": False,
                "message": f"피드백 전송 실패: {str(e)}",
                "recommendation_id": recommendation_id,
                "confirm": confirm
            }
    
    # =========================================================================
    # Fallback Response
    # =========================================================================
    
    @staticmethod
    def _get_fallback_response(request: Dict[str, Any]) -> Dict[str, Any]:
        """기능: AI Server 오류 시 기본 응답 반환.
        
        args: request (원본 요청)
        return: 기본 응답
        """
        device_info = request.get("clicked_device", {})
        
        return {
            "status": "fallback",
            "click_id": f"click_fallback_{request.get('session_id')}",
            "recommendation": {
                "recommendation_id": f"rec_fallback_{datetime.now(KST).timestamp()}",
                "device_id": device_info.get("device_id"),
                "device_name": device_info.get("name"),
                "action": "toggle",
                "params": {},
                "reason": "AI 서버 연결 오류로 기본 토글 동작 제안",
                "confidence": 0.5
            },
            "message": "AI 서버 오류로 Fallback 응답 제공"
        }


# 전역 클라이언트 인스턴스
ai_client = AIServiceClient()


# 전역 클라이언트 인스턴스
ai_client = AIServiceClient()