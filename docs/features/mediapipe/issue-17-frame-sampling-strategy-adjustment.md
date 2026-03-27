[fix] MediaPipe 프레임 샘플링 전략 조정

브랜치명: `fix/17-frame-sampling-strategy-adjustment`

## 작업 목적
현재 MediaPipe 백엔드의 프레임 추출/추론 경로에서 샘플링 밀도가 실제 운동 분석 목적에 비해 과도하게 높게 잡히는 사례가 있다. 특히 benchmark 기준 `sampleIntervalMs = 10`이면 초당 100프레임 처리를 시도하는 셈인데, 일반적인 30 FPS 영상에 대해서는 존재하지도 않는 장면 변화를 더 촘촘하게 추적하려는 구성이 된다. 이 작업의 목적은 기본 샘플링을 실제 영상 FPS에 맞추고, 사용자가 더 낮은 분석 FPS를 원할 때만 명시적으로 줄일 수 있게 해, 정확도 손실 없이 불필요한 추론 연산을 제거하는 것이다.

## 문제 정의
- 현재 benchmark 결과에서 `sampleIntervalMs = 10ms`가 반복적으로 기록되고 있다.
- `10ms` 간격은 `1000 / 10 = 100 FPS`에 해당한다.
- 일반적인 입력 영상은 대체로 `30 FPS` 수준이며, 프레임 간 간격은 약 `33ms`다.
- 이 상태에서는 실제로 존재하지 않는 추가 장면 정보를 얻는 것이 아니라, 유사한 프레임을 과도하게 많이 처리하게 된다.
- 결과적으로 pose inference 호출 수가 필요 이상으로 증가하고, CPU/GPU 연산이 낭비된다.

## 현재 추정 원인
- `poseLandmarker_Python/service/job_manager.py`에서 프레임 추출 옵션 생성 시 `sampling_mode="target_fps"`와 `target_fps=fps`를 사용한다.
- 이때 `fps`가 실제 소스 영상 FPS와 다른 의미로 사용되거나, 분석 목적에 비해 과도하게 높은 값으로 전달되면 추출 단계 전체가 그대로 고밀도 샘플링으로 고정된다.
- benchmark의 `sampleIntervalMs`는 `target_fps`를 기준으로 계산되므로, 현재 10ms 기록은 실질적으로 100 FPS 분석 구성이 적용되고 있음을 의미한다.
- 현재 API와 문서에서 `fps`가 실제 영상 FPS인지, 사용자가 요청한 분석용 샘플링 FPS인지 구분이 명확하지 않다.

## 작업 내용
- 프레임 샘플링 기본값을 실제 소스 영상 FPS로 사용하도록 조정한다.
- 사용자가 분석 FPS를 직접 낮추고 싶을 때만 별도 샘플링 값을 입력할 수 있게 한다.
- 사용자가 입력한 분석 FPS가 실제 영상 FPS보다 높으면, 실제 영상 FPS를 상한으로 사용하도록 clamp 정책을 적용한다.
- 실제 소스 FPS, 요청 메타데이터 FPS, 분석용 target FPS의 책임 경계를 정리한다.
- API 필드와 문서에서 실제 영상 FPS와 분석용 샘플링 FPS를 혼동하지 않도록 명명과 설명을 정리한다.
- benchmark에 기록되는 `sampleIntervalMs`가 기대한 샘플링 정책과 일치하는지 검증한다.

## 기대 효과
- 현재 약 `320 frame / 68초` 수준의 처리량이 `100~110 frame` 수준으로 줄어들 가능성이 있다.
- pose inference 횟수가 약 3배 감소해 전체 처리 시간도 유사한 비율로 단축될 가능성이 높다.
- 동일/유사 프레임 중복 분석이 줄어들어 GPU/CPU 모두에서 연산 낭비가 감소한다.

## 핵심 원칙
- 이 작업은 고급 최적화가 아니라 불필요한 연산 제거다.
- 기본값은 실제 영상이 가진 프레임 수를 넘지 않는다.
- 운동 분석 관점에서는 `30 FPS`면 충분하고, 다수 시나리오에서는 `20 FPS` 전후도 실무적으로 충분할 수 있다.
- 샘플링 정책은 "가능한 많이 본다"가 아니라 "분석 목적에 필요한 만큼만 본다"를 기준으로 정해야 한다.
- 사용자가 더 높은 FPS를 요청하더라도 존재하지 않는 프레임을 새로 만들지는 않는다.

## 제안 정책
- 기본값: `effectiveSamplingFps = sourceVideoFps`
- 사용자 입력 없음: 실제 영상 FPS 그대로 분석
- 사용자 입력 있음: `effectiveSamplingFps = min(requestedSamplingFps, sourceVideoFps)`
- 예시 1: 영상 `30 FPS`, 사용자 요청 `15 FPS` -> `15 FPS`로 분석
- 예시 2: 영상 `30 FPS`, 사용자 요청 `60 FPS` -> `30 FPS`로 분석
- 예시 3: 영상 `30 FPS`, 사용자 요청 없음 -> `30 FPS`로 분석
- 필요 시 `sampleIntervalMs = 1000 / effectiveSamplingFps`로 benchmark와 메타데이터를 일관되게 기록한다.

## 완료 조건
- 기본 샘플링 정책이 실제 영상 FPS를 기본으로 사용하도록 조정된다.
- 사용자가 더 낮은 분석 FPS를 요청할 수 있고, 더 높은 FPS 요청은 실제 영상 FPS로 clamp 된다.
- benchmark summary의 `sampleIntervalMs`가 기대한 정책값과 일치한다.
- 동일 영상 기준 처리 프레임 수와 inference 시간이 유의미하게 감소한다.
- 분석 결과 품질이 운동 분석 기준에서 유지되는지 확인된다.

## 참고 자료
- `poseLandmarker_Python/service/job_manager.py`
- `poseLandmarker_Python/service/video_reader.py`
- `poseLandmarker_Python/service/benchmarking.py`
- `poseLandmarker_Python/docs/optimization/performance-summary.md`

## 작업 결과 요약
- `POST /jobs`에서 분석용 샘플링 FPS를 선택 입력으로 받을 수 있도록 `samplingFps`를 추가했고, 기존 `fps`는 하위 호환 입력으로 유지했다.
- 서버는 실제 영상 메타데이터에서 `sourceVideoFps`를 읽고, 최종 분석 FPS를 `min(requestedSamplingFps, sourceVideoFps)` 규칙으로 결정하도록 수정했다.
- 사용자가 샘플링 FPS를 입력하지 않으면 실제 영상 FPS를 그대로 사용하도록 기본 정책을 변경했다.
- `videoInfo`와 benchmark run metadata에 `requestedSamplingFps`, `effectiveSamplingFps`, `sourceVideoFps`를 함께 기록하도록 정리했다.
- benchmark의 `sampleIntervalMs`는 실제 적용된 분석 FPS 기준으로 계산되도록 수정했다.

## 반영 파일
- `poseLandmarker_Python/controller/jobs.py`
- `poseLandmarker_Python/service/job_manager.py`
- `poseLandmarker_Python/service/video_reader.py`
- `poseLandmarker_Python/service/skeleton_mapper.py`
- `poseLandmarker_Python/service/benchmarking.py`
- `poseLandmarker_Python/schema/benchmark.py`

## 검증
- `python3 -m py_compile`로 관련 Python 파일 문법 검증 완료
- 현재 작업 커밋: `48c93b6`
