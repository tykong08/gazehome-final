#!/usr/bin/env python3
"""
테스트용 더미 데이터 생성 스크립트.

생성 항목:
1. 보정 데이터 (pickle 파일): 시선 추적 모델 파라미터
2. 더미 사용자 데이터: SQLite DB에 저장
3. 더미 기기 정보: 로컬 DB에 저장

사용법:
    python generate_test_data.py
"""

import sys
import json
import pickle
import sqlite3
from pathlib import Path
from datetime import datetime
import numpy as np

# 프로젝트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# 보정 데이터 생성
# ============================================================================

def generate_calibration_data():
    """시선 추적 모델 보정 데이터 생성."""
    print("\n" + "="*70)
    print("📊 보정 데이터 생성 중...")
    print("="*70)
    
    calibration_dir = PROJECT_ROOT / "data" / "calibration"
    calibration_dir.mkdir(parents=True, exist_ok=True)
    
    # Ridge 회귀 모델 파라미터 (더미)
    calibration_data = {
        "model_type": "ridge",
        "calibration_points": 9,
        "calibration_date": datetime.now().isoformat(),
        "model_params": {
            "coef": np.random.randn(486).tolist(),  # 486-dim feature coefficients
            "intercept": np.random.randn(2).tolist(),  # x, y 좌표
            "alpha": 1.0
        },
        "screen_size": {
            "width": 1920,
            "height": 1080
        },
        "validation_accuracy": 0.92,
        "calibration_samples": 30,  # 포인트당 샘플 수
        "notes": "테스트용 더미 보정 데이터"
    }
    
    # Pickle로 저장
    calibration_file = calibration_dir / "calibration_model.pkl"
    with open(calibration_file, "wb") as f:
        pickle.dump(calibration_data, f)
    
    print(f"✅ 보정 데이터 저장: {calibration_file}")
    print(f"   - 모델 타입: {calibration_data['model_type']}")
    print(f"   - 보정 포인트: {calibration_data['calibration_points']}")
    print(f"   - 검증 정확도: {calibration_data['validation_accuracy']*100:.1f}%")
    
    return calibration_data


# ============================================================================
# 더미 사용자 데이터 생성
# ============================================================================

def generate_user_data():
    """더미 사용자 정보 생성."""
    print("\n" + "="*70)
    print("👤 더미 사용자 데이터 생성 중...")
    print("="*70)
    
    users = [
        {
            "user_id": "user_001",
            "username": "김철수",
            "email": "kim@example.com",
            "calibration_completed": True,
            "calibration_date": "2024-10-15T10:30:00",
            "created_at": "2024-10-01T08:00:00"
        },
        {
            "user_id": "user_002",
            "username": "이영희",
            "email": "lee@example.com",
            "calibration_completed": True,
            "calibration_date": "2024-10-20T14:15:00",
            "created_at": "2024-10-05T09:30:00"
        },
        {
            "user_id": "user_003",
            "username": "박민수",
            "email": "park@example.com",
            "calibration_completed": False,
            "calibration_date": None,
            "created_at": "2024-10-25T16:45:00"
        }
    ]
    
    db_path = PROJECT_ROOT / "backend" / "core" / "test_users.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT UNIQUE,
            calibration_completed BOOLEAN DEFAULT 0,
            calibration_date TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # 데이터 삽입
    for user in users:
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, username, email, calibration_completed, calibration_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user["user_id"],
            user["username"],
            user["email"],
            user["calibration_completed"],
            user["calibration_date"],
            user["created_at"],
            datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 사용자 데이터 저장: {db_path}")
    for user in users:
        status = "✓ 보정완료" if user["calibration_completed"] else "✗ 보정필요"
        print(f"   - {user['username']} ({user['user_id']}) {status}")
    
    return users


# ============================================================================
# 더미 기기 정보 생성
# ============================================================================

def generate_device_data():
    """더미 기기 정보 생성."""
    print("\n" + "="*70)
    print("🏠 더미 기기 데이터 생성 중...")
    print("="*70)
    
    devices = [
        {
            "device_id": "device_001",
            "device_type": "air_purifier",
            "name": "거실 공기청정기",
            "model": "LG AP3200",
            "state": {
                "power": "ON",
                "wind_strength": "MID",
                "mode": "CLEAN"
            }
        },
        {
            "device_id": "device_002",
            "device_type": "air_conditioner",
            "name": "거실 에어컨",
            "model": "LG AC3500",
            "state": {
                "power": "ON",
                "target_temp": 25,
                "current_temp": 24,
                "wind_strength": "MID",
                "mode": "COOL"
            }
        },
        {
            "device_id": "device_003",
            "device_type": "air_conditioner",
            "name": "침실 에어컨",
            "model": "LG AC2800",
            "state": {
                "power": "OFF",
                "target_temp": 20,
                "current_temp": 19,
                "wind_strength": "LOW",
                "mode": "COOL"
            }
        }
    ]
    
    # 로컬 상태 저장
    state_dir = PROJECT_ROOT / "data" / "device_states"
    state_dir.mkdir(parents=True, exist_ok=True)
    
    for device in devices:
        state_file = state_dir / f"{device['device_id']}.json"
        state_data = {
            "device_id": device["device_id"],
            "state": device["state"],
            "source": "test_data",
            "timestamp": datetime.now().isoformat(),
            "cache_until": datetime.now().isoformat()
        }
        state_file.write_text(json.dumps(state_data, indent=2, ensure_ascii=False))
        
        print(f"✅ 기기 상태 저장: {device['name']}")
        print(f"   - 기기 ID: {device['device_id']}")
        print(f"   - 기기 타입: {device['device_type']}")
        print(f"   - 현재 상태: {device['state']}")
    
    return devices


# ============================================================================
# 메인
# ============================================================================

def main():
    """테스트 데이터 생성."""
    print("\n" + "="*70)
    print("🧪 테스트 데이터 생성 시작")
    print("="*70)
    
    try:
        # 1. 보정 데이터 생성
        calibration_data = generate_calibration_data()
        
        # 2. 사용자 데이터 생성
        users = generate_user_data()
        
        # 3. 기기 데이터 생성
        devices = generate_device_data()
        
        print("\n" + "="*70)
        print("✅ 모든 테스트 데이터 생성 완료!")
        print("="*70)
        print(f"\n📊 생성 요약:")
        print(f"   - 보정 데이터: 1개")
        print(f"   - 사용자: {len(users)}명")
        print(f"   - 기기: {len(devices)}개")
        print(f"\n💡 테스트 방법:")
        print(f"   1. 백엔드 서버 시작: python backend/run.py")
        print(f"   2. 프론트엔드 시작: npm run dev")
        print(f"   3. 사용자ID 입력: user_001, user_002, user_003 중 선택")
        print(f"   4. 기기 조회 및 제어 테스트")
        
    except Exception as e:
        print(f"\n❌ 데이터 생성 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
