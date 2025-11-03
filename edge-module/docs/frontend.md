# GazeHome Smart Home Frontend

React + Vite 기반 시선 추적 스마트홈 프론트엔드

## 🌟 기능

### ✅ 구현된 기능

- **온보딩 페이지** - 로그인 UI
- **시선 보정** - 웹 기반 5포인트 보정
- **홈 대시보드** - 기기 목록 및 제어
- **실시간 시선 추적** - WebSocket 기반 시선 커서
- **시선 제어** - 2초 hovering으로 기기 토글
- **AI 추천 모달** - 팝업으로 추천 표시

## 📁 프로젝트 구조

```
frontend/
├── src/
│   ├── components/
│   │   ├── GazeCursor.jsx           # 시선 커서
│   │   ├── DeviceCard.jsx           # 기기 카드
│   │   └── RecommendationModal.jsx  # AI 추천 모달
│   ├── pages/
│   │   ├── OnboardingPage.jsx       # 온보딩/로그인
│   │   ├── CalibrationPage.jsx      # 시선 보정
│   │   └── HomePage.jsx             # 메인 홈
│   ├── styles/
│   │   └── global.css               # 글로벌 스타일
│   ├── App.jsx                      # 라우팅
│   └── main.jsx                     # 엔트리포인트
├── public/                          # 정적 파일
├── package.json
├── vite.config.js
└── index.html
```

## 🚀 시작하기

### 1. 의존성 설치

```bash
cd frontend
npm install
```

### 2. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 http://localhost:3000 접속

### 3. 백엔드 서버 실행 (필수)

프론트엔드는 백엔드 API에 의존하므로 반드시 백엔드를 먼저 실행해야 합니다:

```bash
# 다른 터미널에서
cd ../backend
python run.py
```

## 📱 페이지 플로우

### 1. 온보딩 페이지 (`/`)

- 사용자 이름 입력
- "시작하기" 버튼 클릭
- 로그인 상태를 localStorage에 저장

### 2. 보정 페이지 (`/calibration`)

- 첫 로그인 시 자동으로 리다이렉트
- 5포인트 시선 보정 수행
- 각 포인트마다 2-3초 응시
- 완료 후 자동으로 홈으로 이동

**보정 과정:**
1. "보정 시작" 버튼 클릭
2. WebSocket으로 실시간 얼굴 인식
3. 화면에 표시되는 5개 점을 순서대로 응시
4. 각 점마다 25개 샘플 수집
5. 모델 학습 및 저장
6. 홈으로 자동 이동

### 3. 홈 페이지 (`/home`)

- 시선 커서 실시간 표시 (빨간 원)
- 기기 목록 그리드 표시
- 시선으로 기기 제어 (2초 hovering)
- 마우스 클릭으로도 제어 가능
- 30초마다 AI 추천 모달 자동 표시

## 🎮 시선 제어 방법

### Dwell Time 방식

기기 카드를 **2초 동안 응시**하면 자동으로 ON/OFF 토글됩니다.

**시각적 피드백:**
- 카드 테두리가 파란색으로 변경
- 진행 바가 채워짐
- "2초간 응시하여 토글" 메시지 표시
- 2초 완료 시 자동으로 기기 토글

### 마우스 제어

시선 제어가 불편한 경우 각 카드의 "켜기/끄기" 버튼을 클릭할 수 있습니다.

## 🎨 UI 디자인

### 디자인 시스템

- **색상:** CSS 변수로 관리 (`:root`)
- **타이포그래피:** 시스템 폰트 + 나눔고딕
- **간격:** 8px 그리드 시스템
- **애니메이션:** Framer Motion

### 주요 색상

```css
--primary: #667eea    /* 메인 보라색 */
--secondary: #764ba2  /* 보조 보라색 */
--success: #10b981    /* 성공 (녹색) */
--warning: #f59e0b    /* 경고 (주황색) */
--danger: #ef4444     /* 위험 (빨강) */
```

### 반응형

- 모바일: < 640px
- 태블릿: 640px - 1024px
- 데스크톱: > 1024px

## 🔌 API 연동

### REST API

```javascript
// 기기 목록
GET /api/devices

// 기기 제어
POST /api/devices/{device_id}/control
{
  "action": "toggle",
  "params": {}
}

// AI 추천
GET /api/recommendations
```

### WebSocket

```javascript
// 시선 스트리밍
WS /ws/gaze
→ { type: "gaze_update", gaze: [x, y], ... }

// 보정용 특징 스트리밍
WS /ws/features
→ { type: "features", has_face: true, features: [...] }
```

## 🎯 컴포넌트 상세

### GazeCursor

시선 위치를 나타내는 빨간 원 커서

**Props:**
- `x`: 시선 X 좌표
- `y`: 시선 Y 좌표
- `visible`: 표시 여부

**애니메이션:**
- Spring 애니메이션으로 부드러운 이동
- 펄스 효과로 시각적 피드백

### DeviceCard

개별 기기를 나타내는 카드

**Props:**
- `device`: 기기 정보
- `onControl`: 제어 콜백

**기능:**
- 시선 hovering 감지 (dwell time)
- 진행 상황 표시 (progress ring)
- 기기 메타데이터 표시 (온도, 밝기 등)
- 마우스 클릭 지원

### RecommendationModal

AI 추천을 표시하는 모달

**Props:**
- `recommendations`: 추천 목록
- `onAccept`: 추천 수락 콜백
- `onClose`: 닫기 콜백

**기능:**
- 우선순위별 색상 구분
- 주요 추천 강조 표시
- 추가 추천 목록 (최대 3개)
- 클릭으로 즉시 적용

## 🔧 개발 팁

### Vite 프록시 설정

`vite.config.js`에서 백엔드 프록시가 자동 설정됩니다:

```javascript
proxy: {
  '/api': 'http://localhost:8000',
  '/ws': { target: 'ws://localhost:8000', ws: true }
}
```

### 상태 관리

현재는 React 내장 상태 관리 사용:
- `useState` - 로컬 상태
- `useEffect` - 사이드 이펙트
- `localStorage` - 로그인 상태 persist

필요시 Redux, Zustand 등 추가 가능

### Hot Reload

Vite의 HMR(Hot Module Replacement)로 빠른 개발:
- 파일 저장 시 자동 새로고침
- 상태 유지
- 빠른 피드백

## 📦 빌드

### 프로덕션 빌드

```bash
npm run build
```

빌드 결과: `dist/` 디렉토리

### 빌드 미리보기

```bash
npm run preview
```

## 🚢 배포

### 정적 호스팅

빌드된 `dist/` 폴더를 다음 플랫폼에 배포 가능:
- Vercel
- Netlify
- GitHub Pages
- Cloudflare Pages

### Nginx 설정 예제

```nginx
server {
  listen 80;
  server_name example.com;
  
  root /path/to/dist;
  index index.html;
  
  # React Router SPA
  location / {
    try_files $uri $uri/ /index.html;
  }
  
  # API 프록시
  location /api {
    proxy_pass http://localhost:8000;
  }
  
  # WebSocket 프록시
  location /ws {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }
}
```

## 🐛 문제 해결

### 시선 커서가 보이지 않음

1. 백엔드 서버가 실행 중인지 확인
2. WebSocket 연결 상태 확인 (헤더의 연결 상태 표시)
3. 브라우저 콘솔에서 에러 확인

### 보정이 실패함

1. 카메라 권한 허용 확인
2. 얼굴이 화면에 잘 보이는지 확인
3. 조명 상태 확인
4. 백엔드 로그 확인

### 기기가 제어되지 않음

1. 백엔드 API 응답 확인
2. 네트워크 탭에서 요청/응답 확인
3. CORS 에러 확인

## 🔮 향후 개선

- [ ] TypeScript 마이그레이션
- [ ] 상태 관리 라이브러리 (Zustand)
- [ ] 단위 테스트 (Vitest)
- [ ] E2E 테스트 (Playwright)
- [ ] PWA 지원
- [ ] 다크 모드
- [ ] 다국어 지원 (i18n)
- [ ] 접근성 개선 (a11y)
- [ ] 성능 최적화 (lazy loading)

## 📝 라이선스

상위 EyeTrax 프로젝트와 동일
