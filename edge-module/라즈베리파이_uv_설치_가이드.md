# 라즈베리파이 uv 설치 가이드

## 📋 변경 사항

`pyproject.toml`이 라즈베리파이 ARM64 아키텍처를 자동으로 감지하도록 업데이트되었습니다.

### 주요 변경
- `opencv-python`, `mediapipe`: ARM64에서는 설치 제외
- `mediapipe-rpi4`: ARM64에서만 설치되는 옵션 추가

---

## 🚀 라즈베리파이 설치 프로세스

### Step 1: 사전 준비 (macOS에서)

```bash
# edge-module 디렉토리에서
cd edge-module

# 변경사항 확인
git status

# 커밋 & 푸시
git add pyproject.toml
git commit -m "feat: Add Raspberry Pi ARM64 support for mediapipe-rpi4"
git push origin develop
```

---

### Step 2: 라즈베리파이에서 설치

#### 2-1. 시스템 패키지 설치

```bash
# SSH 접속
ssh gaze@raspberrypi.local

# 기본 도구 및 의존성 설치
sudo apt update
sudo apt install -y git python3-pip python3-venv python3-dev \
  ffmpeg python3-opencv \
  libxcb-shm0 libcdio-paranoia-dev libsdl2-2.0-0 libxv1 \
  libtheora0 libva-drm2 libva-x11-2 libvdpau1 libharfbuzz0b \
  libbluray2 libatlas-base-dev libhdf5-dev libgtk-3-0 \
  libdc1394-dev libopenexr-dev
```

#### 2-2. Rust 및 uv 설치

```bash
# Rust 설치 (uv 의존성)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
# → 옵션 1 선택 (기본 설치)

# 환경 변수 로드
source $HOME/.cargo/env

# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# PATH 추가
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
echo 'export PATH="$HOME/.cargo/env:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 확인
uv --version
```

#### 2-3. 프로젝트 클론 및 설정

```bash
# 프로젝트 클론
cd ~
git clone https://github.com/ESWC-AIRIS/edge-module.git
cd edge-module

# develop 브랜치로 전환
git checkout develop
git pull origin develop
```

#### 2-4. Virtual Environment 생성

```bash
# 시스템 패키지(python3-opencv)에 접근할 수 있도록 venv 생성
uv venv --python 3.11 --system-site-packages

# 활성화
source .venv/bin/activate
```

#### 2-5. MediaPipe-RPI4 설치

```bash
# ⚠️ 중요: venv의 pip을 직접 사용 (externally-managed-environment 오류 방지)
.venv/bin/pip install mediapipe-rpi4

# 확인
.venv/bin/python -c "import mediapipe; print(f'✅ MediaPipe {mediapipe.__version__}')"
```

#### 2-6. 프로젝트 의존성 설치

```bash
# uv로 나머지 의존성 설치
# (opencv-python, mediapipe는 platform_machine == 'aarch64'이므로 자동 제외됨)
uv sync

# 또는 개별 설치
uv pip install -e .
```

#### 2-7. 설치 확인

```bash
# Python 패키지 확인
python -c "import mediapipe; print(f'✅ MediaPipe {mediapipe.__version__}')"
python -c "import cv2; print(f'✅ OpenCV {cv2.__version__}')"
python -c "import fastapi; print('✅ FastAPI')"
python -c "import numpy; print(f'✅ NumPy {numpy.__version__}')"
python -c "import sklearn; print('✅ scikit-learn')"

# 전체 import 테스트
python -c "
from backend.core.gaze_tracker import WebGazeTracker
from backend.api.main import app
print('✅ All imports successful!')
"
```

---

## 🔄 업데이트 프로세스 (코드 변경 시)

### macOS에서 푸시

```bash
cd edge-module
git add .
git commit -m "feat: 새로운 기능 추가"
git push origin develop
```

### 라즈베리파이에서 업데이트

```bash
# SSH 접속
ssh gaze@raspberrypi.local
cd ~/edge-module

# 최신 코드 가져오기
git pull origin develop

# venv 활성화
source .venv/bin/activate

# 의존성 업데이트 (필요시)
uv sync

# 또는
uv pip install -e . --upgrade
```

---

## 🎯 실행

### 백엔드 서버 실행

```bash
cd ~/edge-module

# 방법 1: uv run 사용 (권장)
uv run run.py

# 방법 2: venv 직접 사용
source .venv/bin/activate
python backend/run.py

# 방법 3: uvicorn 직접 실행
source .venv/bin/activate
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

**💡 참고**: `uv run`은 자동으로 `.venv`를 사용합니다. mediapipe-rpi4가 `.venv/bin/pip`로 설치되었으므로 `uv run`에서도 정상 작동합니다.

### 프론트엔드 빌드 & 실행

```bash
# 새 터미널 세션
ssh gaze@raspberrypi.local

# Node.js 설치 (최초 1회)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 프론트엔드 디렉토리로 이동
cd ~/edge-module/frontend

# 의존성 설치
npm install

# 프로덕션 빌드
npm run build

# 빌드 결과 서빙
npx serve -s dist -l 5173 --host 0.0.0.0

# 또는 개발 모드
npm run dev -- --host 0.0.0.0
```

---

## 📊 브라우저 접속

라즈베리파이 자체 브라우저:
```
http://localhost:5173
```

같은 네트워크의 다른 기기:
```
http://raspberrypi.local:5173
# 또는
http://<라즈베리파이_IP>:5173
```

---

## 🛠️ 문제 해결

### 1. uv 명령어를 찾을 수 없음

```bash
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

### 2. mediapipe import 실패

```bash
# 시스템 패키지 확인
python3 -c "import cv2; print(cv2.__version__)"

# venv에서 mediapipe-rpi4 확인
.venv/bin/pip list | grep mediapipe

# 재설치 (venv의 pip 사용)
.venv/bin/pip uninstall mediapipe-rpi4
.venv/bin/pip install mediapipe-rpi4
```

### 3. externally-managed-environment 오류

```bash
# ❌ 잘못된 방법
pip install mediapipe-rpi4

# ✅ 올바른 방법 1: venv의 pip 직접 사용
.venv/bin/pip install mediapipe-rpi4

# ✅ 올바른 방법 2: venv 활성화 후 설치
source .venv/bin/activate
pip install mediapipe-rpi4
```

### 4. uv run에서 mediapipe를 찾을 수 없음

```bash
# uv run 테스트
cd ~/edge-module
./test_uv_run.sh

# 정상 작동하지 않으면 venv 직접 사용
source .venv/bin/activate
python backend/run.py
```

---

## ✅ 핵심 요약

### pyproject.toml 변경 내용
```toml
# ARM64에서는 opencv-python, mediapipe 제외
"opencv-python>=4.5; platform_machine != 'aarch64'",
"mediapipe>=0.10; platform_machine != 'aarch64'",

# ARM64 전용 옵션
[project.optional-dependencies]
rpi = [
  "mediapipe-rpi4; platform_machine == 'aarch64'",
  ...
]
```

### 설치 순서
1. ✅ 시스템 패키지 설치 (ffmpeg, python3-opencv, 의존성)
2. ✅ Rust + uv 설치
3. ✅ 프로젝트 클론 & develop 브랜치
4. ✅ `uv venv --system-site-packages` 생성
5. ✅ `pip install mediapipe-rpi4` (venv 내)
6. ✅ `uv sync` (나머지 의존성)
7. ✅ 실행 및 테스트

이제 **한 번의 `uv sync` 명령으로** 라즈베리파이에서 자동으로 올바른 패키지가 설치됩니다! 🎯
