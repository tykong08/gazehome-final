# SQLite Database Schema 상세 설명

## 📂 데이터베이스 위치

```
~/.gazehome/calibrations/gazehome.db
```

**경로 분석:**
- `~` = 사용자 홈 디렉토리
- `.gazehome` = GazeHome 애플리케이션 데이터 디렉토리 (숨김)
- `calibrations` = 캘리브레이션 관련 데이터 저장소
- `gazehome.db` = SQLite 데이터베이스 파일

---

## 🗄️ 데이터베이스 초기화 코드

```python
# backend/core/database.py
def _init_db(self):
    """테이블이 없으면 생성합니다."""
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()
        
        # 4개 테이블 자동 생성
        cursor.execute("CREATE TABLE IF NOT EXISTS users ...")
        cursor.execute("CREATE TABLE IF NOT EXISTS calibrations ...")
        cursor.execute("CREATE TABLE IF NOT EXISTS devices ...")
        cursor.execute("CREATE TABLE IF NOT EXISTS login_history ...")
        
        conn.commit()
```

---

## 📋 테이블 상세 스키마

### 1. **users** - 사용자 정보

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

| 컬럼         | 타입      | 제약조건                  | 설명                        |
| ------------ | --------- | ------------------------- | --------------------------- |
| `id`         | INTEGER   | PK, AI                    | 자동 증가 ID (1, 2, 3, ...) |
| `username`   | TEXT      | UNIQUE, NOT NULL          | 사용자명 (중복 불가)        |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 계정 생성 시간              |
| `last_login` | TIMESTAMP | NULL 가능                 | 마지막 로그인 시간          |

**데이터 예시:**

```sql
INSERT INTO users (username, last_login) VALUES ('alice', '2024-10-22 14:30:00');
INSERT INTO users (username, last_login) VALUES ('bob', '2024-10-22 09:00:00');

-- 조회
SELECT * FROM users;
```

| id  | username | created_at          | last_login          |
| --- | -------- | ------------------- | ------------------- |
| 1   | alice    | 2024-10-21 10:00:00 | 2024-10-22 14:30:00 |
| 2   | bob      | 2024-10-20 09:15:00 | 2024-10-22 09:00:00 |

**사용 사례:**
```python
# 사용자 로그인
user_id = db.get_or_create_user("alice")
# → users 테이블에서 "alice" 조회 또는 생성
# → user_id = 1 반환

# 모든 사용자 조회
users = db.get_all_users()
# → SELECT * FROM users ORDER BY last_login DESC
```

---

### 2. **calibrations** - 캘리브레이션 이력

```sql
CREATE TABLE IF NOT EXISTS calibrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    calibration_file TEXT NOT NULL,
    screen_width INTEGER,
    screen_height INTEGER,
    method TEXT,
    samples_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

| 컬럼               | 타입      | 제약조건                  | 설명                             |
| ------------------ | --------- | ------------------------- | -------------------------------- |
| `id`               | INTEGER   | PK, AI                    | 캘리브레이션 레코드 ID           |
| `user_id`          | INTEGER   | FK (users.id)             | 소유한 사용자 ID                 |
| `calibration_file` | TEXT      | NOT NULL                  | 파일명 (예: "alice.pkl")         |
| `screen_width`     | INTEGER   | NULL 가능                 | 화면 너비 (픽셀)                 |
| `screen_height`    | INTEGER   | NULL 가능                 | 화면 높이 (픽셀)                 |
| `method`           | TEXT      | NULL 가능                 | 캘리브레이션 방식 ("nine_point") |
| `samples_count`    | INTEGER   | NULL 가능                 | 수집된 샘플 수                   |
| `created_at`       | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 캘리브레이션 생성 시간           |

**데이터 예시:**

```sql
INSERT INTO calibrations 
(user_id, calibration_file, screen_width, screen_height, method, samples_count)
VALUES 
(1, 'alice.pkl', 1024, 600, 'nine_point', 45);

INSERT INTO calibrations 
(user_id, calibration_file, screen_width, screen_height, method, samples_count)
VALUES 
(1, 'alice_v2.pkl', 1024, 600, 'nine_point', 48);

-- 최신 캘리브레이션 조회
SELECT * FROM calibrations 
WHERE user_id = 1 
ORDER BY created_at DESC 
LIMIT 1;
```

| id  | user_id | calibration_file | screen_width | screen_height | method     | samples_count | created_at          |
| --- | ------- | ---------------- | ------------ | ------------- | ---------- | ------------- | ------------------- |
| 1   | 1       | alice.pkl        | 1024         | 600           | nine_point | 45            | 2024-10-21 11:00:00 |
| 2   | 1       | alice_v2.pkl     | 1024         | 600           | nine_point | 48            | 2024-10-22 14:00:00 |

**사용 사례:**
```python
# 사용자 캘리브레이션 추가
db.add_calibration(
    username="alice",
    calibration_file="alice_v2.pkl",
    screen_width=1024,
    screen_height=600,
    method="nine_point",
    samples_count=48
)

# 최신 캘리브레이션 가져오기
latest = db.get_latest_calibration("alice")
# → "alice_v2.pkl" 반환

# 캘리브레이션 여부 확인
has_cal = db.has_calibration("alice")
# → True
```

---

### 3. **devices** - 기기 목록 (AI Server 캐시)

```sql
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    device_id TEXT NOT NULL,
    device_name TEXT NOT NULL,
    device_type TEXT,
    capabilities TEXT,
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, device_id)
);
```

| 컬럼           | 타입      | 제약조건                   | 설명                               |
| -------------- | --------- | -------------------------- | ---------------------------------- |
| `id`           | INTEGER   | PK, AI                     | 레코드 ID                          |
| `user_id`      | INTEGER   | FK (users.id)              | 소유한 사용자 ID                   |
| `device_id`    | TEXT      | NOT NULL                   | AI Server의 기기 ID (예: "ac_001") |
| `device_name`  | TEXT      | NOT NULL                   | 기기 표시명 (예: "거실 에어컨")    |
| `device_type`  | TEXT      | NULL 가능                  | 기기 타입 (예: "airconditioner")   |
| `capabilities` | TEXT      | NULL 가능                  | 기능 목록 (JSON 배열)              |
| `last_synced`  | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP  | 마지막 동기화 시간                 |
| **UNIQUE**     | -         | UNIQUE(user_id, device_id) | 사용자당 기기는 유일               |

**데이터 예시:**

```sql
INSERT INTO devices 
(user_id, device_id, device_name, device_type, capabilities, last_synced)
VALUES 
(1, 'ac_001', '거실 에어컨', 'airconditioner', '["turn_on","turn_off","set_temperature"]', '2024-10-22 14:30:00');

INSERT INTO devices 
(user_id, device_id, device_name, device_type, capabilities, last_synced)
VALUES 
(1, 'light_01', '거실 조명', 'light', '["turn_on","turn_off","brightness"]', '2024-10-22 14:30:00');

-- 사용자의 모든 기기 조회
SELECT * FROM devices WHERE user_id = 1;
```

| id  | user_id | device_id | device_name | device_type    | capabilities                             | last_synced         |
| --- | ------- | --------- | ----------- | -------------- | ---------------------------------------- | ------------------- |
| 1   | 1       | ac_001    | 거실 에어컨 | airconditioner | ["turn_on","turn_off","set_temperature"] | 2024-10-22 14:30:00 |
| 2   | 1       | light_01  | 거실 조명   | light          | ["turn_on","turn_off","brightness"]      | 2024-10-22 14:30:00 |

**capabilities JSON 형식:**
```json
{
  "ac_001": ["turn_on", "turn_off", "set_temperature", "set_mode"],
  "light_01": ["turn_on", "turn_off", "brightness", "color"],
  "door_01": ["open", "close", "lock", "unlock"]
}
```

**사용 사례:**
```python
# AI Server에서 기기 조회 후 동기화
devices = await ai_client.get_user_devices(user_id)
db.sync_devices(user_id, devices)
# → devices 테이블 INSERT OR REPLACE

# 로컬 기기 목록 조회 (오프라인 가능)
local_devices = db.get_user_devices(user_id)
# → SELECT * FROM devices WHERE user_id = ?
```

**오프라인 지원:**
```
┌─────────────────────────────────────────────┐
│ 시나리오: AI Server 다운                    │
├─────────────────────────────────────────────┤
│ 1. devices.py: get_devices() 호출           │
│ 2. ai_client: get_user_devices() 실패       │
│ 3. devices.py: 로컬 DB에서 조회             │
│ 4. db.get_user_devices() 호출               │
│ 5. ✅ 기기 목록 반환 (캐시된 데이터)        │
└─────────────────────────────────────────────┘
```

---

### 4. **login_history** - 로그인 이력

```sql
CREATE TABLE IF NOT EXISTS login_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

| 컬럼       | 타입      | 제약조건                  | 설명               |
| ---------- | --------- | ------------------------- | ------------------ |
| `id`       | INTEGER   | PK, AI                    | 로그인 기록 ID     |
| `user_id`  | INTEGER   | FK (users.id)             | 로그인한 사용자 ID |
| `login_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 로그인 시간        |

**데이터 예시:**

```sql
INSERT INTO login_history (user_id) VALUES (1);  -- alice 로그인
INSERT INTO login_history (user_id) VALUES (1);  -- alice 로그인
INSERT INTO login_history (user_id) VALUES (2);  -- bob 로그인
INSERT INTO login_history (user_id) VALUES (1);  -- alice 로그인

-- alice의 로그인 기록 조회
SELECT * FROM login_history 
WHERE user_id = 1 
ORDER BY login_at DESC;
```

| id  | user_id | login_at            |
| --- | ------- | ------------------- |
| 1   | 1       | 2024-10-22 09:00:00 |
| 2   | 1       | 2024-10-22 14:30:00 |
| 4   | 1       | 2024-10-23 08:30:00 |

**사용 사례:**
```python
# 로그인 기록
db.record_login("alice")
# → INSERT INTO login_history (user_id) VALUES (1)

# 사용자 통계 (로그인 횟수)
stats = db.get_user_stats("alice")
# → login_count = 3
```

---

## 🔗 Foreign Key 관계

### users ← calibrations
```sql
FOREIGN KEY (user_id) REFERENCES users(id)

설명:
- calibrations.user_id → users.id 참조
- 사용자 삭제 시 영향 (온캐스케이드 미설정)
- 데이터 무결성 보장
```

### users ← devices
```sql
FOREIGN KEY (user_id) REFERENCES users(id)

설명:
- devices.user_id → users.id 참조
- 사용자별 기기 격리
- 다중 사용자 지원
```

### users ← login_history
```sql
FOREIGN KEY (user_id) REFERENCES users(id)

설명:
- login_history.user_id → users.id 참조
- 사용자별 로그인 기록 추적
- 활동 분석 가능
```

---

## 🔍 쿼리 예시

### 1. 특정 사용자의 모든 데이터 조회

```sql
-- alice의 모든 정보 조회
SELECT 
    u.id,
    u.username,
    u.created_at,
    u.last_login,
    COUNT(DISTINCT c.id) as calibration_count,
    COUNT(DISTINCT d.id) as device_count,
    COUNT(DISTINCT l.id) as login_count
FROM users u
LEFT JOIN calibrations c ON u.id = c.user_id
LEFT JOIN devices d ON u.id = d.user_id
LEFT JOIN login_history l ON u.id = l.user_id
WHERE u.username = 'alice'
GROUP BY u.id;
```

**결과:**
| id  | username | created_at          | last_login          | calibration_count | device_count | login_count |
| --- | -------- | ------------------- | ------------------- | ----------------- | ------------ | ----------- |
| 1   | alice    | 2024-10-21 10:00:00 | 2024-10-22 14:30:00 | 2                 | 3            | 3           |

---

### 2. 최신 캘리브레이션 조회

```sql
SELECT * FROM calibrations
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 1;
```

---

### 3. 사용자별 로그인 통계

```sql
SELECT 
    u.username,
    COUNT(l.id) as login_count,
    MAX(l.login_at) as last_login,
    MIN(l.login_at) as first_login
FROM users u
LEFT JOIN login_history l ON u.id = l.user_id
GROUP BY u.id
ORDER BY login_count DESC;
```

---

### 4. 기기별 사용자 확인

```sql
SELECT 
    u.username,
    d.device_name,
    d.device_type,
    d.last_synced
FROM devices d
JOIN users u ON d.user_id = u.id
ORDER BY u.username, d.device_name;
```

---

## 📊 데이터베이스 크기 예상

### 저장 공간 계산

**기준:**
- username: ~20바이트
- device_name: ~30바이트
- calibration_file: ~30바이트
- capabilities (JSON): ~200바이트

**예상:**
```
사용자 100명
│
├─ users: 100 * 100 = 10KB
├─ calibrations: 100 * 200 * 50 = 1MB
├─ devices: 100 * 5 * 400 = 200KB
└─ login_history: 100 * 100 * 50 = 500KB

총 용량: ~2MB
```

**결론:** SQLite 데이터베이스는 매우 경량 ✅

---

## ⚙️ 데이터베이스 유지보수

### 백업

```bash
# 데이터베이스 백업
cp ~/.gazehome/calibrations/gazehome.db ~/.gazehome/calibrations/gazehome.db.backup

# 특정 날짜로 백업
cp ~/.gazehome/calibrations/gazehome.db ~/.gazehome/calibrations/gazehome.db.2024-10-22
```

### 복구

```bash
# 백업에서 복구
cp ~/.gazehome/calibrations/gazehome.db.backup ~/.gazehome/calibrations/gazehome.db
```

### 통계 확인

```sql
-- 테이블 크기 확인
SELECT 
    name,
    COUNT(*) as rows
FROM sqlite_master
WHERE type='table'
GROUP BY name;

-- 사용자 통계
SELECT COUNT(*) as total_users FROM users;

-- 캘리브레이션 통계
SELECT COUNT(*) as total_calibrations FROM calibrations;

-- 기기 통계
SELECT COUNT(*) as total_devices FROM devices;
```

---

## 🎯 요약

| 항목                  | 설명                                   |
| --------------------- | -------------------------------------- |
| **데이터베이스 위치** | `~/.gazehome/calibrations/gazehome.db` |
| **테이블 수**         | 4개                                    |
| **크기**              | ~2MB (100명 기준)                      |
| **외부 API 의존**     | ❌ 없음                                 |
| **AI Server 영향**    | ❌ 없음                                 |
| **스키마 변경 필요**  | ❌ 불필요                               |
| **백업 필요**         | ✅ 권장                                 |

---

## 📌 핵심 정리

```
GazeHome Edge Module Database
├─ 역할: 로컬 사용자, 캘리브레이션, 기기 정보 저장
├─ 유형: SQLite (파일 기반, 서버 불필요)
├─ 위치: ~/.gazehome/calibrations/gazehome.db
├─ 크기: 매우 경량 (~2MB)
├─ 영향도: AI Server 변경에 영향 없음 (100% 독립)
└─ 상태: 프로덕션 준비 완료 ✅
```
