#!/usr/bin/env python3
"""보정 데이터 초기화 스크립트 - 테스트용

기능:
- 보정 관련 데이터만 삭제 (calibrations 테이블 + .pkl 파일)
- 기기 목록 및 액션은 유지
- 사용자 정보 유지

사용법:
    python reset_calibration.py
    # 또는
    uv run reset_calibration.py
"""
from pathlib import Path
import sqlite3
import sys

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from backend.core.config import settings


def reset_calibration_data():
    """보정 데이터만 초기화 (기기 데이터는 유지)"""
    db_path = settings.calibration_dir / "gazehome.db"
    
    print("=" * 60)
    print("🔄 보정 데이터 초기화 시작")
    print("=" * 60)
    
    # 1. DB에서 calibrations 테이블 데이터만 삭제
    if db_path.exists():
        print(f"\n📂 DB 경로: {db_path}")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # calibrations 테이블 레코드 수 확인
            cursor.execute("SELECT COUNT(*) FROM calibrations")
            count = cursor.fetchone()[0]
            print(f"   ├─ 기존 보정 레코드: {count}개")
            
            # calibrations 테이블만 비우기 (테이블은 유지)
            cursor.execute("DELETE FROM calibrations")
            conn.commit()
            print(f"   └─ ✅ calibrations 테이블 초기화 완료")
            
            # 기기 및 액션 데이터 확인 (유지됨)
            cursor.execute("SELECT COUNT(*) FROM devices")
            device_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM device_actions")
            action_count = cursor.fetchone()[0]
            
            print(f"\n✅ 유지된 데이터:")
            print(f"   ├─ 기기: {device_count}개")
            print(f"   └─ 액션: {action_count}개")
    else:
        print(f"⚠️  DB 파일이 없습니다: {db_path}")
    
    # 2. .pkl 보정 파일 삭제
    print(f"\n📂 보정 파일 디렉토리: {settings.calibration_dir}")
    pkl_files = list(settings.calibration_dir.glob("*.pkl"))
    
    if pkl_files:
        print(f"   ├─ 발견된 .pkl 파일: {len(pkl_files)}개")
        for pkl_file in pkl_files:
            pkl_file.unlink()
            print(f"   │  └─ 🗑️  삭제: {pkl_file.name}")
        print(f"   └─ ✅ 모든 보정 파일 삭제 완료")
    else:
        print(f"   └─ ℹ️  삭제할 .pkl 파일이 없습니다")
    
    print("\n" + "=" * 60)
    print("✅ 보정 데이터 초기화 완료!")
    print("=" * 60)
    print("\n다음 단계:")
    print("  1. 백엔드 서버 실행: cd backend && uv run uvicorn backend.api.main:app --reload")
    print("  2. 프론트엔드 서버 실행: cd frontend && npm run dev")
    print("  3. 브라우저에서 http://localhost:5173 접속")
    print("  4. 온보딩 → 보정 진행\n")


if __name__ == "__main__":
    try:
        reset_calibration_data()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
