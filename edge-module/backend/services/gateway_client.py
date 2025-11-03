"""Gateway와의 직접 통신을 담당하는 클라이언트."""
from __future__ import annotations

import logging
import httpx
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.core.config import settings
from backend.core.database import db

logger = logging.getLogger(__name__)


class GatewayClient:
    """Gateway 직접 통신 클라이언트.
    
    ✅ 기기 목록: Gateway에서 직접 조회
    ✅ 기기 프로필: Gateway에서 직접 조회 (기능 상세 정보)
    ✅ 로컬 DB 동기화: 기기 및 액션 저장
    ❌ 기기 제어: AI-Services 경유
    """
    
    def __init__(self):
        """Gateway 클라이언트 초기화."""
        self.gateway_url = settings.gateway_url.rstrip('/')
        self.devices_endpoint = settings.gateway_devices_endpoint.rstrip('/')
        self.timeout = settings.gateway_request_timeout
        logger.info(f"✅ GatewayClient 초기화: {self.gateway_url}")
        logger.info(f"   - 기기 목록 API: GET {self.devices_endpoint}")
        logger.info(f"   - 기기 프로필 API: GET {self.gateway_url}/api/lg/devices/{{deviceId}}/profile")
    
    async def get_devices(self) -> Dict[str, Any]:
        """Gateway에서 기기 목록 조회 (직접).
        
        Edge-Module이 Gateway에서 직접 기기 목록을 조회합니다.
        
        Returns:
            기기 목록 (표준화된 형식)
            {
                "success": True,
                "devices": [
                    {
                        "device_id": "1d7c7408c31fbaf9ce2ea8634e2eda53f517d835a61440a4f75c5426eadc054a",
                        "name": "거실 공기청정기",
                        "device_type": "air_purifier",
                        "state": "on",
                        "supported_actions": ["turn_on", "turn_off", "clean", "auto"]
                    }
                ],
                "count": 1
            }
        """
        for attempt in range(3):
            try:
                logger.info(f"🔍 Gateway에서 기기 목록 조회 (시도 {attempt + 1}/3)")
                logger.info(f"   - URL: {self.devices_endpoint}")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        self.devices_endpoint,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Gateway 응답 형식: {"response": [...]}
                        devices_raw = result.get("response", [])
                        
                        # 표준화된 형식으로 변환
                        devices = []
                        for device in devices_raw:
                            try:
                                device_info = device.get("deviceInfo", {})
                                
                                formatted_device = {
                                    "device_id": device.get("deviceId"),
                                    "name": device_info.get("alias", "Unknown Device"),
                                    "device_type": device_info.get("deviceType", "unknown").lower(),
                                    "state": self._normalize_state(device.get("status", "offline")),
                                    "supported_actions": device_info.get("supportedActions", [])
                                }
                                
                                devices.append(formatted_device)
                                logger.debug(f"  ✓ {formatted_device['name']} ({formatted_device['device_id']})")
                                
                            except Exception as e:
                                logger.warning(f"  ⚠️  기기 변환 실패: {device} - {e}")
                                continue
                        
                        logger.info(f"✅ Gateway 기기 조회 성공: {len(devices)}개 기기")
                        
                        return {
                            "success": True,
                            "devices": devices,
                            "count": len(devices),
                            "source": "gateway"
                        }
                    
                    else:
                        logger.warning(f"⚠️  Gateway 응답 에러: status={response.status_code}")
                        logger.warning(f"   - Response: {response.text[:200]}")
                        
            except httpx.TimeoutException:
                logger.warning(f"⏱️  Gateway 요청 타임아웃 (시도 {attempt + 1}/3)")
            except httpx.RequestError as e:
                logger.warning(f"❌ Gateway 통신 에러: {e} (시도 {attempt + 1}/3)")
            except Exception as e:
                logger.warning(f"❌ 예상치 못한 에러: {e} (시도 {attempt + 1}/3)")
        
        logger.error(f"❌ Gateway 기기 조회 최종 실패")
        return {
            "success": False,
            "devices": [],
            "count": 0,
            "source": "gateway_failed"
        }
    
    async def get_device_profile(self, device_id: str) -> Dict[str, Any]:
        """Gateway에서 특정 기기의 프로필 조회 (상세 기능 정보).
        
        Args:
            device_id: 기기 ID
        
        Returns:
            기기 프로필 (작업, 타이머, 알림 등)
        """
        profile_url = f"{self.gateway_url}/api/lg/devices/{device_id}/profile"
        
        for attempt in range(3):
            try:
                logger.debug(f"🔍 기기 프로필 조회: {device_id} (시도 {attempt + 1}/3)")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        profile_url,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        profile = response.json()
                        logger.debug(f"   ✓ 프로필 조회 성공: {device_id}")
                        return profile
                    else:
                        logger.warning(f"⚠️  프로필 조회 실패: status={response.status_code}")
                        
            except httpx.TimeoutException:
                logger.warning(f"⏱️  프로필 조회 타임아웃 (시도 {attempt + 1}/3)")
            except Exception as e:
                logger.warning(f"❌ 프로필 조회 에러: {e} (시도 {attempt + 1}/3)")
        
        logger.error(f"❌ 프로필 조회 실패: {device_id}")
        return {}
    
    def _extract_device_actions(self, device_type: str, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """기기 프로필에서 사용 가능한 액션 추출.
        
        Args:
            device_type: 기기 유형 (air_conditioner, dryer, etc.)
            profile: 기기 프로필 데이터
        
        Returns:
            액션 리스트
        """
        actions = []
        
        try:
            # 프로필 구조:
            # {
            #   "property": {...},
            #   "operation": [...],
            #   "timer": {...},
            #   "notification": {...}
            # }
            
            # 1️⃣ operation에서 액션 추출
            operations = profile.get("operation", [])
            if isinstance(operations, list):
                for op in operations:
                    op_name = op.get("_comment", "")
                    commands = op.get("command", {})
                    
                    for cmd_name, cmd_data in commands.items():
                        if isinstance(cmd_data, dict):
                            # 각 명령어가 여러 옵션을 가질 수 있음
                            write_data = cmd_data.get("_write", {})
                            
                            for write_name, write_values in write_data.items():
                                if isinstance(write_values, dict):
                                    value_options = write_values.get("_value", [])
                                    
                                    # 각 옵션을 별도 액션으로 생성
                                    for value in value_options:
                                        actions.append({
                                            "action_type": "operation",
                                            "action_name": f"{write_name}_{value}",
                                            "readable": True,
                                            "writable": True,
                                            "value_type": "enum",
                                            "value_range": json.dumps(value_options)
                                        })
                                elif isinstance(write_values, list):
                                    # 값이 리스트인 경우
                                    actions.append({
                                        "action_type": "operation",
                                        "action_name": write_name,
                                        "readable": True,
                                        "writable": True,
                                        "value_type": "enum",
                                        "value_range": json.dumps(write_values)
                                    })
            
            # 2️⃣ property에서 제어 가능한 속성 추출
            properties = profile.get("property", {})
            if isinstance(properties, dict):
                for prop_name, prop_data in properties.items():
                    if isinstance(prop_data, dict):
                        # property → operation → XXX → w/r 구조
                        operations = prop_data.get("operation", {})
                        if isinstance(operations, dict):
                            for op_name, op_data in operations.items():
                                write_values = op_data.get("w", [])
                                if write_values:
                                    actions.append({
                                        "action_type": "property",
                                        "action_name": f"{prop_name}_{op_name}",
                                        "readable": bool(op_data.get("r")),
                                        "writable": bool(op_data.get("w")),
                                        "value_type": "enum" if isinstance(write_values, list) else "range",
                                        "value_range": json.dumps(write_values)
                                    })
            
            # 3️⃣ timer에서 액션 추출
            timers = profile.get("timer", {})
            if isinstance(timers, dict):
                for timer_name, timer_data in timers.items():
                    if isinstance(timer_data, dict):
                        actions.append({
                            "action_type": "timer",
                            "action_name": timer_name,
                            "readable": True,
                            "writable": True,
                            "value_type": "integer",
                            "value_range": json.dumps(timer_data.get("_value", []))
                        })
            
            logger.info(f"   ✓ 추출된 액션: {len(actions)}개")
            return actions
            
        except Exception as e:
            logger.error(f"❌ 액션 추출 실패: {e}")
            return []
    
    async def sync_all_devices_to_db(self) -> bool:
        """Gateway의 모든 기기를 조회해서 로컬 DB에 동기화.
        
        1. Gateway /api/lg/devices 조회
        2. 각 기기의 /api/lg/devices/{id}/profile 조회
        3. 기기 정보 + 액션을 로컬 DB에 저장
        
        Returns:
            동기화 성공 여부
        """
        try:
            logger.info("=" * 60)
            logger.info("🔄 Gateway 기기 동기화 시작")
            logger.info("=" * 60)
            
            # Step 1: 기기 목록 조회
            devices_result = await self.get_devices()
            if not devices_result.get("success"):
                logger.error("❌ 기기 목록 조회 실패")
                return False
            
            devices = devices_result.get("devices", [])
            logger.info(f"📋 조회된 기기: {len(devices)}개\n")
            
            # Step 2: 각 기기 프로필 조회 및 DB 저장
            for idx, device in enumerate(devices, 1):
                device_id = device.get("device_id")
                device_type = device.get("device_type", "unknown")
                alias = device.get("name", "Unknown Device")
                
                logger.info(f"{idx}. [{device_type.upper()}] {alias}")
                logger.info(f"   Device ID: {device_id}")
                
                # 프로필 조회
                profile = await self.get_device_profile(device_id)
                
                if not profile:
                    logger.warning(f"   ⚠️  프로필 조회 실패, 기본 정보만 저장")
                    profile = {}
                
                # 액션 추출
                actions = self._extract_device_actions(device_type, profile)
                logger.info(f"   📌 액션: {len(actions)}개\n")
                
                # DB 저장
                # 1. 기기 정보 저장
                db.save_device(
                    device_id=device_id,
                    device_type=device_type,
                    alias=alias,
                    model_name=device.get("model_name"),
                    reportable=device.get("reportable", True),
                    device_profile=json.dumps(profile)
                )
                
                # 2. 기기 액션 저장
                if actions:
                    db.save_device_actions(device_id, actions)
            
            logger.info("=" * 60)
            logger.info(f"✅ 동기화 완료: {len(devices)}개 기기 저장됨")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 동기화 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_device_state(self, device_id: str) -> Dict[str, Any]:
        """기기의 실시간 상태 조회 (Gateway 경유).
        
        Gateway의 /api/lg/devices/{device_id}/status 엔드포인트를 호출합니다.
        (주의: /state 엔드포인트는 404 Not Found를 반환하므로 /status를 사용합니다)
        
        Args:
            device_id: 기기 ID
        
        Returns:
            기기 상태 데이터
            {
                "device_id": "...",
                "type": "aircon",
                "power": "POWER_OFF" or "POWER_ON",
                "mode": "COOL",
                "current_temp": 22,
                "target_temp": 25,
                "wind_strength": "MID"
            }
        """
        # /state 대신 /status 엔드포인트 사용
        state_url = f"{self.gateway_url}/api/lg/devices/{device_id}/status"
        
        for attempt in range(3):
            try:
                logger.debug(f"📊 기기 상태 조회: {device_id} (시도 {attempt + 1}/3)")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        state_url,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        state = response.json()
                        logger.debug(f"   ✓ 상태 조회 성공: {device_id}")
                        return state
                    else:
                        logger.warning(f"⚠️  상태 조회 실패: status={response.status_code}")
                        
            except httpx.TimeoutException:
                logger.warning(f"⏱️  상태 조회 타임아웃 (시도 {attempt + 1}/3)")
            except Exception as e:
                logger.warning(f"❌ 상태 조회 에러: {e} (시도 {attempt + 1}/3)")
        
        logger.error(f"❌ 상태 조회 실패: {device_id}")
        return {"error": "상태 조회 실패"}
    
    async def control_device(
        self, 
        device_id: str, 
        action: str, 
        value: Optional[Any] = None
    ) -> Dict[str, Any]:
        """기기 제어 명령을 Gateway로 직접 전송.
        
        Gateway의 /api/lg/control 엔드포인트를 호출하여 기기를 제어합니다.
        
        Args:
            device_id: 기기 ID
            action: 액션명 (예: "purifier_on", "temp_25")
            value: 액션 값 (선택사항)
        
        Returns:
            제어 결과
            {
                "success": true/false,
                "message": "제어 완료" or 에러 메시지,
                "device_id": "...",
                "action": "..."
            }
        """
        control_url = f"{self.gateway_url}/api/lg/control"
        
        # Gateway control 요청 페이로드
        payload = {
            "device_id": device_id,
            "action": action
        }
        
        if value is not None:
            payload["value"] = value
        
        try:
            logger.info(f"🎮 Gateway로 기기 제어:")
            logger.info(f"   - URL: {control_url}")
            logger.info(f"   - 기기: {device_id}")
            logger.info(f"   - 액션: {action}")
            if value:
                logger.info(f"   - 값: {value}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    control_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    message = result.get("message", "기기 제어 완료")
                    
                    logger.info(f"✅ Gateway 제어 성공: {message}")
                    
                    return {
                        "success": True,
                        "message": message,
                        "device_id": device_id,
                        "action": action
                    }
                else:
                    error_text = response.text
                    logger.error(f"❌ Gateway 제어 실패:")
                    logger.error(f"   Status: {response.status_code}")
                    logger.error(f"   Detail: {error_text}")
                    
                    return {
                        "success": False,
                        "message": f"Gateway 제어 실패: {error_text}",
                        "device_id": device_id,
                        "action": action
                    }
                    
        except httpx.TimeoutException:
            logger.error(f"❌ Gateway 통신 타임아웃: {device_id}")
            return {
                "success": False,
                "message": f"Gateway 통신 타임아웃 ({self.timeout}초)",
                "device_id": device_id,
                "action": action
            }
        except Exception as e:
            logger.error(f"❌ 기기 제어 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"기기 제어 실패: {str(e)}",
                "device_id": device_id,
                "action": action
            }
    
    @staticmethod
    def _normalize_state(status: str) -> str:
        """상태 정규화 (on/off).
        
        Gateway 응답을 on/off로 통일합니다.
        """
        status_lower = str(status).lower()
        
        if status_lower in ["on", "true", "1", "active", "running"]:
            return "on"
        elif status_lower in ["off", "false", "0", "inactive", "stopped", "offline"]:
            return "off"
        else:
            return "offline"


# 전역 Gateway 클라이언트 인스턴스
gateway_client = GatewayClient()
