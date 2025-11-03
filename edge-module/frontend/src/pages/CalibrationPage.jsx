import { useState, useEffect, useRef } from 'react'
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Eye, CheckCircle, AlertCircle } from 'lucide-react'
import './CalibrationPage.css'

/**
 * 시선 보정 페이지
 * - 9포인트 웹 기반 보정
 * - 실시간 얼굴 인식 및 특징점 수집
 * - 자동 모델 학습
 * - 웹 UI 기반 Kalman 필터 파인튜닝
 * 
 * @param {Function} onComplete - 보정 완료 콜백
 */
function CalibrationPage({ onComplete }) {
    // 라우터 네비게이션
    const navigate = useNavigate()
    // 보정 상태 (init, ready, calibrating, training, tuning, completed, error)
    const [status, setStatus] = useState('init')
    // 백엔드 세션 ID
    const [sessionId, setSessionId] = useState(null)
    // 보정 포인트 배열
    const [points, setPoints] = useState([])
    // 현재 포인트 인덱스
    const [currentPointIndex, setCurrentPointIndex] = useState(0)
    // 수집된 샘플 개수
    const [samplesCollected, setSamplesCollected] = useState(0)
    // 현재 단계 (waiting, pulsing, capturing)
    const [phase, setPhase] = useState('waiting')
    // 얼굴 인식 여부
    const [hasFace, setHasFace] = useState(false)
    // 사용자 메시지
    const [message, setMessage] = useState('보정을 시작하려면 준비 버튼을 누르세요')

    // 👁️ 얼굴 인식 실패 감지 및 경고
    const [noFaceWarning, setNoFaceWarning] = useState(false)
    const noFaceTimerRef = useRef(null)
    const NO_FACE_TIMEOUT = 10000 // 10초 동안 얼굴 인식 안되면 경고

    // WebSocket 참조
    const wsRef = useRef(null)
    const canvasRef = useRef(null)
    const captureTimerRef = useRef(null)
    // Ref를 사용해 stale closure 방지
    const phaseRef = useRef('waiting')
    const sessionIdRef = useRef(null)
    const currentPointIndexRef = useRef(0)
    const pointsRef = useRef([])
    // 로컬 샘플 버퍼
    const samplesBufferRef = useRef({})

    const samplesPerPoint = 25
    // 각 포인트당 캡처 시간 (초)
    const captureTimeSeconds = 2.5

    /**
     * 클린업: WebSocket 종료, 타이머 정리
     */
    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close()
            }
            if (captureTimerRef.current) {
                clearTimeout(captureTimerRef.current)
            }
            if (noFaceTimerRef.current) {
                clearTimeout(noFaceTimerRef.current)
            }
        }
    }, [])

    /**
     * 자동 보정 시작 (페이지 로드 후 3초 뒤)
     */
    useEffect(() => {
        if (status === 'init') {
            setMessage('보정을 자동으로 시작합니다...')
            const timer = setTimeout(() => {
                console.log('[CalibrationPage] 자동 보정 시작')
                startCalibration()
            }, 3000)

            return () => clearTimeout(timer)
        }
    }, [status])

    /**
     * 👁️ 얼굴 인식 실패 감지 타이머
     * - 보정 중에 10초 이상 얼굴이 인식되지 않으면 경고 팝업
     */
    useEffect(() => {
        // 보정 중일 때만 감지
        if (status !== 'calibrating' && status !== 'tuning') {
            return
        }

        if (hasFace) {
            // 얼굴 인식되면 타이머 리셋
            if (noFaceTimerRef.current) {
                clearTimeout(noFaceTimerRef.current)
                noFaceTimerRef.current = null
            }
            setNoFaceWarning(false)
        } else {
            // 얼굴 인식 안되면 타이머 시작
            if (!noFaceTimerRef.current) {
                noFaceTimerRef.current = setTimeout(() => {
                    console.log('[CalibrationPage] ⚠️ 얼굴 인식 실패 - 경고 표시')
                    setNoFaceWarning(true)

                    // 3초 후 자동으로 보정 재시작
                    setTimeout(() => {
                        handleWarningConfirm()
                    }, 3000)
                }, NO_FACE_TIMEOUT)
            }
        }

        return () => {
            if (noFaceTimerRef.current) {
                clearTimeout(noFaceTimerRef.current)
                noFaceTimerRef.current = null
            }
        }
    }, [hasFace, status])    /**
     * 경고 팝업 확인 - 보정 재시작
     */
    const handleWarningConfirm = () => {
        console.log('[CalibrationPage] 얼굴 인식 실패 - 보정 재시작')

        // 경고 상태 초기화
        setNoFaceWarning(false)

        // WebSocket 종료
        if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
        }

        // 타이머 정리
        if (captureTimerRef.current) {
            clearTimeout(captureTimerRef.current)
            captureTimerRef.current = null
        }

        // 보정 다시 시작
        setTimeout(() => {
            startCalibration()
        }, 1000)
    }

    /**
     * 보정 세션 시작
     * - 백엔드에서 9포인트 보정 시작
     * - WebSocket 연결
     * - 첫 번째 포인트에서 펄스 애니메이션 시작
     */
    const startCalibration = async () => {
        try {
            setStatus('ready')
            setMessage('보정 세션을 시작하는 중...')

            // 백엔드에서 보정 세션 시작
            const response = await fetch('/api/calibration/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    method: 'nine_point',
                    screen_width: window.screen.width,
                    screen_height: window.screen.height,
                }),
            })

            if (!response.ok) {
                const errorText = await response.text()
                throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`)
            }

            const data = await response.json()
            setSessionId(data.session_id)
            sessionIdRef.current = data.session_id
            setPoints(data.points)
            pointsRef.current = data.points

            console.log('[CalibrationPage] 보정 시작 - 포인트:', data.points)

            // 특징 스트림 WebSocket 연결
            connectWebSocket()

            setStatus('calibrating')
            setPhase('pulsing')
            phaseRef.current = 'pulsing'
            setCurrentPointIndex(0)
            currentPointIndexRef.current = 0
            setMessage('첫 번째 점을 응시하세요')

            // 펄스 애니메이션 시작
            startPulseAnimation()

        } catch (error) {
            console.error('보정 시작 실패:', error)
            setStatus('error')
            setMessage('보정 시작 실패: ' + error.message)
        }
    }

    /**
     * WebSocket을 통한 특징 스트림 연결
     * - 실시간 얼굴 인식 및 특징점 수신
     * - 캡처 단계에서 샘플 수집
     */
    const connectWebSocket = () => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/features`)

        ws.onopen = () => {
            console.log('[CalibrationPage] WebSocket 연결됨')
        }

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)

            // 로그 레벨 조정 - capturing 단계에서만 상세 로그
            if (phaseRef.current === 'capturing') {
                console.log('[CalibrationPage] 📡 WebSocket 메시지:', {
                    type: data.type,
                    has_face: data.has_face,
                    blink: data.blink,
                    has_features: !!data.features,
                    phase: phaseRef.current,
                    current_point: currentPointIndexRef.current,
                    samples_count: samplesBufferRef.current[currentPointIndexRef.current]?.length || 0
                })
            }

            if (data.type === 'features') {
                // 얼굴 인식 상태 업데이트 (깜빡임 제외)
                const faceDetected = data.has_face && !data.blink
                setHasFace(faceDetected)

                // 캡처 단계에서만 샘플 수집
                if (phaseRef.current === 'capturing' && faceDetected && data.features) {
                    collectSample(data.features)
                }
            }
        }

        ws.onerror = (error) => {
            console.error('[CalibrationPage] WebSocket 오류:', error)
        }

        ws.onclose = () => {
            console.log('[CalibrationPage] WebSocket 연결 끊김')
        }

        wsRef.current = ws
    }

    /**
     * 펄스 애니메이션 시작
     * - 1초 펄스 후 캡처 단계 시작
     * - 캡처 시간 후 자동으로 다음 포인트로 이동
     */
    const startPulseAnimation = () => {
        const idx = currentPointIndexRef.current
        console.log(`[CalibrationPage] 🎯 펄스 시작: 포인트 ${idx}`)

        setPhase('pulsing')
        phaseRef.current = 'pulsing'
        setSamplesCollected(0)

        // 1초 펄스, 그 후 캡처 시작
        setTimeout(() => {
            console.log(`[CalibrationPage] 📸 캡처 시작: 포인트 ${idx}`)
            setPhase('capturing')
            phaseRef.current = 'capturing'

            // 캡처 시간 후 자동으로 다음 포인트로 이동
            captureTimerRef.current = setTimeout(() => {
                console.log(`[CalibrationPage] ⏰ 캡처 시간 완료: 포인트 ${idx}`)
                moveToNextPoint()
            }, captureTimeSeconds * 1000)
        }, 1000)
    }

    /**
     * 특징점으로부터 샘플 수집
     * @param {Array} features - 얼굴 특징점
     */
    const collectSample = (features) => {
        const idx = currentPointIndexRef.current
        const pts = pointsRef.current

        if (phaseRef.current !== 'capturing') {
            return
        }

        if (!pts[idx]) {
            console.error('[CalibrationPage] ❌ 포인트 없음:', idx, '/', pts.length)
            return
        }

        const currentPoint = pts[idx]

        // 로컬 버퍼에 저장
        if (!samplesBufferRef.current[idx]) {
            samplesBufferRef.current[idx] = []
        }

        // 포인트당 샘플 수 제한
        const currentCount = samplesBufferRef.current[idx].length
        if (currentCount >= samplesPerPoint) {
            return
        }

        samplesBufferRef.current[idx].push({
            features: features,
            point_x: currentPoint.x,
            point_y: currentPoint.y,
        })

        const count = samplesBufferRef.current[idx].length

        // 5개마다 로그 (너무 많은 로그 방지)
        if (count % 5 === 0 || count === 1 || count === samplesPerPoint) {
            console.log(`[CalibrationPage] ✅ 샘플 수집: ${count}/${samplesPerPoint} (포인트 ${idx})`)
        }

        // UI 카운터 업데이트
        setSamplesCollected(count)
    }

    /**
     * 다음 포인트로 이동
     * - 현재 포인트의 샘플들을 백엔드에 전송
     * - 튜닝 모드 또는 정상 모드 처리
     */
    const moveToNextPoint = async () => {
        // 즉시 샘플 수집 중지
        setPhase('moving')
        phaseRef.current = 'moving'

        // 기존 타이머 정리
        if (captureTimerRef.current) {
            clearTimeout(captureTimerRef.current)
            captureTimerRef.current = null
        }

        const sid = sessionIdRef.current
        const idx = currentPointIndexRef.current

        // 튜닝 모드 확인 (세션 ID 없음)
        if (!sid || status === 'tuning') {
            // 튜닝 모드 - 로컬에서만 포인트 이동
            const samples = samplesBufferRef.current[idx] || []
            console.log(`[Tuning] 포인트 ${idx}에서 ${samples.length}개 샘플 수집`)

            const newIdx = idx + 1
            if (newIdx < pointsRef.current.length) {
                // 다음 튜닝 포인트로 이동
                setCurrentPointIndex(newIdx)
                currentPointIndexRef.current = newIdx
                setSamplesCollected(0)
                startPulseAnimation()
                setMessage(`파인튜닝: 포인트 ${newIdx + 1}/3 - 응시하세요`)
            } else {
                // 튜닝 완료 - 분산 계산 및 백엔드에 전송
                console.log('[CalibrationPage] Kalman 튜닝 데이터 수집 완료')
                await computeAndApplyKalmanVariance()
                finishCalibration()
            }
            return
        }

        // 정상 보정 모드
        if (!sid) {
            console.error('세션 ID 없음')
            return
        }

        // 이 포인트의 버퍼링된 샘플들 전송
        const samples = samplesBufferRef.current[idx] || []
        console.log(`[CalibrationPage] 포인트 ${idx}에서 ${samples.length}개 샘플 수집됨`)

        if (samples.length < 5) {
            console.warn(`[CalibrationPage] ⚠️ 포인트 ${idx}에서 샘플 부족 (${samples.length}개) - 다시 수집`)
            // 샘플 버퍼 초기화하고 다시 수집
            samplesBufferRef.current[idx] = []
            setSamplesCollected(0)
            // 펄스 애니메이션부터 다시 시작
            startPulseAnimation()
            return
        }

        // 모든 샘플 한 번에 전송
        try {
            for (const sample of samples) {
                const response = await fetch('/api/calibration/collect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: sid,
                        features: Array.from(sample.features),  // numpy 배열을 JS 배열로 변환
                        point_x: sample.point_x,
                        point_y: sample.point_y,
                    }),
                })

                if (!response.ok) {
                    const error = await response.json()
                    console.warn(`[CalibrationPage] 샘플 전송 실패: ${response.status} - ${error.detail}`)
                }
            }
        } catch (error) {
            console.error('샘플 전송 실패:', error)
        }

        try {
            const response = await fetch(`/api/calibration/next-point`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sid
                }),
            })

            const data = await response.json()
            console.log(`[CalibrationPage] next-point 응답:`, data)

            if (data.has_next) {
                const newIdx = idx + 1
                console.log(`[CalibrationPage] ✅ 다음 포인트로 이동: ${idx} → ${newIdx}`)
                setCurrentPointIndex(newIdx)
                currentPointIndexRef.current = newIdx
                setSamplesCollected(0)
                // 샘플 버퍼 초기화
                if (samplesBufferRef.current[newIdx]) {
                    samplesBufferRef.current[newIdx] = []
                }
                startPulseAnimation()
                setMessage(`포인트 ${newIdx + 1} / ${pointsRef.current.length}`)
            } else {
                console.log('[CalibrationPage] ✅ 모든 포인트 수집 완료')
                // 모든 포인트 수집 완료
                if (status === 'tuning') {
                    // 튜닝 완료
                    console.log('[CalibrationPage] Kalman 튜닝 완료')
                    finishCalibration()
                } else {
                    // 정상 보정 완료, 학습으로 이동
                    completeCalibration()
                }
            }

        } catch (error) {
            console.error('[CalibrationPage] ❌ 다음 포인트 이동 실패:', error)
            // 오류 발생 시 다시 시도
            setMessage('포인트 이동 실패 - 다시 시도 중...')
            setTimeout(() => {
                startPulseAnimation()
            }, 2000)
        }
    }

    /**
     * 보정 완료: 모델 학습 및 Kalman 튜닝 시작
     */
    const completeCalibration = async () => {
        const sid = sessionIdRef.current

        if (!sid) {
            console.error('완료 시 세션 ID 없음')
            return
        }

        try {
            setStatus('training')
            setMessage('모델 학습 중...')

            // localStorage에서 사용자명 가져오기
            const username = localStorage.getItem('gazehome_username') || 'default'

            const response = await fetch('/api/calibration/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sid,
                    username: username,
                }),
            })

            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(`HTTP ${response.status}: ${errorData.detail || '알 수 없는 오류'}`)
            }

            const result = await response.json()

            if (result.success) {
                // 라즈베리파이 최적화: Kalman 튜닝 건너뜀 (NoOp 필터 사용)
                // Kalman 필터 튜닝은 CPU 부하가 높으므로 비활성화
                console.log('[CalibrationPage] Kalman 튜닝 건너뜀 (NoOp 필터 사용)')
                finishCalibration()

            } else {
                setStatus('error')
                setMessage(`보정 실패: ${result.message || '알 수 없는 오류'}`)
            }

        } catch (error) {
            console.error('보정 완료 실패:', error)
            setStatus('error')
            setMessage(`보정 실패: ${error.message || '알 수 없는 오류'}`)
        }
    }

    /**
     * Kalman 필터 파인튜닝 시작
     * - 3개의 튜닝 포인트 생성 (상단 중앙, 좌측 하단, 우측 하단)
     * - 각 포인트에서 특징점 샘플 수집
     * - 분산 계산 및 Kalman 필터 업데이트
     */
    const startKalmanTuning = async () => {
        try {
            console.log('[CalibrationPage] 웹 UI에서 Kalman 튜닝 시작...')

            // 3개 튜닝 포인트 생성
            const screenWidth = window.screen.width
            const screenHeight = window.screen.height

            const tuningPoints = [
                { x: screenWidth / 2, y: screenHeight / 4, index: 0, total: 3 },        // 상단 중앙
                { x: screenWidth / 4, y: 3 * screenHeight / 4, index: 1, total: 3 },    // 좌측 하단
                { x: 3 * screenWidth / 4, y: 3 * screenHeight / 4, index: 2, total: 3 } // 우측 하단
            ]

            console.log('[CalibrationPage] 튜닝 포인트:', tuningPoints)

            setPoints(tuningPoints)
            pointsRef.current = tuningPoints
            setCurrentPointIndex(0)
            currentPointIndexRef.current = 0
            setSamplesCollected(0)
            samplesBufferRef.current = {}

            // 첫 번째 튜닝 포인트에서 시작
            startPulseAnimation()
            setMessage(`파인튜닝: 포인트 1/3 - 응시하세요`)

        } catch (error) {
            console.error('[CalibrationPage] Kalman 튜닝 오류:', error)
            // 튜닝 건너뛰고 완료로 이동
            finishCalibration()
        }
    }

    /**
     * Kalman 분산 계산 및 적용
     * - 튜닝 샘플들로부터 X, Y 분산 계산
     * - 백엔드에 분산 값 전송하여 Kalman 필터 업데이트
     */
    const computeAndApplyKalmanVariance = async () => {
        try {
            // 튜닝 샘플들로부터 모든 시선 위치 수집
            const allGazePositions = []

            for (let i = 0; i < pointsRef.current.length; i++) {
                const samples = samplesBufferRef.current[i] || []
                samples.forEach(sample => {
                    if (sample.point_x && sample.point_y) {
                        allGazePositions.push([sample.point_x, sample.point_y])
                    }
                })
            }

            console.log(`[Kalman 튜닝] ${allGazePositions.length}개 시선 위치 수집`)

            if (allGazePositions.length < 2) {
                console.warn('[Kalman 튜닝] 분산 계산을 위한 데이터 부족')
                return
            }

            // 분산 계산
            const xValues = allGazePositions.map(pos => pos[0])
            const yValues = allGazePositions.map(pos => pos[1])

            const meanX = xValues.reduce((a, b) => a + b, 0) / xValues.length
            const meanY = yValues.reduce((a, b) => a + b, 0) / yValues.length

            const varianceX = xValues.reduce((sum, val) => sum + Math.pow(val - meanX, 2), 0) / xValues.length
            const varianceY = yValues.reduce((sum, val) => sum + Math.pow(val - meanY, 2), 0) / yValues.length

            console.log(`[Kalman 튜닝] 분산 - X: ${varianceX.toFixed(2)}, Y: ${varianceY.toFixed(2)}`)

            // 백엔드에 분산 값 전송
            await fetch('/api/calibration/update-kalman-variance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    variance_x: Math.max(varianceX, 1e-4),
                    variance_y: Math.max(varianceY, 1e-4)
                }),
            })

            console.log('[Kalman 튜닝] Kalman 필터에 분산 적용됨')

        } catch (error) {
            console.error('[Kalman 튜닝] 분산 계산 오류:', error)
        }
    }

    /**
     * 보정 완료
     * - WebSocket 종료
     * - 완료 콜백 실행
     * - 홈으로 이동
     */
    const finishCalibration = () => {
        setStatus('completed')
        setMessage('보정 완료!')

        // WebSocket 종료
        if (wsRef.current) {
            wsRef.current.close()
        }

        // 부모 컴포넌트 콜백 실행
        if (onComplete) {
            onComplete()
        }

        // 즉시 홈으로 이동 (지연 없음)
        console.log('[CalibrationPage] 홈페이지로 이동 중...')
        navigate('/home', { replace: true })
    }

    const currentPoint = points[currentPointIndex]

    return (
        <div className="calibration-page">
            <AnimatePresence mode="wait">
                {/* 초기 상태: 보정 안내 및 자동 시작 */}
                {status === 'init' && (
                    <motion.div
                        className="calibration-intro"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <div className="intro-content">
                            <div className="intro-icon">
                                <Eye size={64} />
                            </div>
                            <h1>시선 보정</h1>
                            <p>정확한 시선 추적을 위해 보정이 필요합니다.</p>
                            <ul className="calibration-steps">
                                <li>화면에 표시되는 9개의 점을 응시합니다</li>
                                <li>각 점마다 2-3초간 응시해주세요</li>
                                <li>얼굴을 움직이지 마세요</li>
                                <li>깜빡임은 자연스럽게 해도 됩니다</li>
                            </ul>
                            <div className="auto-start-message">
                                <span className="loading-spinner"></span>
                                <p>{message}</p>
                            </div>
                        </div>
                    </motion.div>
                )}

                {/* 보정 중: 포인트 및 진행 상황 표시 */}
                {(status === 'calibrating' || status === 'ready') && currentPoint && (
                    <motion.div
                        className="calibration-canvas"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        {/* 보정 포인트 */}
                        <CalibrationPoint
                            x={currentPoint.x}
                            y={currentPoint.y}
                            phase={phase}
                            progress={samplesCollected / samplesPerPoint}
                            hasFace={hasFace}
                        />

                        {/* 상태 바 */}
                        <div className="calibration-status-bar">
                            <div className="status-info">
                                <div className={`face-indicator ${hasFace ? 'active' : ''}`}>
                                    {hasFace ? '얼굴 인식됨' : '얼굴을 인식하는 중...'}
                                </div>
                                <div className="point-counter">
                                    포인트 {currentPointIndex + 1} / {points.length}
                                </div>
                            </div>
                            <div className="progress-bar">
                                <motion.div
                                    className="progress-fill"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${(samplesCollected / samplesPerPoint) * 100}%` }}
                                />
                            </div>
                            <div className="message">{message}</div>
                        </div>

                        {/* 👁️ 얼굴 인식 실패 경고 팝업 */}
                        {noFaceWarning && (
                            <motion.div
                                className="warning-overlay"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                            >
                                <motion.div
                                    className="warning-modal"
                                    initial={{ scale: 0.9, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    exit={{ scale: 0.9, opacity: 0 }}
                                >
                                    <div className="warning-icon">
                                        <AlertCircle size={48} color="#EF4444" />
                                    </div>
                                    <h2>시선 인식 실패</h2>
                                    <p>카메라에서 얼굴을 인식할 수 없습니다.</p>
                                    <ul className="warning-tips">
                                        <li>조명이 충분한 곳에서 시도해주세요</li>
                                        <li>카메라를 정면으로 바라봐주세요</li>
                                        <li>얼굴이 화면 중앙에 위치하도록 조정해주세요</li>
                                        <li>안경이나 모자를 착용하셨다면 벗어주세요</li>
                                    </ul>
                                    <p className="auto-restart-message">
                                        3초 후 자동으로 보정을 다시 시작합니다...
                                    </p>
                                    <button className="warning-button" onClick={handleWarningConfirm}>
                                        지금 다시 시작
                                    </button>
                                </motion.div>
                            </motion.div>
                        )}
                    </motion.div>
                )}

                {/* 학습 중 */}
                {status === 'training' && (
                    <motion.div
                        className="calibration-status"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <div className="status-icon">
                            <div className="loading-spinner"></div>
                        </div>
                        <h2>모델 학습 중...</h2>
                        <p>잠시만 기다려주세요</p>
                    </motion.div>
                )}

                {/* 보정 완료 */}
                {status === 'completed' && (
                    <motion.div
                        className="calibration-status success"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <motion.div
                            className="status-icon"
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                        >
                            <CheckCircle size={64} />
                        </motion.div>
                        <h2>보정 완료!</h2>
                        <p>이제 시선 추적을 사용할 수 있습니다</p>
                    </motion.div>
                )}

                {/* 보정 실패 */}
                {status === 'error' && (
                    <motion.div
                        className="calibration-status error"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <div className="status-icon">
                            <AlertCircle size={64} />
                        </div>
                        <h2>보정 실패</h2>
                        <p>{message}</p>
                        <button className="retry-button" onClick={startCalibration}>
                            다시 시도
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

/**
 * 보정 포인트 컴포넌트
 * - 펄싱 원형 애니메이션
 * - 캡처 단계에서 진행 상황 표시
 * - 얼굴 인식 상태 시각적 피드백
 * 
 * 📍 포인터 위치 조정 가이드:
 * - x: 좌우 위치 (0 = 좌측, window.innerWidth = 우측)
 * - y: 상하 위치 (0 = 상단, window.innerHeight = 하단)
 * - 9포인트: 좌상단, 중상단, 우상단, 좌중앙, 중앙, 우중앙, 좌하단, 중하단, 우하단
 * - 백엔드에서 반환된 points[i].x, points[i].y 값을 수정하거나
 * - 아래 오프셋을 조정하여 포인터 위치 미세 조정 가능
 * 
 * 조정 방법:
 * 1. 백엔드 변경: backend/api/calibration.py의 nine_point_calibration 함수 수정
 * 2. 프론트엔드 변경: 아래 offset 추가
 */
function CalibrationPoint({ x, y, phase, progress, hasFace }) {
    // ⚙️ 포인터 위치 미세 조정 (픽셀 단위)
    const OFFSET_X = 0  // 좌우 조정: 음수 = 좌측, 양수 = 우측
    const OFFSET_Y = 0  // 상하 조정: 음수 = 상단, 양수 = 하단

    const adjustedX = x + OFFSET_X
    const adjustedY = y + OFFSET_Y

    // 기본 반경
    const baseRadius = 20
    // 펄싱 단계에서는 반경이 변함
    const pulseRadius = phase === 'pulsing' ? 15 + 15 * Math.abs(Math.sin(Date.now() / 200)) : baseRadius

    // 캡처 진행률 (시간 기반)
    const [captureProgress, setCaptureProgress] = React.useState(0)

    /**
     * 캡처 단계에서 진행률 애니메이션
     */
    React.useEffect(() => {
        if (phase === 'capturing') {
            const startTime = Date.now()
            const duration = 1000 // 1초

            const interval = setInterval(() => {
                const elapsed = Date.now() - startTime
                const prog = Math.min(elapsed / duration, 1.0)
                setCaptureProgress(prog)

                if (prog >= 1.0) {
                    clearInterval(interval)
                }
            }, 16) // ~60fps

            return () => clearInterval(interval)
        } else {
            setCaptureProgress(0)
        }
    }, [phase])

    return (
        <div
            className="calibration-point-container"
            style={{
                left: adjustedX,
                top: adjustedY,
                transform: 'translate(-50%, -50%)'  // 포인트 중심에 정렬
            }}
        >
            {/* 펄싱 원 */}
            <motion.div
                className={`calibration-circle ${hasFace ? 'has-face' : ''}`}
                animate={{
                    width: pulseRadius * 2,
                    height: pulseRadius * 2,
                }}
                transition={{ duration: 0.1 }}
            />

            {/* 진행 상황 링 */}
            {phase === 'capturing' && (
                <svg className="progress-ring" width="100" height="100">
                    <circle
                        cx="50"
                        cy="50"
                        r="45"
                        fill="none"
                        stroke="rgba(255, 255, 255, 0.3)"
                        strokeWidth="4"
                    />
                    <motion.circle
                        cx="50"
                        cy="50"
                        r="45"
                        fill="none"
                        stroke="white"
                        strokeWidth="4"
                        strokeLinecap="round"
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: captureProgress }}
                        style={{
                            transform: 'rotate(-90deg)',
                            transformOrigin: '50% 50%',
                        }}
                    />
                </svg>
            )}
        </div>
    )
}

export default CalibrationPage
