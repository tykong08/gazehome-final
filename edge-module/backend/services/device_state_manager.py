"""
로컬 디바이스 상태 관리 서비스.

기능:
1. 액션 실행 후 로컬에 디바이스 상태 저장
2. Gateway에서 조회한 상태를 로컬에 캐싱
3. 초기 로그인 시에만 Gateway에서 전체 상태 조회
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# 로컬 상태 저장 경로
STATE_CACHE_DIR = Path("./data/device_states")
STATE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class DeviceStateManager:
    """디바이스 상태 로컬 관리자."""
    
    def __init__(self):
        """초기화."""
        self.cache_ttl = 3600  # 1시간 (초기 로그인 후 캐시 유지 시간)
        self.device_states: Dict[str, Dict[str, Any]] = {}
        self.last_gateway_sync: Optional[datetime] = None
    
    def get_cache_file(self, device_id: str) -> Path:
        """디바이스 캐시 파일 경로 반환."""
        return STATE_CACHE_DIR / f"{device_id}.json"
    
    def save_device_state(
        self,
        device_id: str,
        state: Dict[str, Any],
        source: str = "gateway"
    ) -> bool:
        """디바이스 상태를 로컬에 저장.
        
        Args:
            device_id: 기기 ID
            state: 기기 상태 정보
            source: 상태 출처 (gateway, action, cache)
        
        Returns:
            저장 성공 여부
        """
        try:
            state_data = {
                "device_id": device_id,
                "state": state,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "cache_until": (datetime.now() + timedelta(seconds=self.cache_ttl)).isoformat()
            }
            
            cache_file = self.get_cache_file(device_id)
            cache_file.write_text(json.dumps(state_data, indent=2, ensure_ascii=False))
            
            # 메모리 캐시도 업데이트
            self.device_states[device_id] = state_data
            
            logger.info(f"✅ 디바이스 상태 저장: {device_id} (source: {source})")
            logger.info(f"   - 상태: {state}")
            
            return True
        except Exception as e:
            logger.error(f"❌ 디바이스 상태 저장 실패: {device_id} - {e}")
            return False
    
    def get_device_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """로컬에서 디바이스 상태 조회.
        
        Args:
            device_id: 기기 ID
        
        Returns:
            기기 상태 정보 또는 None
        """
        try:
            # 1. 메모리 캐시 먼저 확인
            if device_id in self.device_states:
                cached_data = self.device_states[device_id]
                cache_until = datetime.fromisoformat(cached_data.get("cache_until", ""))
                
                if datetime.now() < cache_until:
                    logger.info(f"✅ 메모리 캐시에서 상태 조회: {device_id}")
                    return cached_data.get("state")
                else:
                    logger.info(f"⚠️  메모리 캐시 만료: {device_id}")
                    del self.device_states[device_id]
            
            # 2. 파일 캐시 확인
            cache_file = self.get_cache_file(device_id)
            if cache_file.exists():
                cached_data = json.loads(cache_file.read_text())
                cache_until = datetime.fromisoformat(cached_data.get("cache_until", ""))
                
                if datetime.now() < cache_until:
                    logger.info(f"✅ 파일 캐시에서 상태 조회: {device_id}")
                    # 메모리 캐시에도 업데이트
                    self.device_states[device_id] = cached_data
                    return cached_data.get("state")
                else:
                    logger.info(f"⚠️  파일 캐시 만료: {device_id}")
            
            logger.info(f"ℹ️  캐시된 상태 없음: {device_id}")
            return None
        
        except Exception as e:
            logger.error(f"❌ 상태 조회 오류: {device_id} - {e}")
            return None
    
    def update_device_state_from_action(
        self,
        device_id: str,
        action: str,
        device_type: str,
        value: Optional[Any] = None
    ) -> bool:
        """액션 실행 후 로컬 상태 업데이트.
        
        Args:
            device_id: 기기 ID
            action: 실행한 액션 (예: purifier_on, temp_25)
            device_type: 기기 타입 (air_purifier, air_conditioner)
            value: 액션 값
        
        Returns:
            업데이트 성공 여부
        """
        try:
            # 기존 상태 가져오기
            current_state = self.get_device_state(device_id) or {}
            device_type_lower = device_type.lower()
            
            # 액션에 따라 상태 업데이트
            if device_type_lower.startswith("purifier") or device_type_lower == "air_purifier":
                self._update_purifier_state(current_state, action, value)
            elif device_type_lower.startswith("aircon") or device_type_lower == "air_conditioner":
                self._update_aircon_state(current_state, action, value)
            
            # 로컬에 저장
            return self.save_device_state(device_id, current_state, source="action")
        
        except Exception as e:
            logger.error(f"❌ 상태 업데이트 실패: {device_id}/{action} - {e}")
            return False
    
    @staticmethod
    def _update_purifier_state(
        state: Dict[str, Any],
        action: str,
        value: Optional[Any] = None
    ) -> None:
        """공기청정기 상태 업데이트."""
        if action == "purifier_on":
            state["power"] = "ON"
        elif action == "purifier_off":
            state["power"] = "OFF"
        elif action.startswith("wind_"):
            state["wind_strength"] = action.replace("wind_", "").upper()
        elif action in ["circulator", "clean", "auto"]:
            state["mode"] = action.upper()
    
    @staticmethod
    def _update_aircon_state(
        state: Dict[str, Any],
        action: str,
        value: Optional[Any] = None
    ) -> None:
        """에어컨 상태 업데이트."""
        if action == "aircon_on":
            state["power"] = "ON"
        elif action == "aircon_off":
            state["power"] = "OFF"
        elif action.startswith("aircon_wind_"):
            state["wind_strength"] = action.replace("aircon_wind_", "").upper()
        elif action.startswith("temp_"):
            try:
                temp_str = action.replace("temp_", "")
                state["target_temp"] = int(temp_str)
            except ValueError:
                logger.warning(f"⚠️  온도 파싱 실패: {action}")
    
    def clear_cache(self, device_id: Optional[str] = None) -> bool:
        """캐시 삭제.
        
        Args:
            device_id: 특정 기기 ID (None이면 전체 삭제)
        
        Returns:
            삭제 성공 여부
        """
        try:
            if device_id:
                # 특정 기기 캐시 삭제
                if device_id in self.device_states:
                    del self.device_states[device_id]
                cache_file = self.get_cache_file(device_id)
                if cache_file.exists():
                    cache_file.unlink()
                logger.info(f"✅ 캐시 삭제: {device_id}")
            else:
                # 전체 캐시 삭제
                self.device_states.clear()
                for cache_file in STATE_CACHE_DIR.glob("*.json"):
                    cache_file.unlink()
                logger.info(f"✅ 전체 캐시 삭제")
            
            return True
        except Exception as e:
            logger.error(f"❌ 캐시 삭제 실패: {e}")
            return False
    
    def mark_gateway_synced(self) -> None:
        """Gateway 동기화 완료 표시."""
        self.last_gateway_sync = datetime.now()
        logger.info(f"📊 Gateway 동기화 완료: {self.last_gateway_sync.isoformat()}")
    
    def should_sync_with_gateway(self, force: bool = False) -> bool:
        """Gateway와 동기화할지 여부 판단.
        
        Args:
            force: 강제 동기화 여부
        
        Returns:
            동기화 필요 여부
        """
        if force:
            return True
        
        if self.last_gateway_sync is None:
            logger.info("📊 처음 로그인 후 Gateway 동기화 필요")
            return True
        
        # 캐시 TTL이 지나면 다시 동기화
        elapsed = (datetime.now() - self.last_gateway_sync).total_seconds()
        if elapsed > self.cache_ttl:
            logger.info(f"📊 캐시 만료 - Gateway 동기화 필요 (경과: {elapsed:.0f}초)")
            return True
        
        logger.info(f"✅ 캐시 유효 - Gateway 동기화 불필요 (남은 시간: {self.cache_ttl - elapsed:.0f}초)")
        return False


# 전역 인스턴스
device_state_manager = DeviceStateManager()
