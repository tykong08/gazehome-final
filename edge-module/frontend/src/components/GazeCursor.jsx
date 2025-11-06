import { motion } from 'framer-motion'
import { useEffect, useMemo, useRef, useState } from 'react'
import './GazeCursor.css'

/**
 * 시선 커서 컴포넌트
 * - WebSocket으로부터 받은 시선 위치를 실시간으로 표시
 * - 내부적으로 저지연 스무딩 (NoOp 필터 환경 보완)
 * - 🧲 버튼 영역 진입 시 자석 효과 (버튼 중심으로 스냅)
 * - 👁️ 눈깜빡임/미보정 시 마지막 위치 유지
 */

function GazeCursor({
    x,
    y,
    visible,
    blink = false,
    calibrated = true,
    onStablePosition
}) {
    const viewportCenter = useMemo(() => ({
        x: window.innerWidth / 2,
        y: window.innerHeight / 2
    }), [])

    const [displayPos, setDisplayPos] = useState(viewportCenter)
    const [magnetTarget, setMagnetTarget] = useState(null)

    const lastValidPosRef = useRef(viewportCenter)
    const smoothedPosRef = useRef(viewportCenter)
    const lastUpdateRef = useRef(typeof performance !== 'undefined' ? performance.now() : Date.now())
    const magnetCheckIntervalRef = useRef(null)

    const shouldFreeze = blink || !calibrated

    const clamp = (value, min, max) => {
        if (!Number.isFinite(value)) return min
        return Math.min(Math.max(value, min), max)
    }

    const isValidCoordinate = (value) => typeof value === 'number' && Number.isFinite(value)

    useEffect(() => {
        smoothedPosRef.current = displayPos
    }, [displayPos])

    useEffect(() => {
        if (shouldFreeze) {
            lastUpdateRef.current = typeof performance !== 'undefined' ? performance.now() : Date.now()
            return
        }

        if (!isValidCoordinate(x) || !isValidCoordinate(y) || x < 0 || y < 0) {
            return
        }

        const now = typeof performance !== 'undefined' ? performance.now() : Date.now()
        const prevTimestamp = lastUpdateRef.current || now
        const deltaMs = Math.max(now - prevTimestamp, 16)
        lastUpdateRef.current = now

        const normalizedDelta = deltaMs / 16.67
        const SMOOTHING_ALPHA = 0.45
        const MAX_STEP_PX = 120
        const MIN_DELTA = 0.2

        setDisplayPos((prev) => {
            const viewportWidth = window.innerWidth
            const viewportHeight = window.innerHeight

            const targetX = clamp(x, 0, viewportWidth)
            const targetY = clamp(y, 0, viewportHeight)

            const smoothingFactor = 1 - Math.pow(1 - SMOOTHING_ALPHA, normalizedDelta)

            let nextX = prev.x + (targetX - prev.x) * smoothingFactor
            let nextY = prev.y + (targetY - prev.y) * smoothingFactor

            const dx = nextX - prev.x
            const dy = nextY - prev.y
            const distance = Math.hypot(dx, dy)
            const maxStep = Math.max(MAX_STEP_PX * normalizedDelta, 8)

            if (distance > maxStep) {
                const scale = maxStep / distance
                nextX = prev.x + dx * scale
                nextY = prev.y + dy * scale
            }

            if (Math.abs(targetX - prev.x) < MIN_DELTA) {
                nextX = prev.x
            }
            if (Math.abs(targetY - prev.y) < MIN_DELTA) {
                nextY = prev.y
            }

            const clampedX = clamp(nextX, 0, viewportWidth)
            const clampedY = clamp(nextY, 0, viewportHeight)

            lastValidPosRef.current = { x: clampedX, y: clampedY }
            return { x: clampedX, y: clampedY }
        })
    }, [x, y, shouldFreeze])

    useEffect(() => {
        if (shouldFreeze) {
            setMagnetTarget(null)
            return
        }

        magnetCheckIntervalRef.current = setInterval(() => {
            const { x: currentX, y: currentY } = smoothedPosRef.current
            const element = document.elementFromPoint(currentX, currentY)

            if (element) {
                const isButton = element.tagName === 'BUTTON' ||
                    element.classList.contains('action-button') ||
                    element.classList.contains('temp-button') ||
                    element.classList.contains('pagination-button') ||
                    element.classList.contains('icon-button') ||
                    element.classList.contains('refresh-button') ||
                    element.closest('button')

                if (isButton) {
                    const targetElement = element.tagName === 'BUTTON' ? element : element.closest('button')
                    if (targetElement) {
                        const rect = targetElement.getBoundingClientRect()
                        const centerX = rect.left + rect.width / 2
                        const centerY = rect.top + rect.height / 2
                        setMagnetTarget({ x: centerX, y: centerY })
                        return
                    }
                }
            }

            setMagnetTarget(null)
        }, 80)

        return () => {
            if (magnetCheckIntervalRef.current) {
                clearInterval(magnetCheckIntervalRef.current)
            }
        }
    }, [shouldFreeze])

    if (!visible) {
        if (typeof onStablePosition === 'function') {
            onStablePosition({
                x: lastValidPosRef.current.x,
                y: lastValidPosRef.current.y,
                frozen: true,
                magnetized: Boolean(magnetTarget)
            })
        }
        return null
    }

    const basePos = shouldFreeze
        ? lastValidPosRef.current
        : magnetTarget || displayPos

    const displayX = basePos?.x ?? lastValidPosRef.current.x
    const displayY = basePos?.y ?? lastValidPosRef.current.y

    useEffect(() => {
        if (typeof onStablePosition !== 'function') return

        onStablePosition({
            x: displayX,
            y: displayY,
            frozen: shouldFreeze,
            magnetized: Boolean(magnetTarget)
        })
    }, [displayX, displayY, shouldFreeze, magnetTarget, onStablePosition])

    return (
        <motion.div
            className="gaze-cursor"
            animate={{ left: displayX, top: displayY }}
            transition={{
                type: 'spring',
                stiffness: magnetTarget ? 220 : (shouldFreeze ? 12000 : 12),
                damping: magnetTarget ? 30 : (shouldFreeze ? 120 : 26),
                mass: magnetTarget ? 0.4 : 2.5
            }}
        >
            <div className="cursor-ring"></div>
            <div className="cursor-dot"></div>
        </motion.div>
    )
}

export default GazeCursor