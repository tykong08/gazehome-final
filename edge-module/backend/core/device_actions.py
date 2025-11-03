"""스마트 디바이스 액션 정의 및 관리.

공기청정기(Air Purifier):
- 작동 제어: purifier_on, purifier_off
- 바람 세기: wind_low, wind_mid, wind_high, wind_auto, wind_power
- 실행 모드: circulator, clean, auto

에어컨(Air Conditioner):
- 작동 제어: aircon_on, aircon_off
- 바람 세기: aircon_wind_low, aircon_wind_mid, aircon_wind_high, aircon_wind_auto
- 온도 설정: temp_18 ~ temp_30

"""
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class DeviceType(str, Enum):
    """지원하는 기기 타입."""
    AIR_PURIFIER = "air_purifier"
    AIRCON = "air_conditioner"  # aircon, airconditioner 모두 지원


class ActionType(str, Enum):
    """액션의 종류."""
    POWER = "power"          # 전원 on/off
    MODE = "mode"            # 작동 모드
    WIND = "wind"            # 바람 세기
    TEMPERATURE = "temperature"  # 온도 설정


# ===============================================================================
# 📋 공기청정기(Air Purifier) 액션 정의
# ===============================================================================

PURIFIER_ACTIONS = {
    # 작동 제어
    "purifier_on": {
        "name": "전원 켜기",
        "description": "공기청정기를 켭니다",
        "type": ActionType.POWER,
        "category": "operation",
        "icon": "Power",
        "value": None,
    },
    "purifier_off": {
        "name": "전원 끄기",
        "description": "공기청정기를 끕니다",
        "type": ActionType.POWER,
        "category": "operation",
        "icon": "PowerOff",
        "value": None,
    },
    
    # 바람 세기 조정
    "wind_low": {
        "name": "약",
        "description": "공기청정기 바람을 약으로 설정합니다",
        "type": ActionType.WIND,
        "category": "wind_strength",
        "icon": "Wind",
        "value": "low",
    },
    "wind_mid": {
        "name": "중",
        "description": "공기청정기 바람을 중으로 설정합니다",
        "type": ActionType.WIND,
        "category": "wind_strength",
        "icon": "Wind",
        "value": "mid",
    },
    "wind_high": {
        "name": "강",
        "description": "공기청정기 바람을 강으로 설정합니다",
        "type": ActionType.WIND,
        "category": "wind_strength",
        "icon": "Wind",
        "value": "high",
    },
    "wind_auto": {
        "name": "자동",
        "description": "공기청정기 바람을 자동으로 설정합니다",
        "type": ActionType.WIND,
        "category": "wind_strength",
        "icon": "Wind",
        "value": "auto",
    },
    "wind_power": {
        "name": "파워",
        "description": "공기청정기 바람을 파워로 설정합니다",
        "type": ActionType.WIND,
        "category": "wind_strength",
        "icon": "Wind",
        "value": "power",
    },
    
    # 실행 모드
    "circulator": {
        "name": "순환 모드",
        "description": "공기청정기를 순환 모드로 설정합니다",
        "type": ActionType.MODE,
        "category": "operation_mode",
        "icon": "Repeat",
        "value": "circulator",
    },
    "clean": {
        "name": "청정 모드",
        "description": "공기청정기를 청정 모드로 설정합니다",
        "type": ActionType.MODE,
        "category": "operation_mode",
        "icon": "Leaf",
        "value": "clean",
    },
    "auto": {
        "name": "자동 모드",
        "description": "공기청정기를 자동 모드로 설정합니다",
        "type": ActionType.MODE,
        "category": "operation_mode",
        "icon": "Zap",
        "value": "auto",
    },
}


# ===============================================================================
# ❄️  에어컨(Air Conditioner) 액션 정의
# ===============================================================================

AIRCON_ACTIONS = {
    # 작동 제어
    "aircon_on": {
        "name": "전원 켜기",
        "description": "에어컨을 켭니다",
        "type": ActionType.POWER,
        "category": "operation",
        "icon": "Power",
        "value": None,
    },
    "aircon_off": {
        "name": "전원 끄기",
        "description": "에어컨을 끕니다",
        "type": ActionType.POWER,
        "category": "operation",
        "icon": "PowerOff",
        "value": None,
    },
    
    # 바람 세기 조정
    "aircon_wind_low": {
        "name": "약",
        "description": "에어컨 바람을 약으로 설정합니다",
        "type": ActionType.WIND,
        "category": "wind_strength",
        "icon": "Wind",
        "value": "low",
    },
    "aircon_wind_mid": {
        "name": "중",
        "description": "에어컨 바람을 중으로 설정합니다",
        "type": ActionType.WIND,
        "category": "wind_strength",
        "icon": "Wind",
        "value": "mid",
    },
    "aircon_wind_high": {
        "name": "강",
        "description": "에어컨 바람을 강으로 설정합니다",
        "type": ActionType.WIND,
        "category": "wind_strength",
        "icon": "Wind",
        "value": "high",
    },
    "aircon_wind_auto": {
        "name": "자동",
        "description": "에어컨 바람을 자동으로 설정합니다",
        "type": ActionType.WIND,
        "category": "wind_strength",
        "icon": "Wind",
        "value": "auto",
    },
}

# 온도 액션 (18°C ~ 30°C)
for temp in range(18, 31):
    AIRCON_ACTIONS[f"temp_{temp}"] = {
        "name": f"{temp}°C",
        "description": f"에어컨 온도를 {temp}°C로 설정합니다",
        "type": ActionType.TEMPERATURE,
        "category": "temperature",
        "icon": "Thermometer",
        "value": temp,
    }


# ===============================================================================
# 🛠️  유틸리티 함수
# ===============================================================================

def get_device_actions(device_type: str) -> Dict[str, Dict[str, Any]]:
    """기기 타입별 모든 액션 반환.
    
    Args:
        device_type: 기기 타입 (air_purifier, air_conditioner)
    
    Returns:
        액션 딕셔너리
    """
    device_type = device_type.lower()
    
    if device_type in ["air_purifier", "purifier"]:
        return PURIFIER_ACTIONS
    elif device_type in ["air_conditioner", "aircon", "airconditioner"]:
        return AIRCON_ACTIONS
    else:
        return {}


def get_action_info(device_type: str, action: str) -> Optional[Dict[str, Any]]:
    """특정 액션의 정보 반환.
    
    Args:
        device_type: 기기 타입
        action: 액션명
    
    Returns:
        액션 정보 또는 None
    """
    actions = get_device_actions(device_type)
    return actions.get(action)


def validate_action(device_type: str, action: str) -> bool:
    """액션이 유효한지 확인.
    
    Args:
        device_type: 기기 타입
        action: 액션명
    
    Returns:
        유효 여부
    """
    actions = get_device_actions(device_type)
    return action in actions


def get_supported_device_types() -> List[str]:
    """지원하는 기기 타입 반환."""
    return [DeviceType.AIR_PURIFIER.value, DeviceType.AIRCON.value]


def format_action_for_display(action_info: Dict[str, Any]) -> Dict[str, Any]:
    """액션 정보를 프론트엔드 표시용으로 포맷팅.
    
    Args:
        action_info: 액션 정보
    
    Returns:
        포맷팅된 정보
    """
    if not action_info:
        return {}
    
    return {
        "name": action_info.get("name", ""),
        "description": action_info.get("description", ""),
        "type": action_info.get("type", "").value if hasattr(action_info.get("type"), "value") else action_info.get("type", ""),
        "category": action_info.get("category", ""),
        "icon": action_info.get("icon", "Zap"),
        "value": action_info.get("value"),
    }


def get_action_color(action_type: str) -> str:
    """액션 타입별 색상 코드 반환.
    
    Args:
        action_type: 액션 타입 (power, wind, mode, temperature)
    
    Returns:
        색상 코드 (hex)
    """
    color_map = {
        ActionType.POWER: "#FF6B6B",          # 빨강 (전원)
        ActionType.WIND: "#4ECDC4",           # 청록 (바람)
        ActionType.MODE: "#45B7D1",           # 파랑 (모드)
        ActionType.TEMPERATURE: "#FFA07A",    # 주황 (온도)
    }
    return color_map.get(action_type, "#9E9E9E")
