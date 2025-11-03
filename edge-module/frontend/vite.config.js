import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite 설정 - 라즈베리파이 4 & 7inch 디스플레이 최적화
// - React 플러그인 활성화
// - 개발 서버를 포트 3000에서 실행
// - /api와 /ws 경로를 백엔드로 프록시 설정
// - 번들 크기 최소화 (라즈베리파이 메모리 제약)
// - 빌드 최적화
export default defineConfig({
    plugins: [react()],

    // 개발 서버 설정
    server: {
        port: 3000,
        host: '0.0.0.0',  // 모든 네트워크 인터페이스에서 수신
        strictPort: true,  // 포트 충돌 시 오류 발생
        // 프록시 설정
        proxy: {
            '/api': {
                // REST API 요청을 백엔드 서버로 프록시
                // 개발: http://0.0.0.0:8000
                // 프로덕션: http://raspberrypi.local:8000
                target: 'http://0.0.0.0:8000',
                changeOrigin: true,
                // 요청 경로 유지: /api/users/login → /api/users/login
                // (경로 재작성 안 함)
            },
            '/ws': {
                // WebSocket 연결을 백엔드 서버로 프록시
                // /ws/features, /ws/gaze 등 모든 WebSocket 경로
                target: 'ws://0.0.0.0:8000',
                ws: true,
                changeOrigin: true,
                // 요청 경로 유지: /ws/features → /ws/features
                // (경로 재작성 안 함)
            },
        },
    },

    // 빌드 최적화
    build: {
        // 라즈베리파이 최적화: 최소 번들 크기
        minify: 'terser',  // 더 공격적인 압축
        // 청크 크기 최적화
        rollupOptions: {
            output: {
                // 라이브러리는 별도 청크로 분리
                manualChunks: {
                    'react': ['react', 'react-dom'],
                    'framer': ['framer-motion'],
                    'lucide': ['lucide-react'],
                    'router': ['react-router-dom'],
                },
                // 청크 파일명 최소화
                chunkFileNames: 'js/[name].[hash].js',
                entryFileNames: 'js/[name].[hash].js',
                assetFileNames: 'assets/[name].[hash][extname]',
            },
        },
        // 청크 경고 무시 (라즈베리파이에서는 작은 번들이 중요)
        chunkSizeWarningLimit: 600,
        // 소스맵 생성 비활성화 (메모리 절약)
        sourcemap: false,
        // 번들 리포트 생성 안 함
        reportCompressedSize: false,
        // 병렬 처리 최대화 (라즈베리파이 CPU 활용)
        terserOptions: {
            compress: {
                drop_console: true,  // console.log 제거
                drop_debugger: true, // debugger 제거
            },
        },
    },

    // 라즈베리파이 CPU 최적화
    define: {
        // 개발 모드 비활성화
        __DEV__: false,
    },
})
