import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import OnboardingPage from './pages/OnboardingPage'
import HomePage from './pages/HomePage'
import CalibrationPage from './pages/CalibrationPage'
import SettingsPage from './pages/SettingsPage'

/**
 * 메인 애플리케이션 컴인터
 * 넌트
 * - 라우팅 관리
 * - 사용자 로그인 상태 관리
 * - 시선 보정 상태 관리
 * - localStorage를 통한 세션 영속성
 */
function App() {
    // 로그인 상태
    const [isLoggedIn, setIsLoggedIn] = useState(false)
    // 시선 보정 완료 여부
    const [isCalibrated, setIsCalibrated] = useState(false)

    /**
     * 앱 초기화: 자동 로그인 및 보정 상태 확인
     * - 첫 방문: 자동 로그인 → 보정 화면
     * - 보정 완료: 자동 홈 화면
     */
    useEffect(() => {
        // 개발자 도구: 디버그 정보
        console.log('%c💡 GazeHome 애플리케이션 시작', 'background: blue; color: white; padding: 5px 10px; font-weight: bold')

        const initializeApp = async () => {
            // localStorage에서 로그인 정보 확인
            const loggedIn = localStorage.getItem('gazehome_logged_in') === 'true'
            const username = localStorage.getItem('gazehome_username')

            // 이미 로그인된 경우
            if (loggedIn && username) {
                console.log('[App] 💾 localStorage에서 로그인 상태 복원:', username)
                setIsLoggedIn(true)
                await checkCalibrationStatus(username) // ✅ await 추가: 보정 상태 확인 완료 후 렌더링
            } else {
                // 첫 방문 사용자 - 자동 로그인
                console.log('[App] 🆕 첫 방문 사용자 - 자동 로그인 시작')
                await handleAutoLogin() // ✅ await 추가
            }
        }

        initializeApp()
    }, [])

    /**
     * 자동 로그인 처리 (첫 방문 사용자)
     */
    const handleAutoLogin = async () => {
        try {
            console.log('[App] 🚀 자동 로그인 중...')

            // 백엔드 로그인 API 호출
            const response = await fetch('/api/users/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })

            if (!response.ok) {
                throw new Error(`로그인 실패: ${response.status}`)
            }

            const data = await response.json()
            console.log('[App] ✅ 자동 로그인 성공:', data)

            // localStorage에 저장
            const username = data.username
            localStorage.setItem('gazehome_logged_in', 'true')
            localStorage.setItem('gazehome_username', username)

            // ✅ 상태 업데이트를 동시에 처리 (React batching)
            // 이를 통해 중간에 !isCalibrated만 true인 상태 방지
            setIsLoggedIn(true)
            setIsCalibrated(data.has_calibration)

            console.log(`[App] 보정 상태: ${data.has_calibration ? '✅ 보정됨' : '❌ 미보정'}`)

        } catch (error) {
            console.error('[App] ❌ 자동 로그인 실패:', error)
            // 실패해도 로그인 페이지로 이동
            setIsLoggedIn(false)
        }
    }

    /**
     * 사용자의 시선 보정 상태 확인
     * @param {string} username - 사용자명
     */
    const checkCalibrationStatus = async (username) => {
        try {
            console.log(`[App] 📊 사용자 보정 상태 확인: "${username}"`)
            const response = await fetch('/api/calibration/list')
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }
            const data = await response.json()

            // ✅ 보정 파일이 하나라도 존재하면 보정된 것으로 간주
            // 데모 사용자용 simple logic: 파일이 있으면 보정 완료
            const hasCalibration = data.calibrations && data.calibrations.length > 0

            setIsCalibrated(hasCalibration)
            console.log(`[App] ${hasCalibration ? '✅ 보정 완료' : '❌ 미보정'} (파일: ${data.calibrations?.length || 0}개)`)
        } catch (error) {
            console.error('[App] ⚠️ 보정 상태 확인 실패:', error)
            setIsCalibrated(false)
        }
    }    /**
     * 사용자 로그인 처리 (온보딩 페이지 버튼 클릭 시)
     */
    const handleLogin = async () => {
        await handleAutoLogin()
    }

    /**
     * 사용자 로그아웃 처리
     */
    const handleLogout = () => {
        localStorage.removeItem('gazehome_logged_in')
        localStorage.removeItem('gazehome_username')
        setIsLoggedIn(false)
        setIsCalibrated(false)
    }

    /**
     * 시선 보정 완료 처리
     * - 보정 파일이 저장되었으므로 상태 업데이트
     * - 다시 보정해야 할 경우 설정 페이지에서 처리
     */
    const handleCalibrationComplete = () => {
        console.log('[App] ✅ 보정 완료')
        setIsCalibrated(true)
    }

    /**
     * 보정 다시 시작 (설정 페이지에서 호출)
     */
    const handleRecalibrate = () => {
        console.log('[App] 🔄 보정 다시 시작')
        setIsCalibrated(false)
        // /calibration 페이지로 자동 이동됨
    }

    return (
        <BrowserRouter
            future={{
                v7_startTransition: true,
                v7_relativeSplatPath: true,
            }}
        >
            <Routes>
                {/* 루트 경로: 로그인 여부에 따라 라우팅 */}
                <Route
                    path="/"
                    element={
                        !isLoggedIn ? (
                            // 미로그인: 온보딩 페이지
                            <OnboardingPage onLogin={handleLogin} />
                        ) : !isCalibrated ? (
                            // 로그인했으나 미보정: 보정 페이지로 리다이렉트
                            <Navigate to="/calibration" replace />
                        ) : (
                            // 로그인하고 보정 완료: 홈 페이지로 리다이렉트
                            <Navigate to="/home" replace />
                        )
                    }
                />
                {/* 보정 페이지: 로그인한 사용자만 접근 가능 */}
                <Route
                    path="/calibration"
                    element={
                        isLoggedIn ? (
                            <CalibrationPage onComplete={handleCalibrationComplete} />
                        ) : (
                            <Navigate to="/" replace />
                        )
                    }
                />
                {/* 홈 페이지: 로그인 및 보정 완료한 사용자만 접근 가능 */}
                <Route
                    path="/home"
                    element={
                        isLoggedIn && isCalibrated ? (
                            <HomePage onLogout={handleLogout} />
                        ) : (
                            <Navigate to="/" replace />
                        )
                    }
                />
                {/* 설정 페이지: 로그인한 사용자만 접근 가능 */}
                <Route
                    path="/settings"
                    element={
                        isLoggedIn ? (
                            <SettingsPage onRecalibrate={handleRecalibrate} />
                        ) : (
                            <Navigate to="/" replace />
                        )
                    }
                />
            </Routes>
        </BrowserRouter>
    )
}

export default App
