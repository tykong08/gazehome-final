#!/usr/bin/env python3
"""GazeHome 백엔드 서버를 실행합니다."""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 명시적 경로 설정 및 확인
env_file = project_root / ".env"
if not env_file.exists():
    print(f"⚠️  Warning: .env file not found at {env_file}")
    print("ℹ️  Using default configuration...")

import uvicorn
from backend.core.config import settings

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════╗
║   GazeHome 스마트 홈 백엔드 서버         ║
║   (라즈베리파이 최적화 설정)             ║
╚══════════════════════════════════════════╝

서버: http://{settings.host}:{settings.port}
API 문서: http://{settings.host}:{settings.port}/docs
WebSocket: ws://{settings.host}:{settings.port}/ws/gaze

설정:
  - 시선 추적 모델: {settings.model_name}
  - 필터: {settings.filter_method} 
  - 화면 해상도: {settings.screen_width}x{settings.screen_height}
  - 카메라 인덱스: {settings.camera_index}

중지하려면 Ctrl+C를 누르세요
""")
    
    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info"
    )
