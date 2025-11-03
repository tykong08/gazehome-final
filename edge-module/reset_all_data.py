#!/usr/bin/env python3
"""전체 데이터 초기화 스크립트 - 테스트용

기능:
- DB 파일 완전 삭제
- 모든 보정 파일(.pkl) 삭제
- 다음 실행 시 자동으로 재생성됨

사용법:
    python reset_all_data.py
    # 또는
    uv run reset_all_data.py
"""
from pathlib import Path
import sys
import shutil

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from backend.core.config import settings


def reset_all_data():
    """모든 데이터 초기화 (DB + 보정 파일)"""
    calibration_dir = settings.calibration_dir
    
    print("=" * 60)
    print("🔄 전체 데이터 초기화 시작")
    print("=" * 60)
    print(f"\n📂 대상 디렉토리: {calibration_dir}")
    
    if calibration_dir.exists():
        # 디렉토리 내용 확인
        db_files = list(calibration_dir.glob("*.db"))
        pkl_files = list(calibration_dir.glob("*.pkl"))
        
        print(f"\n📋 삭제될 파일:")
        print(f"   ├─ DB 파일: {len(db_files)}개")
        for db_file in db_files:
            print(f"   │  └─ {db_file.name}")
        print(f"   └─ 보정 파일: {len(pkl_files)}개")
        for pkl_file in pkl_files:
            print(f"      └─ {pkl_file.name}")
        
        # 사용자 확인
        print(f"\n⚠️  위 파일들을 모두 삭제합니다.")
        response = input("계속하시겠습니까? (y/N): ").strip().lower()
        
        if response != 'y':
            print("❌ 취소되었습니다.")
            return
        
        # 전체 디렉토리 삭제
        shutil.rmtree(calibration_dir)
        print(f"\n✅ {calibration_dir} 디렉토리 삭제 완료")
        
        # 디렉토리 재생성 (빈 상태)
        calibration_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ 빈 디렉토리 재생성 완료")
    else:
        print(f"\nℹ️  디렉토리가 존재하지 않습니다: {calibration_dir}")
    
    print("\n" + "=" * 60)
    print("✅ 전체 데이터 초기화 완료!")
    print("=" * 60)
    print("\n다음 실행 시:")
    print("  - DB가 자동으로 재생성됩니다")
    print("  - 기기 데이터는 Gateway에서 다시 가져옵니다")
    print("  - 보정을 처음부터 진행해야 합니다\n")


if __name__ == "__main__":
    try:
        reset_all_data()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
