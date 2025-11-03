# 보정 실패 문제 해결 가이드

## 🐛 문제 증상

```
AttributeError: 'DummyCalibrationModel' object has no attribute 'train'
```

라즈베리파이에서 보정 진행 시 위 오류가 발생하며 보정이 실패합니다.

## 🔍 근본 원인 분석

### 1. DummyCalibrationModel의 문제
`backend/core/dummy_calibration.py`에 정의된 `DummyCalibrationModel` 클래스는:
- **목적**: 테스트/데모용으로 실제 보정 없이 더미 모델 생성
- **문제**: `train()` 메서드가 없어서 실제 보정 진행 불가능
- **영향**: `default.pkl` 파일이 DummyCalibrationModel로 저장되면 보정 시 에러 발생

### 2. 왜 Dummy 모델이 사용되었나?

#### 파일 경로 문제 (X)
- Vite 경로 설정과는 **무관**합니다
- 백엔드 FastAPI는 프론트엔드 빌드와 별개로 동작
- 보정 파일 경로: `~/.gazehome/calibrations/default.pkl` (절대 경로)

#### 테스트 데이터 자동 생성 (O)
```python
# scripts/create_test_data.py (삭제됨)
def create_dummy_calibration_data():
    """더미 보정 데이터 생성"""
    from backend.core.dummy_calibration import create_dummy_calibration
    create_dummy_calibration()
```

이 스크립트가 실행되어 DummyCalibrationModel이 `default.pkl`로 저장되었습니다.

### 3. 실제 보정 모델 vs Dummy 모델

| 구분      | 실제 모델 (BaseModel)       | Dummy 모델                          |
| --------- | --------------------------- | ----------------------------------- |
| 클래스    | `RidgeModel`, `SVRModel` 등 | `DummyCalibrationModel`             |
| train()   | ✅ 있음                      | ❌ 없음                              |
| predict() | ✅ 학습 기반 예측            | ✅ 더미 예측 (화면 중앙)             |
| 용도      | 프로덕션                    | 테스트/데모                         |
| 파일 위치 | `model/models/`             | `backend/core/dummy_calibration.py` |

## ✅ 해결 방법

### 1. Dummy 관련 파일 삭제 ✅
```bash
# Mac/라즈베리파이 둘 다 실행
rm backend/core/dummy_calibration.py
rm scripts/create_test_data.py
```

### 2. 백엔드 로직 수정 ✅
**파일**: `backend/api/main.py`

**변경 전**:
```python
# ⭐ 더미 보정 파일 자동 로드
default_calibration = config_settings.calibration_dir / "default.pkl"
if default_calibration.exists():
    gaze_tracker.load_calibration(str(default_calibration))
    logger.info(f"[Backend] ✅ 더미 보정 로드됨: {default_calibration}")
```

**변경 후**:
```python
# ⭐ 실제 보정 파일 로드 (있을 경우만)
default_calibration = config_settings.calibration_dir / "default.pkl"
if default_calibration.exists():
    gaze_tracker.load_calibration(str(default_calibration))
    logger.info(f"[Backend] ✅ 보정 파일 로드됨: {default_calibration}")
else:
    logger.info("[Backend] ℹ️  보정 파일이 없습니다. 신규 보정이 필요합니다.")
```

### 3. OnboardingPage 5초 대기 추가 ✅
**파일**: `frontend/src/pages/OnboardingPage.jsx`

```jsx
useEffect(() => {
    const autoLogin = async () => {
        const startTime = Date.now()
        
        setLoginMessage('사용자 인증 중...')
        await new Promise(resolve => setTimeout(resolve, 1000))

        setLoginMessage('시선 추적 시스템 준비 중...')
        await new Promise(resolve => setTimeout(resolve, 1500))
        
        setLoginMessage('기기 연결 확인 중...')
        await new Promise(resolve => setTimeout(resolve, 1500))

        // 최소 5초 보장
        const elapsed = Date.now() - startTime
        const remaining = Math.max(0, 5000 - elapsed)
        if (remaining > 0) {
            setLoginMessage('시스템 준비 완료...')
            await new Promise(resolve => setTimeout(resolve, remaining))
        }

        await onLogin()
    }
    autoLogin()
}, [onLogin])
```

### 4. CalibrationPage 자동 시작 ✅
**파일**: `frontend/src/pages/CalibrationPage.jsx`

**추가된 로직**:
```jsx
// 자동 보정 시작 (페이지 로드 후 3초 뒤)
useEffect(() => {
    if (status === 'init') {
        setMessage('보정을 자동으로 시작합니다...')
        const timer = setTimeout(() => {
            console.log('[CalibrationPage] 자동 보정 시작')
            startCalibration()
        }, 3000)
        return () => clearTimeout(timer)
    }
}, [status])
```

**UI 변경**:
- "보정 시작" 버튼 제거
- 자동 시작 메시지 및 로딩 스피너 표시

## 🚀 라즈베리파이 적용 방법

### 1. 기존 보정 파일 삭제
```bash
# 손상된 Dummy 모델 제거
rm ~/.gazehome/calibrations/default.pkl
rm ~/.gazehome/calibrations/gazehome.db  # (선택사항)
```

### 2. Git Pull 및 재시작
```bash
cd ~/edge-module
git pull origin develop

# 프론트엔드 재빌드
cd frontend
npm run build

# 백엔드 재시작
cd ..
python backend/run.py
```

### 3. 보정 진행
1. 브라우저에서 `http://localhost:3000` 접속
2. OnboardingPage에서 5초 대기 (자동 로그인)
3. 보정 파일이 없으면 → CalibrationPage로 자동 이동
4. 3초 후 자동으로 보정 시작
5. 9개 포인트 응시 완료
6. 보정 완료 후 → HomePage로 이동

## 📊 플로우 차트

```
시작
  ↓
OnboardingPage (5초 대기)
  ↓
보정 파일 확인
  ↓
├─ 있음 → HomePage (시선 추적 시작)
└─ 없음 → CalibrationPage
           ↓
      3초 후 자동 시작
           ↓
      9포인트 보정 진행
           ↓
      실제 모델 학습 (Ridge/SVR 등)
           ↓
      default.pkl 저장
           ↓
      HomePage로 이동
```

## 🔧 기술적 세부사항

### 보정 모델 생성 과정

1. **특징 추출** (GazeEstimator.extract_features)
   - MediaPipe로 얼굴 특징점 감지
   - 눈 영역 특징점 정규화
   - 특징 벡터 생성 (12차원)

2. **모델 학습** (GazeEstimator.train → BaseModel.train)
   ```python
   # model/models/ridge.py
   class RidgeModel(BaseModel):
       def train(self, X, y):
           """Ridge 회귀 학습"""
           self.model = Ridge(alpha=1.0)
           self.model.fit(X, y)
   ```

3. **모델 저장** (BaseModel.save)
   ```python
   def save(self, path):
       """전체 모델 객체를 pickle로 저장"""
       with open(path, 'wb') as f:
           pickle.dump(self, f)
   ```

### DummyCalibrationModel이 문제가 되는 이유

```python
# ❌ DummyCalibrationModel (삭제됨)
class DummyCalibrationModel:
    def __init__(self):
        self.coef_ = np.random.randn(2, 12) * 0.01
        self.intercept_ = np.array([400.0, 240.0])
    
    def predict(self, X):
        return X @ self.coef_.T + self.intercept_
    
    # ❌ train() 메서드 없음!
```

보정 진행 시 `gaze_tracker.gaze_estimator.train()`를 호출하는데,
DummyCalibrationModel에는 `train()` 메서드가 없어서 AttributeError 발생!

## ✅ 검증 방법

### 1. 로그 확인
```bash
# 백엔드 실행 로그
[Backend] ℹ️  보정 파일이 없습니다. 신규 보정이 필요합니다.
[CalibrationPage] 자동 보정 시작
[Calibration] 세션 calib_xxx: 훈련 성공
[Backend] ✅ 보정 파일 로드됨: /home/gaze/.gazehome/calibrations/default.pkl
```

### 2. 파일 확인
```bash
ls -lh ~/.gazehome/calibrations/default.pkl
# -rw-r--r-- 1 gaze gaze 1.2K ... default.pkl

# 모델 타입 확인
python3 << EOF
import pickle
with open('/home/gaze/.gazehome/calibrations/default.pkl', 'rb') as f:
    model = pickle.load(f)
    print(f"Model type: {type(model)}")
    print(f"Has train: {hasattr(model, 'train')}")
EOF
```

**올바른 출력**:
```
Model type: <class 'model.models.ridge.RidgeModel'>
Has train: True
```

## 📝 요약

| 항목     | 내용                                             |
| -------- | ------------------------------------------------ |
| **문제** | DummyCalibrationModel에 train() 메서드 없음      |
| **원인** | 테스트 스크립트가 더미 모델을 default.pkl로 저장 |
| **해결** | 더미 파일 삭제 + 실제 보정 진행                  |
| **개선** | 온보딩 5초 대기, 보정 자동 시작                  |
| **결과** | 실제 Ridge/SVR 모델로 정상 보정 가능             |

---

**작성일**: 2025년 10월 29일  
**작성자**: GitHub Copilot  
**버전**: 1.0
