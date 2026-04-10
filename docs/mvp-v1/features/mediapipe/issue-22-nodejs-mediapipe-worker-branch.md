[proposal] poseLandmarker_Python 내부 Node.js MediaPipe subprocess 워커 전환

브랜치명: `22-proposal-nodejs-mediapipe-subprocess-worker`

## 작업 목적
현재 `poseLandmarker_Python`는 FastAPI 기반 백엔드, OpenCV 기반 프레임 추출, MediaPipe Python 기반 포즈 추론, 스켈레톤/분석/benchmark 생성으로 구성되어 있다.

하지만 `docs/mvp-v1/features/mediapipe/issue-18-enable-gpu-delegate.md`에서 정리한 것처럼, WSL 환경에서 MediaPipe Python GPU delegate를 안정적으로 실사용 경로로 고정하는 데 한계가 확인됐다.

이 작업의 목적은 `poseLandmarker_Python`의 전체 서비스 구조와 API 표면은 최대한 유지하되, MediaPipe 추론부만 Node.js 런타임으로 분리하고 이를 `poseLandmarker_Python/node_worker/` 내부 subprocess 워커로 연결하는 방향을 기준안으로 정리하는 것이다.

## 문제 정의
- 현재 Python 프로젝트는 서비스 구조 자체는 충분히 분리돼 있지만, 실제 포즈 추론 엔진은 `poseLandmarker_Python/adapter/mediapipe_adapter.py`에 직접 결합돼 있다.
- issue-18 기준으로 WSL에서는 MediaPipe Python GPU delegate가 안정적으로 NVIDIA GPU direct path를 보장하지 못한다.
- 단순히 Python 코드를 유지한 채 delegate 옵션만 바꾸는 접근으로는 이 문제가 해결되지 않을 가능성이 높다.
- 반면 현재 저장소의 `poseLandmarker_JavaScript`는 브라우저 전제 코드이므로, 이를 그대로 서버용 Node.js 추론 엔진으로 재사용하기는 어렵다.

## PoC 확인 결과와 현재 결정
- 2026-03-27 기준 PoC에서 `@mediapipe/tasks-vision`을 순수 Node.js subprocess에서 직접 초기화하면 `document is not defined` 오류가 발생했다.
- 즉, 현재 선택한 MediaPipe JavaScript 런타임은 이 저장소 환경에서 브라우저 DOM 전역 없이 바로 서버 추론 엔진으로 동작하지 않았다.
- 이 결과는 "Node 워커 경계 설계" 자체의 실패가 아니라, "선택한 JS MediaPipe 런타임의 실행 환경 가정" 문제로 해석한다.
- 엔드포인트 기기 성능 의존을 피하기 위해 연산은 계속 서버에서 수행해야 한다.
- 따라서 현재 단계의 우회 전략은 "클라이언트 브라우저 추론"이 아니라 "서버에서 headless browser 런타임을 띄워 MediaPipe JS를 실행"하는 것이다.
- 이 방식은 최종 운영 정답으로 확정한 것이 아니라, 현재 목표인 성능 검증과 GPU 사용 가능성 검증을 위한 임시 경로다.

## 제안 방향
- 기존 `poseLandmarker_Python`를 기준 구현으로 유지한다.
- Node.js MediaPipe 코드는 `poseLandmarker_Python/node_worker/` 아래에 둔다.
- Python FastAPI 서버는 그대로 유지하고, MediaPipe 추론 실행 경로만 Node.js subprocess 워커 호출로 교체한다.
- 핵심 원칙은 "전체 프로젝트 재작성"이 아니라 "추론 엔진 레이어만 분기"다.
- 이번 목표는 별도 Node 서버를 띄우는 구조가 아니라, Python이 필요할 때 Node 프로세스를 실행하는 구조다.
- 단, 현재 PoC 단계의 실제 워커 내부 런타임은 순수 Node가 아니라 headless browser를 포함할 수 있다.

## 권장 구조 판단

### 우선 원칙
- `controller`, `schema`, 결과 JSON shape, benchmark 메타데이터 계약은 최대한 유지한다.
- `video_reader`, `skeleton_mapper`, `analysis_pipeline`, `llm_feedback`처럼 MediaPipe 자체와 직접 결합되지 않은 계층은 가능한 한 동일한 책임 구조를 유지한다.
- 가장 큰 분기 지점은 `service/pose_inference.py`와 그 아래 adapter 경계다.

### 이번 권장 분기 방식
이번 목표 기준으로 가장 현실적인 방향은 아래 구조다.

1. `poseLandmarker_Python`는 그대로 유지
2. `poseLandmarker_Python/node_worker/`에 Node.js 추론 워커 추가
3. Python이 subprocess로 Node worker를 호출
4. Node worker가 내부에서 headless browser 런타임을 띄운다
5. browser 런타임이 MediaPipe JS를 실행한다
6. Node worker가 JSON 결과를 반환

이유는 아래와 같다.
- FastAPI API 표면과 기존 결과 구조를 그대로 유지하기 쉽다.
- PoC와 초기 구현 범위를 가장 작게 잡을 수 있다.
- 별도 장기 실행 Node 서버 운영, 포트 관리, 프로세스 생명주기 관리를 바로 도입할 필요가 없다.
- 나중에 필요하면 동일 계약을 유지한 채 장기 실행 Node 서버형으로 옮길 수 있다.

## 제안 폴더 구조

### 이번 목표 기준 권장안
```text
rack-tracker-forked/
  poseLandmarker_Python/
    adapter/
    service/
    node_worker/
      package.json
      src/
      models/
      README.md
  docs/
```

`node_worker/`는 아래 성격을 갖는다.
- Node.js 기반 MediaPipe 추론 워커 전용 디렉터리
- 독립 `package.json`과 Node 의존성 보유
- 입력: frame batch 또는 frame directory + options JSON
- 출력: Python `PoseInferenceResult`와 호환 가능한 JSON
- 현재 PoC 기준 내부 실행 엔진은 headless browser 기반 MediaPipe JS일 수 있다

이 경우 Python 프로젝트는 아래처럼 바뀐다.
- `service/pose_inference.py`가 직접 MediaPipe Python을 호출하지 않음
- 대신 내부 client 계층이 `node_worker/`를 subprocess로 호출
- Node 결과를 기존 `PoseInferenceResult` 형태로 역직렬화

### 장기 확장 가능안
필요해지면 이후 아래 구조로도 확장할 수 있다.

```text
rack-tracker-forked/
  poseLandmarker_Python/
  poseLandmarker_Node/
  docs/
```

하지만 이는 이번 목표가 아니라 후속 선택지다.

## 아키텍처 초안

### 권장 데이터 흐름
1. Python FastAPI가 업로드와 job 생성 처리
2. Python이 OpenCV 기반 frame extraction 수행
3. Python이 추출된 frame 메타데이터와 옵션을 subprocess로 `node_worker`에 전달
4. Node worker가 headless browser 런타임을 기동
5. browser 런타임이 MediaPipe JS 추론 수행
6. Node worker가 frame별 landmark 결과와 delegate/runtime 메타데이터를 JSON으로 반환
7. Python이 기존 `skeleton_mapper`, `analysis_pipeline`, `benchmarking` 흐름을 계속 수행

### 이 구조의 장점
- 기존 API 표면을 거의 유지할 수 있다.
- benchmark와 결과 파일 형식을 재사용하기 쉽다.
- Node.js 실험 범위를 추론 엔진으로 제한할 수 있다.
- 엔드포인트 기기 성능 의존을 제거하면서도 MediaPipe JS 경로를 서버에서 검증할 수 있다.
- 장기적으로 다른 추론 엔진으로 교체할 때도 worker 경계를 재사용할 수 있다.

### 현재 선택 이유
- 클라이언트 브라우저 추론은 스마트폰, 저사양 노트북, 웹캠 단말 성능에 직접 묶인다.
- 이번 검증의 목적은 "브라우저를 쓰느냐"가 아니라 "엔드포인트가 아닌 서버에서 연산하느냐"다.
- 서버에서 headless browser를 띄우면 브라우저 오버헤드는 생기지만, 클라이언트 성능 병목은 제거할 수 있다.
- 따라서 현재 단계에서는 "운영 최적 구조"보다 "서버 측 성능 검증이 가능한 구조"를 우선한다.

## Node 워커 설계 원칙

### 입력 계약
- Python이 넘기는 입력은 가능하면 명시적 JSON으로 고정한다.
- 포함 권장 항목:
  - `jobId`
  - `frames`
  - `modelVariant`
  - `modelAssetPath`
  - `delegate`
  - `runningMode`
  - confidence 옵션

### 출력 계약
- Node worker 출력은 Python `PoseInferenceResult` shape와 최대한 맞춘다.
- 최소 포함 권장 항목:
  - `sourcePath`
  - `runningMode`
  - `modelName`
  - `frameCount`
  - `detectedFrameCount`
  - `requestedDelegate`
  - `actualDelegate`
  - `delegateFallbackApplied`
  - `delegateErrors`
  - `frames`

### 중요한 제약
- `poseLandmarker_JavaScript` 브라우저 코드를 그대로 가져오지 않는다.
- `document`, `video`, canvas, CDN 기반 WASM 로딩 같은 브라우저 의존은 장기적으로 제거 대상이지만, 현재 PoC 단계에서는 headless browser 내부로 격리한다.
- 순수 Node 런타임에서 파일 입력 기반 batch inference는 현재 PoC에서 실패했다.
- 초기 연결 방식은 subprocess 호출을 기준으로 설계한다.
- Python 코드 여러 곳에서 직접 `node ...` 명령을 흩뿌리지 말고, 전용 client 계층으로 감싼다.

## Python-Node 경계 원칙

### 이번 목표의 호출 방식
- Python FastAPI 외에 별도 Node 서버는 띄우지 않는다.
- Python이 job 처리 중 필요할 때마다 Node 프로세스를 실행한다.
- 입력은 stdin JSON 또는 임시 파일 JSON 중 하나로 전달한다.
- 출력은 stdout JSON 또는 결과 파일 JSON으로 수집한다.
- Node worker 내부에서는 필요하면 headless browser 프로세스를 추가로 띄운다.

### 권장 이유
- 구현 범위가 작다.
- 장애 지점이 적다.
- 서버 두 개의 기동 순서를 관리할 필요가 없다.
- 이후 서버형으로 바꿔도 입출력 계약만 유지하면 상위 계층 변경을 줄일 수 있다.
- 엔드포인트 기기와 무관한 서버 성능 검증을 바로 시작할 수 있다.

### 장기 전환 가능성
향후 아래 조건이 생기면 Node 서버형 전환을 검토할 수 있다.
- 프로세스 기동 비용이 병목이 될 때
- 모델 초기화를 재사용해야 할 때
- 장시간 유지되는 worker pool이 필요할 때
- Python과 Node를 독립 배포해야 할 때

이 경우에도 바뀌어야 하는 범위는 가능한 한 아래로 제한해야 한다.
- `node_worker_client`
- 프로세스 실행 코드
- 타임아웃, 재시도, 헬스체크 방식

반대로 아래 계층은 유지하는 것이 목표다.
- `controller`
- `job_manager` 상위 흐름
- `skeleton_mapper`
- `analysis_pipeline`
- `benchmarking`
- 결과 JSON 스키마

## node_worker_client 인터페이스 초안

### 목적
- Python 서비스 계층이 `subprocess.run("node ...")`를 직접 여기저기 호출하지 않도록 경계를 고정한다.
- 현재는 subprocess 호출형을 구현하되, 나중에 필요하면 같은 인터페이스를 유지한 채 Node 서버형 client로 교체할 수 있게 한다.
- `service/pose_inference.py`는 "어떻게 Node를 실행하는가"보다 "어떤 추론 결과를 받는가"에 집중하게 만든다.

### 권장 배치 위치
- `poseLandmarker_Python/service/node_worker_client.py`

### 책임 범위
- Node worker 실행 명령 조립
- 입력 payload 직렬화
- stdout/stderr 수집
- 종료 코드 검증
- timeout 처리
- worker JSON 응답을 Python 도메인 객체 또는 dict로 역직렬화
- worker 실행 실패를 Python 쪽 예외로 변환

### 맡기지 않을 책임
- FastAPI request parsing
- frame extraction
- skeleton mapping
- benchmark 조립 전체
- 결과 페이지네이션

### 권장 인터페이스 예시
```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

### subprocess 구현체 예시
```python
class SubprocessNodeWorkerClient(NodeWorkerClient):
    def __init__(
        self,
        worker_entry: Path,
        node_binary: str = "node",
        timeout_seconds: float = 120.0,
    ) -> None:
        self._worker_entry = worker_entry
        self._node_binary = node_binary
        self._timeout_seconds = timeout_seconds

    def run_pose_inference(
        self,
        frames: list[ExtractedFrame],
        options: PoseInferenceOptions,
        source_path: str,
    ) -> PoseInferenceResult:
        ...
```

### 장기 확장용 서버형 구현체 예시
```python
class HttpNodeWorkerClient(NodeWorkerClient):
    def __init__(self, base_url: str, timeout_seconds: float = 120.0) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds

    def run_pose_inference(
        self,
        frames: list[ExtractedFrame],
        options: PoseInferenceOptions,
        source_path: str,
    ) -> PoseInferenceResult:
        ...
```

### 호출부 연결 방향
- `PoseInferenceService`는 직접 MediaPipe Python adapter를 모르는 구조로 바꾼다.
- `PoseInferenceService`는 `NodeWorkerClient` 인터페이스에만 의존한다.
- 현재 단계에서는 `SubprocessNodeWorkerClient`를 기본 구현으로 주입한다.

예시 방향:
```python
class PoseInferenceService:
    def __init__(self, worker_client: NodeWorkerClient | None = None) -> None:
        self._worker_client = worker_client or SubprocessNodeWorkerClient(...)
```

### 권장 입력 payload 초안
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

### 권장 출력 payload 초안
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

### 오류 처리 초안
- Node 프로세스 실행 자체 실패:
  - `NodeWorkerProcessError`
- timeout:
  - `NodeWorkerTimeoutError`
- JSON 파싱 실패 또는 필수 필드 누락:
  - `NodeWorkerProtocolError`
- Node worker가 정상 종료했지만 추론 실패를 JSON으로 반환:
  - worker 응답의 `error` 필드를 읽어 `NodeWorkerClientError` 하위 예외로 변환

### 로그 및 진단 원칙
- Python은 최소한 아래를 기록할 수 있어야 한다.
  - worker command
  - timeout 설정값
  - source video path
  - frame count
  - requested delegate
  - exit code
- 단, frame 전체 payload나 landmark 전체 결과를 기본 로그로 남기지는 않는다.

### 구현 시 주의점
- Windows 경로와 WSL 경로를 혼합하지 않도록 worker 입력 경로를 명확히 통일한다.
- 초기 버전은 image buffer 직렬화보다 `imagePath` 전달 방식이 더 단순하다.
- Node worker stdout은 결과 JSON 전용으로 두고, 진단 로그는 stderr로 분리하는 편이 안전하다.
- Python 쪽 상위 계층은 `NodeWorkerClient`의 구현체 종류를 몰라도 동작해야 한다.
- headless browser 방식은 "브라우저가 필요하다"는 뜻이지 "클라이언트 디바이스에서 연산한다"는 뜻이 아니다.
- 성능 비교 시에는 "클라이언트 브라우저 vs 서버 headless browser"와 "서버 headless browser vs 서버 네이티브 런타임"을 구분해서 해석해야 한다.

## 구현 범위 후보
- `poseLandmarker_Python/node_worker/` 신설
- Node package 초기화와 실행 엔트리 구성
- Python -> Node worker subprocess 호출 경계 설계
- 공통 JSON contract 정의
- Node 추론 결과를 기존 Python benchmark/analysis 파이프라인에 연결
- CPU/GPU delegate 및 fallback 메타데이터 수집 정책 정의

## 구현에서 피해야 할 방향
- 기존 `poseLandmarker_Python` 전체를 Node.js로 즉시 재작성하는 것
- 브라우저용 `poseLandmarker_JavaScript`를 큰 수정 없이 서버 코드로 재사용하려는 것
- 초기 단계부터 별도 Node 서버 운영 구조를 먼저 도입하는 것
- benchmark 메타데이터 없이 "GPU가 될 것 같다" 수준으로 진행하는 것

## 단계별 추진안

### 1단계: PoC
- 순수 Node.js 런타임에서 MediaPipe Tasks Vision이 초기화되는지 확인
- 실패 시 headless browser 런타임으로 우회해 서버형 batch inference가 가능한지 확인
- 최소 1개 영상에서 frame batch inference 결과를 JSON으로 뽑아본다

### 2단계: 워커 경계 고정
- Python이 Node worker를 subprocess로 호출하는 방식 확정
- stdin/stdout JSON 또는 임시 파일 JSON으로 경계 정의
- 오류 코드와 실패 메시지 형식을 표준화

### 3단계: 기존 파이프라인 연결
- Node 결과를 Python `PoseInferenceResult`와 동등한 구조로 변환
- 기존 `skeleton_mapper`, `analysis_pipeline`, `benchmarking`와 결합
- benchmark에 Node runtime, requested/actual delegate, fallback 여부 반영

### 4단계: 비교 검증
- 동일 영상 기준 Python MediaPipe와 Node worker 결과 비교
- landmark 누락 여부, 프레임 수, timestamp 정합성 확인
- GPU 사용 여부를 benchmark와 런타임 로그로 검증

## 기술적 리스크
- MediaPipe JavaScript 또는 Tasks Vision이 순수 Node.js에서 공식적으로 얼마나 안정적인지 불확실하다.
- headless browser 방식은 브라우저 기동 비용과 메모리 사용량이 추가된다.
- Node 환경에서 GPU delegate가 실제로 의미 있는 가속 경로를 제공하는지 별도 검증이 필요하다.
- 프레임 전달 방식이 비효율적이면 Python-Node 경계가 오히려 병목이 될 수 있다.
- 브라우저와 Node의 WASM/GPU 실행 조건 차이 때문에 초기화 자체가 실패할 수 있다.

## 성공 기준
- `poseLandmarker_Python/node_worker/` 구조가 문서와 실행 기준으로 정리돼 있다.
- Node worker가 최소 1개 기준 영상에 대해 landmark JSON을 생성할 수 있다.
- Python 백엔드가 Node 결과를 받아 기존 skeleton/analysis/benchmark 흐름을 유지할 수 있다.
- 결과 메타데이터에서 `requestedDelegate`, `actualDelegate`, `delegateFallbackApplied`, `delegateErrors`를 계속 추적할 수 있다.

## 완료 조건
- `node_worker/`의 목적과 책임 범위가 문서화돼 있다.
- Python 유지 범위와 Node 이관 범위가 명확히 나뉘어 있다.
- PoC 선행 항목과 본 구현 항목이 구분돼 있다.
- 실패 시 되돌아올 수 있도록 worker 경계가 독립적으로 설계돼 있다.

## 테스트 방법
1. 기준 영상을 Python 프레임 추출 경로로 처리한다.
2. 추출 프레임을 Node worker에 전달한다.
3. Node worker가 frame별 landmark JSON을 반환하는지 확인한다.
4. Python이 이를 skeleton/analysis/benchmark 구조로 정상 연결하는지 확인한다.
5. 동일 영상 기준 delegate 메타데이터와 처리 시간을 비교한다.

## 현재 결론
- 이번 목표 기준으로는 `poseLandmarker_Python/node_worker/` 내부에 Node.js 워커를 두고, Python이 subprocess로 이를 호출하는 방식이 가장 현실적이다.
- 다만 순수 Node.js MediaPipe 런타임은 현재 PoC에서 `document is not defined`로 실패했다.
- 따라서 지금 단계의 실제 개발 방향은 "Node worker 내부에서 headless browser 런타임으로 우회"다.
- 즉 분기 단위는 여전히 "별도 백엔드 서버"가 아니라 "기존 Python 백엔드 안의 추론 워커 교체"로 잡는다.
- 이후 필요하면 같은 JSON 계약을 유지한 채 장기 실행 Node 서버형 또는 브라우저 없는 서버 런타임으로 옮길 수 있지만, 이번 단계의 목표는 아니다.

## 참고 자료
- `docs/mvp-v1/features/mediapipe/issue-18-enable-gpu-delegate.md`
- `docs/mvp-v1/features/mediapipe/architecture.md`
- `docs/mvp-v1/features/mediapipe/spec.md`
- `poseLandmarker_Python/adapter/mediapipe_adapter.py`
- `poseLandmarker_Python/service/pose_inference.py`
- `poseLandmarker_Python/service/job_manager.py`
- `poseLandmarker_JavaScript/`
