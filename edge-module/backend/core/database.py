"""데모용 간소화된 SQLite 데이터베이스."""
from __future__ import annotations

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import json

from backend.core.config import settings

logger = logging.getLogger(__name__)


class Database:
    """데모용 간단한 SQLite 데이터베이스 (1명 사용자 가정)."""
    
    # 🎯 고정된 데모 사용자
    DEFAULT_USERNAME = "demo_user"
    
    def __init__(self, db_path: Optional[Path] = None):
        """기능: 데이터베이스 초기화.
        
        args: db_path (선택사항, 기본값: ~/.gazehome/calibrations/gazehome.db)
        return: 없음
        """
        if db_path is None:
            db_path = settings.calibration_dir / "gazehome.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 데이터베이스 초기화
        self._init_db()
    
    def _init_db(self):
        """기능: 테이블 생성.
        
        args: 없음
        return: 없음
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # ✅ 사용자 테이블 (간소화: username, id만)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL
                )
            """)
            
            # ✅ 캘리브레이션 테이블 (간소화: 필드 최소화)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calibrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    calibration_file TEXT NOT NULL,
                    method TEXT DEFAULT 'nine_point',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # ✅ 기기 테이블 (Gateway에서 조회한 기기 정보 저장)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL UNIQUE,
                    device_type TEXT NOT NULL,
                    alias TEXT NOT NULL,
                    model_name TEXT,
                    reportable BOOLEAN DEFAULT 1,
                    device_profile TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ✅ 기기 액션 테이블 (기기별 사용 가능한 액션)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    readable BOOLEAN DEFAULT 1,
                    writable BOOLEAN DEFAULT 1,
                    value_type TEXT,
                    value_range TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(device_id),
                    UNIQUE(device_id, action_type, action_name)
                )
            """)
            
            conn.commit()
            logger.info(f"[Database] 초기화됨: {self.db_path}")
            
            # 데모 사용자 생성
            self._init_demo_user()
    
    def _init_demo_user(self):
        """기능: 데모 사용자 생성 및 더미 보정 파일 등록.
        
        args: 없음
        return: 없음
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 이미 존재하는지 확인
            cursor.execute("SELECT id FROM users WHERE username = ?", (self.DEFAULT_USERNAME,))
            result = cursor.fetchone()
            
            if not result:
                cursor.execute(
                    "INSERT INTO users (username) VALUES (?)",
                    (self.DEFAULT_USERNAME,)
                )
                conn.commit()
                logger.info(f"[Database] 데모 사용자 생성: {self.DEFAULT_USERNAME}")
            
            # ⭐ 프로덕션 모드: 더미 보정 생성하지 않음
            # 사용자가 /calibration 페이지에서 실제 보정을 진행해야 함
            user_id = self.get_demo_user_id()
            
            # 보정 파일 확인 (정보 제공용)
            cursor.execute("SELECT id FROM calibrations WHERE user_id = ?", (user_id,))
            has_calibration = cursor.fetchone() is not None
            
            if not has_calibration:
                logger.info("[Database] ℹ️  보정 파일이 없습니다. /calibration 페이지로 이동하세요.")
    
    def get_demo_user_id(self) -> int:
        """기능: 데모 사용자 ID 조회.
        
        args: 없음
        return: 데모 사용자 ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (self.DEFAULT_USERNAME,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # 없으면 생성
            cursor.execute("INSERT INTO users (username) VALUES (?)", (self.DEFAULT_USERNAME,))
            conn.commit()
            return cursor.lastrowid
    
    # =========================================================================
    # 캘리브레이션 관리
    # =========================================================================
    
    def add_calibration(
        self,
        calibration_file: str,
        method: str = "nine_point"
    ):
        """기능: 캘리브레이션 저장.
        
        args: calibration_file, method
        return: 없음
        """
        user_id = self.get_demo_user_id()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO calibrations (user_id, calibration_file, method)
                VALUES (?, ?, ?)
                """,
                (user_id, calibration_file, method)
            )
            conn.commit()
            logger.info(f"[Database] 캘리브레이션 저장됨: {calibration_file}")
    
    def get_calibrations(self) -> List[Dict]:
        """기능: 캘리브레이션 목록 조회.
        
        args: 없음
        return: 캘리브레이션 정보 딕셔너리 목록
        """
        user_id = self.get_demo_user_id()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT * FROM calibrations
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def has_calibration(self) -> bool:
        """기능: 캘리브레이션 존재 확인.
        
        args: 없음
        return: 캘리브레이션 유무 (DB 레코드 + 실제 파일 존재)
        """
        from pathlib import Path
        
        calibrations = self.get_calibrations()
        if not calibrations:
            return False
        
        # ✅ DB에 있는 최신 보정 파일이 실제로 존재하는지 확인
        latest_file = calibrations[0]['calibration_file']
        return Path(latest_file).exists()
    
    def get_latest_calibration(self) -> Optional[str]:
        """기능: 최신 캘리브레이션 파일 조회.
        
        args: 없음
        return: 최신 캘리브레이션 파일 경로 또는 None (파일 존재하는 경우만)
        """
        from pathlib import Path
        
        calibrations = self.get_calibrations()
        for calib in calibrations:
            calib_file = calib['calibration_file']
            # ✅ 파일이 실제로 존재하는 경우만 반환
            if Path(calib_file).exists():
                return calib_file
        return None
    
    # =========================================================================
    # 기기 관리 (AI Server 동기화)
    # =========================================================================
    
    def sync_devices(self, devices: List[Dict]):
        """기능: 기기 목록 동기화 (MongoDB와 동일한 필드명 사용).
        
        AI-Services MongoDB의 user_devices 컬렉션과 동일하게 동기화합니다.
        
        args: devices (AI Server에서 가져온 기기 목록)
              예: [
                    {
                      "device_id": "b403_air_purifier_001",
                      "device_type": "air_purifier",
                      "alias": "거실 공기청정기",
                      "supported_actions": ["turn_on", "turn_off", "clean", "auto"],
                      "is_active": true
                    }
                  ]
        return: 없음
        """
        # MongoDB의 user_id와 동일하게 사용 (문자열)
        user_id = "default_user"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for device in devices:
                # ✅ MongoDB supported_actions → JSON 문자열 변환
                supported_actions_json = json.dumps(device.get("supported_actions", []))
                
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO devices 
                    (user_id, device_id, device_type, alias, supported_actions, is_active, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,  # ✅ 문자열 "default_user"
                        device.get("device_id"),
                        device.get("device_type"),
                        device.get("alias"),  # ✅ device_name → alias (MongoDB 필드명)
                        supported_actions_json,  # ✅ capabilities → supported_actions (MongoDB 필드명)
                        device.get("is_active", True),  # ✅ is_active 필드 추가
                        datetime.utcnow().isoformat()  # ✅ 동기화 시간 기록
                    )
                )
            
            conn.commit()
            logger.info(f"[Database] {len(devices)}개 기기 동기화됨 (MongoDB 스키마)")
    
    def get_devices(self) -> List[Dict]:
        """기능: 기기 목록 조회 (MongoDB 스키마 호환).
        
        args: 없음
        return: 기기 목록 (MongoDB 필드명 사용)
                예: [
                      {
                        "id": 1,
                        "user_id": "default_user",
                        "device_id": "b403_air_purifier_001",
                        "device_type": "air_purifier",
                        "alias": "거실 공기청정기",
                        "supported_actions": ["turn_on", "turn_off", "clean", "auto"],
                        "is_active": True
                      }
                    ]
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT * FROM devices
                ORDER BY id DESC
                """
            )
            
            devices = []
            for row in cursor.fetchall():
                device = dict(row)
                devices.append(device)
            
            logger.info(f"[Database] {len(devices)}개 기기 조회됨")
            return devices
    
    # =========================================================================
    # 기기 관리 (Gateway 동기화)
    # =========================================================================
    
    def save_device(
        self,
        device_id: str,
        device_type: str,
        alias: str,
        model_name: str = None,
        reportable: bool = True,
        device_profile: str = None
    ) -> bool:
        """기능: Gateway에서 조회한 기기 정보를 로컬 DB에 저장.
        
        args: device_id, device_type, alias, model_name, reportable, device_profile (JSON)
        return: 저장 성공 여부
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO devices 
                    (device_id, device_type, alias, model_name, reportable, device_profile, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (device_id, device_type, alias, model_name, reportable, device_profile))
                
                conn.commit()
                logger.info(f"[Database] 기기 저장됨: {alias} ({device_type})")
                return True
                
        except Exception as e:
            logger.error(f"[Database] 기기 저장 실패: {e}")
            return False
    
    def save_device_actions(self, device_id: str, actions: List[Dict]) -> bool:
        """기능: 기기의 사용 가능한 액션 저장.
        
        args: device_id, actions (리스트)
        return: 저장 성공 여부
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 기존 액션 삭제
                cursor.execute("DELETE FROM device_actions WHERE device_id = ?", (device_id,))
                
                # 새 액션 저장
                for action in actions:
                    cursor.execute("""
                        INSERT INTO device_actions 
                        (device_id, action_type, action_name, readable, writable, value_type, value_range)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        device_id,
                        action.get("action_type", "operation"),
                        action.get("action_name"),
                        action.get("readable", True),
                        action.get("writable", True),
                        action.get("value_type"),
                        action.get("value_range")
                    ))
                
                conn.commit()
                logger.info(f"[Database] 기기 액션 저장됨: {device_id} ({len(actions)}개)")
                return True
                
        except Exception as e:
            logger.error(f"[Database] 기기 액션 저장 실패: {e}")
            return False
    
    def get_device_by_id(self, device_id: str) -> Optional[Dict]:
        """기능: 기기 정보 조회 (by device_id).
        
        args: device_id
        return: 기기 정보 딕셔너리 또는 None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"[Database] 기기 조회 실패: {e}")
            return None
    
    def get_device_actions(self, device_id: str) -> List[Dict]:
        """기능: 기기의 사용 가능한 액션 조회.
        
        args: device_id
        return: 액션 리스트
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM device_actions WHERE device_id = ? ORDER BY action_type, action_name",
                    (device_id,)
                )
                
                actions = [dict(row) for row in cursor.fetchall()]
                logger.debug(f"[Database] 기기 액션 조회: {device_id} ({len(actions)}개)")
                return actions
                
        except Exception as e:
            logger.error(f"[Database] 기기 액션 조회 실패: {e}")
            return []


# 전역 데이터베이스 인스턴스
db = Database()