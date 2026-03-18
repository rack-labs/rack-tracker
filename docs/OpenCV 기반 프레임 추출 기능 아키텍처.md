# OpenCV 기반 프레임 추출 기능 아키텍처 초안

> 문서 동기화 강제 프롬프트
>
> 이 문서를 수정하는 AI 또는 작성자는 반드시 아래 짝 문서를 함께 확인해야 한다.
>
> - `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\docs\OpenCV 기반 프레임 추출 기능 명세.md`
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

`poseLandmarker_Python` 백엔드에 OpenCV 기반 프레임 추출 계층을 추가해 다음 요구를 충족한다.

- 비디오 파일을 안정적으로 열고 프레임을 순차 또는 샘플링 방식으로 읽는다.
- 추출 결과를 MediaPipe 포즈 추론 파이프라인에 바로 넘기거나 이미지 파일로 저장할 수 있게 한다.
- 프레임 번호, 타임스탬프, 저장 경로, 백엔드 정보 등 운영에 필요한 메타데이터를 함께 남긴다.
- OpenCV 내부 구조와 현재 프로젝트의 계층 구조를 분리해 향후 구현체 교체나 최적화가 가능하게 한다.

## 2. 참고한 코드베이스 관찰

### OpenCV fork 관찰

- 공개 API는 `modules/videoio/include/opencv2/videoio.hpp`에 정의되어 있다.
- 실제 `VideoCapture` 오픈, `read`, `grab`, `retrieve`, `get`, `set`, `release` 흐름은 `modules/videoio/src/cap.cpp`에 구현되어 있다.
- `VideoCapture::open()`은 백엔드 레지스트리를 통해 파일 입력에 맞는 backend를 선택한다.
- `CAP_PROP_POS_FRAMES`, `CAP_PROP_POS_MSEC`, `CAP_PROP_FPS`, `CAP_PROP_FRAME_COUNT`, `CAP_PROP_BACKEND` 같은 속성이 프레임 추출 설계의 핵심이다.
- Python 바인딩은 `modules/python/src2/cv2.cpp` 중심으로 노출되며, Python 레벨의 `cv2.VideoCapture`는 결국 C++ `VideoCapture` 래퍼로 동작한다.

### 현재 프로젝트 관찰

- `adapter/opencv_adapter.py`는 현재 스텁 상태다.
- `service/video_reader.py`도 현재 스텁 상태다.
- `service/analysis_pipeline.py`, `service/pose_inference.py`가 후속 처리 계층이므로, 프레임 추출은 이 서비스들보다 앞단의 독립 서비스로 두는 것이 자연스럽다.
- `pyproject.toml`에는 아직 `opencv-python` 또는 `opencv-python-headless` 의존성이 없다.

## 3. 설계 원칙

- OpenCV 의존 코드는 adapter 계층에 격리한다.
- 비즈니스 규칙은 service 계층에 둔다.
- 컨트롤러는 요청 검증과 job orchestration만 담당한다.
- 프레임 추출 결과는 "메모리 반환"과 "디스크 저장" 두 경로를 모두 지원하되, 코어 추출 로직은 하나로 유지한다.
- 긴 비디오에서도 메모리 폭주를 막기 위해 generator 또는 iterator 기반 처리로 확장 가능해야 한다.
- MediaPipe 입력 요구사항과 저장 요구사항을 분리해, RGB 변환과 이미지 인코딩 비용을 호출자 선택 옵션으로 둔다.

## 4. 제안 아키텍처

### 4.1 계층 구조

```text
controller
  -> service.job_manager
    -> service.video_reader
      -> adapter.opencv_adapter
        -> cv2.VideoCapture

service.video_reader
  -> schema.job / schema.result / 신규 frame schema
  -> service.pose_inference
```

### 4.2 책임 분리

#### adapter/opencv_adapter.py

OpenCV API 호출을 직접 담당한다.

- 비디오 open / close
- 메타데이터 조회
- seek
- `read()` 반복
- backend 이름 조회
- OpenCV 예외를 프로젝트 예외로 변환

#### service/video_reader.py

프레임 추출 유스케이스를 담당한다.

- 추출 옵션 해석
- interval / target fps / time range 정책 계산
- 저장 여부 판단
- 프레임 메타데이터 조립
- 후속 파이프라인 전달 형식 구성

#### service/analysis_pipeline.py

OpenCV 프레임 추출 서비스와 MediaPipe 포즈 추론 서비스를 연결한다.

- video -> OpenCV frame iterator
- extracted frame -> MediaPipe pose inference
- frame metadata + pose result 병합

#### schema/*

입출력 스키마를 명시한다.

- 프레임 추출 요청 옵션
- 프레임 메타데이터
- 배치 추출 결과
- 실패 사유 코드

## 5. 제안 도메인 모델

### 5.1 요청 옵션

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SamplingMode = Literal["all", "every_n_frames", "target_fps", "time_range"]

@dataclass(slots=True)
class FrameExtractionOptions:
    video_path: Path
    sampling_mode: SamplingMode = "all"
    every_n_frames: int | None = None
    target_fps: float | None = None
    start_ms: float | None = None
    end_ms: float | None = None
    output_dir: Path | None = None
    save_images: bool = False
    image_extension: str = "jpg"
    jpeg_quality: int = 95
    convert_bgr_to_rgb: bool = False
    preferred_backend: str | None = None
    resize_width: int | None = None
    prefetch_buffer: int = 0
```

아래 필드는 초기 구현의 확정 요구사항이라기보다, 추후 속도 실험 결과에 따라 채택 여부를 결정할 수 있는 참고 옵션이다.

- `preferred_backend`: 플랫폼별 backend 성능 차이 비교를 위한 선택 힌트
- `resize_width`: 추론 전 다운스케일 실험을 위한 옵션
- `prefetch_buffer`: reader/consumer 분리 시 prefetch 깊이 조절용 옵션

`decode_mode`나 `benchmark_profile` 같은 상위 옵션도 후보가 될 수 있지만, 초기 버전에는 넣지 않고 문서 차원에서만 참고 사항으로 관리하는 편이 단순하다.

### 5.2 프레임 메타데이터

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(slots=True)
class ExtractedFrame:
    index: int
    timestamp_ms: float
    timestamp_sec: float
    backend: str
    width: int
    height: int
    image: "np.ndarray | None"
    saved_path: Path | None
```

### 5.3 배치 결과

```python
@dataclass(slots=True)
class FrameExtractionResult:
    source_path: Path
    backend: str
    source_fps: float
    frame_count: int | None
    extracted_count: int
    frames: list[ExtractedFrame]
```

실제 구현에서는 긴 비디오 대응을 위해 `frames: list[...]` 대신 iterator 반환형과 summary 반환형을 분리하는 편이 낫다.

## 6. 세부 처리 흐름

### 6.1 초기화

1. 입력 파일 존재 여부와 확장자를 검증한다.
2. `OpenCvAdapter.open_video()`로 `cv2.VideoCapture`를 연다.
3. `isOpened()` 실패 시 즉시 예외를 발생시킨다.
4. `CAP_PROP_FPS`, `CAP_PROP_FRAME_COUNT`, `CAP_PROP_FRAME_WIDTH`, `CAP_PROP_FRAME_HEIGHT`, `CAP_PROP_BACKEND`를 읽는다.

### 6.2 샘플링 정책 결정

샘플링 정책은 service 계층에서 결정한다.

- `all`: 모든 프레임 추출
- `every_n_frames`: `frame_index % n == 0`
- `target_fps`: 원본 FPS를 기준으로 stride 계산
- `time_range`: `start_ms <= timestamp_ms <= end_ms` 범위만 처리

`target_fps`는 단순 정수 stride만 쓰면 누적 오차가 생길 수 있으므로, 아래 방식이 더 안전하다.

- `next_target_ms`를 유지하고
- 현재 프레임의 `timestamp_ms`가 목표 시간 이상일 때만 채택한다.

이 방식은 VFR 또는 seek 이후에도 상대적으로 안정적이다.

### 6.3 프레임 읽기

기본 구현은 `read()` 기반으로 시작한다.

- 구현 단순성
- Python `cv2.VideoCapture` 사용성
- MediaPipe 파이프라인 연결 용이

추후 최적화 지점:

- 정확한 멀티스트림 동기화가 필요하면 `grab()` / `retrieve()` 분리
- 특정 위치 재시작이 필요하면 `CAP_PROP_POS_FRAMES` seek

### 6.4 저장

저장 로직은 코어 추출과 분리한다.

- 추출 여부 결정
- 필요 시 파일명 생성
- `cv2.imwrite()`로 저장
- 저장 성공 여부 확인

권장 파일명:

```text
frame_{frame_index:06d}_{timestamp_ms:010.0f}.jpg
```

이 형식은 정렬, 재처리, 디버깅에 유리하다.

### 6.5 후속 처리 연동

`convert_bgr_to_rgb=True`일 때만 `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)`를 적용한다.

- OpenCV 디스크 저장은 BGR 그대로도 문제없다.
- OpenCV는 프레임 추출만 담당하고 포즈 추론은 수행하지 않는다.
- MediaPipe 입력은 RGB 기준이므로, MediaPipe로 넘기기 직전에만 변환이 필요하다.
- 따라서 저장 전역 공통 변환이 아니라 MediaPipe 소비 직전 선택적으로 변환하는 편이 전체 비용 관점에서 낫다.

## 7. 제안 모듈 인터페이스

### adapter/opencv_adapter.py

```python
class OpenCvAdapter:
    def open_video(self, video_path: str) -> None: ...
    def close(self) -> None: ...
    def is_opened(self) -> bool: ...
    def get_metadata(self) -> dict: ...
    def seek_frame(self, frame_index: int) -> bool: ...
    def read_frame(self) -> tuple[bool, "np.ndarray | None"]: ...
    def backend_name(self) -> str: ...
```

### service/video_reader.py

```python
class VideoReaderService:
    def extract_frames(
        self,
        options: FrameExtractionOptions,
    ) -> FrameExtractionResult: ...

    def iter_frames(
        self,
        options: FrameExtractionOptions,
    ): ...
```

`extract_frames()`는 소규모 파일이나 테스트용, `iter_frames()`는 실제 분석 파이프라인용으로 분리하는 구성이 적절하다.

## 8. 예외 및 장애 처리 정책

### 예외 유형

- `VideoSourceNotFoundError`
- `VideoOpenError`
- `VideoMetadataError`
- `FrameReadError`
- `FrameWriteError`
- `InvalidSamplingOptionError`

### 처리 기준

- open 실패: 즉시 실패
- metadata 일부 누락: 경고 후 가능한 범위만 진행
- 특정 frame read 실패:
  - 중간 1회성 실패는 정책적으로 skip 가능
  - 연속 실패 또는 첫 프레임 실패는 작업 실패 처리
- image write 실패: 저장 모드일 때 작업 실패 또는 partial failure로 기록

초기 버전에서는 단순성을 위해 "첫 read 실패 또는 저장 실패 시 작업 실패"가 적절하다.

## 9. 성능 관점 권고

- 기본 배포는 `opencv-python-headless` 우선 검토
- 결과 리스트 누적 대신 iterator 우선 설계
- 저장 기능이 필요 없으면 메모리 내 전달만 수행
- RGB 변환은 반드시 소비 직전에 수행
- 긴 영상은 job 단위 비동기 처리와 진행률 추적을 붙이는 편이 맞다

추가 참고 사항:

- 아직 실측 전이므로, "OpenCV가 HTML `video`보다 항상 빠르다"는 전제를 문서 기본 가정으로 두지 않는다.
- 대신 속도 개선 여지가 있는 선택지를 옵션 후보로 열어 두고, 추후 벤치마크 결과에 따라 채택 여부를 결정한다.
- 샘플링 분석이 주 목적이면 전체 decode 후 폐기하는 방식보다, 필요한 시점만 가져오는 fast path를 별도로 검토할 가치가 있다.
- backend 선택, downscale, prefetch, seek/grab 기반 sparse sampling은 모두 실험 후보로 남겨 둔다.
- 정확도 우선 경로와 속도 우선 경로를 완전히 같은 구현으로 강제하지 말고, 공통 인터페이스 아래에서 분기 가능한 구조를 유지하는 편이 낫다.

추후 선택 개선을 위한 후보 항목:

- `preferred_backend`
  - Windows에서 FFmpeg, MSMF 등 backend별 처리량 차이를 비교하기 위한 옵션 후보
- `resize_width`
  - 포즈 추론 이전에 해상도를 줄여 전체 처리 시간을 낮출 수 있는지 검증하기 위한 옵션 후보
- `prefetch_buffer`
  - 프레임 읽기와 후속 추론을 producer-consumer 구조로 분리했을 때 처리량 개선이 있는지 보기 위한 옵션 후보
- `decode_mode`
  - `full`, `sampled_fast` 같은 모드로 나눠 전체 프레임 순차 decode와 sparse sampling 최적화 경로를 분리할지 검토하기 위한 후보
- `benchmark_profile`
  - `accuracy`, `balanced`, `speed` 같은 프리셋으로 운영 복잡도를 줄일 수 있는지 검토하기 위한 후보

위 항목들은 "지금 바로 구현한다"는 의미가 아니라, Phase 3 이전 성능 검증에서 비교 대상으로 포함할 수 있는 참고안으로 남긴다.

현재 FastAPI 백엔드 구조를 보면, 프레임 추출은 동기 메서드로 구현하되 job manager에서 백그라운드 실행하는 구조가 가장 무난하다.

## 10. 구현 순서 제안

### Phase 1

- `pyproject.toml`에 OpenCV 의존성 추가
- `adapter/opencv_adapter.py` 실제 구현
- `service/video_reader.py`에 all / every_n_frames 구현
- 저장 경로 옵션과 메타데이터 반환 추가

### Phase 2

- `target_fps` 정책 추가
- MediaPipe 전달 직전 RGB 변환 옵션 추가
- `analysis_pipeline.py`와 연결
- 결과 schema 정리

### Phase 3

- iterator 기반 대용량 처리
- partial failure 정책
- 진행률 로깅
- 벤치마크 및 샘플 비디오 회귀 테스트
- HTML `video` 경로와 OpenCV 경로의 동일 조건 벤치마크
- backend / resize / prefetch / sparse sampling 전략 비교 실험

## 11. 테스트 전략

### 단위 테스트

- 존재하지 않는 파일 입력
- FPS가 0 또는 비정상인 메타데이터 처리
- `every_n_frames=1`, `2`, `5` 동작
- 저장 파일명 규칙 검증
- `target_fps < source_fps`, `target_fps > source_fps` 처리

### 통합 테스트

- 샘플 비디오 1개에 대해 전체 프레임 추출
- 샘플 비디오 1개에 대해 샘플링 추출
- 추출 후 `pose_inference`로 연결되는 흐름 검증

### 수동 검증 포인트

- 실제 저장된 프레임 수
- 타임스탬프 증가 일관성
- backend 이름 확인
- Windows 환경에서 파일 잠금 없이 release 되는지 확인
- 동일 비디오, 동일 샘플링 조건에서 HTML `video` 대비 처리 시간 비교
- downscale 적용 여부에 따른 추론 포함 end-to-end 시간 비교
- backend 변경 시 초기 open 시간과 지속 처리량 차이 비교

## 12. 권장 초안 결론

이번 기능은 OpenCV 자체를 수정하는 작업이 아니라, OpenCV fork의 `videoio` 설계를 참고해 현재 Python 백엔드에 적절한 adapter/service 분리를 도입하는 작업으로 정의하는 것이 맞다.

권장 시작점은 다음 두 파일이다.

- `adapter/opencv_adapter.py`: OpenCV 세부사항 캡슐화
- `service/video_reader.py`: 프레임 추출 정책과 결과 조립

이후 `analysis_pipeline.py`가 `iter_frames()`를 소비하는 형태로 연결하면, 프레임 추출 기능이 독립적으로도 쓰이고 포즈 분석 파이프라인에도 재사용될 수 있다.
