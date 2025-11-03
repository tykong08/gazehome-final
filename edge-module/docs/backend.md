# GazeHome 스마트 홈 백엔드

시선 제어 스마트 홈 애플리케이션을 위한 FastAPI 기반 백엔드 서버입니다.

## 주요 기능

- **실시간 시선 추적**: 30-60 FPS로 시선 좌표를 WebSocket 스트리밍
- **웹 기반 캘리브레이션**: 브라우저에서 완전한 캘리브레이션 워크플로우 (5점 또는 9점)
- **디바이스 제어 API**: 스마트 홈 디바이스 제어를 위한 REST API
- **AI 추천**: 상황 인식 기반 디바이스 제어 제안
- **비동기 아키텍처**: 고성능을 위한 FastAPI 및 asyncio 기반
- **라즈베리 파이 지원**: 라즈베리 파이 배포에 최적화

## 아키텍처

```
backend/
├── api/
│   ├── main.py              # 라이프사이클 관리가 포함된 FastAPI 앱
│   ├── websocket.py         # 시선 스트리밍용 WebSocket 엔드포인트
│   ├── devices.py           # 디바이스 제어 REST API
│   ├── recommendations.py   # AI 추천 API
│   └── calibration.py       # 웹 기반 캘리브레이션 API
├── core/
│   ├── gaze_tracker.py      # 비동기 시선 추적 래퍼
│   └── config.py            # pydantic-settings를 사용한 설정 관리
└── integrations/            # 향후 스마트 홈 플랫폼 통합
```

## 설치

1. **백엔드 의존성 설치:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **eyetrax 패키지 설치** (아직 설치되지 않은 경우):
   ```bash
   cd ..
   pip install -e .
   ```

3. **환경 설정** (선택사항):
   backend 디렉토리에 `.env` 파일 생성:
   ```env
   HOST=0.0.0.0
   PORT=8000
   CAMERA_INDEX=0
   SCREEN_WIDTH=1920
   SCREEN_HEIGHT=1080
   HOME_ASSISTANT_URL=http://homeassistant.local:8123
   HOME_ASSISTANT_TOKEN=your_token_here
   ```

## 사용법

### 서버 시작

```bash
# backend 디렉토리에서
python run.py

# 또는 uvicorn으로 직접 실행
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

서버는 다음 주소에서 사용 가능합니다:
- **API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8000/ws/gaze

### API 엔드포인트

#### REST API

**상태 확인**
```bash
curl http://localhost:8000/health
```

**웹 캘리브레이션 시작**
```bash
curl -X POST http://localhost:8000/api/calibration/start \
  -H "Content-Type: application/json" \
  -d '{
    "method": "five_point",
    "screen_width": 1920,
    "screen_height": 1080
  }'
```

**캘리브레이션 파일 목록 가져오기**
```bash
curl http://localhost:8000/api/calibration/list
```

**모든 디바이스 가져오기**
```bash
curl http://localhost:8000/api/devices
```

**디바이스 제어**
```bash
curl -X POST http://localhost:8000/api/devices/ac_001/control \
  -H "Content-Type: application/json" \
  -d '{"action": "set_temperature", "params": {"temperature": 24}}'
```

**추천 정보 가져오기**
```bash
curl http://localhost:8000/api/recommendations
```

#### WebSocket

**시선 스트림에 연결** (JavaScript 예제):
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/gaze');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'gaze_update') {
    const [x, y] = data.gaze;
    console.log(`시선 위치: (${x}, ${y})`);
  }
};
```

**특징 스트림에 연결** (캘리브레이션용):
```javascript
const featuresWs = new WebSocket('ws://localhost:8000/ws/features');

featuresWs.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'features') {
    console.log('얼굴 감지됨:', data.has_face);
    console.log('특징점:', data.features);
  }
};
```

**제어 명령**:
```javascript
const controlWs = new WebSocket('ws://localhost:8000/ws/control');

// 캘리브레이션 로드
controlWs.send(JSON.stringify({
  command: 'load_calibration',
  file: '/path/to/calibration.pkl'
}));
```

## 디바이스 제어 동작

### 공통 동작
- `turn_on` - 디바이스 켜기
- `turn_off` - 디바이스 끄기
- `toggle` - 디바이스 상태 토글

### 디바이스별 동작

**에어컨 / 온도조절기**
- `set_temperature` - 목표 온도 설정
  ```json
  {"action": "set_temperature", "params": {"temperature": 24}}
  ```
- `set_mode` - 동작 모드 설정 (cool/heat/fan/dry)
  ```json
  {"action": "set_mode", "params": {"mode": "cool"}}
  ```
- `set_fan_speed` - 팬 속도 설정 (low/medium/high/auto)
  ```json
  {"action": "set_fan_speed", "params": {"fan_speed": "auto"}}
  ```

**조명**
- `set_brightness` - 밝기 설정 (0-100%)
  ```json
  {"action": "set_brightness", "params": {"brightness": 75}}
  ```

**공기청정기**
- `set_mode` - 청정기 모드 설정 (auto/sleep/turbo)
- `set_fan_speed` - 팬 속도 설정

## 캘리브레이션

### 웹 기반 캘리브레이션 (신규!)

이제 CLI 없이 브라우저에서 직접 캘리브레이션할 수 있습니다!

**참고:** 자세한 API 문서는 [CALIBRATION_API.md](CALIBRATION_API.md)를 확인하세요.

**빠른 시작:**
1. 백엔드 서버 시작
2. React 프론트엔드 열기 (곧 출시) 또는 API 직접 사용
3. 화면의 캘리브레이션 포인트 따라하기
4. 모델 자동 훈련 및 저장

### CLI 캘리브레이션 (기존 방식)

1. **캘리브레이션 생성** (기존 eyetrax CLI 사용):
   ```bash
   eyetrax calibrate --method five_point --user myuser
   ```

2. **캘리브레이션 파일 배치** `~/.eyetrax/calibrations/default.pkl`에

3. **또는 WebSocket으로 로드**:
   ```javascript
   ws.send(JSON.stringify({
     command: 'load_calibration',
     file: '~/.eyetrax/calibrations/myuser.pkl'
   }));
   ```

## 라즈베리 파이 배포

### 하드웨어 요구사항
- 라즈베리 파이 4 (권장) 또는 파이 3B+
- USB 웹캠 또는 파이 카메라 모듈
- 2GB+ RAM 권장

### 설정

1. **의존성 설치**:
   ```bash
   # 시스템 패키지
   sudo apt-get update
   sudo apt-get install -y python3-opencv libatlas-base-dev

   # Python 패키지
   pip install -r requirements.txt
   pip install -e ..
   ```

2. **카메라 설정**:
   - USB 카메라: 보통 `/dev/video0` (camera_index=0)
   - 파이 카메라: `raspi-config`에서 활성화, `libcamera` 또는 `picamera2` 사용

3. **시작 시 실행** (systemd 서비스):
   `/etc/systemd/system/eyetrax-backend.service` 생성:
   ```ini
   [Unit]
   Description=EyeTrax Smart Home Backend
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/eyetrax/backend
   ExecStart=/usr/bin/python3 run.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   활성화 및 시작:
   ```bash
   sudo systemctl enable eyetrax-backend
   sudo systemctl start eyetrax-backend
   ```

4. **다른 기기에서 접근**:
   - 파이 IP 찾기: `hostname -I`
   - API 접근: `http://192.168.1.X:8000`
   - 또는 mDNS 사용: `http://raspberrypi.local:8000`

## 스마트 홈 통합

### Home Assistant

1. **Home Assistant 프로필에서 장기 액세스 토큰 받기**

2. **`.env`에서 설정**:
   ```env
   HOME_ASSISTANT_URL=http://homeassistant.local:8123
   HOME_ASSISTANT_TOKEN=your_long_lived_token
   ```

3. **`backend/integrations/home_assistant.py`에서 통합 구현** (TODO)

## 개발

### 개발 모드에서 실행

```bash
# 파일 변경 시 자동 재로드
RELOAD=true python run.py
```

### API 문서

다음 주소에서 대화형 API 문서 제공:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 테스트

```bash
# 테스트 의존성 설치
pip install pytest httpx

# 테스트 실행 (TODO: 테스트 생성)
pytest
```

## 문제 해결

### 카메라를 찾을 수 없음
```bash
# 사용 가능한 카메라 목록
ls /dev/video*

# 카메라 테스트
python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL')"
```

### 시선 추적기가 캘리브레이션되지 않음
- 백엔드는 시작되지만 캘리브레이션이 로드될 때까지 시선 예측이 작동하지 않습니다
- 위의 "캘리브레이션" 섹션을 참조하세요

### WebSocket 연결 실패
- `config.py`의 CORS 설정 확인
- 프론트엔드 origin이 `cors_origins` 목록에 있는지 확인
- 라즈베리 파이의 방화벽/포트 포워딩 확인

### 라즈베리 파이에서 성능 문제
- `gaze_tracker.py`에서 프레임 속도 낮추기 (예: 60 FPS 대신 30 FPS)
- 더 작은 모델 사용 (예: "svr" 대신 "ridge")
- 카메라 해상도 줄이기

## 다음 단계

- [ ] ✅ 웹 기반 캘리브레이션 API (완료!)
- [ ] 캘리브레이션을 위한 React 프론트엔드
- [ ] Home Assistant 통합
- [ ] MQTT 통합
- [ ] 사용자 인증
- [ ] 디바이스 상태 지속성
- [ ] 실제 AI 추천 모델
- [ ] 로깅 및 모니터링
- [ ] 단위 테스트

## 라이선스

상위 EyeTrax 프로젝트와 동일합니다.

````

## Development

### Run in Development Mode

```bash
# Auto-reload on file changes
RELOAD=true python run.py
```

### API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Testing

```bash
# Install test dependencies
pip install pytest httpx

# Run tests (TODO: create tests)
pytest
```

## Troubleshooting

### Camera Not Found
```bash
# List available cameras
ls /dev/video*

# Test camera
python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL')"
```

### Gaze Tracker Not Calibrated
- Backend will start but gaze predictions won't work until calibration is loaded
- See "Calibration" section above

### WebSocket Connection Failed
- Check CORS settings in `config.py`
- Ensure frontend origin is in `cors_origins` list
- Check firewall/port forwarding on Raspberry Pi

### Performance Issues on Raspberry Pi
- Lower frame rate in `gaze_tracker.py` (e.g., 30 FPS instead of 60)
- Use smaller model (e.g., "ridge" instead of "svr")
- Reduce camera resolution

## Next Steps

- [ ] ✅ Web-based calibration API (COMPLETED!)
- [ ] React frontend for calibration
- [ ] Home Assistant integration
- [ ] User authentication
- [ ] Device state persistence
- [ ] Real AI recommendation model
- [ ] Logging and monitoring
- [ ] Unit tests

## License

Same as parent EyeTrax project.
