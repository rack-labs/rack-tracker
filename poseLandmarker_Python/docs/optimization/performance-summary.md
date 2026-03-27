# Performance Summary

## 결론

성능 결론부터 말하면, 정확도는 충분히 실사용 가능하고 병목은 사실상 inference 하나입니다. GPU를 요청했지만 실제로는 CPU로 폴백되고 있어, 현재 파이프라인은 구조적으로 성능을 낭비하고 있습니다.

한 줄 평가:

AI는 잘 추론하고 있는데, CPU에서 혼자 헬스하고 있음.

## 현재 측정 결과

- 총 처리 시간: 10.65초
- 총 프레임 수: 320
- 입력 영상 추정 FPS: 약 30fps
- 실제 처리 속도: `320 / 10.65 = 약 30fps`

해석:

입력 속도와 거의 같은 처리량이 나오므로 현재 상태는 실시간 처리 경계선 수준입니다. 단일 영상에서는 버틸 수 있지만, 길이가 늘어나거나 동시 요청이 붙으면 바로 병목이 드러납니다.

## 구간별 성능 해석

### 1. Inference

- 총 7,964ms
- 전체의 74.76%
- 평균 24.88ms / frame
- p95 35.56ms

해석:

CPU 기반 MediaPipe `full` 모델 기준으로는 크게 이상한 수치가 아닙니다. 문제는 이 구간이 전체 성능을 거의 다 잡아먹고 있다는 점입니다. 현재 성능 최적화의 핵심은 inference이며, 다른 구간을 건드려도 체감 개선은 거의 없습니다.

### 2. Frame Extraction

- 508ms
- 전체의 4.7%

해석:

정상 범위입니다. 지금 우선순위가 아닙니다.

### 3. RGB Conversion

- 171ms
- 전체의 1.6%

해석:

최적화 의미가 거의 없습니다.

### 4. Serialization

- 50ms
- 전체의 0.4%

해석:

무시 가능한 수준입니다.

### 5. Analysis

- 0.1ms

해석:

사실상 비용이 없습니다.

## 정확도 / 품질 평가

- `poseDetectedRatio = 1.0`
- `detectedFrameCount = 320`
- `avgVisibility = 0.98`
- `minVisibility = 0.80`
- `lowVisibilityFrameRatio = 0`
- `consecutiveMissedPoseMax = 0`

해석:

- 전 프레임 100% 검출
- 평균 visibility가 매우 높음
- 낮은 품질 프레임 없음
- 연속 miss 없음
- 추적 안정성 매우 높음

결론:

현재 데이터 품질은 production-grade로 판단할 수 있습니다. 정확도 측면에서 급한 문제는 보이지 않습니다.

## 가장 중요한 문제

벤치마크 메타데이터:

- `requestedDelegate: GPU`
- `actualDelegate: CPU`
- `delegateFallbackApplied: true`

이건 단순 성능 저하가 아니라 구성 실패입니다.

애플리케이션은 GPU를 요청했지만 실제 환경에서는 GPU delegate 초기화에 실패했고, 코드가 자동으로 CPU fallback을 적용했습니다. 로컬 재현 결과 MediaPipe GPU 초기화는 아래 오류로 실패했습니다.

```text
ImageCloneCalculator: GPU processing is disabled in build flags
```

해석:

현재 설치된 MediaPipe Python 빌드는 GPU delegate enum을 노출하지만, 실제 GPU 처리 경로는 비활성화된 상태입니다. 따라서 Windows + 현재 Python 패키지 조합에서는 GPU 사용을 기대하기 어렵습니다.

## 비즈니스 관점 평가

현재 상태:

- 정확도: 매우 높음
- 속도: borderline real-time
- 확장성: 낮음

문제 시나리오:

- 10초 영상: 처리 가능
- 1분 영상: 60초 안팎 처리 필요
- 동시 요청 10개: inference 병목이 빠르게 누적

즉, 단건 데모나 제한된 사용량에서는 충분하지만, 다중 요청이나 긴 영상 처리에서는 현재 구조가 빠르게 한계에 도달합니다.

## 개선 우선순위

### 1순위: GPU delegate 정상 적용

예상 효과:

- 체감상 가장 큰 개선 포인트
- inference `25ms/frame` 수준에서 `5~8ms/frame` 수준까지 내려갈 가능성 기대

단, 현재 Windows + `mediapipe` Python 패키지 기준으로는 GPU 지원이 사실상 제한적입니다. 현실적인 방향은 아래 둘 중 하나입니다.

- Ubuntu 기반 GPU 지원 환경으로 이전
- MediaPipe Python 대신 다른 GPU 추론 스택으로 교체

### 2순위: 모델 전략 분리

현재는 `modelVariant: full` 고정에 가깝습니다. 목적별로 모델을 나눠야 합니다.

- MVP / 실시간 우선: `lite`
- 정밀 분석 / 오프라인 품질 우선: `full`

필요하면 `heavy`는 별도 오프라인 분석 전용으로만 검토하는 편이 낫습니다.

### 3순위: Sampling 간격 조정

현재 `samplingIntervalMs = 10ms`는 과도합니다.

- 33ms로 조정하면 30fps 수준
- 50ms로 조정하면 연산량이 즉시 더 줄어듦

정확도 요구사항이 유지되는 범위 안에서 샘플링만 조절해도 처리 비용은 바로 감소합니다. GPU 적용 전에 해도 효과가 있습니다.

### 4순위: 워커 분리 및 병렬 처리

API 서버와 추론 워커를 분리하는 방향이 필요합니다.

- `FastAPI`는 요청 수신만 담당
- 추론은 별도 worker process에서 수행
- 필요 시 queue 기반 비동기 처리

이 단계는 단일 요청 속도 개선보다는 동시성 대응과 안정성 확보 측면에서 중요합니다.

## 최종 정리

현재 상태는 정확도는 이미 충분하고, 성능은 구조적으로 낭비 중입니다.

핵심 액션:

1. GPU delegate 문제를 먼저 해결하거나, GPU가 가능한 다른 추론 스택으로 전환
2. 그 다음 sampling 전략 조정
3. 이후 모델 분리와 worker 구조로 확장성 확보

현재 병목은 사실상 100% inference이며, 나머지 구간 최적화는 우선순위가 낮습니다.
