# 🚀 GazeHome 원클릭 설치 가이드

**목표**: 클린한 상태에서 한 번에 모든 설정을 완료

---

## 📋 전제조건

- **Python 3.11** 설치됨
- **Node.js** 설치됨 (프론트엔드용)
- **Git** 설치됨
- **인터넷 연결**

---

## 🎯 한 번에 실행하는 방법

### 1️⃣ 프로젝트 폴더로 이동

```bash
cd /path/to/edge-module
```

### 2️⃣ setup.sh 실행 권한 부여

```bash
chmod +x setup.sh
```

### 3️⃣ 스크립트 실행

```bash
bash setup.sh
```

**스크립트가 자동으로 수행하는 작업:**
- ✅ 시스템 정보 확인 (Mac/Linux)
- ✅ Python 3.11 확인
- ✅ 기존 `.venv` 삭제 (옵션)
- ✅ 새로운 `.venv` 생성
- ✅ Python 패키지 설치 (requirements.txt)
- ✅ MediaPipe 설치 (플랫폼별)
- ✅ 프론트엔드 의존성 설치 (npm)
- ✅ 환경 설정 (.env 파일)
- ✅ 의존성 검증
- ✅ (Linux only) systemd 서비스 등록 (옵션)

---

## 🔄 기존 환경에서 초기화하기

만약 이미 폴더가 클론되어 있고 초기화하고 싶다면:

### 단계별 수동 초기화

#### **1단계: 기존 가상환경 삭제**

```bash
# Mac/Linux
rm -rf .venv
rm -rf node_modules
rm -rf frontend/node_modules
rm -rf frontend/dist

# 패키지 cache 정리 (선택사항)
rm -rf build dist *.egg-info __pycache__
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
```

#### **2단계: Git 상태 확인**

```bash
# 현재 상태 확인
git status

# 변경사항 리셋 (주의: 로컬 변경이 모두 손실됨)
git reset --hard

# 원격 저장소에서 최신 코드 받기
git pull origin develop
```

#### **3단계: Python 가상환경 생성**

```bash
# Python 3.11로 가상환경 생성
python3.11 -m venv .venv

# 가상환경 활성화
source .venv/bin/activate

# pip 업그레이드
pip install --upgrade pip setuptools wheel
```

#### **4단계: Python 의존성 설치**

```bash
# requirements.txt 설치
pip install -r requirements.txt
```

#### **5단계: MediaPipe 설치**

**Mac에서:**
```bash
pip install mediapipe
```

**Raspberry Pi 4 (ARMv8)에서 - 선택:**

**옵션 A) MediaPipe-RPI4 (권장: 성능)**
```bash
pip install mediapipe-rpi4
```

**옵션 B) 표준 MediaPipe (호환성)**
```bash
pip install mediapipe protobuf==3.20
```

#### **6단계: 프론트엔드 의존성 설치**

```bash
# 프론트엔드 디렉토리로 이동
cd frontend

# npm 의존성 설치
npm install

# 프로덕션 빌드 (선택사항)
npm run build

# 뒤로 이동
cd ..
```

#### **7단계: 환경 설정**

```bash
# 설정 디렉토리 생성
mkdir -p ~/.gazehome/calibrations

# .env 파일 생성
cat > backend/.env << 'EOF'
# AI 서버 설정
AI_SERVER_URL=http://localhost:8001
AI_REQUEST_TIMEOUT=60
AI_MAX_RETRIES=3

# 게이트웨이 설정
GATEWAY_URL=http://localhost:8002
GATEWAY_DEVICES_ENDPOINT=http://localhost:8002/api/lg/devices

# 데이터베이스 경로
DATABASE_PATH=~/.gazehome/calibrations/gazehome.db
CALIBRATION_DIR=~/.gazehome/calibrations

# 백엔드 서버 설정
HOST=0.0.0.0
PORT=8000
EOF
```

#### **8단계: 의존성 검증**

```bash
# 가상환경 활성화 확인
source .venv/bin/activate

# 주요 패키지 확인
python -c "import mediapipe; print('MediaPipe:', mediapipe.__version__)"
python -c "import fastapi; print('FastAPI: OK')"
python -c "import cv2; print('OpenCV:', cv2.__version__)"
python -c "import numpy; print('NumPy: OK')"
```

---

## ▶️ 실행 방법

### 백엔드 실행

```bash
# 1. 가상환경 활성화 (이미 활성화되어 있으면 스킵)
source .venv/bin/activate

# 2. 백엔드 실행
python backend/run.py
```

**출력 예시:**
```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 프론트엔드 실행 (새 터미널)

#### 개발 모드:
```bash
cd frontend
npm run dev
```

**출력 예시:**
```
  VITE v6.1.7  ready in 123 ms

  ➜  Local:   http://localhost:5173/
```

#### 프로덕션 모드:
```bash
cd frontend
npm run build
npx serve -s dist -l 5173 --host 0.0.0.0
```

### 브라우저 접속

- **로컬**: http://localhost:5173
- **Raspberry Pi**: http://raspberrypi.local:5173 (또는 IP 주소)

---

## 🐧 Raspberry Pi에서 자동 시작 설정

### systemd 서비스 등록

```bash
# 프로젝트 절대 경로 확인
pwd  # 예: /home/pi/edge-module

# 서비스 파일 생성
sudo tee /etc/systemd/system/gazehome.service > /dev/null << 'EOF'
[Unit]
Description=GazeHome Backend Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/edge-module
Environment="PATH=/home/pi/edge-module/.venv/bin"
ExecStart=/home/pi/edge-module/.venv/bin/python backend/run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable gazehome.service
```

### 서비스 관리 명령어

```bash
# 서비스 시작
sudo systemctl start gazehome

# 서비스 중지
sudo systemctl stop gazehome

# 서비스 상태 확인
sudo systemctl status gazehome

# 실시간 로그 보기
sudo journalctl -u gazehome -f

# 서비스 비활성화
sudo systemctl disable gazehome
```

---

## 🛠️ 문제 해결

### Q1: "externally-managed-environment" 오류

**증상:**
```
error: externally-managed-environment

× This environment is externally managed
```

**해결:**
```bash
# venv 내부에서 설치
source .venv/bin/activate
pip install <package>
```

### Q2: MediaPipe import 실패

**증상:**
```
ImportError: cannot import name 'solutions' from mediapipe
```

**해결 (Raspberry Pi):**
```bash
# 옵션 1: mediapipe-rpi4로 변경
source .venv/bin/activate
pip uninstall -y mediapipe
pip install mediapipe-rpi4

# 옵션 2: protobuf 버전 고정
pip install mediapipe protobuf==3.20
```

### Q3: OpenCV import 실패

**증상:**
```
ImportError: libGL.so.1: cannot open shared object file
```

**해결 (Raspberry Pi):**
```bash
sudo apt install -y libgl1-mesa-glx libglib2.0-0
```

### Q4: npm install 실패

**증상:**
```
npm ERR! code E403 Forbidden
```

**해결:**
```bash
# npm cache 정리
npm cache clean --force

# node_modules 삭제
rm -rf frontend/node_modules package-lock.json

# 다시 설치
cd frontend && npm install
```

### Q5: 포트 8000/5173이 이미 사용 중

**증상:**
```
OSError: [Errno 48] Address already in use
```

**해결:**

```bash
# Mac에서 포트 확인
lsof -i :8000
lsof -i :5173

# Linux에서 포트 확인
sudo netstat -tuln | grep :8000
sudo netstat -tuln | grep :5173

# 프로세스 종료
kill -9 <PID>
```

---

## 📦 의존성 확인

### Python 의존성 확인

```bash
source .venv/bin/activate
pip list | grep -E "mediapipe|fastapi|opencv|numpy|scikit"
```

**예상 결과:**
```
mediapipe                         0.10.9
fastapi                           0.104.1
opencv-python                     4.8.1.78
numpy                             1.24.3
scikit-learn                       1.3.2
```

### Node.js 의존성 확인

```bash
cd frontend
npm list --depth=0
```

**예상 결과:**
```
gazehome-frontend@1.0.0
├── framer-motion@10.16.16
├── lucide-react@0.294.0
├── react@18.2.0
├── react-dom@18.2.0
└── react-router-dom@6.20.0
```

---

## 🚨 오류가 발생했을 때

사용자가 제시한 오류 메시지를 포함해서 알려주세요:

```bash
# 전체 스택트레이스 캡처
python backend/run.py 2>&1 | tee error.log

# 또는 npm 오류
npm install 2>&1 | tee npm_error.log
```

**알려줄 때 포함사항:**
- ❌ 완전한 오류 메시지
- 📍 발생한 단계
- 🖥️ 실행 환경 (Mac/Linux/RPi)
- 🐍 Python 버전

---

## ✅ 설치 완료 체크리스트

```bash
# 1. 가상환경 활성화 확인
which python | grep .venv

# 2. 모든 Python 패키지 설치 확인
python -m pip show mediapipe fastapi opencv-python

# 3. 프론트엔드 빌드 확인
ls frontend/dist/index.html

# 4. 포트 접근성 확인
curl -I http://localhost:8000/health  # 백엔드
curl -I http://localhost:5173/        # 프론트엔드
```

모두 성공하면 설치 완료! 🎉

