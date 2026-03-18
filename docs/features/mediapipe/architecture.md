# MediaPipe 기반 포즈 랜드마커 기능 아키텍처 초안

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

`poseLandmarker_Python` 백엔드에 MediaPipe 기반 포즈 랜드마커 계층을 추가해 다음 요구를 충족한다.

- 비디오 또는 이미지에서 사람 포즈를 안정적으로 추론한다.
- 추론 결과를 프레임 메타데이터와 함께 후속 분석 계층에 전달한다.
- MediaPipe 내부 세부사항을 adapter 계층에 숨겨, 서비스 계층이 라이브러리 구현에 직접 결합되지 않게 한다.
- 현재 목업 추론 구조를 실제 MediaPipe Tasks Vision 기반 구현으로 자연스럽게 대체할 수 있게 한다.

## 2. 참고한 코드베이스 관찰

### 현재 프로젝트 관찰

- `adapter/mediapipe_adapter.py`는 현재 `create_landmarker()`만 있는 스텁 상태다.
- `service/pose_inference.py`는 현재 `list[ExtractedFrame]`를 받아 목업 랜드마크를 생성한다.
- `service/skeleton_mapper.py`는 추론 결과를 `skeleton.frames`, `skeleton.videoInfo` 구조로 정리한다.
- `service/job_manager.py`는 `video_reader -> pose_inference -> skeleton_mapper -> analysis_pipeline -> llm_feedback` 순서로 작업을 진행한다.
- `schema/frame.py`에는 이미 `ExtractedFrame`, `FrameExtractionResult`가 정의돼 있어 포즈 추론 입력 모델로 재사용하기 좋다.

### MediaPipe 연동 관찰

- 현재 저장소에는 `poseLandmarker_Python/docs/reference/mediapipe/pose-landmarker-guide.md` 문서가 포함돼 있다.
- 해당 가이드는 Python Tasks Vision API 기준으로 아래 개념을 사용한다.
  - `BaseOptions`
  - `PoseLandmarker`
  - `PoseLandmarkerOptions`
  - `VisionRunningMode`
  - `PoseLandmarkerResult`
- 백엔드 배치 처리 구조상 `detect_for_video(mp_image, frame_timestamp_ms)`가 가장 잘 맞는다.
- 이미지 단건 처리나 실시간 스트림은 향후 확장 포인트로 분리하는 편이 적절하다.

## 3. 설계 원칙

- MediaPipe 의존 코드는 adapter 계층에 격리한다.
- 프레임 순회와 추론 orchestration은 service 계층에 둔다.
- 컨트롤러는 요청 접수와 job orchestration만 담당한다.
- 추론 결과 원형과 백엔드 JSON 출력 형태를 분리한다.
- 현재 목업 구현과 실제 MediaPipe 구현이 같은 서비스 인터페이스를 공유하도록 설계한다.
- 장기적으로는 배치 처리, 스트리밍 처리, 단일 이미지 처리를 같은 공통 인터페이스 아래에서 분기할 수 있어야 한다.

## 4. 제안 아키텍처

### 4.1 계층 구조

```text
controller
  -> service.job_manager
    -> service.video_reader
    -> service.pose_inference
      -> adapter.mediapipe_adapter
        -> MediaPipe PoseLandmarker

service.pose_inference
  -> service.skeleton_mapper
    -> schema.result
      -> service.analysis_pipeline
```

### 4.2 책임 분리

#### adapter/mediapipe_adapter.py

MediaPipe API 호출을 직접 담당한다.

- 모델 옵션 생성
- `PoseLandmarker` 인스턴스 생성과 종료
- `detect`, `detect_for_video`, `detect_async` 호출 래핑
- MediaPipe 예외를 프로젝트 예외로 변환

#### service/pose_inference.py

포즈 추론 유스케이스를 담당한다.

- 입력 프레임 반복
- `timestamp_ms`와 `running_mode`에 맞는 API 선택
- 추론 결과 직렬화
- 프레임 메타데이터와 추론 결과 병합

#### service/skeleton_mapper.py

추론 결과를 분석 친화적 구조로 변환한다.

- `videoInfo` 조립
- `frames` 배열 조립
- `nextTimestampCursorMs` 계산

#### service/analysis_pipeline.py

스켈레톤 결과를 운동 분석 결과로 바꾼다.

- timeseries 생성
- KPI 계산
- rep segment 조립
- 이슈 생성

## 5. 제안 도메인 모델

### 5.1 추론 옵션

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

RunningMode = Literal["IMAGE", "VIDEO", "LIVE_STREAM"]

@dataclass(slots=True)
class PoseInferenceOptions:
    model_asset_path: Path
    model_variant: Literal["lite", "full", "heavy"] = "full"
    running_mode: RunningMode = "VIDEO"
    delegate: Literal["GPU", "CPU"] = "GPU"
    num_poses: int = 1
    min_pose_detection_confidence: float = 0.5
    min_pose_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    output_segmentation_masks: bool = False
    result_callback: object | None = None
```

초기 구현에서는 `running_mode="VIDEO"`를 기본값으로 두는 것이 자연스럽다.

이유는 아래와 같다.

- 현재 입력이 `video_reader` 결과 중심이다.
- 각 프레임에 `timestamp_ms`가 이미 있다.
- 후속 분석이 시간축 기반이다.

실행 디바이스 정책은 아래가 기본값으로 적절하다.

- 1차 시도: `delegate="GPU"`
- fallback: GPU 초기화 실패 시 `delegate="CPU"`로 자동 재시도

즉, 운영 기본값은 CPU 우선이 아니라 GPU 우선이다.

모델 변형 기본값은 `full`이 적절하다.

이유는 아래와 같다.

- `lite`는 가장 빠르지만 품질 여유가 작다.
- `heavy`는 가장 정확하지만 CPU fallback 시 부담이 매우 커진다.
- `full`은 GPU 기본, CPU fallback 정책과 가장 균형이 좋다.

현재 MVP v1 출력 범위는 2D 스켈레톤만으로 제한하는 것이 적절하다.

이유는 아래와 같다.

- 지금 단계는 저수준 기능 검증 단계다.
- 2D 출력만으로도 프레임 추출, 추론 연결, 웹 오버레이, 기본 분석 검증이 가능하다.
- 3D world landmark와 다중 영상 융합은 별도 후속 단계로 분리하는 편이 설계가 깔끔하다.

### 5.1.1 사용 가능한 모델 변형

공식 Pose Landmarker 모델 번들은 아래 3가지다.

| 모델 | 번들 크기 | detector 입력 | landmarker 입력 | 데이터 타입 | 성향 |
|---|---:|---|---|---|---|
| `lite` | 3 MB | 224 x 224 x 3 | 256 x 256 x 3 | float16 | 속도 최우선 |
| `full` | 6 MB | 224 x 224 x 3 | 256 x 256 x 3 | float16 | 균형형 |
| `heavy` | 26 MB | 224 x 224 x 3 | 256 x 256 x 3 | float16 | 정확도 최우선 |

공식 모델 카드 기준 참고 성능은 아래와 같다.

| 모델 | Pixel 3 CPU | Pixel 3 GPU |
|---|---:|---:|
| `lite` | 약 44 FPS | 약 49 FPS |
| `full` | 약 18 FPS | 약 40 FPS |
| `heavy` | 약 4 FPS | 약 19 FPS |

이 수치는 모바일 기준 참고값이므로 서버 GPU나 데스크톱 환경에서는 절대값보다 상대 비교 지표로 보는 편이 맞다.

### 5.2 프레임별 추론 결과

```python
from dataclasses import dataclass

@dataclass(slots=True)
class PoseLandmarkPoint:
    name: str
    x: float
    y: float
    z: float
    visibility: float | None
    presence: float | None


@dataclass(slots=True)
class PoseFrameResult:
    frame_index: int
    timestamp_ms: float
    pose_detected: bool
    landmarks: list[PoseLandmarkPoint]
    world_landmarks: list[PoseLandmarkPoint] | None = None
    segmentation_mask: object | None = None
```

MVP v1 직렬화 규칙:

- `landmarks`만 반환한다.
- 이 `landmarks`는 2D 스켈레톤 출력으로 사용한다.
- `world_landmarks`는 스키마 참고용 확장 필드로만 두고, MVP v1에서는 비활성화한다.

### 5.3 배치 추론 결과

```python
@dataclass(slots=True)
class PoseInferenceResult:
    source_path: str
    running_mode: str
    model_name: str
    frame_count: int
    detected_frame_count: int
    frames: list[PoseFrameResult]
```

실제 구현에서는 긴 비디오 대응을 위해 `frames: list[...]` 대신 iterator 반환과 summary 반환을 분리하는 편이 낫다.

## 6. 세부 처리 흐름

### 6.1 초기화

1. 모델 파일 존재 여부를 검증한다.
2. `model_variant`에 맞는 `.task` 번들을 선택한다.
3. `delegate="GPU"`로 `MediaPipeAdapter.create_landmarker()`를 먼저 시도한다.
4. GPU 초기화가 실패하면 `delegate="CPU"`로 한 번 더 시도한다.
5. `running_mode`, confidence, `num_poses` 옵션을 적용한다.
6. GPU, CPU 모두 실패하면 즉시 예외를 발생시킨다.

### 6.2 프레임 입력 준비

입력 프레임은 `ExtractedFrame` 기준으로 받는다.

- `frame.image`
- `frame.index`
- `frame.timestamp_ms`
- `frame.width`
- `frame.height`

MediaPipe 호출 직전 변환은 아래 순서를 권장한다.

1. 이미지 존재 여부 확인
2. 필요 시 BGR -> RGB 변환
3. `mp.Image` 객체 생성
4. `timestamp_ms`를 정수 또는 규격에 맞는 값으로 정리

### 6.3 추론 실행

기본 구현은 `VIDEO` 모드 기반으로 시작한다.

- `PoseLandmarker.detect_for_video(mp_image, timestamp_ms)`
- 프레임 순서 보장
- 시간축 결과와 후속 분석 연결 용이

추후 확장 지점:

- 이미지 단건 처리면 `detect()`
- 실시간 카메라나 웹소켓 입력이면 `detect_async()`

### 6.4 결과 직렬화

MediaPipe 원본 결과는 내부 구조가 후속 분석에 직접 쓰기에는 다소 무겁다.

따라서 service 계층에서 아래 규칙으로 직렬화하는 것이 좋다.

- 프레임 인덱스 유지
- 원본 `timestamp_ms` 유지
- 포즈가 없으면 `poseDetected=False`
- 랜드마크는 이름 있는 리스트로 정리
- 가시성, presence가 있으면 포함
- world landmark는 선택 필드로 둔다

현재 MVP v1에서는 `PoseLandmarkerResult`에서 2D 좌표만 직렬화 대상으로 본다.

즉, 현재 구현 범위는 아래와 같다.

- 반환: `landmarks`
- 보류: `world_landmarks`
- 보류: 다중 영상 3D 융합 결과

### 6.5 후속 처리 연동

`SkeletonMapperService.map_landmarks()`는 아래 역할을 담당한다.

- 프레임 결과를 `skeleton.frames`로 정리
- 추출 결과 메타데이터를 `skeleton.videoInfo`로 정리
- 다음 커서 시간을 `nextTimestampCursorMs`로 계산

이후 `AnalysisPipelineService.analyze()`가 시간 기반 KPI와 이슈를 생성한다.

장기적으로는 2개 이상의 영상을 병렬 처리해 얻은 여러 3D 객체를 융합하는 별도 계층을 둘 수 있다.

다만 이 계층은 MVP v1 범위 밖으로 둔다.

## 7. 제안 모듈 인터페이스

### adapter/mediapipe_adapter.py

```python
class MediaPipeAdapter:
    def create_landmarker(self, options: PoseInferenceOptions): ...
    def close_landmarker(self) -> None: ...
    def detect(self, image): ...
    def detect_for_video(self, image, timestamp_ms: int): ...
    def detect_async(self, image, timestamp_ms: int) -> None: ...
    def active_delegate(self) -> str: ...
```

### service/pose_inference.py

```python
class PoseInferenceService:
    def infer(
        self,
        frames: list[ExtractedFrame],
        options: PoseInferenceOptions | None = None,
    ) -> list[dict]: ...

    def iter_infer(
        self,
        frames,
        options: PoseInferenceOptions | None = None,
    ): ...
```

`infer()`는 소규모 파일이나 테스트용, `iter_infer()`는 실제 긴 비디오 분석 파이프라인용으로 분리하는 구성이 적절하다.

## 8. 예외 및 장애 처리 정책

### 예외 유형

- `ModelAssetNotFoundError`
- `LandmarkerInitializationError`
- `GpuDelegateUnavailableError`
- `InvalidFrameInputError`
- `PoseInferenceError`
- `ResultSerializationError`

### 처리 기준

- 모델 open 실패:
  - GPU로 먼저 시도한다.
  - GPU 실패 시 CPU fallback을 한 번 시도한다.
  - 둘 다 실패하면 작업 실패 처리한다.
- 일부 프레임 이미지 누락:
  - 초기 버전은 작업 실패로 처리하는 편이 단순하다.
- 특정 프레임 추론 실패:
  - 추후 partial failure 정책으로 확장 가능
  - 초기 버전은 첫 실패 시 작업 실패가 무난하다.
- 결과 직렬화 실패:
  - 스키마 불일치 가능성이 크므로 즉시 실패 처리

초기 버전에서는 단순성을 위해 "첫 추론 실패 시 작업 실패"가 적절하다.

## 9. 성능 관점 권고

- 기본 흐름은 `video_reader`의 샘플링 결과를 그대로 사용한다.
- 실행 기본값은 GPU 가속이며, CPU는 fallback 경로로 둔다.
- 모델 기본값은 `full`로 두고, `lite/heavy`는 명시적 선택으로 분리하는 편이 낫다.
- RGB 변환은 MediaPipe 호출 직전에만 수행한다.
- 긴 영상은 결과 리스트 누적 대신 iterator 기반 확장을 고려한다.
- 모델 변형이 여러 개라면 정확도 우선과 속도 우선 프로파일을 분리하는 편이 낫다.
- segmentation mask는 실제 사용 전까지 기본 비활성화가 적절하다.
- MVP v1에서는 2D 출력만 유지해 직렬화 비용과 소비자 복잡도를 줄이는 편이 낫다.

추가 참고 사항:

- 아직 실측 전이므로, 모든 환경에서 같은 GPU 경로가 안정적이라고 가정하지 않는다.
- 성능 병목은 프레임 추출, RGB 변환, MediaPipe 추론, 결과 직렬화가 함께 만든다.
- 따라서 MediaPipe만 단독 최적화하기보다 `video_reader`와 묶은 end-to-end 기준으로 봐야 한다.
- `num_poses`를 크게 두면 비용이 늘어나므로 운동 분석 기본값은 1이 자연스럽다.
- world landmark, segmentation mask 같은 확장 출력은 필요할 때만 켜는 편이 낫다.
- 따라서 운영에서는 "GPU 우선, CPU fallback"을 기본 정책으로 두고 실제 fallback 발생률을 추적하는 편이 낫다.
- 특히 `heavy`는 CPU fallback 시 처리량 저하 폭이 커서 기본값으로 두기보다는 품질 우선 프로파일로 분리하는 편이 안전하다.

추후 선택 개선을 위한 후보 항목:

- `model_variant`
  - lite, full, heavy 중 어떤 모델을 사용할지 지정하기 위한 핵심 옵션
- `delegate`
  - 기본값은 GPU로 두고, CPU fallback 여부와 장치별 성능 차이를 관리하기 위한 옵션 후보
- `output_segmentation_masks`
  - 포즈 외 보조 출력이 실제 제품 가치가 있는지 검증하기 위한 옵션 후보
- `batch_profile`
  - `accuracy`, `balanced`, `speed` 같은 프리셋으로 운영 복잡도를 낮출지 검토하기 위한 후보

위 항목들은 "지금 바로 구현한다"는 의미가 아니라, 실제 MediaPipe 연결 이후 성능 검증에서 비교 대상으로 포함할 수 있는 참고안으로 남긴다.

## 10. 구현 순서 제안

### Phase 1

- MediaPipe Tasks Vision 의존성 확정
- `adapter/mediapipe_adapter.py` 실제 구현
- `service/pose_inference.py`에 실제 landmarker 호출 연결
- 2D 스켈레톤 결과 직렬화 기본 구조 정리

### Phase 2

- `VIDEO` 모드 기준 end-to-end 연결
- `skeleton_mapper.py`와 실제 결과 구조 정합성 보정
- 오류 코드와 예외 메시지 정리
- 샘플 비디오 회귀 테스트 추가

### Phase 3

- `IMAGE`, `LIVE_STREAM` 확장
- iterator 기반 대용량 처리
- partial failure 정책
- 모델 변형별 성능 비교
- segmentation mask / world landmark 확장 검토
- 다중 영상 병렬 처리와 3D 융합 검토

## 11. 테스트 전략

### 단위 테스트

- 존재하지 않는 모델 파일 입력
- 빈 프레임 또는 `image=None` 처리
- `running_mode`별 분기 검증
- 포즈 미검출 프레임 직렬화 검증
- 랜드마크 좌표 스키마 검증

### 통합 테스트

- 샘플 비디오 1개에 대해 프레임 추출 후 포즈 추론
- skeleton mapping까지 이어지는 흐름 검증
- analysis pipeline 입력으로 연결되는지 검증

### 수동 검증 포인트

- 실제 감지 프레임 수
- 프레임별 `timestampMs` 정합성
- 랜드마크 좌표 범위 일관성
- 포즈 미검출 프레임 처리 방식
- 긴 비디오에서 메모리 사용량 증가 여부
- 샘플링 밀도에 따른 end-to-end 처리 시간 차이

## 12. 권장 초안 결론

이번 기능은 MediaPipe 자체를 수정하는 작업이 아니라, MediaPipe Tasks Vision Pose Landmarker를 현재 Python 백엔드 구조에 맞게 adapter/service 분리로 수용하는 작업으로 정의하는 것이 맞다.

권장 시작점은 다음 두 파일이다.

- `adapter/mediapipe_adapter.py`: MediaPipe 세부사항 캡슐화
- `service/pose_inference.py`: 프레임 순회, 추론 호출, 결과 직렬화 담당

이후 `service/skeleton_mapper.py`와 `service/analysis_pipeline.py`가 이 결과를 소비하는 형태로 연결하면, 포즈 랜드마커 기능이 독립적으로도 쓰이고 전체 운동 분석 파이프라인에도 재사용될 수 있다.
