import { motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import './GazeCursor.css'

/**
 * 시선 커서 컴포넌트
 * - WebSocket으로부터 받은 시선 위치를 실시간으로 표시
 * - Spring 애니메이션으로 부드러운 움직임 구현
 * - 👁️ 눈깜빡임 또는 시선 인식 불가 시 포인터 마지막 위치에 고정
 * - 👁️ 0.5초+ 눈깜빡임 감지 → 시선 위치 요소 클릭
 * 
 * @param {number} x - 화면 X 좌표
 * @param {number} y - 화면 Y 좌표
 * @param {boolean} visible - 커서 표시 여부
 * @param {boolean} blink - 눈깜빡임 여부 (true = 눈 감음, 포인터 고정)
 * @param {boolean} calibrated - 시선 인식 가능 여부 (false = 인식 불가, 포인터 고정)
 */

function GazeCursor({ x, y, visible, blink = false, calibrated = true }) {
    const lastValidPosRef = useRef({
        x: window.innerWidth / 2,
        y: window.innerHeight / 2
    })

    const prevBlinkRef = useRef(false)
    const [debounceTimer, setDebounceTimer] = useState(null)
    const shouldFreeze = blink || !calibrated

    // 고정되기 직전에 현재 위치를 유효 위치로 갱신
    useEffect(() => {
        if (!shouldFreeze && x >= 0 && y >= 0) {
            lastValidPosRef.current = { x, y }
        }
    }, [x, y, shouldFreeze])

    // 👁️ 깜빡임 끝남 감지 → 시선 위치 요소 클릭 (50ms 디바운싱)
    useEffect(() => {
        // blink: true → false 전환만 감지 (깜빡임 완료)
        if (!blink && prevBlinkRef.current && !debounceTimer) {
            // 50ms 디바운싱: 과도한 호출 방지
            const timer = setTimeout(() => {
                const element = document.elementFromPoint(
                    lastValidPosRef.current.x,
                    lastValidPosRef.current.y
                )

                if (element && element !== document.body && element !== document.documentElement) {
                    console.log('[GazeCursor] 깜빡임 클릭 감지:', element.className)
                    element.click()
                }

                setDebounceTimer(null)
            }, 50)

            setDebounceTimer(timer)
        }

        prevBlinkRef.current = blink

        return () => {
            if (debounceTimer) clearTimeout(debounceTimer)
        }
    }, [blink, debounceTimer])

    if (!visible) return null

    const displayX = shouldFreeze ? lastValidPosRef.current.x : x
    const displayY = shouldFreeze ? lastValidPosRef.current.y : y

    return (
        <motion.div
            className="gaze-cursor"
            animate={{ left: displayX, top: displayY }}
            transition={{
                type: 'spring',
                stiffness: shouldFreeze ? 10000 : 20,  // 50 → 20 (훨씬 느리게)
                damping: shouldFreeze ? 100 : 15,      // 25 → 15 (더 부드럽게)
                mass: 2.5                               // 1.5 → 2.5 (관성 대폭 증가)
            }}
        >
            <div className="cursor-ring"></div>
            <div className="cursor-dot"></div>
        </motion.div>
    )
}

export default GazeCursor