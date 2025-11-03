import { useState, useEffect } from 'react'
import { Settings, Filter, Sliders, Info, CheckCircle, AlertCircle, RotateCw } from 'lucide-react'
import './SettingsPage.css'

/**
 * 시선 추적 설정 페이지
 * - 필터 설정 (Kalman 필터)
 * - Kalman 매개변수 튜닝
 * - 추적기 정보 표시 (모델, 필터, 보정 상태)
 * - 재보정 시작
 */
function SettingsPage({ onRecalibrate }) {
    // 필터 설정 정보
    const [filterInfo, setFilterInfo] = useState(null)
    // 추적기 상태 정보
    const [trackerInfo, setTrackerInfo] = useState(null)
    // Kalman 노이즈 (측정 노이즈 공분산)
    const [kalmanNoise, setKalmanNoise] = useState(0.2)
    // 튜닝 진행 중 여부
    const [loading, setLoading] = useState(false)
    // 상태 메시지
    const [message, setMessage] = useState('')
    // 메시지 타입 (info, success, error)
    const [messageType, setMessageType] = useState('info')
    // 재보정 진행 중 여부
    const [recalibratingLoading, setRecalibratingLoading] = useState(false)

    /**
     * 초기화: 설정 로드, 주기적으로 추적기 정보 갱신
     */
    useEffect(() => {
        loadSettings()
        // 2초마다 추적기 정보 갱신
        const interval = setInterval(loadTrackerInfo, 2000)
        return () => clearInterval(interval)
    }, [])

    /**
     * 필터 설정 로드
     */
    const loadSettings = async () => {
        try {
            const response = await fetch('/api/settings/filter')
            const data = await response.json()
            setFilterInfo(data)

            // Kalman 측정 노이즈 값 추출
            if (data.kalman_params?.measurement_noise_cov) {
                const noise = data.kalman_params.measurement_noise_cov[0][0]
                setKalmanNoise(noise)
            }
        } catch (error) {
            console.error('설정 로드 실패:', error)
        }
    }

    /**
     * 추적기 상태 정보 로드
     */
    const loadTrackerInfo = async () => {
        try {
            const response = await fetch('/api/settings/tracker-info')
            const data = await response.json()
            setTrackerInfo(data)
        } catch (error) {
            console.error('추적기 정보 로드 실패:', error)
        }
    }

    /**
     * Kalman 필터 자동 튜닝
     */
    const tuneKalman = async () => {
        setLoading(true)
        setMessage('Kalman 필터를 튜닝하는 중...')
        setMessageType('info')

        try {
            const response = await fetch('/api/settings/filter/tune-kalman', {
                method: 'POST',
            })
            const data = await response.json()

            if (data.success) {
                setMessage('Kalman 필터 튜닝 완료!')
                setMessageType('success')
                await loadSettings()
            } else {
                setMessage(data.message || '튜닝 실패')
                setMessageType('error')
            }
        } catch (error) {
            setMessage('튜닝 중 오류 발생')
            setMessageType('error')
        } finally {
            setLoading(false)
            setTimeout(() => setMessage(''), 3000)
        }
    }

    /**
     * Kalman 노이즈 값 설정
     * @param {number} value - 노이즈 분산 값
     */
    const setKalmanNoiseValue = async (value) => {
        setKalmanNoise(value)

        try {
            const response = await fetch(`/api/settings/filter/set-kalman-noise?variance=${value}`, {
                method: 'POST',
            })
            const data = await response.json()

            if (data.success) {
                setMessage(`Kalman 노이즈: ${value.toFixed(2)}`)
                setMessageType('success')
                await loadSettings()
            }
        } catch (error) {
            setMessage('설정 변경 실패')
            setMessageType('error')
        } finally {
            setTimeout(() => setMessage(''), 2000)
        }
    }

    /**
     * 노이즈 값에 따른 레이블 반환
     */
    const getNoiseLabel = (value) => {
        if (value < 0.5) return '민감 (떨림 많음)'
        if (value < 2.0) return '균형'
        if (value < 5.0) return '부드러움'
        return '매우 부드러움 (지연 있음)'
    }

    /**
     * 재보정 요청
     */
    const handleRecalibration = async () => {
        setRecalibratingLoading(true)
        setMessage('재보정 페이지로 이동하는 중...')
        setMessageType('info')

        try {
            // App.jsx의 handleRecalibrate 호출
            if (onRecalibrate) {
                onRecalibrate()
            }

            // 1초 후 보정 페이지로 자동 이동
            setTimeout(() => {
                window.location.href = '/calibration'
            }, 500)
        } catch (error) {
            console.error('재보정 요청 실패:', error)
            setMessage('재보정 요청 실패')
            setMessageType('error')
            setRecalibratingLoading(false)
            setTimeout(() => setMessage(''), 3000)
        }
    }

    return (
        <div className="settings-page">
            <div className="settings-container">
                {/* 페이지 헤더 */}
                <header className="settings-header">
                    <div className="header-icon">
                        <Settings size={32} />
                    </div>
                    <h1>시선 추적 설정</h1>
                    <p>필터 및 추적 설정을 조정합니다</p>
                </header>

                {/* 추적기 정보 섹션 */}
                {trackerInfo && (
                    <section className="settings-section">
                        <div className="section-header">
                            <Info size={24} />
                            <h2>추적기 정보</h2>
                        </div>
                        <div className="info-grid">
                            <div className="info-item">
                                <span className="info-label">모델</span>
                                <span className="info-value">{trackerInfo.model_name}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">필터</span>
                                <span className="info-value">{trackerInfo.filter_method}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">화면 크기</span>
                                <span className="info-value">{trackerInfo.screen_size[0]} × {trackerInfo.screen_size[1]}</span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">보정 상태</span>
                                <span className={`info-value ${trackerInfo.calibrated ? 'success' : 'error'}`}>
                                    {trackerInfo.calibrated ? '완료' : '미완료'}
                                </span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">실행 상태</span>
                                <span className={`info-value ${trackerInfo.is_running ? 'success' : 'error'}`}>
                                    {trackerInfo.is_running ? '실행 중' : '중지됨'}
                                </span>
                            </div>
                            <div className="info-item">
                                <span className="info-label">현재 시선</span>
                                <span className="info-value">
                                    {trackerInfo.current_gaze ?
                                        `(${trackerInfo.current_gaze[0]}, ${trackerInfo.current_gaze[1]})` :
                                        'N/A'}
                                </span>
                            </div>
                        </div>
                    </section>
                )}

                {/* 필터 설정 섹션 */}
                {filterInfo && (
                    <section className="settings-section">
                        <div className="section-header">
                            <Filter size={24} />
                            <h2>필터 설정</h2>
                        </div>

                        {filterInfo.filter_method === 'kalman' ? (
                            <div className="filter-controls">
                                <div className="control-group">
                                    <label>Kalman 필터 부드러움</label>
                                    <div className="slider-container">
                                        <input
                                            type="range"
                                            min="0.1"
                                            max="10"
                                            step="0.1"
                                            value={kalmanNoise}
                                            onChange={(e) => setKalmanNoiseValue(parseFloat(e.target.value))}
                                            disabled={loading}
                                        />
                                        <div className="slider-value">
                                            <span className="value">{kalmanNoise.toFixed(1)}</span>
                                            <span className="label">{getNoiseLabel(kalmanNoise)}</span>
                                        </div>
                                    </div>
                                    <p className="control-hint">
                                        낮은 값: 빠른 반응, 떨림 많음 | 높은 값: 부드러운 움직임, 약간의 지연
                                    </p>
                                </div>

                                <button
                                    className="tune-button"
                                    onClick={tuneKalman}
                                    disabled={loading || !trackerInfo?.calibrated}
                                >
                                    <Sliders size={20} />
                                    {loading ? '튜닝 중...' : '자동 튜닝'}
                                </button>

                                {!trackerInfo?.calibrated && (
                                    <p className="warning-text">
                                        ⚠️ 자동 튜닝을 사용하려면 먼저 보정을 완료하세요
                                    </p>
                                )}

                                {filterInfo.kalman_params && (
                                    <details className="advanced-settings">
                                        <summary>고급 설정</summary>
                                        <div className="params-display">
                                            <h4>측정 노이즈 공분산 (Measurement Noise Covariance)</h4>
                                            <pre>{JSON.stringify(filterInfo.kalman_params.measurement_noise_cov, null, 2)}</pre>

                                            <h4>프로세스 노이즈 공분산 (Process Noise Covariance)</h4>
                                            <pre>{JSON.stringify(filterInfo.kalman_params.process_noise_cov, null, 2)}</pre>
                                        </div>
                                    </details>
                                )}
                            </div>
                        ) : (
                            <div className="filter-info">
                                <p>현재 필터: <strong>{filterInfo.filter_method}</strong></p>
                                {filterInfo.filter_method === 'none' && (
                                    <p className="info-text">
                                        ℹ️ 필터를 사용하지 않습니다. 더 부드러운 커서를 위해 Kalman 필터를 권장합니다.
                                    </p>
                                )}
                            </div>
                        )}
                    </section>
                )}

                {/* 상태 메시지 */}
                {message && (
                    <div className={`status-message ${messageType}`}>
                        {messageType === 'success' && <CheckCircle size={20} />}
                        {messageType === 'error' && <AlertCircle size={20} />}
                        {messageType === 'info' && <Info size={20} />}
                        <span>{message}</span>
                    </div>
                )}

                {/* 정보 섹션 */}
                <section className="settings-section info-section">
                    <h3>Kalman 필터란?</h3>
                    <p>
                        Kalman 필터는 시선 추적 데이터의 노이즈를 제거하고 부드러운 커서 움직임을 제공합니다.
                    </p>
                    <ul>
                        <li><strong>자동 튜닝:</strong> 사용자의 시선 패턴에 맞춰 자동으로 최적값 계산</li>
                        <li><strong>수동 조정:</strong> 슬라이더로 반응속도와 부드러움 조절</li>
                        <li><strong>권장 설정:</strong> 0.2 (기본값) - 균형잡힌 성능</li>
                    </ul>
                </section>

                {/* 재보정 섹션 */}
                <section className="settings-section calibration-section">
                    <div className="section-header">
                        <RotateCw size={24} />
                        <h2>시선 보정</h2>
                    </div>
                    <p className="calibration-description">
                        시선 추적 정확도가 떨어졌거나 다시 보정하고 싶으신 경우, 아래 버튼을 클릭하세요.
                    </p>
                    <button
                        className="recalibration-button"
                        onClick={handleRecalibration}
                        disabled={recalibratingLoading}
                    >
                        {recalibratingLoading ? (
                            <>
                                <span className="loading-spinner"></span>
                                이동 중...
                            </>
                        ) : (
                            <>
                                <RotateCw size={20} />
                                재보정 시작
                            </>
                        )}
                    </button>
                </section>
            </div>
        </div>
    )
}

export default SettingsPage
