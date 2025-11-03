import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Eye, Sparkles, AlertCircle } from 'lucide-react'
import './OnboardingPage.css'

/**
 * 온보딩/스플래시 페이지
 * - 초기 사용자 입장점
 * - 자동 로그인 진행
 * - 보정 상태 확인 후 자동 이동
 */
function OnboardingPage({ onLogin }) {
    // 로그인 진행 중 여부
    const [isLoading, setIsLoading] = useState(true)
    const [loginMessage, setLoginMessage] = useState('시스템 초기화 중...')

    /**
     * 페이지 로드 시 자동 로그인 (최소 5초 대기)
     */
    useEffect(() => {
        const autoLogin = async () => {
            try {
                console.log('🚀 자동 로그인 시작...')
                const startTime = Date.now()

                setLoginMessage('사용자 인증 중...')
                await new Promise(resolve => setTimeout(resolve, 1000))

                setLoginMessage('시선 추적 시스템 준비 중...')
                await new Promise(resolve => setTimeout(resolve, 1500))

                setLoginMessage('기기 연결 확인 중...')
                await new Promise(resolve => setTimeout(resolve, 1500))

                // 페이지가 완전히 로드된 뒤 최소 10초는 온보딩을 유지
                const elapsed = Date.now() - startTime
                const remaining = Math.max(0, 10000 - elapsed)
                if (remaining > 0) {
                    setLoginMessage('시스템 준비 완료...')
                    await new Promise(resolve => setTimeout(resolve, remaining))
                }

                // 부모 로그인 핸들러 호출
                await onLogin()

                console.log('✅ 자동 로그인 완료')
            } catch (error) {
                console.error('❌ 자동 로그인 실패:', error)
                setLoginMessage('로그인 실패. 재시도 중...')
                // 3초 후 재시도
                setTimeout(autoLogin, 3000)
            }
        }

        autoLogin()
    }, [onLogin])

    return (
        <div className="onboarding-page">
            <div className="onboarding-background">
                {/* 배경 애니메이션 효과 */}
                <div className="gradient-orb orb-1"></div>
                <div className="gradient-orb orb-2"></div>
                <div className="gradient-orb orb-3"></div>
            </div>

            <div className="onboarding-content">
                <motion.div
                    className="onboarding-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    {/* 로고 */}
                    <motion.div
                        className="logo-container"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                    >
                        <div className="logo-icon">
                            <Eye size={48} strokeWidth={2} />
                        </div>
                    </motion.div>

                    {/* 제목 */}
                    <motion.h1
                        className="onboarding-title"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 }}
                    >
                        GazeHome
                    </motion.h1>

                    {/* 부제목 */}
                    <motion.p
                        className="onboarding-subtitle"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5 }}
                    >
                        <Sparkles size={16} className="inline-icon" />
                        시선으로 제어하는 스마트한 공간
                    </motion.p>

                    {/* 자동 로그인 진행 상태 */}
                    <motion.div
                        className="login-form"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.6 }}
                    >
                        <div className="auto-login-status">
                            <span className="loading-spinner"></span>
                            <p className="login-message">{loginMessage}</p>
                        </div>
                    </motion.div>

                    {/* 기능 목록 */}
                    <motion.div
                        className="features-list"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.8 }}
                    >
                        <div className="feature-item">
                            <span className="feature-icon">👁️</span>
                            <span>시선 추적 기반 제어</span>
                        </div>
                        <div className="feature-item">
                            <span className="feature-icon">🏠</span>
                            <span>스마트홈 기기 관리</span>
                        </div>
                        <div className="feature-item">
                            <span className="feature-icon">🤖</span>
                            <span>AI 추천 시스템</span>
                        </div>
                    </motion.div>
                </motion.div>

                {/* 푸터 */}
                <motion.div
                    className="onboarding-footer"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1 }}
                >
                    <p>Powered by AIRIS</p>
                </motion.div>
            </div>
        </div>
    )
}

export default OnboardingPage
