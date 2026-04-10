# GPU 추론 경로 탐색 회고 및 최종 결정

작성일: 2026-04-01
브랜치: `22-feature-poselandmarker_python-내부-nodejs-mediapipe-subprocess-워커-전환`

---

## 배경

`poseLandmarker_Python`은 FastAPI + MediaPipe Python으로 포즈 추론을 수행한다.
문제는 **MediaPipe Python이 Windows/WSL2에서 GPU를 지원하지 않는다는 것**이다.
긴 영상 여러 개를 동시에 처리해야 하는 요구사항 아래, CPU 단독 처리는 속도가 부족했다.

이 문제를 해결하기 위해 세 가지 대안 경로를 시도했고, 모두 실패했다.
이 문서는 각 시도의 경위, 실패 원인, 그리고 최종 결정을 기록한다.

---

## 시도 1: Node.js MediaPipe Worker

### 목적
`@mediapipe/tasks-vision`은 JavaScript 런타임에서 GPU를 사용할 수 있었다.
Python FastAPI 서버 내부에서 Node.js subprocess를 띄워 추론만 분리하려 했다.

### 시도한 방식
- `poseLandmarker_Python/node_worker/` 디렉터리에 Node.js 워커 구현
- Python이 subprocess로 Node 프로세스를 호출, stdin/stdout JSON으로 통신
- `service/node_worker_client.py`로 경계를 추상화

### 실패 원인

**1단계 실패: 순수 Node.js에서 MediaPipe 초기화 불가**

```
ReferenceError: document is not defined
```

`@mediapipe/tasks-vision`은 브라우저 DOM 전역(`document`, `window`, `HTMLVideoElement`)을 전제로 설계되어 있다.
Node.js 런타임에서는 초기화 자체가 불가능하다.

**2단계 시도: headless Chromium으로 우회**

브라우저 환경을 서버에서 에뮬레이션하는 방식으로 우회를 시도했다.

- Puppeteer 또는 Playwright로 headless Chromium을 기동
- 브라우저 컨텍스트 안에서 MediaPipe JS 초기화
- 프레임 데이터를 브라우저로 전달, 결과를 JSON으로 수집

이 방식은 기술적으로 가능하지만, **운영 경로로 유지할 수 없다고 판단했다:**

- headless Chromium 기동 비용 (메모리, 시간)이 추론 비용보다 크다
- 브라우저 GPU 컨텍스트가 서버 환경에서 실제로 GPU를 사용하는지 보장할 수 없다
- 프레임 데이터를 브라우저 내부로 전달하는 경계가 복잡하고 불안정하다
- 이것은 "서버에서 GPU 추론"이 아니라 "서버에서 브라우저 흉내"다

### 결론
Node.js MediaPipe Worker 경로는 폐기한다.
관련 코드(`node_worker/`, `node_worker_client.py`, config 플래그)는 레거시로 남아 있다.
참고 문서: `issue-22-nodejs-mediapipe-worker-branch.md`

---

## 시도 2: MediaPipe C++ 빌드 (Windows)

### 목적
MediaPipe C++ API는 GPU를 지원한다.
Python subprocess로 C++ 실행 파일을 호출하면 Windows에서도 GPU 추론이 가능할 것으로 기대했다.

### 시도한 방식
- MediaPipe 저장소를 fork하여 Windows용 Bazel 빌드 시도
- `poseLandmarker_Python/cpp_worker/`에 C++ 워커 구현
- `service/cpp_worker_client.py`로 Python-C++ 경계 추상화
- OpenGL ES 컨텍스트 문제 해결을 위한 ANGLE 레이어 wiring 시도

### 실패 원인

**레이어 1: Bazel on Windows**

MediaPipe는 Bazel을 빌드 시스템으로 사용한다.
Windows에서 Bazel은 다음 문제가 반복적으로 발생한다:
- Windows 경로 길이 제한 (MAX_PATH)
- symlink 생성 권한 요구
- MSVC / Clang 툴체인 호환성 불일치

**레이어 2: GPU 파이프라인 = OpenGL ES**

MediaPipe C++ GPU 파이프라인은 OpenGL ES를 전제로 설계되어 있다.
Windows에서 OpenGL ES를 사용하려면 ANGLE (OpenGL ES → DirectX 번역 레이어)이 필요하다.
MediaPipe는 ANGLE을 자동으로 핸들링하지 않는다. 직접 wiring해야 한다.

탐색한 내용:
- `cpp-worker-windows-gl-platform-layer-design.md`
- `windows-gl-adapter-minimum-interface.md`
- `windows-gl-helper-wiring-patch-plan.md`
- `windows-gl-mediapipe-shim-plan.md`
- `windows-gl-context-smoke-test-plan.md`
- `windows-gl-gpu-enable-patch-scope.md`
- `windows-gl-stage2-image-to-tensor-result.md`
- `cpp-worker-gl-context-feasibility.md`
- `cpp-worker-windows-gpu-next-session-handoff.md`

**레이어 3: GL 컨텍스트 생명주기**

MediaPipe 내부의 GPU 리소스 관리와 GL 컨텍스트 핸드오프 로직은
Linux 환경을 가정하고 설계되어 있다.
Windows에서 세션 간 컨텍스트 재사용, 리소스 해제, 컨텍스트 공유 방식이 다르게 동작한다.

**레이어 4: 공식 미지원**

MediaPipe 팀은 Windows GPU를 공식 지원하지 않는다.
이슈가 제기되어도 방치된다.

### 결론
각 레이어가 독립적으로 해결되어야 하며, 각 단계마다 문서화되지 않은 Windows 전용 버그가 존재한다.
이 경로는 수주~수개월의 통합 작업이 필요하고, 최종 성공도 보장되지 않는다.
**C++ 빌드 경로는 폐기한다.**

관련 코드(`cpp_worker/`, `cpp_worker_client.py`, config 플래그)는 레거시로 남아 있다.
탐색 문서는 `cpp-worker-*.md`, `windows-gl-*.md`, `windows-gpu-resources-replacement-plan.md`에 보존한다.

---

## 시도 3: ONNX 변환 (tflite2onnx / tf2onnx)

### 목적
MediaPipe BlazePose 모델(.task 파일)을 ONNX로 변환하면,
`onnxruntime-gpu`를 통해 Windows에서 CUDA GPU 추론이 가능해진다.
`uv`로 관리되는 기존 Python 환경에 그대로 통합할 수 있다는 장점이 있었다.

### 시도한 방식

**모델 추출**
`.task` 파일은 zip 아카이브다. 내부에서 TFLite 모델을 추출:
- `pose_detector.tflite` — 사람 위치 검출 (1단계)
- `pose_landmarks_detector.tflite` — 랜드마크 추론 (2단계)

**1차 시도: tf2onnx**
```
ModuleNotFoundError: No module named 'tensorflow'
```
`tf2onnx`는 TFLite 변환 시에도 TensorFlow를 module-level에서 import한다.
TensorFlow를 설치하지 않으면 사용할 수 없다.
→ `tflite2onnx`로 교체

**2차 시도: tflite2onnx — pose_detector.tflite**
```
NotImplementedError: Unsupported TFLite OP: 124 DENSIFY!
```
BlazePose 검출 모델은 희소 행렬 최적화(`DENSIFY` op)를 사용한다.
이 op는 `tflite2onnx`가 지원하지 않는다.

→ 검출기를 제거하고 full-frame ROI로 대체하는 방식으로 우회 시도.
(rack tracker 사용 사례는 고정 카메라 환경이므로 full-frame ROI가 허용 가능했다.)

**3차 시도: tflite2onnx — pose_landmarks_detector.tflite**
```
IndexError: too many indices for array
  File "tflite2onnx/op/padding.py", line ...
```
랜드마크 모델 내부의 padding op를 처리하는 과정에서 `tflite2onnx` 내부 버그가 발생했다.
이 모델 구조에 특화된 버그로, 라이브러리를 수정하지 않는 한 우회 불가능하다.

### 결론

| 모델 | 문제 | 해결 가능성 |
|------|------|------------|
| pose_detector.tflite | DENSIFY op 미지원 | 검출기 없이 우회 가능하지만 정확도 저하 |
| pose_landmarks_detector.tflite | tflite2onnx 내부 버그 (padding op) | 라이브러리 수정 없이 불가 |

BlazePose TFLite 모델은 현재 어떤 변환 도구로도 ONNX로 변환할 수 없다.
**ONNX 변환 경로는 폐기한다.**

관련 코드(`service/onnx_worker_client.py`, config 플래그)는 레거시로 남아 있다.
구조 자체는 다른 ONNX 모델(예: YOLOv8-pose)을 사용할 때 참고할 수 있다.

---

## 최종 결정

### 결정 내용

> **개발: Windows CPU-only MediaPipe Python**
> **운영: native Linux 서버 + MediaPipe Python GPU (SFF 서버 구축)**

### 이유

- MediaPipe Python GPU는 **native Linux에서만 안정적으로 동작**한다
- WSL2는 GPU passthrough가 불완전해 MediaPipe GPU delegate가 실제 NVIDIA 경로를 보장하지 않는다
- Windows에서는 CPU 전용으로 개발하고, SFF Linux 서버에 배포하는 구조가 가장 현실적이다
- 기존 Python FastAPI 코드베이스, 결과 스키마, API 표면은 **그대로 유지**된다
- 코드 변경 없이 환경만 바꾸면 GPU 추론이 가능해진다

### 코드 정리 대상 (다음 단계)

아래 레거시 코드는 이 결정이 확정된 시점에 제거한다:

**디렉터리**
- `poseLandmarker_Python/node_worker/`
- `poseLandmarker_Python/cpp_worker/`

**파일**
- `poseLandmarker_Python/service/node_worker_client.py`
- `poseLandmarker_Python/service/cpp_worker_client.py`
- `poseLandmarker_Python/service/onnx_worker_client.py`

**config 플래그**
- `NODE_WORKER_ENABLED`, `NODE_WORKER_DIR`, `NODE_WORKER_ENTRY`, `NODE_WORKER_TIMEOUT_SECONDS`
- `CPP_WORKER_ENABLED`, `CPP_WORKER_DIR`, `CPP_WORKER_ENTRY`, `CPP_WORKER_TIMEOUT_SECONDS`
- `ONNX_WORKER_ENABLED`, `ONNX_MODEL_DIR`

**pose_inference.py 분기 로직**
- `_should_use_node_worker()`, `_should_use_cpp_worker()`, ONNX 경로

**schema/pose.py**
- `InferenceBackend`에서 `node_worker`, `cpp_worker`, `onnx_worker` 제거 → `python`만 유지

---

## 교훈

1. **MediaPipe는 플랫폼 가정이 강하다.** GPU 경로는 native Linux 전제다. 이를 다른 환경으로 이식하려는 시도는 모두 실패했다.

2. **변환 도구를 믿지 마라.** TFLite 모델의 ONNX 변환은 "가능해 보이는" 도구가 여럿 있지만, 실제로는 특정 op에서 막힌다. 모델 파일을 직접 받아 변환을 확인하기 전까지 성공을 가정하지 마라.

3. **경계 설계는 옳았다.** `NodeWorkerClient`, `CppWorkerClient`, `OnnxWorkerClient`를 인터페이스로 분리한 구조 덕분에 각 시도가 상위 계층에 영향을 주지 않았다. 레거시 제거도 깔끔하게 할 수 있다.

4. **문서가 시간을 아낀다.** 각 실패 경로를 문서화하지 않으면 나중에 같은 시도를 반복하게 된다.
