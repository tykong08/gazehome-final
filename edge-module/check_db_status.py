#!/usr/bin/env python3
"""DB 상태 확인 스크립트 - 테스트용

기능:
- DB 테이블별 레코드 수 확인
- 보정 파일 목록 확인
- 기기 및 액션 상세 정보 확인

사용법:
    python check_db_status.py
    # 또는
    uv run check_db_status.py
"""
from pathlib import Path
import sqlite3
import sys
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from backend.core.config import settings


def check_db_status():
    """DB 상태 확인"""
    db_path = settings.calibration_dir / "gazehome.db"
    calibration_dir = settings.calibration_dir
    
    print("=" * 80)
    print("📊 GazeHome DB 상태 확인")
    print("=" * 80)
    
    # 디렉토리 정보
    print(f"\n📂 데이터 디렉토리: {calibration_dir}")
    print(f"   └─ 존재 여부: {'✅ 있음' if calibration_dir.exists() else '❌ 없음'}")
    
    # DB 파일 정보
    print(f"\n📂 DB 파일: {db_path}")
    if db_path.exists():
        size = db_path.stat().st_size
        modified = datetime.fromtimestamp(db_path.stat().st_mtime)
        print(f"   ├─ 크기: {size:,} bytes")
        print(f"   └─ 수정일: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # DB 테이블 정보
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            print("\n" + "─" * 80)
            print("📋 테이블별 레코드 수")
            print("─" * 80)
            
            # 1. Users
            cursor.execute("SELECT COUNT(*) as count FROM users")
            user_count = cursor.fetchone()['count']
            print(f"\n👤 users: {user_count}개")
            
            if user_count > 0:
                cursor.execute("SELECT * FROM users")
                for row in cursor.fetchall():
                    print(f"   └─ ID: {row['id']}, Username: {row['username']}")
            
            # 2. Calibrations
            cursor.execute("SELECT COUNT(*) as count FROM calibrations")
            calib_count = cursor.fetchone()['count']
            print(f"\n🎯 calibrations: {calib_count}개")
            
            if calib_count > 0:
                cursor.execute("SELECT * FROM calibrations ORDER BY created_at DESC")
                for idx, row in enumerate(cursor.fetchall(), 1):
                    file_exists = Path(row['calibration_file']).exists()
                    status = "✅" if file_exists else "❌"
                    print(f"   ├─ [{idx}] ID: {row['id']}")
                    print(f"   │   ├─ 파일: {row['calibration_file']}")
                    print(f"   │   ├─ 존재: {status}")
                    print(f"   │   ├─ 방법: {row['method']}")
                    print(f"   │   └─ 생성: {row['created_at']}")
            
            # 3. Devices
            cursor.execute("SELECT COUNT(*) as count FROM devices")
            device_count = cursor.fetchone()['count']
            print(f"\n🏠 devices: {device_count}개")
            
            if device_count > 0:
                cursor.execute("SELECT * FROM devices ORDER BY created_at")
                for idx, row in enumerate(cursor.fetchall(), 1):
                    print(f"   ├─ [{idx}] {row['alias']} ({row['device_type']})")
                    print(f"   │   ├─ ID: {row['device_id']}")
                    print(f"   │   ├─ 모델: {row['model_name']}")
                    print(f"   │   └─ 생성: {row['created_at']}")
            
            # 4. Device Actions
            cursor.execute("SELECT COUNT(*) as count FROM device_actions")
            action_count = cursor.fetchone()['count']
            print(f"\n⚡ device_actions: {action_count}개")
            
            if action_count > 0:
                cursor.execute("""
                    SELECT d.alias, da.action_type, da.action_name, da.readable, da.writable
                    FROM device_actions da
                    JOIN devices d ON da.device_id = d.device_id
                    ORDER BY d.alias, da.action_type, da.action_name
                """)
                
                current_device = None
                for row in cursor.fetchall():
                    if row['alias'] != current_device:
                        current_device = row['alias']
                        print(f"\n   [{current_device}]")
                    
                    rw = []
                    if row['readable']:
                        rw.append('R')
                    if row['writable']:
                        rw.append('W')
                    rw_str = '/'.join(rw) if rw else '-'
                    
                    print(f"   ├─ {row['action_type']}.{row['action_name']} ({rw_str})")
    else:
        print(f"   └─ ❌ DB 파일이 없습니다")
    
    # .pkl 파일 정보
    print("\n" + "─" * 80)
    print("📦 보정 파일 (.pkl)")
    print("─" * 80)
    
    if calibration_dir.exists():
        pkl_files = sorted(calibration_dir.glob("*.pkl"))
        
        if pkl_files:
            print(f"\n총 {len(pkl_files)}개의 .pkl 파일:")
            for pkl_file in pkl_files:
                size = pkl_file.stat().st_size
                modified = datetime.fromtimestamp(pkl_file.stat().st_mtime)
                print(f"   ├─ {pkl_file.name}")
                print(f"   │   ├─ 크기: {size:,} bytes")
                print(f"   │   └─ 수정: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("\n   └─ ℹ️  .pkl 파일이 없습니다")
    else:
        print("\n   └─ ❌ 디렉토리가 없습니다")
    
    print("\n" + "=" * 80)
    print("✅ 확인 완료")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        check_db_status()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
