import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Eye, LogOut, Settings, Sparkles,
    Bell, User, ChevronLeft, ChevronRight
} from 'lucide-react'
import GazeCursor from '../components/GazeCursor'
import DeviceCard from '../components/DeviceCard'
import RecommendationModal from '../components/RecommendationModal'
import './HomePage.css'
import { resolveGazeTarget, registerGazeTarget } from '../utils/gazeRegistry'

/**
 * 홈 페이지 (메인 대시보드)
 * - 스마트홈 기기 제어
 * - 시선 추적 커서 표시
 * - 실시간 시선 위치 기반 dwell time 제어
 * - AI 추천 모달 주기적 표시
 * - 눈깜빡임(0.5초 이상) 감지 → 클릭 인식
 */
function HomePage({ onLogout }) {
    // 연결된 기기 목록
    const [devices, setDevices] = useState([])
    // AI 추천 목록
    const [recommendations, setRecommendations] = useState([])
    // 추천 모달 표시 여부
    const [showRecommendations, setShowRecommendations] = useState(false)
    // 실시간 시선 위치 (x, y)
    const [gazePosition, setGazePosition] = useState({ x: 0, y: 0 })
    // WebSocket 연결 상태
    const [isConnected, setIsConnected] = useState(false)
    // 🔍 시선 인식 가능 여부 (false = 눈이 감겼거나 인식 불가)
    const [calibrated, setCalibrated] = useState(true)
    // 로그인한 사용자명
    const [username, setUsername] = useState('')
    // 👁️ 0.5초 이상 눈깜빡임 감지
    const [prolongedBlink, setProlongedBlink] = useState(false)
    // 👁️ 현재 눈깜빡임 상태 (포인터 고정용)
    const [blink, setBlink] = useState(false)
    // 🔒 글로벌 포인터 고정 상태 (버튼 위 포인터 1.5초 고정)
    const [isPointerLocked, setIsPointerLocked] = useState(false)
    // 🔒 현재 제어 중인 기기 (중복 클릭 방지)
    const [controllingDevice, setControllingDevice] = useState(null)
    const [stableCursor, setStableCursor] = useState(() => {
        if (typeof window === 'undefined') {
            return { x: 0, y: 0, frozen: true, magnetized: false }
        }
        return {
            x: window.innerWidth / 2,
            y: window.innerHeight / 2,
            frozen: true,
            magnetized: false
        }
    })
    const autopilotEnabled = useMemo(() => {
        if (typeof window === 'undefined') {
            return false
        }

        try {
            const params = new URLSearchParams(window.location.search)
            if (params.has('demo')) {
                return params.get('demo') !== '0'
            }
            const stored = window.localStorage?.getItem('gazehome_demo_autopilot')
            if (stored !== null) {
                return stored === 'true'
            }
        } catch (error) {
            console.warn('[HomePage] Autopilot 설정 확인 실패:', error)
        }

        // 기본값: 데모 편의를 위해 활성화
        return true
    }, [])
    const autopilotStateRef = useRef({
        running: false,
        completed: false,
        waitingForRecommendation: false,
        cancelled: false,
        started: false
    })
    useEffect(() => {
        console.log('[HomePage][Demo] autopilotEnabled:', autopilotEnabled)
    }, [autopilotEnabled])
    const autopilotActiveRef = useRef(false)
    const autopilotTargetRef = useRef(null)
    const autopilotTickerRef = useRef(null)
    const autopilotTimeoutsRef = useRef(new Set())
    const autopilotIntervalsRef = useRef(new Set())
    const introAnimationRanRef = useRef(false)

    const activeGazeTargetRef = useRef({ element: null, handlers: null, exitTimeout: null })
    const paginationTimerRef = useRef(null)
    const paginationCleanupRef = useRef({ prev: null, next: null })
    const [paginationDwelling, setPaginationDwelling] = useState(null)
    const [paginationProgress, setPaginationProgress] = useState(0)
    const headerTimersRef = useRef(new Map())
    const headerCleanupRef = useRef(new Map())
    const [headerDwelling, setHeaderDwelling] = useState(null)
    const [headerProgress, setHeaderProgress] = useState(0)
    const HEADER_DWELL_MS = 1500
    const GAZE_STICKY_MARGIN = 35
    const GAZE_EXIT_DELAY_MS = 320

    // 📄 페이지네이션 - 한 번에 1개 기기만 표시
    // 고정 기기 ID (에어컨1, 공기청정기 - 에어컨이 1페이지에 표시)
    const FIXED_DEVICE_IDS = [
        '1d7c7408c31fbaf9ce2ea8634e2eda53f517d835a61440a4f75c5426eadc054a', // 에어컨1 (1페이지)
        '13b708c0aa7f00b62835388f82643ae0cf0470fe24a14754f8d0bcb915513803'  // 공기청정기 (2페이지)
    ]
    // 현재 표시 중인 기기 인덱스
    const [currentDeviceIndex, setCurrentDeviceIndex] = useState(0)
    const currentDeviceIndexRef = useRef(currentDeviceIndex)
    /**
     * 📄 우선 순위 기기 목록 (에어컨/공기청정기 → 없으면 전체)
     */
    const autopilotDevices = useMemo(() => {
        const pinned = devices.filter((device) =>
            FIXED_DEVICE_IDS.includes(device.device_id)
        )
        if (pinned.length > 0) {
            return pinned
        }

        const fallback = devices.filter((device) => {
            const type = (device?.device_type || '').toLowerCase()
            return type.includes('air_conditioner') || type.includes('aircon') || type.includes('purifier')
        })

        if (fallback.length > 0) {
            return fallback
        }

        return devices
    }, [devices])
    useEffect(() => {
        console.log('[HomePage][Demo] autopilotDevices:', autopilotDevices.map((device) => ({
            id: device.device_id,
            type: device.device_type,
            name: device.name
        })))
    }, [autopilotDevices])

    const displayDevices = autopilotDevices.length > 0
        ? [autopilotDevices[currentDeviceIndex % autopilotDevices.length]]
        : []

    const purifierIndex = useMemo(() => (
        autopilotDevices.findIndex(device =>
            (device?.device_type || '').toLowerCase().includes('purifier')
        )
    ), [autopilotDevices])

    /**
     * 포인터 1.5초 고정 함수
     * - 버튼 클릭 시 호출
     * - 1.5초 동안 hovering 감지 차단
     */
    const lockPointer = useCallback((duration = 1500) => {
        setIsPointerLocked(true)
        setTimeout(() => {
            setIsPointerLocked(false)
        }, duration)
    }, [])

    const cancelPaginationDwell = useCallback(() => {
        if (paginationTimerRef.current) {
            clearInterval(paginationTimerRef.current)
            paginationTimerRef.current = null
        }
        setPaginationDwelling(null)
        setPaginationProgress(0)
    }, [])

    const cancelHeaderDwell = useCallback((key) => {
        const timers = headerTimersRef.current
        if (key) {
            const timer = timers.get(key)
            if (timer) {
                clearInterval(timer)
                timers.delete(key)
            }
            if (headerDwelling === key) {
                setHeaderDwelling(null)
                setHeaderProgress(0)
            }
        } else {
            timers.forEach((timer) => clearInterval(timer))
            timers.clear()
            setHeaderDwelling(null)
            setHeaderProgress(0)
        }
    }, [headerDwelling])

    const startHeaderDwell = useCallback((key, callback) => {
        if (!key || headerTimersRef.current.has(key) || isPointerLocked) {
            return
        }

        setHeaderDwelling(key)
        setHeaderProgress(0)

        const startTime = Date.now()
        const timer = setInterval(() => {
            const elapsed = Date.now() - startTime
            const progress = Math.min((elapsed / HEADER_DWELL_MS) * 100, 100)
            setHeaderProgress(progress)

            if (progress >= 100) {
                clearInterval(timer)
                headerTimersRef.current.delete(key)
                setHeaderDwelling(null)
                setHeaderProgress(0)
                callback()
                lockPointer()
            }
        }, 50)

        headerTimersRef.current.set(key, timer)
    }, [HEADER_DWELL_MS, isPointerLocked, lockPointer])

    const clearGazeTarget = useCallback(() => {
        cancelPaginationDwell()
        cancelHeaderDwell()
        const current = activeGazeTargetRef.current
        if (current.exitTimeout) {
            clearTimeout(current.exitTimeout)
            current.exitTimeout = null
        }
        if (current.element && current.handlers?.onLeave) {
            current.handlers.onLeave()
        }
        activeGazeTargetRef.current = { element: null, handlers: null, exitTimeout: null }
    }, [cancelPaginationDwell, cancelHeaderDwell])

    const startPaginationDwell = useCallback((buttonType, callback) => {
        if (paginationTimerRef.current || isPointerLocked) {
            return
        }

        setPaginationDwelling(buttonType)
        setPaginationProgress(0)

        const startTime = Date.now()
        paginationTimerRef.current = setInterval(() => {
            const elapsed = Date.now() - startTime
            const progress = Math.min((elapsed / 1500) * 100, 100)
            setPaginationProgress(progress)

            if (progress >= 100) {
                clearInterval(paginationTimerRef.current)
                paginationTimerRef.current = null
                setPaginationDwelling(null)
                setPaginationProgress(0)
                callback()
                lockPointer()
            }
        }, 50)
    }, [isPointerLocked, lockPointer])

    const updateGazeTarget = useCallback((cursorX, cursorY) => {
        const current = activeGazeTargetRef.current

        const clearExitTimer = () => {
            if (current.exitTimeout) {
                clearTimeout(current.exitTimeout)
                current.exitTimeout = null
            }
        }

        const scheduleExit = () => {
            if (current.exitTimeout) {
                return
            }
            current.exitTimeout = setTimeout(() => {
                if (current.handlers?.onLeave) {
                    current.handlers.onLeave()
                }
                activeGazeTargetRef.current = { element: null, handlers: null, exitTimeout: null }
            }, GAZE_EXIT_DELAY_MS)
        }

        const isWithinStickyZone = () => {
            if (!current.element) {
                return false
            }
            const rect = current.element.getBoundingClientRect()
            return (
                cursorX >= rect.left - GAZE_STICKY_MARGIN &&
                cursorX <= rect.right + GAZE_STICKY_MARGIN &&
                cursorY >= rect.top - GAZE_STICKY_MARGIN &&
                cursorY <= rect.bottom + GAZE_STICKY_MARGIN
            )
        }

        const element = document.elementFromPoint(cursorX, cursorY)
        const resolved = resolveGazeTarget(element)

        if (resolved?.element === current.element) {
            clearExitTimer()
            return
        }

        if (!resolved?.element) {
            if (isWithinStickyZone()) {
                clearExitTimer()
                return
            }
            scheduleExit()
            return
        }

        if (current.element && current.handlers?.onLeave) {
            clearExitTimer()
            current.handlers.onLeave()
        }

        if (resolved.handlers?.onEnter) {
            resolved.handlers.onEnter()
        }

        activeGazeTargetRef.current = {
            element: resolved.element,
            handlers: resolved.handlers,
            exitTimeout: null
        }
    }, [GAZE_EXIT_DELAY_MS, GAZE_STICKY_MARGIN])

    const handleStableCursorUpdate = useCallback((position) => {
        setStableCursor((prev) => {
            if (
                Math.abs(prev.x - position.x) < 0.25 &&
                Math.abs(prev.y - position.y) < 0.25 &&
                prev.frozen === position.frozen &&
                prev.magnetized === position.magnetized
            ) {
                return prev
            }
            return position
        })
    }, [])

    useEffect(() => {
        currentDeviceIndexRef.current = currentDeviceIndex
    }, [currentDeviceIndex])

    const pause = useCallback((ms) => new Promise((resolve) => {
        const timeoutId = setTimeout(() => {
            autopilotTimeoutsRef.current.delete(timeoutId)
            resolve()
        }, ms)
        autopilotTimeoutsRef.current.add(timeoutId)
    }), [])

    const waitForCondition = useCallback((checkFn, timeout = 5000, intervalMs = 120) => new Promise((resolve) => {
        const start = Date.now()
        const intervalId = setInterval(() => {
            if (autopilotStateRef.current.cancelled) {
                clearInterval(intervalId)
                autopilotIntervalsRef.current.delete(intervalId)
                resolve(false)
                return
            }
            if (checkFn()) {
                clearInterval(intervalId)
                autopilotIntervalsRef.current.delete(intervalId)
                resolve(true)
                return
            }
            if (Date.now() - start >= timeout) {
                clearInterval(intervalId)
                autopilotIntervalsRef.current.delete(intervalId)
                resolve(false)
            }
        }, intervalMs)
        autopilotIntervalsRef.current.add(intervalId)
    }), [])

    const waitForElement = useCallback((getter, timeout = 5000) => new Promise((resolve) => {
        const start = Date.now()
        const intervalId = setInterval(() => {
            if (autopilotStateRef.current.cancelled) {
                clearInterval(intervalId)
                autopilotIntervalsRef.current.delete(intervalId)
                resolve(null)
                return
            }
            const element = getter()
            if (element) {
                clearInterval(intervalId)
                autopilotIntervalsRef.current.delete(intervalId)
                resolve(element)
                return
            }
            if (Date.now() - start >= timeout) {
                clearInterval(intervalId)
                autopilotIntervalsRef.current.delete(intervalId)
                resolve(null)
            }
        }, 120)
        autopilotIntervalsRef.current.add(intervalId)
    }), [])

    const ensureAutopilotTicker = useCallback(() => {
        if (autopilotTickerRef.current) {
            return
        }
        const intervalId = setInterval(() => {
            if (!autopilotTargetRef.current) {
                return
            }
            setGazePosition({
                x: autopilotTargetRef.current.x,
                y: autopilotTargetRef.current.y
            })
        }, 80)
        autopilotTickerRef.current = intervalId
        autopilotIntervalsRef.current.add(intervalId)
    }, [setGazePosition])

    const stopAutopilotOverride = useCallback(() => {
        autopilotActiveRef.current = false
        autopilotTargetRef.current = null

        if (autopilotTickerRef.current) {
            clearInterval(autopilotTickerRef.current)
            autopilotIntervalsRef.current.delete(autopilotTickerRef.current)
            autopilotTickerRef.current = null
        }

        autopilotTimeoutsRef.current.forEach((timeoutId) => {
            clearTimeout(timeoutId)
        })
        autopilotTimeoutsRef.current.clear()

        autopilotIntervalsRef.current.forEach((intervalId) => {
            clearInterval(intervalId)
        })
        autopilotIntervalsRef.current.clear()
    }, [])

    const moveCursorTo = useCallback(async (target, duration = 520, easing = 'easeInOut') => {
        if (!target) return

        const startPos = autopilotTargetRef.current || {
            x: stableCursor.x,
            y: stableCursor.y
        }

        const clampedStart = {
            x: Number.isFinite(startPos.x) ? startPos.x : window.innerWidth / 2,
            y: Number.isFinite(startPos.y) ? startPos.y : window.innerHeight / 2
        }

        const deltaX = target.x - clampedStart.x
        const deltaY = target.y - clampedStart.y
        const distance = Math.hypot(deltaX, deltaY)
        if (distance < 2) {
            autopilotTargetRef.current = target
            setGazePosition(target)
            return
        }

        const steps = Math.max(Math.ceil(duration / 40), 6)

        autopilotActiveRef.current = true
        ensureAutopilotTicker()

        const ease = (t) => {
            switch (easing) {
                case 'linear':
                    return t
                case 'easeOut':
                    return 1 - Math.pow(1 - t, 2)
                case 'easeIn':
                    return t * t
                default: // easeInOut
                    return t < 0.5
                        ? 2 * t * t
                        : 1 - Math.pow(-2 * t + 2, 2) / 2
            }
        }

        for (let i = 1; i <= steps; i++) {
            if (autopilotStateRef.current.cancelled) {
                break
            }

            const progress = ease(i / steps)
            const intermediate = {
                x: clampedStart.x + deltaX * progress,
                y: clampedStart.y + deltaY * progress
            }

            autopilotTargetRef.current = intermediate
            setGazePosition(intermediate)
            await pause(duration / steps)
        }

        autopilotTargetRef.current = target
        setGazePosition(target)
    }, [ensureAutopilotTicker, pause, setGazePosition, stableCursor.x, stableCursor.y])

    const dwellOnElement = useCallback(async (element, dwellMs = 1600, settleMs = 400) => {
        if (!element) {
            console.warn('[HomePage][Demo] dwellOnElement: element not found')
            return false
        }

        const rect = element.getBoundingClientRect()
        const target = {
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height / 2
        }

        await moveCursorTo(target, Math.max(420, Math.min(640, Math.hypot(rect.width, rect.height) * 14)))

        const isImmediate = element.dataset?.immediate === 'true'
        const effectiveDwell = isImmediate ? Math.min(360, dwellMs) : dwellMs
        const effectiveSettle = isImmediate ? Math.min(180, settleMs) : settleMs

        const resolved = resolveGazeTarget(element)
        if (resolved?.handlers?.onEnter) {
            try {
                resolved.handlers.onEnter()
            } catch (error) {
                console.warn('[HomePage][Demo] onEnter handler failed:', error)
            }
        }

        await pause(effectiveDwell)

        if (resolved?.handlers?.onLeave) {
            try {
                resolved.handlers.onLeave()
            } catch (error) {
                console.warn('[HomePage][Demo] onLeave handler failed:', error)
            }
        }

        if (effectiveSettle > 0) {
            await pause(effectiveSettle)
        }

        return true
    }, [moveCursorTo, pause])

    const findPurifierCard = useCallback(() => {
        const cards = document.querySelectorAll('.device-card')
        for (const card of cards) {
            const typeText = card.querySelector('.device-type')?.textContent?.toLowerCase() || ''
            if (typeText.includes('air_purifier')) {
                return card
            }
        }
        return null
    }, [])

    const findPurifierButton = useCallback((keyword) => {
        const card = findPurifierCard()
        if (!card) return null

        const buttons = card.querySelectorAll('button')
        for (const button of buttons) {
            const text = button.textContent?.trim()
            if (text && text.includes(keyword)) {
                return button
            }
        }
        return null
    }, [findPurifierCard])

    const clampValue = useCallback((value, min, max) => Math.min(Math.max(value, min), max), [])

    const jitterCursor = useCallback(async (durationMs = 5000) => {
        if (typeof window === 'undefined') {
            return
        }

        const width = window.innerWidth
        const height = window.innerHeight
        const start = Date.now()

        autopilotActiveRef.current = true
        ensureAutopilotTicker()

        while (Date.now() - start < durationMs) {
            if (autopilotStateRef.current.cancelled || !autopilotActiveRef.current) {
                break
            }

            const baseX = stableCursor.x || width / 2
            const baseY = stableCursor.y || height / 2
            const angle = Math.random() * Math.PI * 2
            const radius = 28 + Math.random() * 24
            const nextTarget = {
                x: clampValue(baseX + Math.cos(angle) * radius, 24, width - 24),
                y: clampValue(baseY + Math.sin(angle) * radius, 24, height - 24)
            }

            autopilotTargetRef.current = nextTarget
            setGazePosition(nextTarget)

            const wait = 320 + Math.random() * 180
            await pause(wait)
        }
    }, [clampValue, ensureAutopilotTicker, pause, setGazePosition, stableCursor.x, stableCursor.y])

    const startIntroAnimation = useCallback(async () => {
        if (introAnimationRanRef.current) {
            return
        }
        introAnimationRanRef.current = true

        try {
            console.log('[HomePage][Demo] Intro pointer animation start')
            await jitterCursor(2600)
        } catch (error) {
            console.warn('[HomePage][Demo] Intro animation failed:', error)
        } finally {
            if (!autopilotStateRef.current.started) {
                stopAutopilotOverride()
            }
        }
    }, [jitterCursor, stopAutopilotOverride])

    const runDemoSequence = useCallback(async () => {
        if (!autopilotEnabled) {
            return
        }

        const state = autopilotStateRef.current
        if (state.running || state.completed || state.cancelled) {
            return
        }

        if (autopilotDevices.length === 0 || purifierIndex === -1) {
            state.completed = true
            return
        }

        state.running = true
        state.started = true
        autopilotActiveRef.current = true
        if (!autopilotTargetRef.current) {
            autopilotTargetRef.current = { x: stableCursor.x, y: stableCursor.y }
        }

        try {
            console.log('[HomePage][Demo] 초기 5초 포인터 워밍업 시작')
            await jitterCursor(5000)
            console.log('[HomePage][Demo] 초기 워밍업 완료')

            if (autopilotDevices.length > 1 && currentDeviceIndexRef.current !== purifierIndex) {
                const direction = purifierIndex > currentDeviceIndexRef.current ? 'next' : 'prev'
                const paginationButton = await waitForElement(() => (
                    document.querySelector(direction === 'next'
                        ? '.pagination-button.next'
                        : '.pagination-button.prev')
                ), 4000)

                if (paginationButton) {
                    console.log('[HomePage][Demo] 페이지 전환 버튼 dwell 시작:', direction)
                    await dwellOnElement(paginationButton)
                    await waitForCondition(() => currentDeviceIndexRef.current === purifierIndex, 5000)
                } else {
                    console.warn('[HomePage][Demo] 페이지 전환 버튼을 찾을 수 없습니다')
                }
            }

            const powerOnButton = await waitForElement(() => findPurifierButton('전원 켜'), 6000)
            if (powerOnButton) {
                console.log('[HomePage][Demo] 공기청정기 전원 켜기 dwell')
                await dwellOnElement(powerOnButton)
                console.log('[HomePage][Demo] 전원 켜기 후 10초 대기')
                await pause(10000)
            } else {
                console.warn('[HomePage][Demo] 공기청정기 전원 켜기 버튼을 찾을 수 없습니다')
            }

            const powerOffButton = await waitForElement(() => findPurifierButton('전원 끄'), 6000)
            if (powerOffButton) {
                console.log('[HomePage][Demo] 공기청정기 전원 끄기 dwell')

                await dwellOnElement(powerOffButton)
                await pause(400)
            } else {
                console.warn('[HomePage][Demo] 공기청정기 전원 끄기 버튼을 찾을 수 없습니다')
            }

            state.waitingForRecommendation = true
        } catch (error) {
            console.error('[HomePage][Demo] 자동 데모 시퀀스 오류:', error)
        } finally {
            state.running = false
        }
    }, [
        autopilotEnabled,
        dwellOnElement,
        findPurifierButton,
        jitterCursor,
        autopilotDevices.length,
        pause,
        purifierIndex,
        stableCursor.x,
        stableCursor.y,
        waitForCondition,
        waitForElement
    ])
    // 다음 버튼 핸들러
    const handleNextDevice = useCallback(() => {
        cancelPaginationDwell()
        if (autopilotDevices.length > 0) {
            setCurrentDeviceIndex((prev) => (prev + 1) % autopilotDevices.length)
        }
    }, [cancelPaginationDwell, autopilotDevices.length])

    // 이전 버튼 핸들러
    const handlePrevDevice = useCallback(() => {
        cancelPaginationDwell()
        if (autopilotDevices.length > 0) {
            setCurrentDeviceIndex((prev) =>
                prev === 0 ? autopilotDevices.length - 1 : prev - 1
            )
        }
    }, [cancelPaginationDwell, autopilotDevices.length])

    const makePaginationButtonRef = useCallback((type, callback) => (node) => {
        const store = paginationCleanupRef.current
        if (store[type]) {
            store[type]()
            store[type] = null
        }

        if (node) {
            store[type] = registerGazeTarget(node, {
                onEnter: () => {
                    if (node.disabled) return
                    startPaginationDwell(type, callback)
                },
                onLeave: cancelPaginationDwell
            })
        }
    }, [startPaginationDwell, cancelPaginationDwell])

    const prevButtonRef = useMemo(
        () => makePaginationButtonRef('prev', handlePrevDevice),
        [makePaginationButtonRef, handlePrevDevice]
    )

    const nextButtonRef = useMemo(
        () => makePaginationButtonRef('next', handleNextDevice),
        [makePaginationButtonRef, handleNextDevice]
    )

    const makeHeaderButtonRef = useCallback((key, callback) => (node) => {
        const cleanupMap = headerCleanupRef.current
        if (cleanupMap.has(key)) {
            cleanupMap.get(key)()
            cleanupMap.delete(key)
        }

        if (node) {
            const cleanup = registerGazeTarget(node, {
                onEnter: () => {
                    const isDisabled = node.hasAttribute('disabled') || node.getAttribute('aria-disabled') === 'true'
                    if (isDisabled) {
                        cancelHeaderDwell(key)
                        return
                    }
                    startHeaderDwell(key, callback)
                },
                onLeave: () => cancelHeaderDwell(key)
            })
            cleanupMap.set(key, cleanup)
        }
    }, [startHeaderDwell, cancelHeaderDwell])

    /**
     * 초기화: 사용자명 로드, 기기/추천 로드, WebSocket 연결
     */
    useEffect(() => {
        // localStorage에서 사용자명 로드
        const storedUsername = localStorage.getItem('gazehome_username') || '사용자'
        setUsername(storedUsername)

        // 🔔 Browser Notification 권한 요청
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    console.log('[HomePage] Browser Notification 권한 승인됨')
                    // 권한 승인 시 시작 알림
                    new Notification('GazeHome에 오신 것을 환영합니다!', {
                        body: `${storedUsername}님, 시선으로 스마트홈을 제어해보세요.`,
                        icon: '/gazehome-icon.png'
                    })
                } else {
                    console.log('[HomePage] Browser Notification 권한 거부됨')
                }
            })
        }

        loadDevices()
        loadRecommendations()
        connectGazeStream()

        // 30초마다 추천 업데이트 및 모달 표시
        const interval = setInterval(() => {
            loadRecommendations()
            setShowRecommendations(true)
        }, 30000)

        // 🎯 DeviceCard에서 발생한 클릭 이벤트 리스너
        const handleDeviceClicked = (event) => {
            const { device_id, device_name, recommendation } = event.detail
            console.log(`[HomePage] 기기 클릭 감지: ${device_name}`, recommendation)

            // ✅ 기기 상태 업데이트 (로컬)
            // Backend에서 변환된 액션이 포함된 응답에서 새로운 상태 추론
            try {
                // Backend 응답에서 action 필드 추출 (변환된 액션)
                // 예: "aircon_off", "turn_on", "dryer_start" 등
                // 이를 바탕으로 새로운 상태 추론

                // ✅ 방법 1: action 필드에서 상태 추론
                // "aircon_off", "dryer_stop", "turn_off" → "off"
                // "aircon_on", "dryer_start", "turn_on" → "on"
                let newState = 'off'  // 기본값

                if (recommendation && recommendation.action) {
                    const action = recommendation.action.toLowerCase()
                    if (action.includes('on') || action.includes('start')) {
                        newState = 'on'
                    } else if (action.includes('off') || action.includes('stop')) {
                        newState = 'off'
                    }
                }

                // ✅ devices 배열 업데이트 (낙관적 업데이트)
                const updatedDevices = devices.map(device =>
                    device.device_id === device_id
                        ? { ...device, state: newState }
                        : device
                )
                setDevices(updatedDevices)
                console.log(`[HomePage] ✅ 기기 상태 업데이트: ${device_name} → ${newState}`)
            } catch (error) {
                console.warn(`[HomePage] ⚠️  상태 업데이트 실패: ${error}`)
            }

            // AI 추천이 있으면 추천 모달 표시
            if (recommendation) {
                setRecommendations([{
                    id: `rec_click_${Date.now()}`,
                    title: `${device_name} 제어 추천`,
                    description: recommendation.reason || '',
                    device_id: device_id,
                    device_name: device_name,
                    action: recommendation.action || 'toggle',
                    params: recommendation.params || {},
                    reason: recommendation.reason || '시선 클릭 기반 추천',
                    priority: 5,
                    timestamp: new Date().toISOString()
                }])
                setShowRecommendations(true)
            }
        }

        window.addEventListener('device-clicked', handleDeviceClicked)

        return () => {
            clearInterval(interval)
            window.removeEventListener('device-clicked', handleDeviceClicked)
        }
    }, [])

    /**
     * 스마트홈 기기 목록 로드 (로컬 DB에서 조회)
     * 
     * Backend 응답 형식:
     * {
     *   "success": true,
     *   "devices": [
     *     {
     *       "device_id": "1d7c7408...",
     *       "name": "거실 에어컨",
     *       "device_type": "air_conditioner",
     *       "model_name": "LG AC Pro",
     *       "actions": [
     *         {
     *           "id": 1,
     *           "action_type": "operation",
     *           "action_name": "POWER_ON",
     *           "readable": true,
     *           "writable": true,
     *           "value_type": "enum",
     *           "value_range": "[\"POWER_ON\", \"POWER_OFF\"]"
     *         }
     *       ],
     *       "action_count": 42
     *     }
     *   ],
     *   "count": 5,
     *   "source": "local_db"
     * }
     */
    const loadDevices = async () => {
        try {
            const response = await fetch('/api/devices/')
            const data = await response.json()

            if (data.success && data.devices) {
                console.log('[HomePage] 기기 목록 로드 성공:', data)
                console.log('   기기 개수:', data.devices.length)

                // ✅ 로컬 DB에서 가져온 기기 데이터를 그대로 사용
                // device_id, name, device_type, actions[] 포함
                setDevices(data.devices)

                data.devices.forEach(device => {
                    console.log(`   - ${device.name} (${device.device_type}): ${device.action_count}개 액션`)
                })
            } else {
                console.warn('기기 목록 응답 형식 오류:', data)
                setDevices([])
            }
        } catch (error) {
            console.error('기기 로드 실패:', error)
            setDevices([])
        }
    }

    /**
     * AI 추천 로드
     * 주의: 현재 구현에서는 주기적 호출이 없으므로, 기기 클릭 시에만 추천 수신
     */
    const loadRecommendations = async () => {
        try {
            // 현재 백엔드에서 추천 조회 엔드포인트가 없음
            // 추천은 POST /api/devices/{device_id}/click 응답에 포함됨
            console.log('[HomePage] 추천 로드 스킵 (device click response에서 수신)')
            setRecommendations([])
        } catch (error) {
            console.error('추천 로드 실패:', error)
            setRecommendations([])
        }
    }

    /**
     * WebSocket을 통한 시선 스트림 연결
     * - 실시간 시선 위치 수신
     * - 연결 끊김 시 자동 재연결
     */
    const connectGazeStream = () => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/gaze`)

        ws.onopen = () => {
            console.log('시선 스트림 연결됨')
            setIsConnected(true)
        }

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)

            // 시선 업데이트 메시지 처리
            if (data.type === 'gaze_update' && data.gaze) {
                if (!autopilotActiveRef.current) {
                    setGazePosition({ x: data.gaze[0], y: data.gaze[1] })
                }

                // 👁️ 현재 눈깜빡임 상태 (포인터 고정)
                if (data.blink !== undefined) {
                    setBlink(data.blink)
                }

                // � 시선 인식 가능 여부 (false = 시선 불인식, 포인터 마지막 위치 고정)
                // 시선 인식 가능 여부 (false = 시선 불인식, 포인터 마지막 위치 고정)
                if (data.calibrated !== undefined) {
                    setCalibrated(data.calibrated)
                }

                // 1초 이상 눈깜빡임 감지
                if (data.prolonged_blink !== undefined) {
                    setProlongedBlink(data.prolonged_blink)

                    if (data.prolonged_blink) {
                        console.log('[HomePage] 눈깜빡임 1초+ 감지 - 클릭으로 인식!')
                    }
                }
            }

            // 추천 메시지 처리 (WebSocket을 통한 백엔드 푸시)
            if (data.type === 'recommendation') {
                // ✅ WebSocket 메시지 구조: { type: 'recommendation', data: { recommendation_id, title, contents } }
                const recData = data.data || data

                console.log('[HomePage] 추천 수신:', recData.title)
                console.log('[HomePage] 추천 ID:', recData.recommendation_id)
                console.log('[HomePage] 추천 내용:', recData.contents || recData.description || recData.content)
                console.log('[HomePage] 추천 시간:', new Date().toLocaleString())

                const recommendation = {
                    id: recData.recommendation_id,
                    recommendation_id: recData.recommendation_id, // ✅ AI-Server에서 온 ID 그대로 사용
                    title: recData.title,
                    contents: recData.contents || recData.description || recData.content,
                    timestamp: new Date().toISOString()
                }

                setRecommendations([recommendation])
                setShowRecommendations(true)

                // 🔔 Browser Notification API를 통한 알람
                if ('Notification' in window && Notification.permission === 'granted') {
                    new Notification('GazeHome 추천', {
                        body: recData.title,
                        icon: '/gazehome-icon.png',
                        badge: '/gazehome-badge.png',
                        tag: 'ws-recommendation',
                        requireInteraction: true
                    })
                    console.log('[HomePage] Browser Notification 발송됨')
                }
            }
        }

        ws.onerror = (error) => {
            console.error('WebSocket 오류:', error)
            setIsConnected(false)
        }

        ws.onclose = () => {
            console.log('WebSocket 연결 끊김')
            setIsConnected(false)
            // 3초 후 재연결 시도
            setTimeout(connectGazeStream, 3000)
        }
    }

    useEffect(() => {
        if (!autopilotEnabled) {
            console.log('[HomePage][Demo] Autopilot disabled - skip runDemoSequence')
            return
        }
        if (autopilotDevices.length === 0) {
            console.log('[HomePage][Demo] No autopilot devices available - skip')
            return
        }
        if (autopilotStateRef.current.completed) {
            console.log('[HomePage][Demo] Autopilot already completed - skip')
            return
        }
        if (autopilotStateRef.current.cancelled) {
            console.log('[HomePage][Demo] Autopilot cancelled - skip')
            return
        }
        console.log('[HomePage][Demo] Trigger runDemoSequence()')
        runDemoSequence()
    }, [autopilotEnabled, autopilotDevices.length, runDemoSequence])

    useEffect(() => {
        if (!autopilotEnabled) {
            return
        }
        if (introAnimationRanRef.current) {
            return
        }
        if (autopilotDevices.length === 0) {
            return
        }
        startIntroAnimation()
    }, [autopilotEnabled, autopilotDevices.length, startIntroAnimation])

    useEffect(() => {
        if (!autopilotEnabled) {
            return
        }
        const state = autopilotStateRef.current
        if (!state.waitingForRecommendation || state.running || state.completed) {
            return
        }
        if (!showRecommendations || recommendations.length === 0) {
            return
        }

        let active = true
        state.running = true

        const run = async () => {
            try {
                const acceptButton = await waitForElement(() => {
                    const modal = document.querySelector('.recommendation-modal')
                    return modal?.querySelector('.action-button.accept') || null
                }, 5000)

                if (!active) {
                    return
                }

                if (acceptButton) {
                    console.log('[HomePage][Demo] 추천 수락 dwell')
                    await dwellOnElement(acceptButton)
                } else {
                    console.warn('[HomePage][Demo] 추천 수락 버튼을 찾을 수 없습니다')
                }
            } catch (error) {
                console.error('[HomePage][Demo] 추천 수락 자동화 오류:', error)
            } finally {
                if (!active) {
                    return
                }
                state.running = false
                state.waitingForRecommendation = false
                state.completed = true
                stopAutopilotOverride()
            }
        }

        run()

        return () => {
            active = false
        }
    }, [
        autopilotEnabled,
        dwellOnElement,
        recommendations,
        showRecommendations,
        stopAutopilotOverride,
        waitForElement
    ])

    useEffect(() => {
        return () => {
            autopilotStateRef.current.cancelled = true
            stopAutopilotOverride()
        }
    }, [stopAutopilotOverride])

    useEffect(() => {
        if (isPointerLocked || !calibrated || blink || stableCursor.frozen) {
            clearGazeTarget()
            return
        }

        if (stableCursor.x >= 0 && stableCursor.y >= 0) {
            updateGazeTarget(stableCursor.x, stableCursor.y)
        }
    }, [stableCursor, blink, calibrated, isPointerLocked, updateGazeTarget, clearGazeTarget])

    useEffect(() => () => clearGazeTarget(), [clearGazeTarget])
    useEffect(() => () => cancelPaginationDwell(), [cancelPaginationDwell])
    useEffect(() => () => cancelHeaderDwell(), [cancelHeaderDwell])

    const handleNotificationOpen = useCallback(() => {
        setShowRecommendations(true)
    }, [])

    const handleRestartCalibration = useCallback(() => {
        console.log('[HomePage] 🔄 보정 다시 시작')
        window.location.href = '/calibration'
    }, [])

    const handleLogoutClick = useCallback(() => {
        if (typeof onLogout === 'function') {
            onLogout()
        }
    }, [onLogout])

    /**
     * 기기 제어
     * @param {string} deviceId - 기기 ID
     * @param {string} action - 제어 액션 (toggle, turn_on, turn_off 등)
     * @param {Object} params - 추가 파라미터
     */
    const handleDeviceControl = async (deviceId, action, params = {}) => {
        // 🔒 다른 기기 제어 중이면 return
        if (controllingDevice) {
            console.log('[HomePage] 기기 제어 중 - 건너뜀:', controllingDevice)
            return
        }

        try {
            setControllingDevice(deviceId)
            console.log('[HomePage] 기기 제어 시작:', deviceId, action)

            // Backend: POST /api/devices/{device_id}/click
            // 올바른 요청 형식: { "user_id": "...", "action": "..." }
            // 응답 형식: { "success": true, "device_id": "...", "result": { "recommendation": {...} } }
            const response = await fetch(`/api/devices/${deviceId}/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: localStorage.getItem('gazehome_user_id') || 'default_user',
                    action: action || 'toggle'
                }),
            })

            const result = await response.json()

            if (result.success) {
                console.log('[HomePage] 기기 제어 성공:', result)
                // 제어 성공 시 기기 목록 갱신
                await loadDevices()
            } else {
                console.error('[HomePage] 기기 제어 실패:', result)
            }
        } catch (error) {
            console.error('[HomePage] 기기 제어 오류:', error)
        } finally {
            // 500ms 후 제어 완료 (다음 기기 제어 가능)
            setTimeout(() => {
                setControllingDevice(null)
                console.log('[HomePage] 기기 제어 완료')
            }, 500)
        }
    }

    /**
     * 추천 수락 핸들러
     * - 추천된 액션 실행
     * - 사용자 피드백 전송
     */
    const handleRecommendationAccept = async (recommendation) => {
        // 추천 액션 실행
        await handleDeviceControl(
            recommendation.device_id,
            recommendation.action,
            recommendation.params
        )

        // 피드백 전송
        try {
            await fetch('/api/recommendations/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recommendation_id: recommendation.id || recommendation.recommendation_id,
                    user_id: localStorage.getItem('gazehome_user_id') || '1',
                    accepted: true
                }),
            })
            console.log('[HomePage] 피드백 전송 완료')
        } catch (error) {
            console.error('[HomePage] 피드백 전송 실패:', error)
        }

        setShowRecommendations(false)
        setRecommendations([])
    }

    return (
        <div className="home-page">
            {/* 시선 커서 표시 */}
            {/*
                visible은 WebSocket 연결 상태(isConnected) 뿐만 아니라
                보정 상태(calibrated)가 true일 때도 표시되도록 합니다.
                이 변경은 개발/디버깅 시 포인터가 보이지 않는 문제를 완화합니다.
            */}
            <GazeCursor
                x={gazePosition.x}
                y={gazePosition.y}
                visible={isConnected || calibrated}
                blink={blink}
                calibrated={calibrated}
                onStablePosition={handleStableCursorUpdate}
            />

            {/* 헤더 */}
            <header className="home-header">
                <div className="container">
                    <div className="header-content">
                        {/* 좌측: 로고 및 연결 상태 */}
                        <div className="header-left">
                            <div className="logo">
                                <Eye size={32} />
                                <span>GazeHome</span>
                            </div>
                            <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                                <div className="status-dot"></div>
                                {isConnected ? '시선 추적 중' : '연결 끊김'}
                            </div>
                        </div>

                        {/* 우측: 알림, 사용자 메뉴, 설정, 로그아웃 버튼 */}
                        <div className="header-right">
                            {/* 알림 버튼 */}
                            <button
                                ref={makeHeaderButtonRef('header_notification', handleNotificationOpen)}
                                className="notification-button"
                                onMouseEnter={() => startHeaderDwell('header_notification', handleNotificationOpen)}
                                onMouseLeave={() => cancelHeaderDwell('header_notification')}
                                onClick={handleNotificationOpen}
                                style={{
                                    position: 'relative',
                                    overflow: 'hidden',
                                    background: headerDwelling === 'header_notification'
                                        ? `linear-gradient(to right, var(--primary) ${headerProgress}%, transparent ${headerProgress}%)`
                                        : undefined
                                }}
                            >
                                <Bell size={20} />
                                {recommendations.length > 0 && (
                                    <span className="notification-badge">{recommendations.length}</span>
                                )}
                                {headerDwelling === 'header_notification' && (
                                    <span
                                        style={{
                                            position: 'absolute',
                                            bottom: 0,
                                            left: 0,
                                            height: '3px',
                                            width: `${headerProgress}%`,
                                            backgroundColor: 'var(--primary)',
                                            transition: 'width 50ms linear'
                                        }}
                                    />
                                )}
                            </button>

                            {/* 설정 버튼 → 다시 보정 화면 */}
                            <button
                                ref={makeHeaderButtonRef('header_calibration', handleRestartCalibration)}
                                className="icon-button"
                                onMouseEnter={() => startHeaderDwell('header_calibration', handleRestartCalibration)}
                                onMouseLeave={() => cancelHeaderDwell('header_calibration')}
                                onClick={handleRestartCalibration}
                                title="다시 보정"
                                style={{
                                    position: 'relative',
                                    overflow: 'hidden',
                                    background: headerDwelling === 'header_calibration'
                                        ? `linear-gradient(to right, var(--primary) ${headerProgress}%, transparent ${headerProgress}%)`
                                        : undefined
                                }}
                            >
                                <Settings size={20} />
                                {headerDwelling === 'header_calibration' && (
                                    <span
                                        style={{
                                            position: 'absolute',
                                            bottom: 0,
                                            left: 0,
                                            height: '3px',
                                            width: `${headerProgress}%`,
                                            backgroundColor: 'var(--primary)',
                                            transition: 'width 50ms linear'
                                        }}
                                    />
                                )}
                            </button>

                            {/* 로그아웃 버튼 */}
                            <button
                                ref={makeHeaderButtonRef('header_logout', handleLogoutClick)}
                                className="icon-button"
                                onMouseEnter={() => startHeaderDwell('header_logout', handleLogoutClick)}
                                onMouseLeave={() => cancelHeaderDwell('header_logout')}
                                onClick={handleLogoutClick}
                                style={{
                                    position: 'relative',
                                    overflow: 'hidden',
                                    background: headerDwelling === 'header_logout'
                                        ? `linear-gradient(to right, var(--danger) ${headerProgress}%, transparent ${headerProgress}%)`
                                        : undefined
                                }}
                            >
                                <LogOut size={20} />
                                {headerDwelling === 'header_logout' && (
                                    <span
                                        style={{
                                            position: 'absolute',
                                            bottom: 0,
                                            left: 0,
                                            height: '3px',
                                            width: `${headerProgress}%`,
                                            backgroundColor: 'var(--danger)',
                                            transition: 'width 50ms linear'
                                        }}
                                    />
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* 메인 콘텐츠 */}
            <main className="home-main">
                <div className="container">
                    {/* 환영 섹션 */}
                    <motion.div
                        className="welcome-section"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        <h1>안녕하세요, {username}님</h1>
                        <p>시선으로 스마트홈을 제어해보세요</p>
                    </motion.div>

                    {/* 기기 그리드 - 페이지네이션 방식 */}
                    <motion.div
                        className="devices-section"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.2 }}
                    >
                        <div className="section-header">
                            <h2>내 기기</h2>
                            <span className="device-count">
                                {autopilotDevices.length}개 기기
                            </span>
                        </div>

                        {/* 기기 페이지네이션 */}
                        {autopilotDevices.length > 0 ? (
                            <>
                                <div className="pagination-controls">
                                    {/* 이전 버튼 */}
                                    <button
                                        ref={prevButtonRef}
                                        className={`pagination-button prev ${paginationDwelling === 'prev' ? 'dwelling' : ''}`}
                                        onMouseEnter={() => startPaginationDwell('prev', handlePrevDevice)}
                                        onMouseLeave={cancelPaginationDwell}
                                        onClick={handlePrevDevice}
                                        disabled={autopilotDevices.length === 1}
                                        style={{
                                            position: 'relative',
                                            overflow: 'hidden',
                                            background: paginationDwelling === 'prev'
                                                ? `linear-gradient(to right, var(--primary) ${paginationProgress}%, transparent ${paginationProgress}%)`
                                                : undefined
                                        }}
                                    >
                                        <ChevronLeft size={32} />
                                        이전
                                        {paginationDwelling === 'prev' && (
                                            <span
                                                style={{
                                                    position: 'absolute',
                                                    bottom: '4px',
                                                    left: 0,
                                                    height: '4px',
                                                    width: `${paginationProgress}%`,
                                                    backgroundColor: 'var(--primary)',
                                                    transition: 'width 50ms linear'
                                                }}
                                            />
                                        )}
                                    </button>

                                    {/* 페이지 인디케이터 */}
                                    <div className="page-indicator">
                                        <span className="current-page">
                                            {currentDeviceIndex + 1}
                                        </span>
                                        <span> / {autopilotDevices.length}</span>
                                    </div>

                                    {/* 다음 버튼 */}
                                    <button
                                        ref={nextButtonRef}
                                        className={`pagination-button next ${paginationDwelling === 'next' ? 'dwelling' : ''}`}
                                        onMouseEnter={() => startPaginationDwell('next', handleNextDevice)}
                                        onMouseLeave={cancelPaginationDwell}
                                        onClick={handleNextDevice}
                                        disabled={autopilotDevices.length === 1}
                                        style={{
                                            position: 'relative',
                                            overflow: 'hidden',
                                            background: paginationDwelling === 'next'
                                                ? `linear-gradient(to right, var(--primary) ${paginationProgress}%, transparent ${paginationProgress}%)`
                                                : undefined
                                        }}
                                    >
                                        다음
                                        <ChevronRight size={32} />
                                        {paginationDwelling === 'next' && (
                                            <span
                                                style={{
                                                    position: 'absolute',
                                                    bottom: '4px',
                                                    left: 0,
                                                    height: '4px',
                                                    width: `${paginationProgress}%`,
                                                    backgroundColor: 'var(--primary)',
                                                    transition: 'width 50ms linear'
                                                }}
                                            />
                                        )}
                                    </button>
                                </div>

                                {/* 기기 카드 */}
                                <div className="devices-grid">
                                    <AnimatePresence mode="wait">
                                        {displayDevices.map((device) => (
                                            <motion.div
                                                key={device.device_id}
                                                initial={{ opacity: 0, x: 20 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                exit={{ opacity: 0, x: -20 }}
                                                transition={{ duration: 0.3 }}
                                            >
                                                <DeviceCard
                                                    device={device}
                                                    onControl={handleDeviceControl}
                                                />
                                            </motion.div>
                                        ))}
                                    </AnimatePresence>
                                </div>
                            </>
                        ) : (
                            <div className="no-devices-message">
                                <p>등록된 기기가 없습니다</p>
                                <p className="hint">에어컨1과 공기청정기를 등록해주세요</p>
                            </div>
                        )}
                    </motion.div>
                </div>
            </main>

            {/* 추천 모달 */}
            <AnimatePresence>
                {showRecommendations && recommendations.length > 0 && (
                    <RecommendationModal
                        recommendations={recommendations}
                        onAccept={handleRecommendationAccept}
                        onClose={() => setShowRecommendations(false)}
                        prolongedBlink={prolongedBlink}
                        isPointerLocked={isPointerLocked}
                        onPointerEnter={lockPointer}
                    />
                )}
            </AnimatePresence>
        </div>
    )
}

export default HomePage
