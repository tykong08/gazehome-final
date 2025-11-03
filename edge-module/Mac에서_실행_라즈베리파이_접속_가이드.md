# Mac에서 실행 + 라즈베리파이에서 접속 가이드

## 📋 개요

라즈베리파이에서 의존성 설치가 어려운 경우, Mac에서 백엔드를 실행하고 라즈베리파이에서 웹 브라우저만 사용하는 방법입니다.

---

## 🖥️ 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Mac (개발 환경)                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Backend (FastAPI)                                    │   │
│  │ - 시선 추적 엔진 (WebGazeTracker)                    │   │
│  │ - API 서버 (port 8000)                               │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Frontend (Vite Dev Server)                           │   │
│  │ - React SPA (port 5173)                              │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────┘
                 │ 네트워크 (WiFi/Ethernet)
┌────────────────┴────────────────────────────────────────────┐
│              라즈베리파이 (클라이언트)                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Chromium 브라우저                                    │   │
│  │ - http://<Mac_IP>:5173 접속                          │   │
│  │ - 7인치 터치스크린 UI                                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ 장점

- ✅ 라즈베리파이에서 복잡한 의존성 설치 불필요
- ✅ Mac의 강력한 성능 활용 (시선 추적 더 빠름)
- ✅ 개발/디버깅 용이 (Mac에서 직접 확인)
- ✅ 라즈베리파이는 디스플레이만 담당

---

## 🚀 설정 방법

### Step 1: Mac에서 백엔드 실행

```bash
# edge-module 디렉토리로 이동
cd edge-module

# 백엔드 실행 (모든 네트워크 인터페이스에서 수신)
cd backend
uv run uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# 또는
uv run run.py
```

**중요**: `--host 0.0.0.0`으로 설정해야 외부 접속 가능!

---

### Step 2: Mac에서 프론트엔드 실행

```bash
# 새 터미널 열기
cd edge-module/frontend

# Vite 개발 서버 실행 (외부 접속 허용)
npm run dev -- --host 0.0.0.0

# 출력 예시:
# ➜  Local:   http://localhost:5173/
# ➜  Network: http://192.168.1.100:5173/  ← Mac IP 확인!
```

**Mac IP 주소 확인**:
```bash
# Mac의 로컬 IP 확인
ifconfig | grep "inet " | grep -v 127.0.0.1

# 또는
ipconfig getifaddr en0  # WiFi
ipconfig getifaddr en1  # Ethernet
```

---

### Step 3: Mac 방화벽 설정

#### macOS Ventura 이상
```bash
# 시스템 설정 > 네트워크 > 방화벽
# 또는 터미널에서:

# 방화벽 상태 확인
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# 방화벽이 켜져 있다면, 포트 허용
# 시스템 설정 > 네트워크 > 방화벽 > 옵션
# Python, Node.js 허용
```

#### 간단한 방법: 방화벽 일시 해제 (테스트용)
```bash
# 방화벽 끄기 (테스트 후 다시 켜기!)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off

# 테스트 완료 후 다시 켜기
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
```

---

### Step 4: 라즈베리파이 설정

#### 4-1. 브라우저 설치 (최초 1회)

```bash
# SSH 접속
ssh gaze@raspberrypi.local

# Chromium 설치
sudo apt update
sudo apt install -y chromium-browser

# 또는 Firefox
sudo apt install -y firefox-esr
```

#### 4-2. Chromium 키오스크 모드 스크립트 생성

```bash
# 홈 디렉토리에 스크립트 생성
cat > ~/start_gazehome.sh << 'EOF'
#!/bin/bash
# GazeHome 클라이언트 시작 스크립트

# Mac IP 주소 (여기를 수정하세요!)
MAC_IP="192.168.1.100"

# 화면 절전 해제
xset s off
xset -dpms
xset s noblank

# Chromium 키오스크 모드로 실행
chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --no-first-run \
  --window-position=0,0 \
  --window-size=800,480 \
  "http://${MAC_IP}:5173"
EOF

chmod +x ~/start_gazehome.sh
```

---

### Step 5: 라즈베리파이에서 접속

#### 방법 1: GUI에서 직접 실행

```bash
# 라즈베리파이 데스크톱 환경에서
./start_gazehome.sh
```

#### 방법 2: SSH에서 원격 실행

```bash
# Mac에서
ssh gaze@raspberrypi.local

# X 디스플레이 설정
export DISPLAY=:0

# 스크립트 실행
./start_gazehome.sh
```

#### 방법 3: 자동 시작 (부팅 시)

```bash
# autostart 디렉토리 생성
mkdir -p ~/.config/autostart

# 자동 시작 파일 생성
cat > ~/.config/autostart/gazehome.desktop << EOF
[Desktop Entry]
Type=Application
Name=GazeHome
Exec=/home/gaze/start_gazehome.sh
X-GNOME-Autostart-enabled=true
EOF
```

---

## 🔧 문제 해결

### 1. Mac에서 접속이 안 됨

**증상**: 라즈베리파이 브라우저에서 "연결할 수 없음"

**해결**:
```bash
# Mac에서 포트 리스닝 확인
lsof -i :5173
lsof -i :8000

# 방화벽 확인
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# 같은 네트워크인지 확인
# Mac
ifconfig | grep "inet "

# 라즈베리파이
ip addr show
```

---

### 2. CORS 오류

**증상**: 브라우저 콘솔에 "CORS policy" 오류

**해결**: `backend/core/config.py`에 라즈베리파이 IP 추가
```python
cors_origins: list[str] = [
    "http://localhost:5173",
    "http://192.168.1.*:5173",  # 동일 네트워크 모든 IP 허용
    # 또는 특정 IP
    "http://192.168.1.50:5173",  # 라즈베리파이 IP
]
```

---

### 3. WebSocket 연결 실패

**증상**: 시선 추적 데이터가 전송되지 않음

**해결**: 프론트엔드에서 WebSocket URL 수정
```javascript
// frontend/src/pages/HomePage.jsx
// 하드코딩된 localhost 대신 현재 호스트 사용
const wsUrl = `ws://${window.location.hostname}:8000/ws/gaze`
```

---

### 4. 카메라 접근 불가

**증상**: "Camera not found" 오류

**중요**: Mac의 카메라를 사용하므로 **Mac에서 카메라 권한 허용** 필요!

```bash
# Mac 시스템 설정 > 개인 정보 보호 > 카메라
# Python, Terminal 허용
```

---

## 📱 최적화 팁

### 라즈베리파이 화면 회전

```bash
# /boot/config.txt 수정
sudo nano /boot/config.txt

# 추가
display_rotate=1  # 90도
# display_rotate=2  # 180도
# display_rotate=3  # 270도

# 재부팅
sudo reboot
```

### 터치스크린 보정

```bash
sudo apt install -y xinput-calibrator
xinput_calibrator
```

### 성능 최적화

```bash
# Chromium 하드웨어 가속 활성화
chromium-browser --enable-features=VaapiVideoDecoder

# GPU 메모리 증가 (/boot/config.txt)
gpu_mem=256
```

---

## 🎯 전체 워크플로우

### Mac (개발자)

```bash
# 터미널 1: 백엔드
cd edge-module/backend
uv run uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# 터미널 2: 프론트엔드
cd edge-module/frontend
npm run dev -- --host 0.0.0.0

# IP 확인
ifconfig | grep "inet " | grep -v 127.0.0.1
# 예: 192.168.1.100
```

### 라즈베리파이 (사용자)

```bash
# start_gazehome.sh 수정
MAC_IP="192.168.1.100"  # Mac IP로 변경

# 실행
./start_gazehome.sh

# 또는 자동 시작 설정
```

### 테스트

1. 라즈베리파이 화면에 GazeHome UI 표시 확인
2. 온보딩 → 보정 진행
3. Mac 카메라로 얼굴 인식
4. 라즈베리파이 화면에서 시선 커서 확인
5. 기기 제어 테스트

---

## ✅ 핵심 요약

| 항목              | 위치         | 포트 |
| ----------------- | ------------ | ---- |
| 백엔드 (FastAPI)  | Mac          | 8000 |
| 프론트엔드 (Vite) | Mac          | 5173 |
| 시선 추적 카메라  | Mac          | -    |
| UI 디스플레이     | 라즈베리파이 | -    |
| 터치 입력         | 라즈베리파이 | -    |

**장점**:
- ✅ 설치 간단 (라즈베리파이에서 의존성 불필요)
- ✅ 성능 우수 (Mac의 강력한 CPU/GPU)
- ✅ 개발 편의성 (Mac에서 직접 디버깅)

**단점**:
- ❌ 네트워크 의존성 (WiFi 필수)
- ❌ Mac 항상 켜져 있어야 함
- ❌ 이동성 제한

**결론**: 데모/개발 단계에서는 이 방식이 더 효율적일 수 있습니다!
