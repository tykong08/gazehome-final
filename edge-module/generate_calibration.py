#!/usr/bin/env python3
"""
7인치 화면(800x480)용 보정 파일 생성 도구
9-point calibration 모의 데이터 생성
"""

import pickle
import numpy as np
from pathlib import Path
from model.models import create_model
from backend.core.config import settings


def generate_synthetic_calibration():
    """
    합성 보정 데이터 생성 (실제 눈 추적 없이)
    9개 포인트: 좌상, 상중, 우상, 좌중, 중중, 우중, 좌하, 하중, 우하
    """
    
    # 7인치 화면 해상도 (800x480)
    screen_w, screen_h = 800, 480
    
    # 9-point 캘리브레이션 화면 좌표
    calibration_points = [
        # (x, y)
        (100, 60),      # 좌상
        (400, 60),      # 상중
        (700, 60),      # 우상
        (100, 240),     # 좌중
        (400, 240),     # 중중
        (700, 240),     # 우중
        (100, 420),     # 좌하
        (400, 420),     # 하중
        (700, 420),     # 우하
    ]
    
    # 수집할 eye features (실제 환경에서는 WebGazeTracker가 생성)
    # face_features: [face_x, face_y, face_width, face_height]
    # gaze_features: [left_eye_x, left_eye_y, right_eye_x, right_eye_y,
    #                 left_iris_x, left_iris_y, right_iris_x, right_iris_y]
    # 총 12개 feature
    
    X_train = []  # eye features
    y_train = []  # screen coordinates
    
    np.random.seed(42)  # 재현성
    
    # 각 포인트당 샘플 생성 (시뮬레이션)
    samples_per_point = 30  # 각 포인트 30샘플 = 총 270샘플
    
    for screen_x, screen_y in calibration_points:
        for _ in range(samples_per_point):
            # 얼굴 위치 (카메라 프레임 중심 근처)
            face_x = 320 + np.random.normal(0, 10)
            face_y = 240 + np.random.normal(0, 10)
            face_w = 200 + np.random.normal(0, 5)
            face_h = 150 + np.random.normal(0, 5)
            
            # 눈 위치 (정규화: 0-1 범위)
            left_eye_x = 0.35 + np.random.normal(0, 0.02)
            left_eye_y = 0.45 + np.random.normal(0, 0.02)
            right_eye_x = 0.65 + np.random.normal(0, 0.02)
            right_eye_y = 0.45 + np.random.normal(0, 0.02)
            
            # 홍채 위치 (정규화)
            left_iris_x = 0.35 + np.random.normal(0, 0.02)
            left_iris_y = 0.45 + np.random.normal(0, 0.02)
            right_iris_x = 0.65 + np.random.normal(0, 0.02)
            right_iris_y = 0.45 + np.random.normal(0, 0.02)
            
            # 선형 맵핑 추가 (화면 좌표와의 상관성)
            # 실제 눈 위치 → 화면 좌표의 간단한 선형 관계
            normalized_x = screen_x / screen_w  # 0-1
            normalized_y = screen_y / screen_h  # 0-1
            
            left_eye_x += normalized_x * 0.05 - 0.025
            left_eye_y += normalized_y * 0.05 - 0.025
            right_eye_x += normalized_x * 0.05 - 0.025
            right_eye_y += normalized_y * 0.05 - 0.025
            left_iris_x += normalized_x * 0.05 - 0.025
            left_iris_y += normalized_y * 0.05 - 0.025
            right_iris_x += normalized_x * 0.05 - 0.025
            right_iris_y += normalized_y * 0.05 - 0.025
            
            # feature 12개: [face_x, face_y, face_w, face_h, 
            #               left_eye_x, left_eye_y, right_eye_x, right_eye_y,
            #               left_iris_x, left_iris_y, right_iris_x, right_iris_y]
            features = np.array([
                face_x, face_y, face_w, face_h,
                left_eye_x, left_eye_y, right_eye_x, right_eye_y,
                left_iris_x, left_iris_y, right_iris_x, right_iris_y
            ], dtype=np.float32)
            
            X_train.append(features)
            y_train.append([screen_x, screen_y])
    
    X_train = np.array(X_train, dtype=np.float32)
    y_train = np.array(y_train, dtype=np.float32)
    
    print(f"✅ 합성 데이터 생성 완료")
    print(f"   - 샘플 수: {len(X_train)}")
    print(f"   - Feature 차원: {X_train.shape[1]}")
    print(f"   - 타겟 차원: {y_train.shape[1]}")
    
    return X_train, y_train, calibration_points


def train_and_save_model(X_train, y_train, calibration_points):
    """
    Ridge 모델 학습 및 저장
    """
    
    print(f"\n📊 Ridge 모델 학습 중...")
    
    # Ridge 모델 생성 및 학습
    model = create_model("ridge")
    model.fit(X_train, y_train)
    
    print(f"✅ 모델 학습 완료")
    print(f"   - 모델: Ridge Regression")
    print(f"   - Alpha: {model.model.alpha}")
    
    # 보정 디렉토리 생성
    calibration_dir = settings.calibration_dir
    calibration_dir.mkdir(parents=True, exist_ok=True)
    
    # 보정 파일 저장 (사용자명: demo_user)
    calibration_file = calibration_dir / "demo_user.pkl"
    
    # 메타데이터 포함
    calibration_data = {
        "model": model,
        "model_name": "ridge",
        "screen_size": (800, 480),
        "calibration_points": calibration_points,
        "num_samples": len(X_train),
        "feature_dim": X_train.shape[1],
    }
    
    with open(calibration_file, "wb") as f:
        pickle.dump(calibration_data, f)
    
    print(f"\n💾 보정 파일 저장 완료")
    print(f"   - 경로: {calibration_file}")
    print(f"   - 화면 크기: 800x480 (7인치)")
    print(f"   - 보정 포인트: 9개")
    print(f"   - 샘플 수: {calibration_data['num_samples']}")
    
    return calibration_file


def test_model(model_data, X_train, y_train):
    """
    모델 성능 테스트
    """
    
    print(f"\n🧪 모델 성능 테스트")
    
    model = model_data["model"]
    predictions = model.predict(X_train)
    
    # 오차 계산
    errors = np.linalg.norm(predictions - y_train, axis=1)
    
    print(f"   - 평균 오차(pixels): {np.mean(errors):.2f}")
    print(f"   - 중앙값 오차(pixels): {np.median(errors):.2f}")
    print(f"   - 최대 오차(pixels): {np.max(errors):.2f}")
    print(f"   - 표준편차(pixels): {np.std(errors):.2f}")
    
    # 실제 vs 예측 샘플 출력
    print(f"\n📍 샘플 예측 결과 (첫 5개):")
    for i in range(min(5, len(X_train))):
        actual = y_train[i]
        predicted = predictions[i]
        error = errors[i]
        print(f"   [{i}] 실제: ({actual[0]:.0f}, {actual[1]:.0f}) → "
              f"예측: ({predicted[0]:.0f}, {predicted[1]:.0f}) | 오차: {error:.2f}px")


if __name__ == "__main__":
    print("=" * 60)
    print("🎯 7인치 화면(800x480) 보정 파일 생성")
    print("=" * 60)
    
    # 1. 합성 데이터 생성
    X_train, y_train, calibration_points = generate_synthetic_calibration()
    
    # 2. 모델 학습 및 저장
    calibration_file = train_and_save_model(X_train, y_train, calibration_points)
    
    # 3. 보정 파일 로드 및 테스트
    print(f"\n🔄 보정 파일 로드 중...")
    with open(calibration_file, "rb") as f:
        model_data = pickle.load(f)
    
    print(f"✅ 보정 파일 로드 완료")
    print(f"   - 화면 크기: {model_data['screen_size']}")
    print(f"   - 모델: {model_data['model_name']}")
    
    # 4. 성능 테스트
    test_model(model_data, X_train, y_train)
    
    print(f"\n" + "=" * 60)
    print(f"✨ 보정 파일 생성 완료!")
    print(f"   다음 실행 시 자동으로 로드됩니다.")
    print(f"=" * 60)
