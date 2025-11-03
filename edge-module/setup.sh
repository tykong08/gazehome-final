#!/bin/bash
# GazeHome 원클릭 설치 스크립트 (Mac & Raspberry Pi 호환)
# 사용법: bash setup.sh

set -e  # 오류 발생 시 중단

echo "🚀 GazeHome 통합 설치 스크립트"
echo "=================================="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
print_step() {
    echo -e "${BLUE}[단계 $1]${NC} $2"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# ============================================================================
# 단계 1: 시스템 정보 확인
# ============================================================================
print_step "1" "시스템 정보 확인 중..."

OS_TYPE=$(uname -s)
if [ "$OS_TYPE" = "Darwin" ]; then
    print_success "macOS 감지됨"
    IS_MAC=true
elif [ "$OS_TYPE" = "Linux" ]; then
    print_success "Linux 감지됨"
    IS_MAC=false
else
    print_error "지원하지 않는 OS입니다: $OS_TYPE"
    exit 1
fi

# ============================================================================
# 단계 2: 필수 도구 확인
# ============================================================================
print_step "2" "필수 도구 확인 중..."

# Python 3.11 확인
if command -v python3.11 &> /dev/null; then
    PYTHON_BIN="python3.11"
    print_success "Python 3.11 found"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_warning "Python 3.11을 찾을 수 없습니다. 현재 버전: $PYTHON_VERSION"
    PYTHON_BIN="python3"
else
    print_error "Python을 설치하세요"
    exit 1
fi

# Git 확인
if ! command -v git &> /dev/null; then
    print_error "git을 설치하세요"
    exit 1
fi
print_success "git 확인됨"

# Node.js 확인
if ! command -v node &> /dev/null; then
    print_warning "Node.js를 찾을 수 없습니다. 프론트엔드 빌드 스킵됩니다."
    HAS_NODE=false
else
    print_success "Node.js $(node --version) 확인됨"
    HAS_NODE=true
fi

# ============================================================================
# 단계 3: 기존 가상환경 삭제 (옵션)
# ============================================================================
print_step "3" "기존 가상환경 확인 중..."

if [ -d ".venv" ]; then
    print_warning "기존 .venv 디렉토리가 존재합니다"
    read -p "삭제하고 새로 생성하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_warning ".venv 삭제 중..."
        rm -rf .venv
        print_success ".venv 삭제 완료"
    else
        print_warning ".venv를 유지하고 진행합니다"
    fi
else
    print_success "기존 가상환경이 없습니다"
fi

# ============================================================================
# 단계 4: Python 가상환경 생성
# ============================================================================
print_step "4" "Python 3.11 가상환경 생성 중..."

$PYTHON_BIN -m venv .venv --upgrade-deps

if [ ! -f ".venv/bin/python" ]; then
    print_error "가상환경 생성 실패"
    exit 1
fi

print_success "가상환경 생성 완료: .venv/"

# ============================================================================
# 단계 5: 가상환경 활성화 및 의존성 설치
# ============================================================================
print_step "5" "가상환경 활성화 및 의존성 설치 중..."

source .venv/bin/activate

# pip 업그레이드
print_warning "pip 업그레이드 중..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1

# requirements.txt 설치
print_warning "Python 패키지 설치 중..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_success "requirements.txt 설치 완료"
else
    print_error "requirements.txt 파일을 찾을 수 없습니다"
    exit 1
fi

# ============================================================================
# 단계 6: MediaPipe 설치 (플랫폼별)
# ============================================================================
print_step "6" "MediaPipe 설치 중..."

if [ "$IS_MAC" = true ]; then
    print_warning "macOS: 표준 mediapipe 설치"
    pip install mediapipe
    print_success "mediapipe 설치 완료"
else
    # Linux (Raspberry Pi)
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ]; then
        print_warning "Raspberry Pi 4 (ARMv8) 감지됨"
        print_warning "mediapipe-rpi4 또는 표준 mediapipe 중 선택:"
        echo "1) mediapipe-rpi4 (권장: 더 빠른 성능)"
        echo "2) mediapipe (더 나은 호환성)"
        read -p "선택 (1 또는 2): " mp_choice
        
        if [ "$mp_choice" = "1" ]; then
            print_warning "mediapipe-rpi4 설치 중..."
            pip install mediapipe-rpi4
            print_success "mediapipe-rpi4 설치 완료"
        else
            print_warning "mediapipe 설치 중..."
            pip install mediapipe protobuf==3.20
            print_success "mediapipe 설치 완료"
        fi
    else
        print_warning "표준 mediapipe 설치"
        pip install mediapipe
        print_success "mediapipe 설치 완료"
    fi
fi

# ============================================================================
# 단계 7: Python 의존성 검증
# ============================================================================
print_step "7" "Python 의존성 검증 중..."

echo ""
VALIDATION_FAILED=false

python -c "import mediapipe; print('✅ MediaPipe: $(' mediapipe.__version__ ')')" 2>/dev/null || { print_error "MediaPipe"; VALIDATION_FAILED=true; }
python -c "import fastapi; print('✅ FastAPI')" 2>/dev/null || { print_error "FastAPI"; VALIDATION_FAILED=true; }
python -c "import uvicorn; print('✅ Uvicorn')" 2>/dev/null || { print_error "Uvicorn"; VALIDATION_FAILED=true; }
python -c "import numpy; print('✅ NumPy')" 2>/dev/null || { print_error "NumPy"; VALIDATION_FAILED=true; }
python -c "import cv2; print('✅ OpenCV')" 2>/dev/null || { print_error "OpenCV"; VALIDATION_FAILED=true; }
python -c "import sklearn; print('✅ Scikit-learn')" 2>/dev/null || { print_error "Scikit-learn"; VALIDATION_FAILED=true; }
python -c "import websockets; print('✅ WebSockets')" 2>/dev/null || { print_error "WebSockets"; VALIDATION_FAILED=true; }

echo ""

if [ "$VALIDATION_FAILED" = true ]; then
    print_error "일부 의존성이 누락되었습니다. 위를 확인하세요."
    exit 1
fi

print_success "모든 Python 의존성이 설치되었습니다"

# ============================================================================
# 단계 8: 프론트엔드 의존성 설치
# ============================================================================
print_step "8" "프론트엔드 의존성 설치 중..."

if [ "$HAS_NODE" = true ]; then
    if [ -d "frontend" ]; then
        cd frontend
        
        if [ -d "node_modules" ]; then
            print_warning "기존 node_modules 디렉토리가 존재합니다"
            read -p "삭제하고 새로 설치하시겠습니까? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf node_modules package-lock.json
                print_warning "node_modules 삭제 완료"
            fi
        fi
        
        print_warning "npm install 실행 중..."
        npm install > /dev/null 2>&1
        print_success "프론트엔드 의존성 설치 완료"
        
        cd ..
    else
        print_warning "frontend 디렉토리를 찾을 수 없습니다"
    fi
else
    print_warning "Node.js가 없어 프론트엔드 빌드를 스킵합니다"
fi

# ============================================================================
# 단계 9: 환경 설정
# ============================================================================
print_step "9" "환경 설정 중..."

mkdir -p ~/.gazehome/calibrations

if [ ! -f "backend/.env" ]; then
    print_warning ".env 파일 생성 중..."
    cat > backend/.env << 'EOF'
# AI 서버 설정
AI_SERVER_URL=http://localhost:8001
AI_REQUEST_TIMEOUT=60
AI_MAX_RETRIES=3

# 게이트웨이 설정
GATEWAY_URL=http://localhost:8002
GATEWAY_DEVICES_ENDPOINT=http://localhost:8002/api/lg/devices

# 데이터베이스 경로
DATABASE_PATH=/home/$(whoami)/.gazehome/calibrations/gazehome.db
CALIBRATION_DIR=/home/$(whoami)/.gazehome/calibrations

# 백엔드 서버 설정
HOST=0.0.0.0
PORT=8000
EOF
    print_success ".env 파일 생성 완료"
else
    print_success ".env 파일이 이미 존재합니다"
fi

# ============================================================================
# 단계 10: 최종 요약
# ============================================================================
print_step "10" "설치 완료!"

echo ""
echo "=================================="
echo "✅ GazeHome 설치가 완료되었습니다!"
echo "=================================="
echo ""
echo "📋 다음 단계:"
echo ""
echo "1️⃣  가상환경 활성화:"
echo "   source .venv/bin/activate"
echo ""
echo "2️⃣  백엔드 실행 (Mac/Linux):"
echo "   python backend/run.py"
echo ""
echo "3️⃣  프론트엔드 실행 (새 터미널):"
echo "   cd frontend && npm run dev"
echo ""
echo "4️⃣  브라우저 접속:"
echo "   http://localhost:5173"
echo ""
echo "📦 프로덕션 빌드:"
echo "   cd frontend && npm run build"
echo ""
echo "=================================="
echo ""

# ============================================================================
# 단계 11: 선택적 systemd 서비스 설정 (Linux만)
# ============================================================================
if [ "$IS_MAC" = false ]; then
    echo ""
    echo "🐧 Linux 시스템 감지됨"
    read -p "systemd 서비스를 등록하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "11" "systemd 서비스 생성 중..."
        
        PROJECT_PATH=$(pwd)
        
        sudo tee /etc/systemd/system/gazehome.service > /dev/null << EOF
[Unit]
Description=GazeHome Backend Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_PATH
Environment="PATH=$PROJECT_PATH/.venv/bin"
ExecStart=$PROJECT_PATH/.venv/bin/python backend/run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
        
        print_warning "systemd 서비스 등록 중..."
        sudo systemctl daemon-reload
        sudo systemctl enable gazehome.service
        
        print_success "systemd 서비스 등록 완료"
        echo ""
        echo "🚀 서비스 시작: sudo systemctl start gazehome"
        echo "🛑 서비스 중지: sudo systemctl stop gazehome"
        echo "📊 상태 확인: sudo systemctl status gazehome"
        echo "📜 로그 보기: sudo journalctl -u gazehome -f"
    fi
fi

echo ""
print_success "설치 스크립트 실행 완료!"
