/**
 * 디바이스 액션 관리 유틸리티
 * 
 * 기능:
 * 1. 백엔드에서 디바이스 액션 정보 조회
 * 2. 액션별 색상, 아이콘 매핑
 * 3. 액션 정보 포맷팅
 */

const API_BASE = '/api/devices'

/**
 * 지원하는 디바이스 타입 조회
 * @returns {Promise<string[]>}
 */
export async function getDeviceTypes() {
    try {
        const response = await fetch(`${API_BASE}/actions/types`)
        const data = await response.json()

        if (data.success) {
            return data.device_types || []
        }
        console.error('getDeviceTypes error:', data.message)
        return []
    } catch (error) {
        console.error('Failed to fetch device types:', error)
        return []
    }
}

/**
 * 특정 디바이스 타입의 모든 액션 조회
 * @param {string} deviceType - 디바이스 타입 (air_purifier, air_conditioner)
 * @returns {Promise<Object>} 액션 정보 객체
 */
export async function getDeviceActions(deviceType) {
    try {
        const response = await fetch(`${API_BASE}/actions/${deviceType}`)
        const data = await response.json()

        if (data.success) {
            return data.actions || {}
        }
        console.error('getDeviceActions error:', data.message)
        return {}
    } catch (error) {
        console.error(`Failed to fetch actions for ${deviceType}:`, error)
        return {}
    }
}

/**
 * 특정 액션의 상세 정보 조회
 * @param {string} deviceType - 디바이스 타입
 * @param {string} action - 액션명
 * @returns {Promise<Object|null>} 액션 상세 정보
 */
export async function getActionInfo(deviceType, action) {
    try {
        const response = await fetch(`${API_BASE}/actions/${deviceType}/${action}`)
        const data = await response.json()

        if (data.success && data.is_valid) {
            return data.info || null
        }
        console.error('getActionInfo error:', data.message)
        return null
    } catch (error) {
        console.error(`Failed to fetch action info for ${deviceType}/${action}:`, error)
        return null
    }
}

/**
 * 액션 타입별 기본 색상
 */
export const ACTION_COLORS = {
    'power': '#FF6B6B',           // 빨강
    'wind': '#4ECDC4',            // 청록
    'mode': '#45B7D1',            // 파랑
    'temperature': '#FFA07A',     // 주황
}

/**
 * 액션 타입별 아이콘 매핑
 */
export const ACTION_ICONS = {
    'power': 'Power',
    'wind': 'Wind',
    'mode': 'Settings',
    'temperature': 'Thermometer',
    'Power': 'Power',
    'PowerOff': 'PowerOff',
    'Wind': 'Wind',
    'Repeat': 'Repeat',
    'Leaf': 'Leaf',
    'Zap': 'Zap',
    'Thermometer': 'Thermometer',
}

/**
 * 액션 타입별 색상 가져오기
 * @param {string} actionType - 액션 타입
 * @returns {string} 색상 코드 (hex)
 */
export function getActionColor(actionType) {
    return ACTION_COLORS[actionType] || '#9E9E9E'
}

/**
 * 액션 타입별 아이콘 가져오기
 * @param {string} iconName - 아이콘명
 * @returns {string} 아이콘명
 */
export function getActionIcon(iconName) {
    return ACTION_ICONS[iconName] || 'Zap'
}

/**
 * 액션명을 보기 좋게 포맷팅
 * @param {string} actionName - 액션명 (snake_case)
 * @returns {string} 포맷팅된 이름
 */
export function formatActionName(actionName) {
    if (!actionName) return ''

    return actionName
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ')
}

/**
 * 디바이스에 액션 정보 추가
 * @param {Object} device - 디바이스 객체
 * @param {Object} actionsData - 액션 데이터
 * @returns {Object} 액션 정보가 추가된 디바이스 객체
 */
export function enrichDeviceWithActions(device, actionsData) {
    return {
        ...device,
        available_actions: actionsData,
        action_count: Object.keys(actionsData).length,
    }
}

/**
 * 액션을 카테고리별로 그룹화
 * @param {Object} actions - 액션 객체
 * @returns {Object} 카테고리별로 그룹화된 액션
 */
export function groupActionsByCategory(actions) {
    const grouped = {}

    Object.entries(actions).forEach(([actionKey, actionInfo]) => {
        const category = actionInfo.category || 'etc'
        if (!grouped[category]) {
            grouped[category] = []
        }
        grouped[category].push({
            action: actionKey,  // ✅ 실제 액션명 (API 전송용, 영문)
            label: actionInfo.name,  // ✅ UI 표시용 (한글)
            ...actionInfo,
        })
    })

    return grouped
}

/**
 * 카테고리명을 한글로 표시
 * @param {string} category - 카테고리명
 * @returns {string} 한글 카테고리명
 */
export function getCategoryLabel(category) {
    const categoryLabels = {
        'operation': '작동 제어',
        'wind_strength': '바람 세기',
        'operation_mode': '실행 모드',
        'temperature': '온도 설정',
    }
    return categoryLabels[category] || category
}
