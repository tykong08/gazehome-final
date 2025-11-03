# GazeHome - AI-Powered Gaze Control System

라즈베리파이 기반 시선 추적 스마트홈 제어 시스템

## 시스템 구성

### Edge Module (Raspberry Pi)
- **Backend**: FastAPI (Port 8000)
  - WebSocket 기반 실시간 시선 데이터 스트리밍
  - SQLite 데이터베이스 (사용자, 디바이스, 보정 데이터)
  - WebGazeTracker (Ridge 모델, 9-point 보정)
  
- **Frontend**: React + Vite (Port 5173)
  - 3초 dwell time 기반 디바이스 제어
  - 눈 깜빡임 감지 클릭
  - 실시간 시선 커서 표시

### AI Services (AWS EC2)
- 디바이스 추천 및 컨텍스트 분석
- URL: http://34.227.8.172:8000

### Gateway (Port 8001)
- LG ThinQ API 통합
- 스마트 디바이스 직접 제어

## 주요 기능

### 시선 추적 및 보정
- 9-point 보정 방식
- Ridge 회귀 모델
- NoOp/Kalman 필터
- 보정 파일: `~/.gazehome/calibrations/{username}.pkl`

### 디바이스 제어
- Edge Module → Gateway → LG ThinQ (직접 제어)
- AI 서버는 추천 기능에만 사용
- 온도 조절, 전원, 모드 변경 등

### 사용자 관리
- 고정 사용자: `demo_user`
- 자동 로그인 (10초 스플래시)
- 보정 데이터 자동 로드

## 설치 및 실행

### Backend
```bash
cd edge-module/backend
python run.py
```

### Frontend
```bash
cd edge-module/frontend
npm install
npm run dev
```

## 화면 사양
- 7인치 라즈베리파이 디스플레이
- 해상도: 800×480

## 개발 환경
- Python 3.11
- Node.js
- OpenCV (웹캠 시선 추적)
- FastAPI
- React 18

## 라이선스
MIT License
