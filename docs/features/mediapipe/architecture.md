# MediaPipe 기반 포즈 랜드마커 기능 아키텍처

> 문서 동기화 강제 프롬프트
>
> 이 문서를 수정하는 AI 또는 작성자는 반드시 아래 짝 문서를 함께 확인해야 한다.
>
> - `docs/features/mediapipe/spec.md`
>
> 규칙:
>
> - 아키텍처가 바뀌면 명세 문서도 즉시 확인하고, 사용자 설명이나 입출력 설명이 달라졌다면 함께 수정한다.
> - 명세가 바뀌어 현재 아키텍처 설명과 충돌하면, 이 문서도 즉시 수정한다.
> - 둘 중 하나만 수정하고 다른 문서를 방치하지 않는다.
> - 특히 아래 항목이 바뀌면 상대 문서를 반드시 같이 수정한다.
>   - 입력 포트
>   - 출력 포트
>   - 데이터 흐름
>   - 옵션 이름
>   - 목업 데이터 정책
>   - 예외 정책
>   - 성능 관련 옵션 또는 권고
>
> 실행 지시:
>
> - 이 문서를 수정한 뒤에는 반드시 짝 문서를 다시 읽고, 같은 의미가 유지되는지 점검하라.
> - 필요하면 두 문서를 같은 커밋 또는 같은 작업 단위에서 함께 수정하라.

## 1. 목적

현재 `poseLandmarker_Python` 백엔드는 MediaPipe Pose Landmarker를 실제 분석 파이프라인 안에 연결해 아래 흐름을 제공한다.

- 업로드 비디오 또는 기본 목업 비디오를 입력으로 받는다.
- OpenCV 기반 프레임 추출을 수행한다.
- MediaPipe Pose Landmarker로 프레임별 33개 랜드마크를 추론한다.
- 결과를 `skeleton`, `analysis`, `llmFeedback`, `benchmark` 구조로 정리한다.
- 상태 조회, 결과 조회, 스켈레톤 다운로드, benchmark 조회 API를 제공한다.

이 문서는 2026-03-27 기준 저장소 구현을 설명한다. 더 이상 `목업 추론을 실제 MediaPipe로 대체할 예정`인 설계 문서가 아니라, 현재 동작 중인 구현 문서다.

## 2. 현재 구현 관찰

### 핵심 모듈

- `poseLandmarker_Python/controller/jobs.py`
  - `POST /jobs`
  - 업로드 파일 저장 또는 기본 목업 비디오 선택
  - `samplingFps`, `exerciseType`, `modelAssetPath`, `modelVariant`, `delegate`를 `JobManager`로 전달
- `poseLandmarker_Python/controller/results.py`
  - `GET /jobs/{job_id}/result`
  - `GET /jobs/{job_id}/skeleton`
  - `GET /jobs/{job_id}/skeleton/download`
  - `GET /jobs/{job_id}/benchmark`
  - `GET /jobs/{job_id}/benchmark/frames`
- `poseLandmarker_Python/service/job_manager.py`
  - 전체 파이프라인 오케스트레이션
  - job 상태 및 메모리 저장소 관리
  - 무거운 단계의 `asyncio.to_thread()` 오프로딩
- `poseLandmarker_Python/service/video_reader.py`
  - 비디오 프레임 추출
- `poseLandmarker_Python/service/pose_inference.py`
  - 프레임별 MediaPipe 추론 실행
  - 33개 랜드마크 직렬화
  - 프레임별 benchmark 측정치 생성  
- `poseLandmarker_Python/adapter/mediapipe_adapter.py`
  - MediaPipe import
  - `PoseLandmarker` 생성/종료
  - GPU 우선, CPU fallback 초기화
- `poseLandmarker_Python/service/skeleton_mapper.py`
  - `skeleton.frames`, `skeleton.videoInfo`, `nextTimestampCursorMs` 생성
- `poseLandmarker_Python/service/analysis_pipeline.py`
  - 기본 분석 결과 생성
- `poseLandmarker_Python/service/benchmarking.py`
  - summary/detail benchmark 결과 생성 및 파일 저장
- `poseLandmarker_Python/service/llm_feedback.py`
  - 현재는 rule-based placeholder 피드백 생성

### 설정 및 자산

- 기본 비디오: `poseLandmarker_Python/src/video/backSquat.mp4`
- 모델 디렉터리: `poseLandmarker_Python/models/mediapipe/`
- 지원 모델:
  - `pose_landmarker_lite.task`
  - `pose_landmarker_full.task`
  - `pose_landmarker_heavy.task`
- 기본 모델 변형: `full`
- 기본 delegate: `GPU`
- 임시 저장 위치:
  - 업로드: `poseLandmarker_Python/tmp/uploads`
  - 추출 프레임: `poseLandmarker_Python/tmp/frames`
  - 스켈레톤: `poseLandmarker_Python/tmp/skeletons`
  - benchmark: `poseLandmarker_Python/tmp/benchmarks`

## 3. 계층 구조

```text
FastAPI app
  -> controller.jobs
    -> service.job_manager.create_job()
      -> background task: JobManager._run_job()
        -> service.video_reader.extract_frames()
        -> service.pose_inference.run()
          -> adapter.mediapipe_adapter.create_landmarker()
          -> adapter.mediapipe_adapter.detect_for_video()
        -> service.skeleton_mapper.map_landmarks()
        -> service.analysis_pipeline.analyze()
        -> service.benchmarking.build_result()
        -> service.llm_feedback.generate()
        -> tmp/skeletons/{job_id}.json
        -> tmp/benchmarks/benchmark_{job_id}.summary.json
        -> tmp/benchmarks/benchmark_{job_id}.frames.json
  -> controller.results
    -> job_manager.get_result()
    -> job_manager.get_skeleton_page()
    -> job_manager.get_benchmark()
    -> job_manager.get_benchmark_frame_metrics()
```

## 4. 실행 흐름

### 4.1 요청 수신

`POST /jobs`는 아래 입력을 받는다.

- `video`
- `fps` 또는 `samplingFps`
- `exerciseType`
- `modelAssetPath`
- `modelVariant`
- `delegate`

비디오가 없으면 `MOCK_VIDEO_PATH`를 사용한다. 업로드가 있으면 `tmp/uploads`에 저장한 뒤 그 경로를 사용한다.

### 4.2 요청 검증

`JobManager.create_job()`는 job 등록 전에 inference override를 검증한다.

- `"string"` 또는 빈 문자열은 미입력으로 간주
- `modelVariant`는 `lite`, `full`, `heavy`만 허용
- `delegate`는 `CPU`, `GPU`만 허용
- `samplingFps`는 `> 0` 이어야 함

검증 실패는 비동기 job 생성 전에 `HTTP 400`으로 즉시 반환된다.

### 4.3 백그라운드 실행

`JobManager._run_job()`는 아래 순서로 동작한다.

1. 프레임 추출
2. Pose 추론
3. 스켈레톤 매핑 및 파일 저장
4. 분석 생성
5. benchmark 생성
6. LLM feedback 생성
7. job 완료 처리

CPU 바운드 단계는 `asyncio.to_thread()`로 worker thread에서 실행한다. 목적은 `GET /jobs/{job_id}` 같은 가벼운 polling 요청이 이벤트 루프 블로킹 영향을 덜 받게 하는 것이다.

### 4.4 외부 노출 상태

현재 외부 상태 값은 아래처럼 보인다.

- `queued`
- `extracting`
- `analyzing`
- `generating_feedback`
- `completed`
- `failed`

주의할 점:

- 내부적으로는 `extracting` 단계 안에서 프레임 추출뿐 아니라 pose inference와 skeleton 저장까지 수행한다.
- 별도 `inferring` 상태는 아직 외부로 노출하지 않는다.

## 5. 책임 분리

### `adapter/mediapipe_adapter.py`

MediaPipe 의존성을 직접 캡슐화한다.

- `mediapipe` import
- `PoseLandmarkerOptions` 조립
- delegate enum 해석
- `PoseLandmarker.create_from_options()` 호출
- `detect()`, `detect_for_video()`, `detect_async()` 래핑
- delegate별 초기화 오류 메시지 수집

실행 정책:

- 요청 delegate가 `GPU`면 `GPU -> CPU` 순서로 초기화 시도
- 요청 delegate가 `CPU`면 CPU만 시도
- GPU 요청이었고 CPU fallback까지 모두 실패하면 `GpuDelegateUnavailableError`
- 그 외 초기화 실패는 `LandmarkerInitializationError`

### `service/pose_inference.py`

프레임 순회와 결과 직렬화를 담당한다.

- 입력: `list[ExtractedFrame]`
- 기본 실행 모드: `VIDEO`
- MediaPipe 호출: `detect_for_video(mp_image, timestamp_ms)`
- 입력 이미지가 3채널인지 검사
- BGR 프레임을 RGB로 뒤집어 `mp.Image` 생성
- 첫 번째 pose만 사용해 33개 랜드마크를 이름 기반으로 직렬화
- 프레임별 benchmark 생성

현재 출력 범위:

- 포함:
  - `landmarks`
  - `poseDetected`
  - `frameIndex`
  - `timestampMs`
- 스키마에는 있으나 미사용:
  - `world_landmarks`
  - `segmentation_mask`

### `service/skeleton_mapper.py`

추론 결과를 프론트/후속 분석 친화적 스켈레톤 구조로 변환한다.

- `frames`
- `videoInfo`
- `nextTimestampCursorMs`

`videoInfo`에는 현재 아래 값이 기록된다.

- `videoSrc`
- `displayName`
- `sourceFps`
- `frameCount`
- `width`
- `height`
- `backend`
- `extractedCount`
- `requestedSamplingFps`
- `effectiveSamplingFps`
- `runningMode`
- `modelName`
- `detectedFrameCount`

### `service/analysis_pipeline.py`

현재는 placeholder 성격의 기본 분석 계층이다.

- `summary`
- `kpis`
- `timeseries`
- `events`
- `repSegments`
- `issues`

실제 운동 분석 모델이라기보다 스켈레톤 결과를 후속 소비 가능한 구조로 정리하는 초기 단계에 가깝다.

### `service/benchmarking.py`

benchmark summary/detail 생성과 파일 저장을 담당한다.

- run metadata
- timing summary
- quality summary
- comparison tags
- frame-level metrics
- summary/detail 파일 경로

저장 파일:

- `tmp/benchmarks/benchmark_{job_id}.summary.json`
- `tmp/benchmarks/benchmark_{job_id}.frames.json`

### `service/llm_feedback.py`

현재는 실제 LLM 연동이 아니라 규칙 기반 placeholder 응답을 생성한다.

- `version: "v1"`
- `model: "rule-based-placeholder"`
- `overallComment`
- `highlights`
- `corrections`
- `coachCue`

## 6. 도메인 모델

### 6.1 추론 옵션

```python
@dataclass(slots=True)
class PoseInferenceOptions:
    model_asset_path: Path
    model_variant: Literal["lite", "full", "heavy"] = "full"
    running_mode: Literal["IMAGE", "VIDEO", "LIVE_STREAM"] = "VIDEO"
    delegate: Literal["GPU", "CPU"] = "GPU"
    num_poses: int = 1
    min_pose_detection_confidence: float = 0.5
    min_pose_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    output_segmentation_masks: bool = False
    result_callback: object | None = None
```

현재 job API에서 실제로 외부 입력으로 받는 옵션은 아래만 연결돼 있다.

- `modelAssetPath`
- `modelVariant`
- `delegate`

나머지 confidence 계열 옵션과 `num_poses`는 코드 기본값을 사용한다.

### 6.2 프레임 결과

```python
@dataclass(slots=True)
class PoseFrameResult:
    frame_index: int
    timestamp_ms: float
    pose_detected: bool
    landmarks: list[PoseLandmarkPoint]
    world_landmarks: list[PoseLandmarkPoint] | None = None
    segmentation_mask: object | None = None
    benchmark: PoseFrameBenchmark | None = None
```

직렬화 결과는 현재 아래 shape만 외부로 노출한다.

```json
{
  "frameIndex": 12,
  "timestampMs": 400.0,
  "poseDetected": true,
  "landmarks": [
    {
      "name": "left_shoulder",
      "x": 0.42,
      "y": 0.31,
      "z": -0.12,
      "visibility": 0.97,
      "presence": 0.98
    }
  ]
}
```

### 6.3 배치 추론 결과

```python
@dataclass(slots=True)
class PoseInferenceResult:
    source_path: str
    running_mode: RunningMode
    model_name: str
    frame_count: int
    detected_frame_count: int
    requested_delegate: Delegate
    actual_delegate: Delegate
    delegate_fallback_applied: bool
    delegate_errors: dict[str, str]
    frames: list[PoseFrameResult]
```

현재 구현은 iterator 기반 스트리밍 결과가 아니라 메모리 내 리스트 결과를 반환한다.

### 6.4 스켈레톤 결과

```json
{
  "frames": [],
  "videoInfo": {},
  "nextTimestampCursorMs": 0
}
```

`GET /jobs/{job_id}/skeleton`은 전체 결과 대신 page 응답을 제공한다.

- `frames`
- `videoInfo`
- `nextTimestampCursorMs`
- `offset`
- `limit`
- `totalFrames`

### 6.5 최종 결과

`GET /jobs/{job_id}/result`는 아래 최상위 구조를 반환한다.

```json
{
  "skeleton": {},
  "analysis": {},
  "llmFeedback": {},
  "benchmark": {}
}
```

즉, MediaPipe 기능은 이제 독립된 포즈 추론 모듈을 넘어 최종 motion-analysis 응답 일부로 편입돼 있다.

## 7. API 표면

### Job 생성 및 상태

- `POST /jobs`
- `GET /jobs/{job_id}`

### 결과 조회

- `GET /jobs/{job_id}/result`
- `GET /jobs/{job_id}/skeleton`
- `GET /jobs/{job_id}/skeleton/download`
- `GET /jobs/{job_id}/benchmark`
- `GET /jobs/{job_id}/benchmark/frames`

조회 정책:

- 결과형 API는 job이 `completed`가 아니면 `HTTP 409`
- 존재하지 않는 job이면 `HTTP 404`

## 8. 예외 및 실패 정책

코드상 주요 예외는 아래와 같다.

- `ModelAssetNotFoundError`
- `LandmarkerInitializationError`
- `GpuDelegateUnavailableError`
- `InvalidFrameInputError`
- `PoseInferenceError`
- `ResultSerializationError`

현재 실패 정책은 단순하다.

- 잘못된 요청 옵션: job 생성 전 `HTTP 400`
- 모델 파일 없음: job 실패
- MediaPipe import/초기화 실패: job 실패
- 프레임 이미지 누락 또는 포맷 오류: job 실패
- 특정 프레임 추론 실패: job 전체 실패
- 결과 직렬화 실패: job 전체 실패

partial failure, frame skip, degraded-success 정책은 아직 구현돼 있지 않다.

## 9. 성능 및 운영 관점

- 기본 delegate는 `GPU`이며 실패 시 `CPU` fallback을 시도한다.
- 기본 모델은 `full`이다.
- `samplingFps`를 낮춰 추론 비용을 직접 줄일 수 있다.
- RGB 변환, 추론, 직렬화 시간은 프레임별로 계측된다.
- summary benchmark와 frame-level benchmark를 분리해 비교 UI와 상세 분석 UI를 분리할 수 있다.
- 현재 `PoseInferenceService.run()`은 모든 프레임 결과를 메모리에 적재하므로 매우 긴 영상에 대한 스트리밍 최적화는 아직 후속 과제다.

## 10. 현재 범위와 미구현 범위

현재 구현 범위:

- 업로드 비디오 또는 목업 비디오 분석
- MediaPipe VIDEO 모드 기반 추론
- 33개 랜드마크 직렬화
- 스켈레톤 JSON 저장
- 기본 분석 결과 생성
- placeholder LLM feedback 생성
- benchmark summary/detail 저장 및 조회

현재 미구현 또는 비활성 범위:

- 단일 이미지 전용 API
- LIVE_STREAM 기반 실시간 추론 API
- world landmarks 외부 노출
- segmentation mask 외부 노출
- frame-level partial failure 복구
- 실제 LLM 기반 피드백 생성

## 11. Node Worker 전환 목표 아키텍처

이 절은 현재 구현 설명이 아니라 `poseLandmarker_Python`의 MediaPipe 추론부를 Node.js 워커로 교체할 때 적용할 목표 구조를 정의한다.

현재 PoC에서 확인된 제약:

- `@mediapipe/tasks-vision`을 순수 Node.js subprocess에서 직접 초기화하면 `document is not defined`가 발생했다.
- 즉, 현재 선택한 MediaPipe JS 런타임은 이 저장소 환경에서 브라우저 DOM 전역을 요구한다.
- 따라서 현재 성능 검증 단계에서는 "순수 Node 추론"이 아니라 "서버에서 headless browser를 띄워 MediaPipe JS를 실행"하는 경로를 목표 구조로 둔다.
- 이 결정의 목적은 엔드포인트 기기 성능 의존을 없애는 것이며, 브라우저 없는 서버 런타임이 장기적으로 더 적합할 수 있다는 판단은 유지한다.

전환 원칙:

- FastAPI API 표면과 최종 결과 JSON shape는 유지한다.
- Python은 오케스트레이션, 파일 관리, 후처리 계층을 계속 담당한다.
- Node.js는 MediaPipe 추론 엔진 계층만 담당한다.
- Python과 Node의 경계는 `node_worker_client` 한 곳으로 고정한다.
- 현재 PoC 기준 Node 워커 내부 런타임은 headless browser를 포함할 수 있다.

### 11.1 목표 계층 구조

```text
FastAPI app
  -> controller.jobs
    -> service.job_manager.create_job()
      -> background task: JobManager._run_job()
        -> service.video_reader.extract_frames()
        -> service.pose_inference.run()
          -> service.node_worker_client.NodeWorkerClient.run_pose_inference()
            -> node_worker subprocess
              -> headless browser runtime
                -> MediaPipe Tasks Vision runtime
        -> service.skeleton_mapper.map_landmarks()
        -> service.analysis_pipeline.analyze()
        -> service.benchmarking.build_result()
        -> service.llm_feedback.generate()
```

핵심 차이:

- `service/pose_inference.py`는 더 이상 `adapter/mediapipe_adapter.py`에 직접 의존하지 않는다.
- 추론 엔진 선택, 프로세스 호출, stdout/stderr 처리, 타임아웃 처리는 `service/node_worker_client.py`로 이동한다.
- 현재 Node 워커 내부의 핵심 역할은 브라우저 없는 JS 런타임을 강제하는 것이 아니라, 서버 측 headless browser 실행을 캡슐화하는 것이다.
- `skeleton_mapper`, `analysis_pipeline`, `benchmarking`, `llm_feedback`는 가능한 한 기존 책임을 유지한다.

### 11.2 `node_worker_client` 배치와 책임

권장 배치 위치:

- `poseLandmarker_Python/service/node_worker_client.py`

`NodeWorkerClient`가 가져야 할 책임:

- Node 워커 실행 명령 조립
- 입력 payload 직렬화
- subprocess 실행과 timeout 적용
- stdout JSON 수집
- stderr 진단 로그 수집
- 종료 코드 검증
- worker 응답을 `PoseInferenceResult` 또는 동등한 내부 도메인 구조로 역직렬화
- worker 실패를 Python 예외 계층으로 변환

`NodeWorkerClient`가 맡지 않을 책임:

- FastAPI request parsing
- frame extraction
- skeleton mapping
- benchmark 최종 조립
- 결과 페이지네이션

즉, 이 계층은 "Node를 어떻게 호출하는가"만 캡슐화하고, "추론 결과를 어떻게 후처리하는가"는 상위 Python 서비스가 계속 담당한다.

추가 원칙:

- `node_worker_client`는 Node 워커 내부 구현이 순수 Node인지 headless browser인지 알 필요가 없다.
- 상위 Python 계층은 "서버에서 추론이 수행된다"는 사실만 보장받으면 된다.

### 11.3 권장 인터페이스

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from schema.frame import ExtractedFrame
from schema.pose import PoseInferenceOptions, PoseInferenceResult


@dataclass(slots=True)
class NodeWorkerExecution:
    command: list[str]
    cwd: Path
    timeout_seconds: float


class NodeWorkerClientError(Exception):
    pass


class NodeWorkerProcessError(NodeWorkerClientError):
    pass


class NodeWorkerTimeoutError(NodeWorkerClientError):
    pass


class NodeWorkerProtocolError(NodeWorkerClientError):
    pass


class NodeWorkerClient:
    def run_pose_inference(
        self,
        frames: list[ExtractedFrame],
        options: PoseInferenceOptions,
        source_path: str,
    ) -> PoseInferenceResult:
        raise NotImplementedError
```

인터페이스 설계 의도:

- `PoseInferenceService`는 워커 구현체 종류를 몰라도 된다.
- 현재 기본 구현체는 subprocess 기반이어야 한다.
- 장기적으로 HTTP 또는 장기 실행 프로세스 기반 구현체로 교체하더라도 상위 서비스 계약은 유지한다.

### 11.4 기본 구현체와 주입 방식

초기 기본 구현체는 `SubprocessNodeWorkerClient`다.

```python
class PoseInferenceService:
    def __init__(self, worker_client: NodeWorkerClient | None = None) -> None:
        self._worker_client = worker_client or SubprocessNodeWorkerClient(...)
```

구성 원칙:

- `PoseInferenceService`는 `NodeWorkerClient` 인터페이스에만 의존한다.
- 기본값은 subprocess 구현체를 생성하되, 테스트에서는 mock 또는 fake client를 주입할 수 있어야 한다.
- Python 코드 여러 곳에서 직접 `node ...` 명령을 흩뿌리지 않는다.
- Node 워커 내부에서 browser launch 전략이 바뀌더라도 Python 주입 구조는 그대로 유지한다.

### 11.5 Python-Node 데이터 흐름

목표 데이터 흐름은 아래와 같다.

1. `JobManager`가 업로드 비디오 저장 또는 목업 비디오 선택
2. `video_reader.extract_frames()`가 프레임 파일과 메타데이터 생성
3. `PoseInferenceService`가 `NodeWorkerClient`에 추론 요청
4. `NodeWorkerClient`가 frame 목록과 옵션을 JSON payload로 직렬화
5. Node 워커가 headless browser를 기동하고 로컬 브라우저 페이지를 연다
6. browser 런타임이 frame image path와 model asset을 읽어 MediaPipe JS 추론 수행
7. Node 워커가 frame별 랜드마크와 delegate/runtime 메타데이터를 JSON으로 반환
8. Python이 이를 `PoseInferenceResult`로 역직렬화
9. 기존 `skeleton_mapper`, `analysis_pipeline`, `benchmarking`, `llm_feedback`가 후속 처리

초기 전송 방식은 image buffer 직접 전달이 아니라 `imagePath` 전달 방식을 권장한다.

이유:

- Python과 Node 사이에 대용량 바이너리 버퍼 직렬화를 피할 수 있다.
- 기존 `video_reader`가 이미 프레임 파일을 생성하고 있으므로 재사용이 쉽다.
- subprocess stdin/stdout은 JSON 메타데이터 교환에만 집중할 수 있다.
- headless browser 방식에서도 frame asset 제공 방식이 단순하다.

### 11.6 입력 payload 계약

권장 입력 payload는 아래 shape를 기준으로 한다.

```json
{
  "sourcePath": "C:/video.mp4",
  "options": {
    "modelAssetPath": "C:/models/pose_landmarker_full.task",
    "modelVariant": "full",
    "runningMode": "VIDEO",
    "delegate": "GPU",
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
      "imagePath": "C:/tmp/frames/job_x/frame_000000.jpg"
    }
  ]
}
```

계약 원칙:

- `sourcePath`는 원본 비디오 기준 경로다.
- `frames[].imagePath`는 Node 런타임에서 직접 접근 가능한 절대 경로여야 한다.
- `options`는 현재 `PoseInferenceOptions`의 실사용 필드를 우선 반영한다.
- 경로 체계는 한 실행 컨텍스트 안에서 Windows 경로와 WSL 경로를 혼합하지 않는다.

### 11.7 출력 payload 계약

권장 출력 payload는 아래 shape를 기준으로 한다.

```json
{
  "sourcePath": "C:/video.mp4",
  "runningMode": "VIDEO",
  "modelName": "pose_landmarker_full.task",
  "frameCount": 120,
  "detectedFrameCount": 116,
  "requestedDelegate": "GPU",
  "actualDelegate": "CPU",
  "delegateFallbackApplied": true,
  "delegateErrors": {
    "GPU": "RuntimeError: ..."
  },
  "frames": [
    {
      "frameIndex": 0,
      "timestampMs": 0.0,
      "poseDetected": true,
      "landmarks": []
    }
  ]
}
```

출력 매핑 원칙:

- 최상위 메타데이터는 기존 `PoseInferenceResult` 필드와 1:1로 대응시킨다.
- `frames[].frameIndex`, `frames[].timestampMs`, `frames[].poseDetected`, `frames[].landmarks`는 현재 Python 후처리 계층이 기대하는 필드를 유지한다.
- `world_landmarks`, `segmentation_mask`는 현재 외부 미노출 항목이므로 초기 전환 범위에서는 선택적 필드로 둔다.

### 11.8 오류 및 예외 정책

Node 워커 경계에서는 최소한 아래 오류를 구분한다.

- 프로세스 실행 자체 실패
  - 예: `node` 바이너리 없음, 엔트리 파일 없음
  - Python 예외: `NodeWorkerProcessError`
- timeout
  - Python 예외: `NodeWorkerTimeoutError`
- 프로토콜 위반
  - 예: stdout이 JSON이 아님, 필수 필드 누락
  - Python 예외: `NodeWorkerProtocolError`
- 워커 내부 추론 실패
  - 예: 모델 로드 실패, delegate 초기화 실패, 프레임 읽기 실패, browser launch 실패
  - worker JSON의 `error` 필드를 읽어 `NodeWorkerClientError` 하위 예외로 변환

상위 실패 처리 원칙은 현재 구현을 유지한다.

- worker 호출 실패는 job 전체 실패로 처리한다.
- 특정 프레임만 건너뛰는 partial failure 정책은 초기 전환 범위에 포함하지 않는다.

### 11.9 로그 및 진단 원칙

Python 쪽 기본 진단 로그에 포함할 항목:

- worker command
- worker cwd
- timeout 설정값
- source video path
- frame count
- requested delegate
- exit code

로그 분리 원칙:

- Node 워커의 결과 JSON은 stdout 전용으로 사용한다.
- Node 워커의 진단 로그는 stderr로 분리한다.
- 기본 로그에는 전체 frame payload나 전체 landmark 배열을 남기지 않는다.
- browser console 로그는 가능하면 Node 워커가 수집해 stderr로 재노출한다.

이 분리는 JSON 파싱 안정성과 운영 진단성을 동시에 확보하기 위한 것이다.

### 11.10 구현체 확장 전략

장기적으로 아래 구현체를 추가할 수 있다.

- `SubprocessNodeWorkerClient`
- `HttpNodeWorkerClient`

하지만 현재 목표 구현은 subprocess 방식으로 한정한다.

이유:

- 별도 Node 서버 기동과 포트 관리를 도입하지 않아도 된다.
- 초기 구현 범위를 가장 작게 유지할 수 있다.
- 상위 Python 서비스 구조를 거의 그대로 보존할 수 있다.
- 서버에서 headless browser 기반 성능 검증을 빠르게 시작할 수 있다.

현재 성능 해석 원칙:

- headless browser는 클라이언트 브라우저보다 엔드포인트 기기 성능 의존이 적다.
- 그러나 브라우저 없는 서버 네이티브 런타임과 비교하면 일반적으로 오버헤드가 더 크다.
- 따라서 현재 benchmark 해석은 "운영 최적화 완료"가 아니라 "서버 측 실행 가능성 및 상대 성능 확인"으로 한정해야 한다.

서버형 전환이 필요한 조건:

- 프로세스 기동 비용이 병목이 될 때
- 모델 초기화 재사용이 필요할 때
- worker pool 또는 헬스체크가 필요할 때
- Python과 Node를 독립 배포해야 할 때

그 경우에도 상위 계층 영향 범위는 `node_worker_client` 내부로 제한하는 것이 목표다.
