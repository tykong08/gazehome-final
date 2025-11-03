"""스마트 홈 디바이스 제어를 위한 REST API 엔드포인트."""
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.ai_client import ai_client
from backend.services.gateway_client import gateway_client
from backend.core.database import db

logger = logging.getLogger(__name__)
router = APIRouter()


class DeviceClickRequest(BaseModel):
    """기기 액션 요청."""
    action: str = Field(..., description="액션명")
    value: Optional[str] = Field(None, description="액션 값 (선택사항)")





# ===============================================================================
# 🔄 기기 동기화 엔드포인트
# ===============================================================================

@router.post("/sync")
async def sync_devices_from_gateway():
    """기능: Gateway에서 모든 기기와 액션을 조회해서 로컬 DB에 동기화.
    
    Flow:
    1. Gateway /api/lg/devices에서 기기 목록 조회
    2. 각 기기의 /api/lg/devices/{id}/profile 조회
    3. 기기 정보 + 액션을 로컬 SQLite DB에 저장
    4. 동기화 결과 반환
    
    Returns:
        {
            "success": true,
            "devices_synced": 5,
            "total_actions": 42,
            "timestamp": "2024-01-01T12:00:00"
        }
    """
    try:
        logger.info("\n" + "="*60)
        logger.info("� 기기 동기화 시작 (Gateway → Local DB)")
        logger.info("="*60)
        
        success = await gateway_client.sync_all_devices_to_db()
        
        if success:
            # 동기화된 기기 수 계산
            all_devices = db.get_devices()
            total_devices = len(all_devices)
            total_actions = 0
            
            for device in all_devices:
                actions = db.get_device_actions(device.get("device_id"))
                total_actions += len(actions)
            
            logger.info("="*60)
            logger.info(f"✅ 동기화 완료!")
            logger.info(f"   - 동기화된 기기: {total_devices}개")
            logger.info(f"   - 총 액션: {total_actions}개")
            logger.info("="*60 + "\n")
            
            return {
                "success": True,
                "devices_synced": total_devices,
                "total_actions": total_actions,
                "timestamp": datetime.now().isoformat(),
                "message": f"성공: {total_devices}개 기기, {total_actions}개 액션"
            }
        else:
            logger.error("❌ 동기화 실패")
            return {
                "success": False,
                "message": "Gateway와의 동기화 실패",
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"❌ 동기화 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# ===============================================================================
# 📋 기기 목록 조회 엔드포인트 (로컬 DB)
# ===============================================================================

@router.get("/")
async def get_devices():
    """기능: 로컬 DB에서 기기 목록 + 각 기기의 사용 가능한 액션 조회.
    
    Flow:
    1. SQLite에서 devices 테이블 조회
    2. 각 기기의 device_actions 조회
    3. Frontend 호환 형식으로 응답
    
    Returns:
        {
            "success": true,
            "devices": [
                {
                    "device_id": "1d7c7408...",
                    "name": "거실 에어컨",
                    "device_type": "air_conditioner",
                    "actions": [
                        {
                            "id": 1,
                            "action_type": "operation",
                            "action_name": "POWER_ON_POWER_OFF",
                            "readable": true,
                            "writable": true,
                            "value_type": "enum",
                            "value_range": "[\"POWER_ON\", \"POWER_OFF\"]"
                        }
                    ]
                }
            ],
            "count": 5,
            "source": "local_db"
        }
    """
    try:
        logger.info("� 기기 목록 조회 (Local DB)")
        
        # 1️⃣ 로컬 DB에서 기기 목록 조회
        devices = db.get_devices()
        
        if not devices:
            logger.warning("⚠️  로컬 DB에 기기가 없음. 먼저 동기화 필요")
            return {
                "success": True,
                "devices": [],
                "count": 0,
                "source": "local_db",
                "message": "기기가 없습니다. POST /api/devices/sync를 실행해주세요."
            }
        
        # 2️⃣ 각 기기의 액션 조회
        device_list = []
        for device in devices:
            device_id = device.get("device_id")
            actions = db.get_device_actions(device_id)
            
            device_list.append({
                "device_id": device_id,
                "name": device.get("alias"),
                "device_type": device.get("device_type"),
                "model_name": device.get("model_name"),
                "actions": actions,
                "action_count": len(actions)
            })
        
        logger.info(f"✅ 기기 조회 성공: {len(device_list)}개")
        
        return {
            "success": True,
            "devices": device_list,
            "count": len(device_list),
            "source": "local_db"
        }
    
    except Exception as e:
        logger.error(f"❌ 기기 조회 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}"
        }


# ===============================================================================
# 🎯 기기 제어 엔드포인트
# ===============================================================================

@router.post("/{device_id}/click")
async def handle_device_action(device_id: str, request: DeviceClickRequest):
    """기능: 기기의 특정 액션 실행.
    
    Flow:
    1. 로컬 DB에서 기기 정보 조회
    2. AI-Services로 기기 제어 요청
    3. AI-Services → Gateway → LG ThinQ API
    4. 액션 성공 후 로컬 DB에 상태 저장 (Gateway 조회 없이)
    
    Args:
        device_id: 기기 ID
        request:
            - action: 액션명 (예: "purifier_on", "temp_25")
            - value: 액션 값 (선택사항)
    
    Returns:
        {
            "success": true,
            "device_id": "1d7c7408...",
            "device_name": "거실 에어컨",
            "device_type": "air_conditioner",
            "action": "temp_25",
            "message": "제어 성공"
        }
    """
    try:
        action = request.action
        value = request.value
        
        logger.info(f"🎯 기기 제어 요청:")
        logger.info(f"   - 기기 ID: {device_id}")
        logger.info(f"   - 액션: {action}")
        if value:
            logger.info(f"   - 값: {value}")
        
        # 1️⃣ 로컬 DB에서 기기 정보 조회
        device = db.get_device_by_id(device_id)
        if not device:
            logger.warning(f"❌ 기기를 찾을 수 없음: {device_id}")
            raise HTTPException(status_code=404, detail="기기를 찾을 수 없습니다")
        
        device_name = device.get("alias", device_id)
        device_type = device.get("device_type")
        
        logger.info(f"   - 기기명: {device_name}")
        logger.info(f"   - 기기타입: {device_type}")
        
        # 2️⃣ Gateway로 직접 기기 제어 요청 (AI-Services 우회)
        logger.info(f"🚀 Gateway로 직접 제어 요청 중...")
        
        # Gateway client 사용
        control_result = await gateway_client.control_device(
            device_id=device_id,
            action=action,
            value=value
        )
        
        success = control_result.get("success", False)
        message = control_result.get("message", "제어 완료")
        
        if success:
            logger.info(f"✅ Gateway 제어 성공: {message}")
        else:
            logger.warning(f"⚠️ Gateway 제어 실패: {message}")
        
        # 3️⃣ 액션 성공 후 로컬에 상태 저장 (Gateway 조회 없음)
        if success:
            from backend.services.device_state_manager import device_state_manager
            
            logger.info(f"💾 로컬 상태 저장 중...")
            device_state_manager.update_device_state_from_action(
                device_id=device_id,
                action=action,
                device_type=device_type,
                value=value
            )
        
        return {
            "success": success,
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "action": action,
            "value": value,
            "message": message
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 기기 제어 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "device_id": device_id,
            "message": f"오류: {str(e)}"
        }


# ===============================================================================
# ℹ️  기기 상세 정보 조회 엔드포인트
# ===============================================================================

@router.get("/{device_id}")
async def get_device_detail(device_id: str):
    """기능: 특정 기기의 상세 정보 + 모든 액션 조회.
    
    Args:
        device_id: 기기 ID
    
    Returns:
        {
            "success": true,
            "device_id": "1d7c7408...",
            "name": "거실 에어컨",
            "device_type": "air_conditioner",
            "model_name": "LG AC 2024",
            "device_profile": {...},
            "actions": [...]
        }
    """
    try:
        logger.info(f"ℹ️  기기 상세 정보 조회: {device_id}")
        
        device = db.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="기기를 찾을 수 없습니다")
        
        actions = db.get_device_actions(device_id)
        
        # device_profile은 JSON 문자열이므로 파싱
        device_profile = device.get("device_profile")
        if isinstance(device_profile, str):
            try:
                device_profile = json.loads(device_profile)
            except:
                device_profile = {}
        
        return {
            "success": True,
            "device_id": device_id,
            "name": device.get("alias"),
            "device_type": device.get("device_type"),
            "model_name": device.get("model_name"),
            "device_profile": device_profile,
            "actions": actions,
            "action_count": len(actions)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 기기 정보 조회 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}"
        }


# ===============================================================================
# 📋 기기 프로필 조회 엔드포인트 (사용 가능한 액션)
# ===============================================================================

@router.get("/{device_id}/profile")
async def get_device_profile(device_id: str):
    """기능: 특정 기기의 프로필 조회 (사용 가능한 모든 액션).
    
    Gateway의 /api/lg/devices/{deviceId}/profile에서 조회한 정보를 DB에서 반환합니다.
    
    Args:
        device_id: 기기 ID
    
    Returns:
        {
            "success": true,
            "device_id": "1d7c7408...",
            "name": "거실 공기청정기",
            "device_type": "air_purifier",
            "actions": [
                {
                    "id": 1,
                    "action_type": "operation",
                    "action_name": "POWER_ON",
                    "readable": true,
                    "writable": true,
                    "value_type": "enum",
                    "value_range": "[\"POWER_ON\", \"POWER_OFF\"]"
                },
                ...
            ]
        }
    """
    try:
        logger.info(f"📋 기기 프로필 조회: {device_id}")
        
        device = db.get_device_by_id(device_id)
        if not device:
            logger.warning(f"⚠️  기기를 찾을 수 없습니다: {device_id}")
            raise HTTPException(status_code=404, detail="기기를 찾을 수 없습니다")
        
        # DB에서 액션 조회
        actions = db.get_device_actions(device_id)
        
        logger.info(f"✅ 프로필 조회 성공: {len(actions)}개 액션")
        
        return {
            "success": True,
            "device_id": device_id,
            "name": device.get("alias"),
            "device_type": device.get("device_type"),
            "actions": actions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 프로필 조회 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}"
        }


# ===============================================================================
# 📊 기기 상태 조회 엔드포인트
# ===============================================================================

@router.get("/{device_id}/state")
async def get_device_state(device_id: str, force_gateway: bool = False):
    """기능: 특정 기기의 상태 조회.
    
    Flow:
    1. 초기 로그인 후: Gateway에서 조회 후 로컬 캐시에 저장
    2. 이후: 로컬 캐시 사용 (TTL 내)
    3. 캐시 만료 시: 다시 Gateway에서 조회
    4. force_gateway=true: 강제로 Gateway 조회
    
    Args:
        device_id: 기기 ID
        force_gateway: Gateway 강제 조회 여부
    
    Returns:
        {
            "success": true,
            "device_id": "device_123",
            "name": "거실 에어컨",
            "device_type": "air_conditioner",
            "state": { power: "ON", target_temp: 25, ... },
            "source": "cache" 또는 "gateway",
            "timestamp": "2025-10-28T12:30:45"
        }
    """
    try:
        from backend.services.device_state_manager import device_state_manager
        
        logger.info(f"📊 기기 상태 조회: {device_id}")
        
        # DB에서 기기 확인
        device = db.get_device_by_id(device_id)
        if not device:
            logger.warning(f"⚠️  기기를 찾을 수 없습니다: {device_id}")
            raise HTTPException(status_code=404, detail="기기를 찾을 수 없습니다")
        
        device_type = device.get("device_type")
        
        # 1️⃣ 로컬 캐시 우선 확인 (Gateway 강제 조회 아닐 때)
        if not force_gateway:
            cached_state = device_state_manager.get_device_state(device_id)
            if cached_state:
                logger.info(f"✅ 로컬 캐시에서 상태 조회")
                return {
                    "success": True,
                    "device_id": device_id,
                    "name": device.get("alias"),
                    "device_type": device_type,
                    "state": cached_state,
                    "source": "cache",
                    "timestamp": datetime.now().isoformat()
                }
        
        # 2️⃣ Gateway에서 조회 (초기 로그인 또는 캐시 만료 또는 강제 조회)
        logger.info(f"🌐 Gateway에서 상태 조회 중...")
        from backend.services.gateway_client import gateway_client
        
        state_response = await gateway_client.get_device_state(device_id)
        
        if not state_response or "error" in state_response:
            logger.warning(f"⚠️  Gateway에서 상태 조회 실패, 로컬 캐시 사용")
            
            # Gateway 실패 시 로컬 캐시로 폴백
            cached_state = device_state_manager.get_device_state(device_id)
            if cached_state:
                logger.info(f"✅ 로컬 캐시로 폴백")
                return {
                    "success": True,
                    "device_id": device_id,
                    "name": device.get("alias"),
                    "device_type": device_type,
                    "state": cached_state,
                    "source": "cache_fallback",
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "success": False,
                "device_id": device_id,
                "message": "Gateway 상태 조회 실패 및 캐시 없음",
                "error": state_response.get("error") if isinstance(state_response, dict) else str(state_response)
            }
        
        # 3️⃣ Gateway에서 조회한 상태를 로컬 캐시에 저장
        state_data = state_response
        device_state_manager.save_device_state(device_id, state_data, source="gateway")
        
        logger.info(f"✅ Gateway에서 상태 조회 및 로컬 캐시 저장")
        
        return {
            "success": True,
            "device_id": device_id,
            "name": device.get("alias"),
            "device_type": device_type,
            "state": state_data,
            "source": "gateway",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ 상태 조회 중 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}"
        }


# ===============================================================================
# 🎮 디바이스 액션 관리 엔드포인트
# ===============================================================================

from backend.core.device_actions import (
    get_device_actions,
    get_action_info,
    validate_action,
    get_supported_device_types,
    format_action_for_display,
    get_action_color,
)


@router.get("/actions/types")
async def get_action_types():
    """기능: 지원하는 기기 타입 조회.
    
    Returns:
        {
            "success": true,
            "device_types": ["air_purifier", "air_conditioner"],
            "count": 2
        }
    """
    try:
        device_types = get_supported_device_types()
        logger.info(f"✅ 지원하는 기기 타입 조회: {len(device_types)}개")
        
        return {
            "success": True,
            "device_types": device_types,
            "count": len(device_types)
        }
    except Exception as e:
        logger.error(f"❌ 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}"
        }


@router.get("/actions/{device_type}")
async def get_device_type_actions(device_type: str):
    """기능: 특정 기기 타입의 모든 액션 조회.
    
    Args:
        device_type: 기기 타입 (air_purifier, air_conditioner)
    
    Returns:
        {
            "success": true,
            "device_type": "air_purifier",
            "actions": {
                "purifier_on": {
                    "name": "전원 켜기",
                    "description": "공기청정기를 켭니다",
                    "type": "power",
                    "category": "operation",
                    "icon": "Power",
                    "value": null
                },
                ...
            },
            "count": 13
        }
    """
    try:
        actions = get_device_actions(device_type)
        
        if not actions:
            logger.warning(f"⚠️  지원하지 않는 기기 타입: {device_type}")
            return {
                "success": False,
                "message": f"지원하지 않는 기기 타입: {device_type}"
            }
        
        # 액션 정보를 프론트엔드 포맷으로 변환
        formatted_actions = {}
        for action_name, action_info in actions.items():
            formatted_actions[action_name] = format_action_for_display(action_info)
        
        logger.info(f"✅ {device_type} 액션 조회: {len(actions)}개")
        
        return {
            "success": True,
            "device_type": device_type,
            "actions": formatted_actions,
            "count": len(actions)
        }
    
    except Exception as e:
        logger.error(f"❌ 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}"
        }


@router.get("/actions/{device_type}/{action}")
async def get_action_detail(device_type: str, action: str):
    """기능: 특정 액션의 상세 정보 조회.
    
    Args:
        device_type: 기기 타입
        action: 액션명
    
    Returns:
        {
            "success": true,
            "device_type": "air_purifier",
            "action": "purifier_on",
            "info": {
                "name": "전원 켜기",
                "description": "공기청정기를 켭니다",
                "type": "power",
                "category": "operation",
                "icon": "Power",
                "value": null,
                "color": "#FF6B6B"
            },
            "is_valid": true
        }
    """
    try:
        action_info = get_action_info(device_type, action)
        is_valid = validate_action(device_type, action)
        
        if not is_valid:
            logger.warning(f"⚠️  유효하지 않은 액션: {device_type}/{action}")
            return {
                "success": False,
                "device_type": device_type,
                "action": action,
                "is_valid": False,
                "message": f"유효하지 않은 액션: {action}"
            }
        
        formatted_info = format_action_for_display(action_info)
        formatted_info["color"] = get_action_color(action_info.get("type"))
        
        logger.info(f"✅ 액션 상세 조회: {device_type}/{action}")
        
        return {
            "success": True,
            "device_type": device_type,
            "action": action,
            "info": formatted_info,
            "is_valid": is_valid
        }
    
    except Exception as e:
        logger.error(f"❌ 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류: {str(e)}"
        }

