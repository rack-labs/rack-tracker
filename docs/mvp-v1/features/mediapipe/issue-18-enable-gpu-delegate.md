[fix] MediaPipe GPU delegate 실제 사용 가능화

브랜치명: 20-fix-mediapipe-gpu-delegate-실제-사용-가능화

## 작업 목적
현재 MediaPipe 백엔드는 `delegate=GPU`를 기본 정책으로 두고 있지만, 실제 실행 환경에서는 GPU delegate 초기화가 실패해 CPU fallback으로 내려가는 경우가 있었다. 이 작업의 목적은 GPU 사용 가능 환경을 명확히 정비하고, 실제 benchmark에서 `requestedDelegate=GPU`, `actualDelegate=GPU`, `delegateFallbackApplied=false`가 안정적으로 기록되도록 만드는 것이다.

## 문제 정의
- 코드 정책은 이미 GPU 우선, 실패 시 CPU fallback으로 잡혀 있다.
- 하지만 benchmark 결과에서 `requestedDelegate: GPU`, `actualDelegate: CPU`, `delegateFallbackApplied: true`가 반복적으로 관측된 이력이 있다.
- 성능 문서 기준으로 이 상태는 단순 최적화 미적용이 아니라 GPU 구성 실패다.
- 현재 CPU fallback 상태에서는 추론 병목이 크게 남아 있고, 긴 영상이나 다중 요청에서 처리 시간이 빠르게 누적된다.

## 현재 추정 원인
- `poseLandmarker_Python/adapter/mediapipe_adapter.py`는 GPU delegate enum을 사용해 초기화를 시도하지만, 실제 MediaPipe Python 빌드가 GPU 경로를 제대로 포함하지 않을 수 있다.
- 성능 문서에 기록된 오류 메시지 `ImageCloneCalculator: GPU processing is disabled in build flags`는 설치된 빌드에서 GPU 처리 경로가 비활성화되었음을 시사한다.
- 즉, 애플리케이션 코드 문제만이 아니라 실행 OS, Python 패키지 빌드, 드라이버/런타임, MediaPipe 배포 형태가 함께 맞아야 한다.

## 작업 내용
- GPU delegate가 실제로 지원되는 운영 환경 조합을 확정한다.
- 현재 개발/배포 환경에서 MediaPipe Python GPU 경로가 가능한지 검증하고, 불가능하면 지원 환경을 명시적으로 전환한다.
- GPU 초기화 성공 조건과 실패 조건을 문서화한다.
- benchmark와 로그에서 GPU 직접 사용 여부와 fallback 여부를 더 명확히 확인할 수 있게 한다.
- 최소 1개 기준 영상에서 GPU 직접 실행 benchmark를 다시 수집한다.

## 구현 범위 후보
- Ubuntu 기반 GPU 지원 환경으로 실행 환경 전환
- MediaPipe Python GPU 지원 경로 재구성
- 필요 시 MediaPipe Python 대신 GPU 가능한 다른 추론 스택 검토
- 배포 문서에 GPU 의존성, 드라이버, 런타임, 검증 절차 정리

## 기대 효과
- 실제 추론 병목이 가장 크게 줄어들 가능성이 높다.
- benchmark 기준 inference 시간이 CPU baseline 대비 크게 단축될 수 있다.
- 긴 영상 처리와 동시 요청 상황에서 전체 시스템 처리량이 개선될 수 있다.

## 핵심 원칙
- 이 작업의 완료 기준은 코드에 `delegate=GPU` 옵션이 있는지가 아니라, 실제 실행 결과가 GPU direct path인지다.
- GPU 사용 가능 여부는 추정이 아니라 benchmark와 런타임 로그로 검증해야 한다.
- 지원하지 않는 환경에서는 조용히 기대만 남기지 말고, 명시적으로 CPU fallback 또는 비지원 상태를 드러내야 한다.

## 완료 조건
- 지원 대상 환경에서 `delegate=GPU` 요청 시 실제로 GPU delegate 초기화가 성공한다.
- benchmark summary에 `requestedDelegate=GPU`, `actualDelegate=GPU`, `delegateFallbackApplied=false`가 기록된다.
- 기준 영상에서 GPU 사용 전후 성능 차이를 비교할 수 있는 benchmark가 확보된다.
- GPU 미지원 환경에서는 실패 원인과 fallback 동작이 문서 및 로그 기준으로 명확히 설명된다.

## 테스트 방법
1. GPU 지원 대상 환경을 준비한다.
2. `POST /jobs` 요청에서 `delegate=GPU`로 작업을 생성한다.
3. 작업 완료 후 benchmark summary의 delegate 메타데이터를 확인한다.
4. `actualDelegate`가 `GPU`로 기록되는지 확인한다.
5. 동일 영상 기준 CPU/GPU benchmark를 비교해 inference 시간 차이를 확인한다.

## 참고 자료
- `poseLandmarker_Python/adapter/mediapipe_adapter.py`
- `poseLandmarker_Python/service/pose_inference.py`
- `poseLandmarker_Python/docs/optimization/performance-summary.md`
- `docs/mvp-v1/features/mediapipe/architecture.md`

## 2026-03-27 추가 진단 메모

### 이번 확인으로 좁혀진 원인
- Ubuntu로 이관한 뒤에도 GPU가 항상 안정적으로 붙는 상태는 아니었다.
- 현재 코드는 `GPU`를 먼저 요청하고, 실패하면 `CPU`로 fallback 하도록 이미 구성돼 있다.
- 실제 문제는 정책 누락이 아니라 런타임 환경에서 MediaPipe GPU delegate 초기화가 흔들리는 점이다.

### 확인 근거
- `poseLandmarker_Python/tmp/check_gpu_delegate.py` 실행 결과, MediaPipe GPU delegate 초기화가 `EGL` 단계에서 실패했다.
- 대표 오류는 아래 의미로 정리할 수 있다.
  - `egl_initializedUnable to initialize EGL`
  - `kGpuService ... was not provided and cannot be created`
- 같은 시점에 `nvidia-smi`도 정상 GPU 접근 상태가 아니었고, `GPU access blocked by the operating system` 메시지가 확인됐다.
- 즉 현재 병목은 애플리케이션이 GPU 옵션을 안 주는 문제가 아니라, OS/드라이버/EGL 경로가 실제 GPU 실행을 성립시키지 못하는 문제다.

### 현재 상태 해석
- 저장된 benchmark summary를 보면 `requestedDelegate=GPU`인데도 `actualDelegate=CPU`, `delegateFallbackApplied=true`인 실행과,
  `actualDelegate=GPU`, `delegateFallbackApplied=false`인 실행이 섞여 있다.
- 따라서 "코드가 항상 CPU만 쓰는 상태"로 단정할 수는 없고, 실행 환경 조건에 따라 GPU delegate 초기화 성공 여부가 달라지는 상태로 보는 것이 맞다.
- 이 상태에서는 Ubuntu 전환만으로 GPU 사용 문제가 해결됐다고 판단하면 안 된다.

### 이번에 반영한 코드 보강
- GPU delegate 초기화 실패 원인이 benchmark 결과에 남도록 보강했다.
- 추가된 방향은 아래와 같다.
  - delegate별 초기화 예외 메시지를 adapter에서 수집
  - pose inference 결과에 `delegate_errors` 포함
  - benchmark run metadata에 `delegateErrors` 포함
- 이제 CPU fallback이 발생해도 단순히 `actualDelegate=CPU`만 기록되는 것이 아니라, 왜 fallback 되었는지 결과 JSON에서 같이 확인할 수 있다.

### 현재 결론
- 현 시점의 핵심 blocker는 MediaPipe Python 코드가 아니라 Ubuntu 실행 환경의 GPU 접근성과 EGL 초기화 가능 여부다.
- 완료 기준은 여전히 동일하다.
  - `delegate=GPU` 요청
  - 실제 초기화 성공
  - benchmark에 `actualDelegate=GPU`
  - `delegateFallbackApplied=false`
- 위 조건이 재현 가능하게 안정화되기 전까지는 GPU 사용 가능화가 완료된 것으로 볼 수 없다.

## WSL 결론 정리

### 이번 확인에서 확정된 사항
- Windows 호스트의 NVIDIA 드라이버와 GPU 자체는 정상이다.
  - `nvidia-smi`에서 RTX 4070, Driver Version `555.97`, CUDA Version `12.5`가 확인됐다.
- WSL 내부에서도 `/dev/dxg`는 존재하고, `/usr/lib/wsl/lib` 아래에 `libcuda.so`, `libnvidia-ml.so.1` 등 WSL GPU bridge 라이브러리는 존재한다.
- 하지만 WSL 내부의 OpenGL/EGL userspace는 NVIDIA가 아니라 Mesa software rasterizer로 연결되어 있다.
  - `glxinfo -B` 결과: `OpenGL vendor string: Mesa`
  - `OpenGL renderer string: llvmpipe`
  - `Accelerated: no`
  - `eglinfo` 결과: `EGL vendor string: Mesa Project`, `EGL driver name: swrast`
- 즉 MediaPipe Python GPU delegate는 `gpu_init=success`가 나와도, 실제로는 NVIDIA GPU가 아니라 소프트웨어 렌더링 경로를 타는 상태로 해석하는 것이 맞다.

### 실무적 결론
- 현재 WSL 환경에서는 "MediaPipe Python GPU delegate로 실제 NVIDIA GPU 연산을 안정적으로 사용한다"는 목표를 충족하지 못한다.
- 따라서 이 이슈를 닫을 수 있는 현실적인 경로는 아래 둘 중 하나다.
  1. Native Ubuntu 환경에서 NVIDIA OpenGL/EGL 경로가 실제로 잡히는 상태로 실행한다.
  2. WSL을 유지해야 한다면 MediaPipe Python GPU delegate 사용을 포기하고, CUDA 기반 추론 스택으로 전환한다.

### 선택지 해석
- `Native Ubuntu를 쓴다`는 것은 단순히 Ubuntu 셸만 쓰는 것이 아니라, 실제 Linux 호스트에서 `nvidia-smi`, `glxinfo -B`, `eglinfo`가 모두 NVIDIA 경로로 확인되는 환경을 뜻한다.
- `MediaPipe for Python을 포기한다`는 것은 MediaPipe 전체를 반드시 버린다는 뜻은 아니고, 적어도 현재 목표인 "Python 백엔드에서 MediaPipe GPU delegate로 GPU 가속" 경로는 포기한다는 의미다.
- WSL 유지가 우선이라면 CUDA 친화적인 대안 스택이 더 현실적이다.

## 대안 방향 메모

### Node.js 추론 워커 검토
- Python runtime과 JavaScript runtime이 병존하는 구조 자체는 가능하다.
- 하지만 현재 저장소의 JavaScript MediaPipe 코드는 브라우저 전제 코드이며, `document`, `video element`, CDN 기반 WASM 로딩 흐름을 사용한다.
- 따라서 지금 코드를 그대로 Node.js 워커로 옮겨 Python 백엔드의 MediaPipe 추론을 단순 대체하는 것은 어렵다.
- 별도 Node.js 워커를 두려면 브라우저 의존이 없는 형태로 다시 구성해야 하고, 공식 지원 범위와 운영 복잡도를 고려하면 우선순위가 높지 않다.

### 브라우저 기반 MediaPipe 대체 가능성
- 브라우저에서 MediaPipe JavaScript로 2D skeleton을 추출하는 구조는 가능하다.
- 다만 이 프로젝트의 최종 목표가 "여러 카메라 영상에서 skeleton을 추출하고, 이를 이용해 정밀도 높은 3D 객체를 합성하는 것"이라면 브라우저를 메인 추론 엔진으로 두는 것은 적합하지 않다.
- 이유는 아래와 같다.
  - 여러 영상 스트림의 장시간 안정 처리에 불리하다.
  - GPU/메모리 사용량 제어가 제한적이다.
  - 작업 큐, 재시도, 배치 재처리, 재현 가능한 서버 파이프라인 운영에 불리하다.
  - 다중 카메라 동기화, calibration, triangulation, bundle adjustment 같은 후처리는 서버 중심 구조가 더 적합하다.

### 현재 시점의 구조 판단
- 브라우저는 업로드, 미리보기, 간단한 실시간 2D pose 확인 정도의 보조 역할에는 적합하다.
- 하지만 본 프로젝트의 핵심 처리 경로는 서버 중심 파이프라인으로 두는 것이 맞다.
- 따라서 issue-18의 결론은 단순히 "MediaPipe Python을 JS로 바꾼다"가 아니라, 아래와 같이 정리하는 것이 타당하다.
  1. 최종 시스템의 중심 엔진은 서버 측 추론/재구성 파이프라인이어야 한다.
  2. WSL에서 MediaPipe Python GPU delegate를 계속 붙잡는 것은 장기 방향으로 비효율적이다.
  3. 장기적으로는 native Ubuntu 기반 서버 추론 또는 CUDA 친화적 대안 추론 스택 검토가 더 현실적이다.

## Node 워커 병존안 메모

### 가능한 아키텍처
- `uv` 기반 FastAPI 백엔드는 그대로 유지한 채, 별도 Node.js 추론 워커를 함께 두는 구조는 가능하다.
- 예시 흐름은 아래와 같다.
  1. FastAPI가 영상 업로드와 frame extraction을 처리한다.
  2. frame extraction이 끝나면 Python이 Node.js worker를 subprocess 또는 별도 서비스 형태로 호출한다.
  3. Node.js worker가 pose inference를 수행하고 skeleton 결과를 JSON으로 반환한다.
  4. Python 백엔드는 이 결과를 기존 데이터 분석 파이프라인으로 넘긴다.
- 즉 Python runtime과 JavaScript runtime이 한 백엔드 시스템 안에 병존하는 것은 구조적으로 문제되지 않는다.

### 중요한 전제
- 이 방안은 현재 `poseLandmarker_JavaScript` 브라우저 코드를 재사용한다는 뜻이 아니다.
- 브라우저 전제 코드(`document`, `video element`, CDN 기반 wasm 로딩)는 버리고, Node 런타임에서 동작하는 추론 워커를 별도로 다시 작성하는 전제를 둔다.

### 기술적 리스크
- 병존 구조 자체보다 더 중요한 문제는 "Node.js에서 MediaPipe JavaScript 기반 pose inference가 안정적으로 성립하느냐"다.
- 현재 확인된 공식 문서와 패키지 예시는 대부분 브라우저/Web API 중심이다.
- 따라서 Node.js worker를 설계하는 것은 가능하지만, 그 worker의 추론 엔진으로 MediaPipe JS를 선택하는 것은 별도 PoC 검증이 선행돼야 한다.
- 즉 이 방안은 곧바로 본 구현으로 들어갈 대상이라기보다, 먼저 작은 실험으로 성립 여부를 확인해야 하는 후보안으로 보는 것이 맞다.

### PoC 검증 항목
- 순수 Node.js 런타임에서 MediaPipe Tasks Vision이 초기화되는지
- 브라우저 API 없이 파일 입력 기반 frame batch inference가 가능한지
- GPU 사용 여부를 단순 성공 로그가 아니라 실제 처리량과 런타임 메타데이터로 검증할 수 있는지
- Python 백엔드와 JSON 입출력 규약으로 안정적으로 연결 가능한지
- 실패 시 곧바로 다른 추론 엔진으로 갈아탈 수 있도록 worker 경계를 독립적으로 유지할 수 있는지

### 다음 점검 항목
1. 호스트 환경에서 `nvidia-smi`가 정상 동작하는지 확인
2. NVIDIA 드라이버와 `libEGL` 계열 라이브러리가 올바르게 연결돼 있는지 확인
3. WSL, 원격 세션, 컨테이너 등 중간 계층이 있다면 GPU passthrough 및 EGL 사용 가능 여부 확인
4. 수정된 benchmark `delegateErrors` 필드로 fallback 원인이 일관되게 같은지 수집
