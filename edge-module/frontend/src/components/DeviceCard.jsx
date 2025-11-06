import { useState, useEffect, useRef, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
    Power, PowerOff, Wind, Sun, Droplets,
    Thermometer, Fan, Lightbulb, Zap, Repeat, Leaf,
    Plus, Minus, RefreshCw
} from 'lucide-react'
import {
    getDeviceActions,
    groupActionsByCategory,
    getCategoryLabel,
    getActionColor,
} from '../utils/deviceActions'
import { registerGazeTarget } from '../utils/gazeRegistry'
import './DeviceCard.css'

/**
 * 기기 타입별 아이콘 매핑
 */
const DEVICE_ICONS = {
    'air_purifier': Fan,
    'airpurifier': Fan,
    'air_conditioner': Wind,
    'aircon': Wind,
    'airconditioner': Wind
}

/**
 * 액션 아이콘 매핑
 */
const ACTION_ICON_MAP = {
    'Power': Power,
    'PowerOff': PowerOff,
    'Wind': Wind,
    'Thermometer': Thermometer,
    'Repeat': Repeat,
    'Leaf': Leaf,
    'Zap': Zap,
}

/**
 * 개별 기기 카드 컴포넌트 (v3 - 상태 관리 포함)
 * 
 * 기능:
 * - 기기 정보 표시
 * - 디바이스 액션 동적 렌더링
 * - 액션 클릭 시 AI-서버에 전송
 * - 기기 상태 유지 및 표시
 * - Gateway에서 실시간 상태 동기화
 * 
 * @param {Object} device - 기기 정보 (device_id, name, device_type)
 * @param {Function} onControl - 기기 제어 콜백
 */
function DeviceCard({ device, onControl }) {
    const [isExecuting, setIsExecuting] = useState(false)
    const [actions, setActions] = useState({})
    const [deviceState, setDeviceState] = useState({})
    const [lastAction, setLastAction] = useState(null)
    const [loading, setLoading] = useState(true)
    const [currentTemp, setCurrentTemp] = useState(() => {
        const initial = Number(device?.current_temperature || device?.target_temp)
        return Number.isFinite(initial) ? initial : 24
    })
    const cardRef = useRef(null)
    const statePollingRef = useRef(null)
    const actionGazeCleanupRef = useRef(new Map())
    const actionDwellCallbacksRef = useRef(new Map())
    const tempGazeCleanupRef = useRef({ minus: null, plus: null })

    // 👁️ Dwell Time 기능 (2초간 바라보면 액션 실행)
    const [dwellingButton, setDwellingButton] = useState(null) // 현재 바라보는 버튼
    const [dwellProgress, setDwellProgress] = useState(0) // 진행률 (0-100)
    const dwellTimerRef = useRef(null)
    const DWELL_TIME = 1500 // 1.5초 응시로 액션 실행

    // ============================================================================
    // 초기화: 액션 정보 로드
    // ============================================================================
    useEffect(() => {
        loadActionsForDevice()
        fetchDeviceState() // ✅ 함수명 수정

        return () => {
            if (statePollingRef.current) {
                clearInterval(statePollingRef.current)
            }
        }
    }, [device.device_id, device.device_type])

    useEffect(() => {
        const nextTemp = Number(deviceState?.target_temp ?? deviceState?.current_temperature)
        if (Number.isFinite(nextTemp) && nextTemp !== currentTemp) {
            setCurrentTemp(nextTemp)
        }
    }, [deviceState?.target_temp, deviceState?.current_temperature, currentTemp])

    /**
     * 디바이스 액션 정보 로드
     */
    const loadActionsForDevice = async () => {
        try {
            setLoading(true)
            // device_type에서 'device_' 접두사 제거
            let deviceType = device.device_type.toLowerCase()
            if (deviceType.startsWith('device_')) {
                deviceType = deviceType.replace('device_', '')
            }

            console.log(`[DeviceCard] 액션 로드 시도: ${device.name}, type: ${deviceType}`)
            const actionsData = await getDeviceActions(deviceType)

            if (Object.keys(actionsData).length > 0) {
                setActions(actionsData)
                console.log(`[DeviceCard] ✅ 액션 로드 성공: ${device.name} (${Object.keys(actionsData).length}개)`)
            } else {
                console.warn(`[DeviceCard] ⚠️  액션 없음: ${device.name}, type: ${deviceType}`)
            }
        } catch (error) {
            console.error(`[DeviceCard] ❌ 액션 로드 실패:`, error)
        } finally {
            setLoading(false)
        }
    }

    /**
     * 기기 상태 수동 조회 (새로고침 버튼 클릭 시)
     */
    const fetchDeviceState = async () => {
        try {
            console.log(`[DeviceCard] 🔄 상태 조회 중: ${device.name}`)
            const response = await fetch(`/api/devices/${device.device_id}/state`)
            const data = await response.json()

            if (data.success && data.state) {
                setDeviceState(data.state)
                console.log(`[DeviceCard] 📊 상태 업데이트:`, data.state)
            }
        } catch (error) {
            console.warn(`[DeviceCard] ⚠️  상태 조회 실패:`, error)
        }
    }

    // 자동 폴링 제거 - 수동 새로고침만 사용

    /**
     * 액션 실행 핸들러
     */
    const handleActionClick = async (actionName, actionInfo) => {
        try {
            setIsExecuting(true)
            console.log(`[DeviceCard] 🎯 액션 실행: ${device.name} → ${actionName}`)

            // AI-서버로 제어 요청
            const response = await fetch(`/api/devices/${device.device_id}/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: actionName,
                    value: actionInfo?.value
                })
            })

            const result = await response.json()
            console.log(`[DeviceCard] 💬 응답:`, result)

            if (result.success) {
                console.log(`[DeviceCard] ✅ 액션 완료: ${result.message}`)

                // 마지막 액션 기록
                setLastAction({
                    name: actionName,
                    time: new Date(),
                    status: 'success'
                })

                // 즉시 상태 업데이트
                await fetchDeviceState() // ✅ 함수명 수정

                // 부모 컴포넌트에 알림
                if (onControl) {
                    onControl(device.device_id, actionName, result)
                }
            } else {
                console.error(`[DeviceCard] ❌ 액션 실패:`, result.message)
                setLastAction({
                    name: actionName,
                    time: new Date(),
                    status: 'error'
                })
            }
        } catch (error) {
            console.error(`[DeviceCard] ❌ 오류:`, error)
            setLastAction({
                name: actionName,
                time: new Date(),
                status: 'error'
            })
        } finally {
            setIsExecuting(false)
        }
    }

    /**
     * 👁️ Dwell Time 시작: 버튼에 시선이 머물 때
     */
    const handleButtonEnter = (actionName, actionInfo) => {
        // 이미 타이머 진행 중이면 무시 (중복 방지)
        if (dwellTimerRef.current) {
            return
        }

        // 액션 실행 중이면 무시
        if (isExecuting) {
            return
        }

        console.log(`[DeviceCard] 👁️ Dwell 시작: ${actionName}`)
        setDwellingButton(actionName)
        setDwellProgress(0)

        let startTime = Date.now()
        dwellTimerRef.current = setInterval(() => {
            const elapsed = Date.now() - startTime
            const progress = Math.min((elapsed / DWELL_TIME) * 100, 100)
            setDwellProgress(progress)

            // 2초 완료
            if (progress >= 100) {
                clearInterval(dwellTimerRef.current)
                dwellTimerRef.current = null
                console.log(`[DeviceCard] ✅ Dwell 완료: ${actionName}`)

                // 온도 조절 버튼인 경우 actionInfo.callback 실행
                if (actionInfo?.callback) {
                    actionInfo.callback()
                } else {
                    handleActionClick(actionName, actionInfo)
                }

                setDwellingButton(null)
                setDwellProgress(0)
            }
        }, 50)
    }

    /**
     * 👁️ Dwell Time 취소: 버튼에서 시선이 떠날 때
     */
    const handleButtonLeave = () => {
        if (dwellTimerRef.current) {
            clearInterval(dwellTimerRef.current)
            console.log(`[DeviceCard] ❌ Dwell 취소`)
        }
        setDwellingButton(null)
        setDwellProgress(0)
    }

    const getActionButtonRef = (action) => (node) => {
        const key = action.action
        const cleanupMap = actionGazeCleanupRef.current
        const dwellMap = actionDwellCallbacksRef.current

        if (cleanupMap.has(key)) {
            cleanupMap.get(key)()
            cleanupMap.delete(key)
        }

        if (node) {
            const enterHandler = () => {
                if (!node || node.disabled) {
                    handleButtonLeave()
                    return
                }
                handleButtonEnter(action.action, action)
            }

            dwellMap.set(key, enterHandler)

            const cleanup = registerGazeTarget(node, {
                onEnter: enterHandler,
                onLeave: handleButtonLeave
            })
            cleanupMap.set(key, cleanup)
        } else {
            dwellMap.delete(key)
        }
    }

    useEffect(() => {
        const nextTemp = Number(deviceState?.target_temp)
        if (Number.isFinite(nextTemp) && nextTemp !== currentTemp) {
            setCurrentTemp(nextTemp)
        }
    }, [deviceState?.target_temp])

    const runTempMinusAction = () => {
        if (!isDevicePowered || isExecuting) return
        const newTemp = Math.max(18, currentTemp - 1)
        setCurrentTemp(newTemp)
        handleActionClick(`temp_${newTemp}`, { name: `${newTemp}°C`, type: 'temperature' })
    }

    const runTempPlusAction = () => {
        if (!isDevicePowered || isExecuting) return
        const newTemp = Math.min(30, currentTemp + 1)
        setCurrentTemp(newTemp)
        handleActionClick(`temp_${newTemp}`, { name: `${newTemp}°C`, type: 'temperature' })
    }

    const startTempMinusDwell = () => {
        if (!isDevicePowered || isExecuting || currentTemp <= 18) {
            handleButtonLeave()
            return
        }
        handleButtonEnter('temp_minus', {
            callback: runTempMinusAction
        })
    }

    const startTempPlusDwell = () => {
        if (!isDevicePowered || isExecuting || currentTemp >= 30) {
            handleButtonLeave()
            return
        }
        handleButtonEnter('temp_plus', {
            callback: runTempPlusAction
        })
    }

    const setTempMinusRef = (node) => {
        const cleanupStore = tempGazeCleanupRef.current
        if (cleanupStore.minus) {
            cleanupStore.minus()
            cleanupStore.minus = null
        }

        if (node) {
            cleanupStore.minus = registerGazeTarget(node, {
                onEnter: startTempMinusDwell,
                onLeave: handleButtonLeave
            })
        }
    }

    const setTempPlusRef = (node) => {
        const cleanupStore = tempGazeCleanupRef.current
        if (cleanupStore.plus) {
            cleanupStore.plus()
            cleanupStore.plus = null
        }

        if (node) {
            cleanupStore.plus = registerGazeTarget(node, {
                onEnter: startTempPlusDwell,
                onLeave: handleButtonLeave
            })
        }
    }

    // 컴포넌트 언마운트 시 타이머 정리
    useEffect(() => {
        return () => {
            if (dwellTimerRef.current) {
                clearInterval(dwellTimerRef.current)
            }
        }
    }, [])

    // 기기 타입에 맞는 아이콘
    const Icon = DEVICE_ICONS[device.device_type] || Power

    // 액션을 카테고리별로 그룹화
    const groupedActions = groupActionsByCategory(actions)
    const sortedCategories = useMemo(() => {
        const entries = Object.entries(groupedActions)
        entries.sort(([a], [b]) => {
            if (device.device_type.toLowerCase().includes('aircon')) {
                if (a === 'temperature' && b === 'wind_strength') return -1
                if (a === 'wind_strength' && b === 'temperature') return 1
            }
            return a.localeCompare(b)
        })
        return entries
    }, [groupedActions, device.device_type])
    const isDevicePowered = useMemo(() => {
        const raw = (deviceState?.power ?? deviceState?.state ?? device?.state ?? '').toString().toLowerCase()
        return ['on', 'power_on', 'running', 'true', '1', 'enabled'].includes(raw)
    }, [deviceState?.power, deviceState?.state, device?.state])

    // 현재 상태 표시 텍스트
    const getStateDisplay = () => {
        if (!deviceState || Object.keys(deviceState).length === 0) {
            return '상태 조회 중...'
        }

        const type = device.device_type.toLowerCase()

        if (type.includes('purifier')) {
            // 공기청정기: 전원 + 바람 + 모드
            const power = deviceState.power || 'OFF'
            const wind = deviceState.wind_strength || '-'
            return `${power} | 바람: ${wind}`
        } else if (type.includes('aircon') || type.includes('air_con')) {
            // 에어컨: 전원 + 온도 + 바람
            const power = deviceState.power || 'OFF'
            const temp = deviceState.target_temp || '-'
            const wind = deviceState.wind_strength || '-'
            return `${power} | ${temp}°C | 바람: ${wind}`
        }

        return '상태 미지원'
    }

    return (
        <motion.div
            ref={cardRef}
            className="device-card"
            whileHover={{ y: -4 }}
            transition={{ duration: 0.2 }}
        >
            {/* 카드 헤더 */}
            <div className="device-header">
                <div className="device-icon">
                    <Icon size={32} />
                </div>
                <div className="device-info">
                    <h3 className="device-name">{device.name}</h3>
                    <p className="device-type">{device.device_type}</p>
                    <p className="device-state">{getStateDisplay()}</p>
                </div>

                {/* 새로고침 버튼 */}
                <motion.button
                    className="refresh-button"
                    onClick={fetchDeviceState}
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                    title="상태 새로고침"
                >
                    <RefreshCw size={24} />
                </motion.button>
            </div>

            {/* 액션 섹션 */}
            <div className="device-actions-section">
                {loading ? (
                    <div className="loading-actions">
                        <p>액션 로드 중...</p>
                    </div>
                ) : Object.keys(groupedActions).length > 0 ? (
                    sortedCategories.map(([category, categoryActions]) => {
                        // 온도 카테고리는 +/- 버튼으로 렌더링
                        if (category === 'temperature') {
                            return (
                                <div key={category} className="action-group">
                                    <h4 className="action-group-title">{getCategoryLabel(category)}</h4>
                                    <div className="temperature-control">
                                        <motion.button
                                            ref={setTempMinusRef}
                                            className={`temp-button ${dwellingButton === 'temp_minus' ? 'dwelling' : ''}`}
                                            onMouseEnter={startTempMinusDwell}
                                            onMouseLeave={handleButtonLeave}
                                            disabled={isExecuting || currentTemp <= 18 || !isDevicePowered}
                                            whileHover={{ scale: (isExecuting || currentTemp <= 18 || !isDevicePowered) ? 1 : 1.1 }}
                                            whileTap={{ scale: (isExecuting || currentTemp <= 18 || !isDevicePowered) ? 1 : 0.9 }}
                                            style={{
                                                background: dwellingButton === 'temp_minus'
                                                    ? `linear-gradient(to right, var(--primary) ${dwellProgress}%, transparent ${dwellProgress}%)`
                                                    : 'transparent'
                                            }}
                                        >
                                            <Minus size={16} />
                                        </motion.button>

                                        <div className="temp-display">
                                            <Thermometer size={14} />
                                            <span className="temp-value">{currentTemp}°C</span>
                                        </div>

                                        <motion.button
                                            ref={setTempPlusRef}
                                            className={`temp-button ${dwellingButton === 'temp_plus' ? 'dwelling' : ''}`}
                                            onMouseEnter={startTempPlusDwell}
                                            onMouseLeave={handleButtonLeave}
                                            disabled={isExecuting || currentTemp >= 30 || !isDevicePowered}
                                            whileHover={{ scale: (isExecuting || currentTemp >= 30 || !isDevicePowered) ? 1 : 1.1 }}
                                            whileTap={{ scale: (isExecuting || currentTemp >= 30 || !isDevicePowered) ? 1 : 0.9 }}
                                            style={{
                                                background: dwellingButton === 'temp_plus'
                                                    ? `linear-gradient(to right, var(--primary) ${dwellProgress}%, transparent ${dwellProgress}%)`
                                                    : 'transparent'
                                            }}
                                        >
                                            <Plus size={16} />
                                        </motion.button>
                                    </div>
                                </div>
                            )
                        }

                        // 나머지 카테고리는 기존대로 버튼 렌더링
                        return (
                            <div key={category} className="action-group">
                                <h4 className="action-group-title">{getCategoryLabel(category)}</h4>
                                <div className="action-buttons">
                                    {categoryActions.map((action) => {
                                        const ActionIcon = ACTION_ICON_MAP[action.icon] || Zap
                                        const actionColor = getActionColor(action.type)
                                        const isActive = lastAction?.name === action.action && lastAction?.status === 'success'
                                        const isDwelling = dwellingButton === action.action
                                        const actionType = (action.type || '').toLowerCase()
                                        const isPowerAction = actionType === 'power'
                                        const isActionEnabled = isPowerAction || isDevicePowered
                                        const isDisabled = isExecuting || !isActionEnabled

                                        return (
                                            <motion.button
                                                ref={getActionButtonRef(action)}
                                                key={action.action}
                                                className={`action-button ${isActive ? 'active' : ''} ${isDwelling ? 'dwelling' : ''}`}
                                                onMouseEnter={() => {
                                                    const handler = actionDwellCallbacksRef.current.get(action.action)
                                                    if (handler) {
                                                        handler()
                                                    }
                                                }}
                                                onMouseLeave={handleButtonLeave}
                                                disabled={isDisabled}
                                                whileHover={{ scale: isDisabled ? 1 : 1.05 }}
                                                whileTap={{ scale: isDisabled ? 1 : 0.95 }}
                                                style={{
                                                    borderColor: actionColor,
                                                    backgroundColor: isActive ? actionColor + '20' : 'transparent',
                                                    background: isDwelling
                                                        ? `linear-gradient(to right, ${actionColor}40 ${dwellProgress}%, transparent ${dwellProgress}%)`
                                                        : isActive ? actionColor + '20' : 'transparent'
                                                }}
                                                title={action.description}
                                            >
                                                <ActionIcon size={16} />
                                                <span>{action.label}</span>
                                                {isDwelling && (
                                                    <span className="dwell-indicator" style={{
                                                        position: 'absolute',
                                                        bottom: '2px',
                                                        left: '0',
                                                        height: '3px',
                                                        width: `${dwellProgress}%`,
                                                        backgroundColor: actionColor,
                                                        transition: 'width 50ms linear'
                                                    }}></span>
                                                )}
                                            </motion.button>
                                        )
                                    })}
                                </div>
                            </div>
                        )
                    })
                ) : (
                    <div className="no-actions">
                        <p>사용 가능한 액션이 없습니다</p>
                        <p className="hint">기기를 동기화하세요</p>
                    </div>
                )}
            </div>

            {/* 마지막 액션 표시 */}
            {lastAction && (
                <div className={`last-action ${lastAction.status}`}>
                    <span>
                        {lastAction.status === 'success' ? '✅' : '❌'}
                        {lastAction.name}
                    </span>
                </div>
            )}

            {/* 로딩 상태 */}
            {isExecuting && (
                <div className="device-loading">
                    <div className="spinner"></div>
                    <p>실행 중...</p>
                </div>
            )}
        </motion.div>
    )
}

export default DeviceCard
