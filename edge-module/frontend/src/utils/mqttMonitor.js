/**
 * MQTT 알람 모니터링 유틸리티
 * 
 * 개발자 도구 콘솔에서 실행:
 * 1. MQTT 메시지 모니터링 시작:
 *    window.mqttMonitor.start()
 * 
 * 2. MQTT 메시지 기록 확인:
 *    window.mqttMonitor.getLogs()
 * 
 * 3. MQTT 메시지 필터링 조회:
 *    window.mqttMonitor.filterLogs('recommendation')
 * 
 * 4. MQTT 메시지 실시간 콘솔 출력 토글:
 *    window.mqttMonitor.toggleVerbose()
 * 
 * 5. 모니터링 통계:
 *    window.mqttMonitor.getStats()
 */

class MQTTMonitor {
    constructor() {
        this.logs = []
        this.isMonitoring = false
        this.isVerbose = true
        this.maxLogs = 100
        this.startTime = null
    }

    /**
     * 모니터링 시작
     */
    start() {
        if (this.isMonitoring) {
            console.warn('⚠️ MQTT 모니터링이 이미 시작됨')
            return
        }

        this.isMonitoring = true
        this.startTime = Date.now()
        this.logs = []

        console.log('%c✅ MQTT 모니터링 시작됨', 'color: green; font-weight: bold; font-size: 14px')
        console.log('%c💡 사용 가능한 명령어:', 'color: blue; font-weight: bold')
        console.log('  • window.mqttMonitor.getLogs() - 모든 메시지 조회')
        console.log('  • window.mqttMonitor.filterLogs("type") - 필터링 조회')
        console.log('  • window.mqttMonitor.getStats() - 통계 조회')
        console.log('  • window.mqttMonitor.toggleVerbose() - 상세 출력 토글')
        console.log('  • window.mqttMonitor.stop() - 모니터링 중지')

        // WebSocket 메시지 인터셉트
        const originalWebSocket = WebSocket
        const self = this

        window.WebSocket = function (...args) {
            const ws = new originalWebSocket(...args)
            const originalSend = ws.send
            const originalOnmessage = ws.onmessage

            // Send 메시지 기록
            ws.send = function (data) {
                try {
                    const parsed = JSON.parse(data)
                    if (parsed.type === 'gaze_update') {
                        // gaze_update는 너무 자주 발생하므로 제외
                    } else {
                        self.logMessage('SEND', parsed, data)
                    }
                } catch {
                    self.logMessage('SEND', data, data)
                }
                return originalSend.call(this, data)
            }

            // Receive 메시지 기록
            const newOnmessage = function (event) {
                try {
                    const data = JSON.parse(event.data)
                    self.logMessage('RECEIVE', data, event.data)

                    // MQTT 추천 메시지 특별 처리
                    if (data.type === 'recommendation') {
                        self.handleRecommendation(data)
                    }
                } catch {
                    self.logMessage('RECEIVE', event.data, event.data)
                }

                if (originalOnmessage) {
                    return originalOnmessage.call(this, event)
                }
            }

            Object.defineProperty(ws, 'onmessage', {
                get() { return newOnmessage },
                set(handler) { originalOnmessage = handler }
            })

            ws.addEventListener('message', newOnmessage)

            return ws
        }

        Object.setPrototypeOf(window.WebSocket, originalWebSocket)
    }

    /**
     * 메시지 로깅
     */
    logMessage(direction, data, rawData) {
        const log = {
            timestamp: new Date(),
            direction: direction,
            type: data.type || 'unknown',
            data: data,
            rawData: rawData,
            elapsed: Date.now() - this.startTime
        }

        this.logs.push(log)

        // 최대 로그 수 초과 시 제거
        if (this.logs.length > this.maxLogs) {
            this.logs.shift()
        }

        // 실시간 콘솔 출력
        if (this.isVerbose) {
            this.printLog(log)
        }
    }

    /**
     * 로그 콘솔 출력
     */
    printLog(log) {
        const time = log.timestamp.toLocaleTimeString('ko-KR', { hour12: false })
        const elapsed = `${(log.elapsed / 1000).toFixed(2)}s`
        const type = log.type.toUpperCase()
        const direction = log.direction === 'SEND' ? '📤' : '📥'

        let color = 'color: gray'
        if (type === 'RECOMMENDATION') {
            color = 'color: red; font-weight: bold'
        } else if (type === 'GAZE_UPDATE') {
            color = 'color: blue'
        }

        console.log(
            `%c[${time}] ${direction} ${type} (${elapsed})`,
            color
        )
        console.log(log.data)
    }

    /**
     * MQTT 추천 메시지 특별 처리
     */
    handleRecommendation(data) {
        console.log('%c🔔 MQTT 추천 수신! 🔔', 'background: linear-gradient(90deg, #ff6b6b, #ee5a6f); color: white; padding: 10px; border-radius: 5px; font-weight: bold; font-size: 16px')
        console.log('%c제목:', 'color: red; font-weight: bold', data.title)
        console.log('%c내용:', 'color: red; font-weight: bold', data.content)
        console.log('%c발송 시간:', 'color: red; font-weight: bold', new Date().toLocaleString('ko-KR'))
    }

    /**
     * 모든 로그 조회
     */
    getLogs() {
        if (!this.isMonitoring) {
            console.warn('⚠️ 모니터링이 시작되지 않음')
            return []
        }

        console.log(`%c📊 총 ${this.logs.length}개의 MQTT 메시지`, 'color: green; font-weight: bold')
        console.table(this.logs.map(log => ({
            'Time': log.timestamp.toLocaleTimeString('ko-KR', { hour12: false }),
            'Direction': log.direction,
            'Type': log.type,
            'Data': JSON.stringify(log.data)
        })))

        return this.logs
    }

    /**
     * 메시지 필터링 조회
     */
    filterLogs(filter) {
        const filtered = this.logs.filter(log =>
            log.type.toLowerCase().includes(filter.toLowerCase()) ||
            JSON.stringify(log.data).toLowerCase().includes(filter.toLowerCase())
        )

        console.log(`%c🔍 필터링 결과: ${filtered.length}개`, 'color: blue; font-weight: bold')
        console.table(filtered.map(log => ({
            'Time': log.timestamp.toLocaleTimeString('ko-KR', { hour12: false }),
            'Type': log.type,
            'Data': JSON.stringify(log.data)
        })))

        return filtered
    }

    /**
     * 통계 조회
     */
    getStats() {
        if (!this.isMonitoring) {
            console.warn('⚠️ 모니터링이 시작되지 않음')
            return null
        }

        const stats = {
            총메시지수: this.logs.length,
            발송메시지: this.logs.filter(l => l.direction === 'SEND').length,
            수신메시지: this.logs.filter(l => l.direction === 'RECEIVE').length,
            추천메시지: this.logs.filter(l => l.type === 'recommendation').length,
            시선업데이트: this.logs.filter(l => l.type === 'gaze_update').length,
            기타메시지: this.logs.filter(l => !['recommendation', 'gaze_update'].includes(l.type)).length,
            실행시간: `${((Date.now() - this.startTime) / 1000).toFixed(2)}초`
        }

        console.log('%c📈 MQTT 모니터링 통계', 'background: blue; color: white; padding: 5px 10px; font-weight: bold')
        console.table(stats)

        return stats
    }

    /**
     * 상세 출력 토글
     */
    toggleVerbose() {
        this.isVerbose = !this.isVerbose
        console.log(`%c${this.isVerbose ? '✅' : '❌'} 실시간 상세 출력: ${this.isVerbose ? '활성화' : '비활성화'}`, 'color: green; font-weight: bold')
    }

    /**
     * 모니터링 중지
     */
    stop() {
        if (!this.isMonitoring) {
            console.warn('⚠️ 모니터링이 시작되지 않음')
            return
        }

        this.isMonitoring = false
        console.log('%c⏹️ MQTT 모니터링 중지됨', 'color: red; font-weight: bold')
        console.log(`%c총 ${this.logs.length}개 메시지 기록됨`, 'color: gray')
    }

    /**
     * 로그 초기화
     */
    clearLogs() {
        this.logs = []
        console.log('%c🗑️ 로그 초기화됨', 'color: gray')
    }
}

// 전역 객체로 export
export const mqttMonitor = new MQTTMonitor()

// window에 등록 (개발자 도구에서 접근 가능)
if (typeof window !== 'undefined') {
    window.mqttMonitor = mqttMonitor
}

export default mqttMonitor
