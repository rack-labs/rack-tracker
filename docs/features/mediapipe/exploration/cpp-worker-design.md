# MediaPipe C++ Worker 설계 초안

## 1. 목적

이 문서는 현재 `poseLandmarker_Python`의 MediaPipe 추론 경계를 Node 워커 대신 C++ 로컬 프로그램으로 교체할 때의 최소 설계를 정의한다.

목표는 아래 두 가지다.

- 현재 FastAPI API 표면과 최종 결과 JSON shape를 유지한다.
- OpenCV 기반 프레임 추출은 Python이 계속 담당하고, MediaPipe Pose 추론만 C++ 워커가 담당한다.

이 문서는 초안이다. 현재 구현 설명은 여전히 `docs/features/mediapipe/architecture.md`와 `docs/features/mediapipe/spec.md`를 기준으로 본다.

## 2. 현재 코드 기준 삽입 지점

현재 저장소에서 추론 경계는 이미 `NodeWorkerClient`로 분리되어 있다.

- `poseLandmarker_Python/service/pose_inference.py`
- `poseLandmarker_Python/service/node_worker_client.py`
- `poseLandmarker_Python/schema/pose.py`
- `poseLandmarker_Python/schema/frame.py`

현재 `PoseInferenceService.run()`은 아래 두 경로 중 하나를 사용한다.

- Python 내부 MediaPipe adapter 경로
- `SubprocessNodeWorkerClient` 경로

C++ worker 전환 시 가장 안전한 방법은 아래다.

- `PoseInferenceService`는 유지
- `NodeWorkerClient` 자리에 `CppWorkerClient`를 추가
- 기본 구현을 `SubprocessCppWorkerClient`로 둠
- 상위 계층은 worker 구현 언어를 모르게 유지

## 3. 권장 구조

```text
FastAPI app
  -> controller.jobs
    -> service.job_manager.create_job()
      -> background task: JobManager._run_job()
        -> service.video_reader.extract_frames()
        -> service.pose_inference.run()
          -> service.cpp_worker_client.CppWorkerClient.run_pose_inference()
            -> subprocess: mediapipe_pose_worker.exe
              -> MediaPipe C API or C++ API
        -> service.skeleton_mapper.map_landmarks()
        -> service.analysis_pipeline.analyze()
        -> service.benchmarking.build_result()
        -> service.llm_feedback.generate()
```

핵심 원칙:

- Python은 파일 관리, 오케스트레이션, 후처리, API 응답을 유지한다.
- C++ worker는 프레임별 pose inference만 담당한다.
- Python과 C++의 경계는 `cpp_worker_client` 한 곳으로 고정한다.

## 4. C++ worker 책임

워커가 맡아야 할 책임:

- 입력 JSON 파싱
- 모델 파일 경로 검증
- delegate 설정 적용
- MediaPipe Pose Landmarker 생성
- 프레임 이미지 파일 로드
- `VIDEO` 모드 기준 프레임별 추론 실행
- 랜드마크를 JSON 직렬화
- stdout 결과 출력
- stderr 진단 로그 출력
- 명확한 종료 코드 반환

워커가 맡지 않을 책임:

- 비디오 디코딩
- 프레임 샘플링
- 스켈레톤 매핑
- benchmark summary 조립
- 상태 polling
- 결과 페이지네이션

## 5. MediaPipe 연동 방식

`mediapipe-forked` 기준으로 선택 가능한 경로는 두 가지다.

### 5.1 권장: C API 기반

사용 후보:

- `mediapipe/tasks/c/vision/pose_landmarker/pose_landmarker.h`
- `mediapipe/tasks/c/vision/core/image.h`

장점:

- ABI 경계가 더 단순하다.
- worker 내부 코드가 비교적 얇아진다.
- `MpImageCreateFromFile()`를 그대로 활용할 수 있다.

주의:

- 결과 구조 메모리 해제를 정확히 처리해야 한다.
- C API 빌드 산출물 구성이 Bazel 기준이라 초기 빌드가 무겁다.

### 5.2 대안: C++ API 기반

사용 후보:

- `mediapipe/tasks/cc/vision/pose_landmarker/pose_landmarker.h`

장점:

- C++ 레벨 타입 접근성이 더 좋다.
- MediaPipe 결과 구조 해석이 직관적이다.

주의:

- worker 코드가 C ABI보다 템플릿과 C++ 타입 의존이 더 많아진다.
- 외부 재사용보다는 단일 실행파일 내부 구현에 적합하다.

현재 저장소 용도에서는 별도 로컬 exe를 만드는 방식이므로 둘 다 가능하다. 초기 구현은 C API 우선이 안전하다.

## 6. Python 쪽 권장 인터페이스

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from schema.frame import ExtractedFrame
from schema.pose import PoseInferenceOptions, PoseInferenceResult


@dataclass(slots=True)
class CppWorkerExecution:
    command: list[str]
    cwd: Path
    timeout_seconds: float


class CppWorkerClientError(Exception):
    pass


class CppWorkerProcessError(CppWorkerClientError):
    pass


class CppWorkerTimeoutError(CppWorkerClientError):
    pass


class CppWorkerProtocolError(CppWorkerClientError):
    pass


class CppWorkerClient:
    def run_pose_inference(
        self,
        frames: list[ExtractedFrame],
        options: PoseInferenceOptions,
        source_path: str,
    ) -> PoseInferenceResult:
        raise NotImplementedError
```

초기 기본 구현체:

```python
class SubprocessCppWorkerClient(CppWorkerClient):
    ...
```

## 7. 입력 payload 초안

현재 Node worker는 base64 이미지를 넘기지만, C++ worker는 파일 경로 기반으로 단순화하는 편이 낫다.

권장 이유:

- `video_reader`가 이미 프레임 파일을 저장할 수 있다.
- Python에서 JPEG 재인코딩 비용을 줄일 수 있다.
- C++ worker가 `MpImageCreateFromFile()`로 바로 읽을 수 있다.
- stdin JSON 크기를 크게 줄일 수 있다.

권장 입력 shape:

```json
{
  "sourcePath": "C:/video/backSquat.mp4",
  "options": {
    "modelAssetPath": "C:/models/mediapipe/pose_landmarker_full.task",
    "modelVariant": "full",
    "runningMode": "VIDEO",
    "delegate": "CPU",
    "numPoses": 1,
    "minPoseDetectionConfidence": 0.5,
    "minPosePresenceConfidence": 0.5,
    "minTrackingConfidence": 0.5,
    "outputSegmentationMasks": false
  },
  "frames": [
    {
      "frameIndex": 0,
      "timestampMs": 0.0,
      "imagePath": "C:/tmp/frames/job_x/frame_000000.jpg",
      "width": 1280,
      "height": 720
    }
  ]
}
```

입력 계약 원칙:

- `frames[].imagePath`는 절대 경로를 권장한다.
- `timestampMs`는 단조 증가해야 한다.
- 초기 구현은 `runningMode == "VIDEO"`만 허용한다.
- 초기 구현은 `numPoses == 1`만 실사용 범위로 본다.

## 8. 출력 payload 초안

상위 Python 후처리 계층이 이미 기대하는 shape와 최대한 맞춘다.

```json
{
  "sourcePath": "C:/video/backSquat.mp4",
  "runningMode": "VIDEO",
  "modelName": "pose_landmarker_full.task",
  "frameCount": 120,
  "detectedFrameCount": 116,
  "requestedDelegate": "GPU",
  "actualDelegate": "CPU",
  "delegateFallbackApplied": true,
  "delegateErrors": {
    "GPU": "Failed to initialize GPU delegate"
  },
  "frames": [
    {
      "frameIndex": 0,
      "timestampMs": 0.0,
      "poseDetected": true,
      "landmarks": [
        {
          "name": "nose",
          "x": 0.501234,
          "y": 0.182345,
          "z": -0.732111,
          "visibility": 0.9981,
          "presence": 0.9972
        }
      ],
      "benchmark": {
        "frameIndex": 0,
        "timestampMs": 0.0,
        "rgbConversionMs": 0.0,
        "inferenceMs": 8.421,
        "serializationMs": 0.153,
        "totalFramePipelineMs": 8.771,
        "poseDetected": true,
        "landmarkCount": 33,
        "avgVisibility": 0.9451,
        "minVisibility": 0.7213
      }
    }
  ]
}
```

출력 계약 원칙:

- 최상위 필드는 `PoseInferenceResult`와 1:1 대응시킨다.
- `landmarks`는 현재 Python serializer가 쓰는 33개 이름 체계를 유지한다.
- `worldLandmarks`와 `segmentationMask`는 초기 범위에서 생략 가능하다.
- 벤치마크는 프레임 단위로 넣고, summary 조립은 Python이 계속 담당한다.

## 9. 오류 계약 초안

stdout은 성공 또는 구조화된 오류 JSON 하나만 출력한다.

오류 예시:

```json
{
  "error": {
    "code": "MODEL_NOT_FOUND",
    "message": "Model asset not found: C:/models/mediapipe/pose_landmarker_full.task"
  }
}
```

오류 구분:

- `WORKER_START_FAILED`
- `INVALID_INPUT`
- `MODEL_NOT_FOUND`
- `IMAGE_NOT_FOUND`
- `IMAGE_LOAD_FAILED`
- `LANDMARKER_INIT_FAILED`
- `INFERENCE_FAILED`
- `PROTOCOL_ERROR`

Python 매핑 원칙:

- 프로세스 실행 실패 -> `CppWorkerProcessError`
- 타임아웃 -> `CppWorkerTimeoutError`
- stdout JSON 파싱 실패 -> `CppWorkerProtocolError`
- worker `error.code` 수신 -> `CppWorkerClientError` 하위 예외

초기 정책:

- 프레임 하나라도 실패하면 job 전체 실패
- partial failure는 도입하지 않음

## 10. 로그 원칙

Python 로그에 남길 항목:

- worker command
- worker cwd
- timeout
- source path
- frame count
- requested delegate
- exit code

C++ worker 로그 원칙:

- stdout: 결과 JSON 전용
- stderr: 진단 로그 전용
- 개별 landmark 배열 전체를 stderr에 반복 출력하지 않음

## 11. Python 변경 포인트

최소 변경 대상:

- `poseLandmarker_Python/service/node_worker_client.py`
  - C++ worker용 새 구현 추가 또는 별도 `cpp_worker_client.py`로 분리
- `poseLandmarker_Python/service/pose_inference.py`
  - 기본 worker 선택 로직 확장
- `poseLandmarker_Python/schema/pose.py`
  - `InferenceBackend`에 `"cpp_worker"` 추가 검토
- `poseLandmarker_Python/service/video_reader.py`
  - worker 모드에서 `saved_path`가 항상 보장되도록 점검
- `poseLandmarker_Python/config/config.py`
  - worker exe 경로, timeout, 기본 모델 경로 설정 추가

권장 방향:

- Node worker 코드를 덮어쓰지 말고 `cpp_worker_client.py`를 별도 추가
- 기능 플래그로 `NODE_WORKER_ENABLED`와 분리된 `CPP_WORKER_ENABLED`를 둠

## 12. C++ worker 최소 요구사항

초기 버전의 최소 요구사항:

- 단일 exe 또는 단일 shared library + thin exe wrapper
- stdin 한 줄 JSON 입력
- stdout 한 줄 JSON 출력
- `VIDEO` 모드만 지원
- `CPU` delegate 우선 지원
- `GPU`는 후속 단계
- 단일 pose만 사용
- JPEG 또는 PNG 프레임 파일 입력

초기 범위에서 일부러 제외할 것:

- 장기 실행 worker pool
- 실시간 스트리밍
- 멀티포즈 직렬화
- segmentation mask 반환
- world landmarks 외부 반환

## 13. 모델 자산 정책

`pose_landmarker` 모델은 API 호출형 서비스가 아니라 로컬 모델 asset 기반이다.

현재 공식 문서 기준:

- Pose Landmarker는 다운로드 가능한 model bundle을 제공한다.
- lite, full, heavy 세 변형이 있다.
- Task API는 로컬 모델 파일 경로 또는 모델 버퍼를 입력으로 받는다.

프로젝트 정책 권장안:

- 기본값은 `pose_landmarker_full.task`
- 저장 위치는 `poseLandmarker_Python/models/mediapipe/`
- `lite`, `full`, `heavy` 파일명을 고정 규칙으로 유지
- 런타임 네트워크 다운로드에 의존하지 않음

## 14. 구현 순서 권장안

1. `cpp_worker_client.py` 인터페이스 추가
2. frame payload를 `imagePath` 기반으로 바꾸기
3. CPU 전용 C++ worker exe 만들기
4. `pose_landmarker_full.task` 기준 단일 이미지/단일 프레임 smoke test
5. Python 파이프라인과 end-to-end 연결
6. frame benchmark 연결
7. GPU delegate 검토

## 15. 현재 결론

현재 `rack-tracker-forked` 구조에서는 MediaPipe 전체를 Python 안에서 다시 구현할 필요가 없다.

가장 현실적인 경로는 아래다.

- Python은 현재 역할 유지
- 추론 경계만 subprocess C++ worker로 교체
- 모델 파일은 로컬 asset으로 관리
- 첫 단계는 CPU 전용, VIDEO 모드 전용으로 작게 시작

이 방식이면 기존 아키텍처를 크게 깨지 않고, 이후 Node worker 대비 C++ worker 성능 비교도 가능하다.
