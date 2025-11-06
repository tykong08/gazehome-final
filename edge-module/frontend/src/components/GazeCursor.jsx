import { motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import './GazeCursor.css'

/**
 * 시선 커서 컴포넌트
 * - WebSocket으로부터 받은 시선 위치를 실시간으로 표시
 * - Spring 애니메이션으로 부드러운 움직임 구현
 * - 👁️ 눈깜빡임 또는 시선 인식 불가 시 포인터 마지막 위치에 고정
 * - 👁️ 0.5초+ 눈깜빡임 감지 → 시선 위치 요소 클릭
 * - 🧲 버튼 영역 진입 시 자석 효과 (버튼 중심으로 스냅)
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

    // 🧲 자석 효과: 버튼 중심 좌표 저장
    const [magnetTarget, setMagnetTarget] = useState(null)
    const magnetCheckIntervalRef = useRef(null)

    // 고정되기 직전에 현재 위치를 유효 위치로 갱신
    useEffect(() => {
        if (!shouldFreeze && x >= 0 && y >= 0) {
            lastValidPosRef.current = { x, y }
        }
    }, [x, y, shouldFreeze])

    // 🧲 자석 효과: 버튼 영역 진입 감지 (100ms마다 체크)
    useEffect(() => {
        if (shouldFreeze) {
            // 포인터 고정 중에는 자석 효과 비활성화
            setMagnetTarget(null)
            return
        }

        magnetCheckIntervalRef.current = setInterval(() => {
            const currentX = x >= 0 ? x : lastValidPosRef.current.x
            const currentY = y >= 0 ? y : lastValidPosRef.current.y

            // 현재 포인터 위치의 요소 가져오기
            const element = document.elementFromPoint(currentX, currentY)

            if (element) {
                // 버튼 또는 클릭 가능한 요소인지 확인
                const isButton = element.tagName === 'BUTTON' ||
                    element.classList.contains('action-button') ||
                    element.classList.contains('temp-button') ||
                    element.classList.contains('pagination-button') ||
                    element.classList.contains('icon-button') ||
                    element.classList.contains('refresh-button') ||
                    element.closest('button')

                if (isButton) {
                    // 버튼의 중심 좌표 계산
                    const targetElement = element.tagName === 'BUTTON' ? element : element.closest('button')
                    if (targetElement) {
                        const rect = targetElement.getBoundingClientRect()
                        const centerX = rect.left + rect.width / 2
                        const centerY = rect.top + rect.height / 2

                        // 자석 효과: 버튼 중심으로 스냅
                        setMagnetTarget({ x: centerX, y: centerY })
                        return
                    }
                }
            }

            // 버튼 영역 밖이면 자석 해제
            setMagnetTarget(null)
        }, 100) // 100ms마다 체크 (부드러운 전환)

        return () => {
            if (magnetCheckIntervalRef.current) {
                clearInterval(magnetCheckIntervalRef.current)
            }
        }
    }, [x, y, shouldFreeze])

    // 👁️ 깜빡임 클릭 비활성화 - 오직 2초 응시만 사용
    // useEffect(() => {
    //     // blink: true → false 전환만 감지 (깜빡임 완료)
    //     if (!blink && prevBlinkRef.current && !debounceTimer) {
    //         // 50ms 디바운싱: 과도한 호출 방지
    //         const timer = setTimeout(() => {
    //             const element = document.elementFromPoint(
    //                 lastValidPosRef.current.x,
    //                 lastValidPosRef.current.y
    //             )

    //             if (element && element !== document.body && element !== document.documentElement) {
    //                 console.log('[GazeCursor] 깜빡임 클릭 감지:', element.className)
    //                 element.click()
    //             }

    //             setDebounceTimer(null)
    //         }, 50)

    //         setDebounceTimer(timer)
    //     }

    //     prevBlinkRef.current = blink

    //     return () => {
    //         if (debounceTimer) clearTimeout(debounceTimer)
    //     }
    // }, [blink, debounceTimer])

    if (!visible) return null

    // 🧲 자석 효과 적용: 버튼 중심 또는 실제 시선 위치
    const displayX = magnetTarget
        ? magnetTarget.x
        : (shouldFreeze ? lastValidPosRef.current.x : x)
    const displayY = magnetTarget
        ? magnetTarget.y
        : (shouldFreeze ? lastValidPosRef.current.y : y)

    return (
        <motion.div
            className="gaze-cursor"
            animate={{ left: displayX, top: displayY }}
            transition={{
                type: 'spring',
                stiffness: magnetTarget ? 150 : (shouldFreeze ? 10000 : 8),   // 자석: 150, 고정: 10000, 일반: 8
                damping: magnetTarget ? 25 : (shouldFreeze ? 100 : 20),       // 자석: 25, 고정: 100, 일반: 20
                mass: magnetTarget ? 0.5 : 3.0                                 // 자석: 0.5 (빠른 응답), 일반: 3.0
            }}
        >
            <div className="cursor-ring"></div>
            <div className="cursor-dot"></div>
        </motion.div>
    )
}

export default GazeCursor