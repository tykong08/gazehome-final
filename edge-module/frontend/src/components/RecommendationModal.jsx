import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, AlertCircle, CheckCircle } from 'lucide-react'
import './RecommendationModal.css'

/**
 * AI 추천 모달 컴포넌트
 * - AI 추천을 표시 (title, contents만)
 * - 사용자가 추천을 수락하거나 거절할 수 있음
 * - 🔒 버튼 클릭 후 1.5초 포인터 고정
 * - 👁️ 모달 위에서 깜빡임 감지 → "수락" 버튼 실행
 * 
 * @param {Array} recommendations - 추천 배열 (단일 추천만 사용)
 * @param {Function} onAccept - 추천 수락 콜백
 * @param {Function} onClose - 모달 닫기 콜백
 * @param {boolean} prolongedBlink - 0.5초 이상 눈깜빡임
 * @param {boolean} isPointerLocked - 전역 포인터 고정 상태
 * @param {Function} onPointerEnter - 포인터 고정 콜백 (버튼 호버 시)
 */
function RecommendationModal({ recommendations, onAccept, onClose, prolongedBlink, isPointerLocked, onPointerEnter }) {
    // 🔒 포인터 고정 상태
    const [isLocked, setIsLocked] = useState(false)
    const lockTimerRef = useRef(null)

    // ⏱️ 포인터 고정 시간 (ms)
    const LOCK_DURATION = 1500  // 1.5초

    // 이전 prolongedBlink 상태 추적 (상태 변화 감지용)
    const prevBlinkRef = useRef(false)

    // 👁️ Dwell Time 기능 (3초간 바라보면 토글 - 데모 최적화)
    const [dwellingButton, setDwellingButton] = useState(null) // 'accept' 또는 'reject'
    const [dwellProgress, setDwellProgress] = useState(0) // 진행률 (0-100)
    const dwellTimerRef = useRef(null)
    const DWELL_TIME = 3000 // 3초 (데모용 - 포인터 고정 시간 증가)

    // 최상위 추천 (단일 추천)
    const topRecommendation = recommendations[0]

    // 디버깅: 추천 데이터 확인
    console.log('[RecommendationModal] 추천 데이터:', topRecommendation)
    console.log('[RecommendationModal] title:', topRecommendation?.title)
    console.log('[RecommendationModal] contents:', topRecommendation?.contents)

    if (!topRecommendation) return null

    /**
     * 버튼 클릭 핸들러
     * - 포인터 고정 시작
     * - AI-Server에 YES/NO 응답 전송 (/api/recommendations/confirm)
     * - 콜백 실행
     */
    const handleButtonClick = async (callback, accepted = true) => {
        // 포인터 고정 시작
        console.log(`[RecommendationModal] 🔒 포인터 고정 시작 (${LOCK_DURATION}ms)`)
        setIsLocked(true)

        // 기존 타이머 정리
        if (lockTimerRef.current) {
            clearTimeout(lockTimerRef.current)
        }

        // 1.5초 후 포인터 고정 해제
        lockTimerRef.current = setTimeout(() => {
            console.log(`[RecommendationModal] 🔓 포인터 고정 해제`)
            setIsLocked(false)
        }, LOCK_DURATION)

        // AI-Server에 사용자 응답 전송
        // Flow: Frontend → Edge-Module (/api/recommendations/confirm) → AI-Server
        try {
            const response_text = accepted ? "YES (수락)" : "NO (거절)"
            console.log(`[RecommendationModal] 📤 AI-Server로 응답 전송: ${response_text}`)

            const response = await fetch('/api/recommendations/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recommendation_id: topRecommendation.recommendation_id,
                    confirm: accepted ? "YES" : "NO"
                }),
            })

            if (response.ok) {
                const result = await response.json()
                console.log(`[RecommendationModal] ✅ 응답 전송 완료:`, result)

                if (accepted && result.ai_server_response?.success) {
                    console.log(`[RecommendationModal] → AI-Server가 기기 제어를 수행합니다`)
                } else if (!accepted) {
                    console.log(`[RecommendationModal] → 사용자가 거부했습니다`)
                }
            } else {
                console.error(`[RecommendationModal] ❌ 응답 전송 실패: ${response.status}`)
            }
        } catch (error) {
            console.error('[RecommendationModal] ❌ 응답 전송 오류:', error)
        }

        // 콜백 실행
        callback()
    }

    /**
     * 👁️ Dwell Time 시작: 버튼에 시선이 머물 때
     */
    const handleButtonEnter = (buttonType, callback, accepted) => {
        if (isLocked) return

        console.log(`[RecommendationModal] 👁️ Dwell 시작: ${buttonType}`)
        setDwellingButton(buttonType)
        setDwellProgress(0)

        let startTime = Date.now()
        dwellTimerRef.current = setInterval(() => {
            const elapsed = Date.now() - startTime
            const progress = Math.min((elapsed / DWELL_TIME) * 100, 100)
            setDwellProgress(progress)

            // 2초 완료
            if (progress >= 100) {
                clearInterval(dwellTimerRef.current)
                console.log(`[RecommendationModal] ✅ Dwell 완료: ${buttonType}`)
                handleButtonClick(callback, accepted)
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
            console.log(`[RecommendationModal] ❌ Dwell 취소`)
        }
        setDwellingButton(null)
        setDwellProgress(0)
    }

    // 컴포넌트 언마운트시 타이머 정리
    useEffect(() => {
        return () => {
            if (lockTimerRef.current) {
                clearTimeout(lockTimerRef.current)
            }
            if (dwellTimerRef.current) {
                clearInterval(dwellTimerRef.current)
            }
        }
    }, [])

    /**
     * 👁️ 눈깜빡임 감지 - 모달 내 버튼 클릭
     * prolongedBlink가 false → true 전환 감지 (깜빡임 완료)
     * 
     * 주의: 이 기능은 dwell time과 별개로 작동 (눈깜빡임으로 즉시 실행)
     */
    useEffect(() => {
        if (isLocked) return

        // 이전 상태: false, 현재 상태: true (깜빡임 END)
        if (!prevBlinkRef.current && prolongedBlink) {
            prevBlinkRef.current = prolongedBlink

            // 시선이 모달 영역에 있는지 확인
            const modal = document.querySelector('.recommendation-modal')
            const gazeCursor = document.querySelector('.gaze-cursor')

            if (!modal || !gazeCursor) return

            const modalRect = modal.getBoundingClientRect()
            const cursorRect = gazeCursor.getBoundingClientRect()
            const cursorX = cursorRect.left + cursorRect.width / 2
            const cursorY = cursorRect.top + cursorRect.height / 2

            // 시선이 모달 내부에 있는지 확인
            const isInside =
                cursorX >= modalRect.left &&
                cursorX <= modalRect.right &&
                cursorY >= modalRect.top &&
                cursorY <= modalRect.bottom

            if (isInside) {
                // 👁️ 모달 위에서 깜빡임 감지 → "적용하기" 버튼 클릭
                console.log(`[RecommendationModal] 👁️ 1초 깜빡임 클릭 감지 - "적용하기" 실행`)
                handleButtonClick(() => onAccept(topRecommendation), true)
            }
        } else {
            // 상태 업데이트
            prevBlinkRef.current = prolongedBlink
        }
    }, [prolongedBlink, isLocked, topRecommendation])

    return (
        <motion.div
            className="recommendation-modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
        // 모달 팝업 - 오버레이 클릭 시 닫지 않음
        >
            <motion.div
                className="recommendation-modal"
                initial={{ opacity: 0, scale: 0.9, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: 20 }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* 모달 헤더 */}
                <div className="modal-header">
                    <div className="modal-title">
                        <Sparkles size={24} className="title-icon" />
                        <h2>🔔 AI 추천</h2>
                    </div>
                    {/* 닫기 버튼 제거 - 추천 팝업은 사용자가 선택할 때까지 표시 */}
                </div>

                {/* 주요 추천 사항 */}
                <div className="recommendation-content">
                    {/* 추천 제목 및 내용 */}
                    <h3 className="recommendation-title">
                        {topRecommendation.title || '제목 없음'}
                    </h3>
                    <p className="recommendation-description">
                        {topRecommendation.contents || '내용 없음'}
                    </p>

                    {/* 액션 버튼 - YES / NO */}
                    <div className="modal-actions">
                        <button
                            className={`action-button accept ${dwellingButton === 'accept' ? 'dwelling' : ''}`}
                            onMouseEnter={() => handleButtonEnter('accept', () => onAccept(topRecommendation), true)}
                            onMouseLeave={handleButtonLeave}
                            disabled={isLocked}
                            style={{
                                position: 'relative',
                                overflow: 'hidden',
                                background: dwellingButton === 'accept'
                                    ? `linear-gradient(to right, var(--success) ${dwellProgress}%, transparent ${dwellProgress}%)`
                                    : ''
                            }}
                        >
                            <CheckCircle size={20} />
                            수락
                            {dwellingButton === 'accept' && (
                                <span style={{
                                    position: 'absolute',
                                    bottom: 0,
                                    left: 0,
                                    height: '4px',
                                    width: `${dwellProgress}%`,
                                    backgroundColor: 'var(--success)',
                                    transition: 'width 50ms linear'
                                }}></span>
                            )}
                        </button>
                        <button
                            className={`action-button reject ${dwellingButton === 'reject' ? 'dwelling' : ''}`}
                            onMouseEnter={() => handleButtonEnter('reject', () => onClose(), false)}
                            onMouseLeave={handleButtonLeave}
                            disabled={isLocked}
                            style={{
                                position: 'relative',
                                overflow: 'hidden',
                                background: dwellingButton === 'reject'
                                    ? `linear-gradient(to right, var(--danger) ${dwellProgress}%, transparent ${dwellProgress}%)`
                                    : ''
                            }}
                        >
                            <AlertCircle size={20} />
                            거절
                            {dwellingButton === 'reject' && (
                                <span style={{
                                    position: 'absolute',
                                    bottom: 0,
                                    left: 0,
                                    height: '4px',
                                    width: `${dwellProgress}%`,
                                    backgroundColor: 'var(--danger)',
                                    transition: 'width 50ms linear'
                                }}></span>
                            )}
                        </button>
                    </div>
                </div>

                {/* 추가 추천 목록 - 제거 (단일 추천만 표시) */}
            </motion.div>
        </motion.div>
    )
}

export default RecommendationModal
