# MediaPipe C++ Worker Session Handoff

## 목적

이 문서는 `rack-tracker-forked`에서 진행 중인 MediaPipe Pose Landmarker의 C++ 로컬 worker 통합 작업을 새 Codex 세션에서 바로 이어가기 위한 핸드오프 문서다.

기준 시점:

- 날짜: 2026-03-30
- 작업 루트: `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked`
- 이 문서는 2026-03-30 후속 Codex 세션에서 실제 빌드 재개 결과와 목표 변경까지 반영해 갱신됨
- 아래 내용에는 그 다음 후속 세션에서 `build-worker.ps1`를 다시 실행하며 추가로 진행한 protobuf 정리와 새 MediaPipe blocker도 반영되어 있음

## 현재 목표

현재 목표는 이전 세션의 `CPU-only exe를 먼저 만든다`에서 바뀌었다.

새 목표는 다음이다.

- OpenCV는 프레임 추출만 담당
- MediaPipe는 로컬 C++ worker exe에서 pose 추론만 담당
- Python 상위 파이프라인은 유지
- Python은 `stdin/stdout JSON` 기반으로 C++ worker와 통신
- 최종적으로 `POSE_CPP_WORKER_ENABLED=true`일 때 C++ worker 경로가 실제로 동작해야 함
- 그리고 이제는 Windows에서 MediaPipe GPU 경로까지 열 수 있는 빌드 그래프를 우선 설계해야 함

중요한 최신 전략 변경:

- 지금까지는 깨지는 external dependency를 하나씩 patch하며 전체 Bazel graph를 정면돌파하는 방식으로 진행했다
- 하지만 최신 판단은 이 전략이 비효율적이라는 것이다
- 다음 세션부터의 1순위 목표는 `protobuf compiler / language generators 자체를 graph에서 제거하거나 최소화`하는 방향으로 전환하는 것이다
- 즉 `csharp`, `java`, `rust` generator를 계속 patch로 살리는 것이 아니라, pose worker에 불필요한 compiler/tooling dependency가 왜 graph에 들어오는지부터 끊는 쪽이 우선이다
- 다시 말해 최신 권장 전략은 `더 patch`가 아니라 `불필요한 build target 자체 제거`다

중요:

- 기존 `build-worker.ps1`는 `--define MEDIAPIPE_DISABLE_GPU=1`를 넣고 있었다
- 이 값은 런타임 delegate를 끄는 설정이 아니라 Bazel 빌드 그래프에서 GPU 관련 의존을 최대한 덜 끌어오게 하려는 안정화용 define이었다
- 사용자가 이 방향을 중단하고 `지금부터 GPU 빌드 방향으로 목표를 바꿔서 그래프를 다시 설계`하라고 명시했으므로, 다음 세션부터는 이 define을 기본 전제로 두면 안 된다

## 외부 경로

### MediaPipe fork

- `C:\Users\neighbor\Documents\Code\Github\mediapipe-forked`

### 모델 파일

- `C:\Users\neighbor\Documents\Code\Github\pose_landmarker_models`

포함 파일:

- `pose_landmarker_lite.task`
- `pose_landmarker_full.task`
- `pose_landmarker_heavy.task`

### OpenCV prebuilt

- 압축 해제 루트: `C:\Users\neighbor\Documents\Code\Github\opencv-prebuilt\opencv`

확인된 핵심 파일:

- `C:\Users\neighbor\Documents\Code\Github\opencv-prebuilt\opencv\build\x64\vc15\lib\opencv_world3410.lib`
- `C:\Users\neighbor\Documents\Code\Github\opencv-prebuilt\opencv\build\x64\vc15\bin\opencv_world3410.dll`

## rack-tracker-forked 에서 이미 변경된 파일

### 설계 문서

- [cpp-worker-design.md](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\docs\features\mediapipe\cpp-worker-design.md)

### Python 설정 및 통합

- [config.py](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\config\config.py)
- [README.md](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\README.md)
- [cpp_worker_client.py](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\service\cpp_worker_client.py)
- [pose_inference.py](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\service\pose_inference.py)
- [job_manager.py](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\service\job_manager.py)
- [pose.py](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\schema\pose.py)

### C++ worker 소스 및 빌드 스캐폴드

- [README.md](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\README.md)
- [BUILD.bazel](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\BUILD.bazel)
- [main.cc](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\src\main.cc)
- [build-worker.ps1](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\build-worker.ps1)

### 보조 패치/검색 스크립트

기존 문서에 있던 스크립트들 외에 이번 세션에서 아래 스크립트가 추가되었다.

- [patch_protobuf_java_lite_field_generator_includes.ps1](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\patch_protobuf_java_lite_field_generator_includes.ps1)
- [patch_protobuf_csharp_local_includes.ps1](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\patch_protobuf_csharp_local_includes.ps1)
- [patch_xnnpack_generate_build_identifier_windows.ps1](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\patch_xnnpack_generate_build_identifier_windows.ps1)
- [patch_protobuf_java_build_internal_helpers_hdrs.ps1](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\patch_protobuf_java_build_internal_helpers_hdrs.ps1)
- [patch_model_asset_bundle_resources.ps1](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\patch_model_asset_bundle_resources.ps1)

즉 지금 `build-worker.ps1`는 protobuf/java, protobuf/csharp, protobuf/rust, tflite, XNNPACK 쪽까지 external cache 패치를 폭넓게 실행한다.

## C++ worker 구현 상태

### main.cc 개요

`main.cc`는 아래 구조로 작성되어 있다.

- MediaPipe C API 사용
- `stdin`에서 JSON 입력 읽음
- 프레임별 `imagePath`, `timestampMs` 처리
- `MpImageCreateFromFile`
- 내부 task 생성은 `IMAGE` running mode로 고정
- 프레임별 추론 호출은 `MpPoseLandmarkerDetectImage`
- 결과를 기존 Python `PoseInferenceResult` shape에 맞는 JSON으로 `stdout` 출력
- 에러 시 `{"error": ...}` JSON 출력 후 종료 코드 1 반환

추가 관찰:

- worker 코드는 입력 delegate로 `CPU`와 `GPU`를 받을 수 있게 작성되어 있다
- worker는 프로토콜 입력으로 `VIDEO`와 `IMAGE`를 모두 받지만, 실제 처리 방식은 추출된 각 프레임을 독립적으로 처리하는 `IMAGE` 경로다
- worker는 현재 `numPoses=1`, `outputSegmentationMasks=false`만 허용한다
- 이 전제는 tracking/stream path와 segmentation path를 worker 빌드 그래프에서 줄이기 위한 현재 전략과 맞물려 있다

### Python 연동 상태

이미 다음 기능이 들어가 있다.

- `POSE_CPP_WORKER_ENABLED=true`면 C++ worker 우선 시도
- worker 입력은 `imagePath` 기반 JSON
- worker 출력은 기존 `PoseInferenceResult`로 역직렬화
- worker 경로/모델 경로 오류 시 명확한 예외 발생
- C++ worker 사용 시 job 단계에서 프레임 이미지를 디스크에 저장

즉 Python 쪽 경계는 이미 구현돼 있고 현재 blocker는 exe 빌드 체인이다.

## 설정 관련 사항

### 모델 디렉터리

`POSE_MODEL_DIR` 환경변수를 지원하도록 바뀌어 있다.

예시:

```powershell
$env:POSE_MODEL_DIR="C:\Users\neighbor\Documents\Code\Github\pose_landmarker_models"
```

### C++ worker 관련 환경변수

코드상 이미 반영된 환경변수:

- `POSE_CPP_WORKER_ENABLED`
- `POSE_CPP_WORKER_ENTRY`
- `POSE_CPP_WORKER_DIR`
- `POSE_CPP_WORKER_TIMEOUT_SECONDS`
- `POSE_MODEL_DIR`

## mediapipe-forked 에서 이미 가한 변경

### WORKSPACE OpenCV 경로 변경

다음 경로로 `windows_opencv`가 바뀐 상태다.

- `C:\Users\neighbor\Documents\Code\Github\opencv-prebuilt\opencv\build`

### 임시/직접 패치된 외부 또는 fork 파일

작업 도중 아래 유형의 패치가 들어갔다.

- `mediapipe/framework/profiler/profiler_resource_util_common.cc`
  - `MP_ASSIGN_OR_RETURN` 매크로를 피하는 형태로 로직 단순화
- `mediapipe/tasks/cc/core/BUILD`
  - pose worker에 불필요한 text custom op 의존 제거
- `mediapipe/tasks/cc/core/mediapipe_builtin_op_resolver.cc`
  - `sentencepiece`, `ragged`, `language detector` custom op 제거
- `mediapipe/util/tflite/tflite_signature_reader.cc`
  - Windows/MSVC에서 깨지는 `MP_ASSIGN_OR_RETURN` 사용을 명시적 `StatusOr` 처리로 우회

external cache 쪽에서는 이번 세션에 다음 범주의 patch가 실제로 연결되거나 추가되었다.

- `external/com_google_protobuf/src/google/protobuf/compiler/java/lite/...`
- `external/com_google_protobuf/src/google/protobuf/compiler/java/internal_helpers.h`
- `external/com_google_protobuf/src/google/protobuf/compiler/csharp/...`
- `external/com_google_protobuf/src/google/protobuf/compiler/rust/...`
- `external/com_google_protobuf/src/google/protobuf/io/...`
- `external/org_tensorflow/tensorflow/lite/kernels/BUILD`
- `external/XNNPACK/BUILD.bazel`

주의:

- 이 패치들은 Bazel external cache 내부라 캐시 재생성 시 사라질 수 있다
- `_virtual_includes` 같은 Bazel 산출물은 source patch만으로 바로 안 바뀔 수 있어 `bazel clean`이 필요하다
- 실제로 이번 세션에서도 patch 순서 문제와 stale artifact 때문에 `bazel clean`을 한 번 실행했다

## 빌드 명령

이번 세션에서 실제로 반복 사용한 기본 명령은 아래였다.

```powershell
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -ExecutionPolicy Bypass -File C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\build-worker.ps1 -PythonBinary C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\.venv\Scripts\python.exe
```

현재 `build-worker.ps1` 내부 Bazel 호출은 기본적으로 아래 형태다.

```powershell
& $BazelBinary build -c opt --verbose_failures --subcommands //mediapipe/tasks/c/vision/pose_landmarker/worker:mediapipe_pose_worker
```

중요:

- `MEDIAPIPE_DISABLE_GPU=1`는 더 이상 기본값이 아니다
- CPU-only 재현이 필요할 때만 `build-worker.ps1 -DisableGpu`로 넣는다
- 다만 최신 graph slimming은 worker runtime 가정을 `IMAGE + single pose + no segmentation`으로 더 좁혀 build surface를 줄이는 쪽으로 진행 중이다

예상 산출물 경로:

- `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\bin\mediapipe_pose_worker.exe`

현재는 이 파일이 아직 없다.

## 이번 세션에서 실제로 한 일

이번 후속 세션에서는 handoff 문서를 읽은 뒤 실제로 빌드를 재개했고, 아래 작업을 수행했다.

1. `build-worker.ps1`를 읽고 실제 빌드 재현
2. `_bazel_neighbor` 쓰기 권한이 필요해 escalation 후 external cache patch 적용이 가능한 상태에서 빌드 재개
3. `protobuf java/lite`의 `field_generator.h` include 문제를 직접 패치하는 스크립트 추가
4. `protobuf csharp` local include를 디렉터리 단위로 정리하는 스크립트 추가
5. `protobuf java/internal_helpers` 패치가 뒤쪽 범용 patch에 되돌려지는 순서 문제를 찾아 `build-worker.ps1` patch 순서를 수정
6. stale `_virtual_includes` 문제를 줄이기 위해 `bazel clean` 실행
7. `XNNPACK`의 `generate_build_identifier` genrule이 Windows에서 `bash.exe`를 요구하던 문제를 `cmd_bat` 추가 patch로 우회
8. 별도 타깃으로 `@com_google_protobuf//src/google/protobuf/compiler/csharp:csharp`를 빌드해, 적어도 일부 빌드 옵션 조합에서는 `csharp.lib` 생성까지 성공하는 것을 확인
9. 사용자 요청에 따라 목표를 `CPU-only exe 우선`에서 `GPU 빌드 방향으로 그래프 재설계`로 전환

그 다음 후속 세션에서는 아래 추가 작업을 수행했다.

10. `build-worker.ps1`를 여러 차례 재실행하며 실제 실패 지점을 최신 상태로 재현
11. `protobuf csharp` include 문제의 원인이 `patch_protobuf_header_local_includes_to_full.ps1`와 patch 순서 충돌이라는 점을 확인하고 `build-worker.ps1` patch 순서를 조정
12. `protobuf java/full`, `protobuf java/lite`에서 `generator_factory.h`, `field_generator.h`, `java_features.pb.h`, `message_serialization.h`가 self-include 또는 잘못된 full include로 깨지는 문제를 좁혀서 관련 patch 스크립트를 수정
13. 너무 광범위하게 protobuf include를 로컬 include로 뒤집던 경로가 오히려 `cpp/field.h -> helpers.h` 같은 정상 include graph까지 깨뜨린다는 점을 확인하고, `build-worker.ps1`에서 범용 `protobuf local includes` / `protobuf compiler local includes` 적용을 제거
14. `protobuf java:internal_helpers` target의 `hdrs`에 `java_features.pb.h`가 빠져 `_virtual_includes/internal_helpers` 경로에서 깨지던 문제를 `patch_protobuf_java_build_internal_helpers_hdrs.ps1`로 보완
15. protobuf/toolchain 쪽 compile failure를 상당수 제거한 뒤, 첫 MediaPipe 본체 blocker가 `mediapipe/tasks/cc/core/model_asset_bundle_resources.cc`의 `MP_ASSIGN_OR_RETURN` 매크로 문제라는 점을 확인하고 `patch_model_asset_bundle_resources.ps1`를 추가
16. 그 patch 적용 뒤 빌드를 더 진행해, 현재는 protobuf/toolchain이 주 blocker가 아니라 `mediapipe/framework/packet.cc`의 동일 계열 MSVC 매크로 문제가 blocker라는 점까지 확인

그 다음 현재 세션에서는 아래 정리 작업을 추가로 수행했다.

17. `build-worker.ps1`의 기본 `HermeticPythonVersion`을 `3.12`에서 `3.11`로 조정했다
   - 실제 현재 프로젝트 venv는 `Python 3.14.3`였고
   - TensorFlow hermetic python repo 기본값과 lockfile 매핑은 `3.11` 쪽이 기준이므로, build/query 기본값을 그쪽으로 맞췄다
18. `build-worker.ps1`에서 `--define MEDIAPIPE_DISABLE_GPU=1`를 기본값에서 제거하고 `-DisableGpu` 스위치로만 넣도록 바꿨다
   - 즉 최신 기본 경로는 GPU graph를 열 수 있는 상태를 유지하고
   - 예전 CPU-only 재현이 필요할 때만 명시적으로 `-DisableGpu`를 넘기게 했다
19. `patch_protobuf_runtime_alias_to_core.ps1`를 추가했다
   - 이 스크립트는 external `com_google_protobuf/BUILD.bazel`의 `@com_google_protobuf//:protobuf` alias를
     `protobuf_layering_check_legacy`에서 `//src/google/protobuf:protobuf`로 바꾼다
   - 목적은 `protobuf_layering_check_legacy`가 끌고 오는 `compiler:importer` 등 불필요한 compiler/runtime 혼합 의존을 줄이는 것이다
20. 위 새 patch 스크립트를 `build-worker.ps1` patch 순서에 연결했다
21. 새 patch 스크립트 자체는 단독 실행으로 정상 적용되는 것을 확인했다
22. `mediapipe/framework/tool/mediapipe_proto.bzl`를 읽어, `mediapipe_proto_library()`가 기본값으로 `cc` 외에 `py`, `java`, `java_lite`, `jspb`, `go`, `dart`, `objc`, `kt_lite`, `options_lib`까지 함께 정의하는 구조임을 확인했다
23. worker 경로에서 실제로 참조되는 `tasks/cc/core/proto`, `tasks/cc/vision/pose_detector/proto`, `tasks/cc/vision/pose_landmarker/proto`에 대해서는 저장소 내부 참조 검색상 `*_java_proto*`, `*_py_pb2`, `*_jspb_proto`, `*_go_proto`, `*_dart_proto` 직접 사용처를 찾지 못했다
24. 그래서 `rack-tracker-forked\poseLandmarker_Python\cpp_worker\overlays\...` 아래에 위 3개 BUILD overlay를 추가했다
   - 여기서는 `mediapipe_proto_library()` 호출에 `def_py_proto=False`, `def_java_lite_proto=False`, `def_kt_lite_proto=False`, `def_objc_proto=False`, `def_java_proto=False`, `def_jspb_proto=False`, `def_go_proto=False`, `def_dart_proto=False`, `def_options_lib=False`를 줘서 worker 경로 proto 패키지의 non-CC target 생성을 줄이도록 했다
25. `build-worker.ps1`는 이제 `cpp_worker\overlays` 디렉터리를 재귀적으로 `mediapipe-forked`에 복사한다
   - 즉 새 구조 수정은 fork 바깥 현재 저장소에서 관리되고 빌드 직전에 overlay로 주입된다
26. `bazel query somepath( worker -> @com_google_protobuf//src/google/protobuf/compiler:importer )`를 재시도했다
   - `_bazel_neighbor` 쓰기 권한은 escalation으로 해결됨
   - 하지만 현재는 TensorFlow hermetic Python 초기화가 query 단계에서 막혀 정확한 path를 아직 얻지 못했다
   - `System Python was not found` 또는 `Could not find requirements_lock.txt ... Specified python version: 3.11` 계열 오류가 번갈아 나타남
27. worker runtime 전제를 실제 코드에 더 강하게 반영했다
   - `main.cc`는 이제 내부적으로 task를 `IMAGE` mode로 생성한다
   - worker는 프레임별로 `MpPoseLandmarkerDetectImage(...)`를 호출한다
   - 입력 `runningMode`는 `VIDEO` 또는 `IMAGE`를 받을 수 있지만, 실제 graph 선택은 non-stream IMAGE 경로를 쓴다
28. worker 전용 source overlay 2개를 추가했다
   - `poseLandmarker_Python\cpp_worker\overlays\mediapipe\tasks\cc\vision\pose_landmarker\pose_landmarker_graph.cc`
   - `poseLandmarker_Python\cpp_worker\overlays\mediapipe\tasks\cc\vision\pose_landmarker\pose_landmarks_detector_graph.cc`
29. 위 overlay는 worker 경로를 현재 실제 제약에 맞게 축소한다
   - `PoseDetectorGraph -> SinglePoseLandmarksDetectorGraph` 직결
   - stream tracking path 제거
   - multi-pose loop path 제거
   - segmentation path 제거
30. `inference_interpreter_delegate_runner.cc`가 새 blocker로 올라온 것을 확인한 뒤, 이 타깃이 실제 inference runtime 경로에 속한다고 판단해 `patch_inference_interpreter_delegate_runner.ps1`를 추가했다
31. 그 patch를 넘긴 뒤 최신 blocker가 다시 `image_to_tensor_calculator.cc`로 돌아온 것을 확인했다
   - 이건 이제 단순한 다음 patch 후보가 아니라 worker runtime path의 실제 필수 dependency로 해석해야 한다

## 지금까지 넘긴 주요 blocker

아래는 이번 시점까지 실제로 확인하고 일부 우회한 문제들이다.

1. Bazel/Bazelisk 부재
2. Python toolchain 인식 실패
3. `mediapipe/util/analytics` 패키지 누락
4. Windows symlink 권한 문제
5. OpenCV 경로 없음
6. worker package visibility 문제
7. `pthreadpool`의 MSVC C11 플래그 문제
8. `flatbuffers` Windows genrule 문제
9. `protobuf`의 virtual include / include path 문제 다수
10. `sentencepiece` 등 pose와 무관한 text custom op가 불필요하게 빌드되는 문제
11. `tflite_signature_reader.cc`의 `MP_ASSIGN_OR_RETURN` 매크로 문제
12. `tensorflow/lite/kernels`의 StableHLO 소스가 pose worker 빌드에 불필요하게 포함되는 문제
13. stale Bazel `_virtual_includes`가 source patch를 즉시 반영하지 않는 문제
14. `XNNPACK`의 `generate_build_identifier`가 Windows에서 `bash.exe`를 요구하던 문제
15. MediaPipe / framework 내부 일부 `.cc`가 MSVC에서 `MP_ASSIGN_OR_RETURN` 계열 매크로 때문에 깨지는 문제

## 세션 종료 시점의 마지막 확인된 blocker

이전 세션 마지막 blocker는 아래였다.

- 실패 명령: `build-worker.ps1`가 내부에서 호출하는 `-c opt --define MEDIAPIPE_DISABLE_GPU=1` worker 전체 빌드
- 실패 타깃: `@@com_google_protobuf//src/google/protobuf/compiler/csharp:csharp`
- 실패 파일: `src/google/protobuf/compiler/csharp/csharp_enum.cc`
- 직접 보인 에러:
  - `csharp_enum.h`에서 `google/protobuf/compiler/csharp/csharp_source_generator_base.h`를 찾지 못함

하지만 그 다음 후속 세션에서 이 문제는 넘겼고, 현재 최신 blocker는 아래다.

- 실패 명령: `build-worker.ps1`가 내부에서 호출하는 `-c opt --define MEDIAPIPE_DISABLE_GPU=1` worker 전체 빌드
- 최신 실패 타깃: `//mediapipe/framework:packet`
- 최신 실패 파일: `C:\Users\neighbor\Documents\Code\Github\mediapipe-forked\mediapipe\framework\packet.cc`
- 직접 보인 에러:
  - `mediapipe/framework/packet.cc(69): error C2065: 'MP_STATUS_MACROS_IMPL_REM': 선언되지 않은 식별자입니다.`
  - `mediapipe/framework/packet.cc(69): error C2144: 구문 오류: auto'은(는) ';' 다음에 와야 합니다.`

그 직전에는 아래 MediaPipe core 파일도 같은 계열로 실패했고, 이건 이번 세션에서 patch를 추가해 넘겼다.

- `mediapipe/tasks/cc/core/model_asset_bundle_resources.cc`
  - `MP_ASSIGN_OR_RETURN` 사용부를 명시적 `StatusOr` 처리로 바꾸는 `patch_model_asset_bundle_resources.ps1` 추가

즉 최신 시점 blocker는 이제 protobuf/toolchain보다는 MediaPipe 본체의 Windows/MSVC 매크로 호환성으로 넘어왔다.

하지만 이걸 그대로 "다음 깨지는 곳마다 patch"로 계속 가는 것은 최신 판단 기준으로 비추천이다.

더 본질적인 최신 blocker 해석은 아래다.

- 현재 실제 병목은 `worker 코드`가 아니라 `Bazel + MediaPipe + Protobuf 전체 빌드 그래프`
- 특히 pose worker runtime에 필요 없는 `protobuf compiler`와 language generators (`csharp`, `java`, `rust`)가 graph에 들어오면서 시간을 크게 소모하고 있다
- 지금까지 protobuf 관련 patch가 많이 쌓인 이유도 결국 이 불필요한 compiler graph를 계속 살리려 했기 때문이다
- 따라서 다음 세션에서는 `packet.cc` 같은 개별 MSVC patch를 바로 늘리기 전에, 먼저 `왜 protobuf compiler 전체가 그래프에 포함되는가`를 끊는 것이 더 중요하다

현재 세션에서 여기에 대해 추가로 확인한 정황은 아래다.

- MediaPipe 저장소 내부 여러 BUILD가 `@com_google_protobuf//:protobuf`에 직접 의존한다
- external protobuf 쪽 `@com_google_protobuf//:protobuf` alias는 기본적으로 `protobuf_layering_check_legacy`를 가리킨다
- `protobuf_layering_check_legacy`는 well-known type convenience deps뿐 아니라 `//src/google/protobuf/compiler:importer`까지 직접 의존한다
- 따라서 최신 세션 판단상, compiler graph가 끼어드는 핵심 원인 후보 중 하나는 이 legacy runtime alias다
- 이번 세션에서 추가한 patch는 바로 이 경로를 끊어보려는 첫 구조적 수정이다
- 추가로 이번 세션에서 확인한 점:
  - `mediapipe/framework/tool/mediapipe_proto.bzl`의 `mediapipe_proto_library_impl()`는 기본적으로 non-CC 언어 타깃도 함께 정의한다
  - 이건 곧바로 모두 build된다는 뜻은 아니지만, worker 경로 proto 패키지의 graph 표면적을 넓히는 구조라는 점은 분명하다
  - 그래서 최신 세션에서는 `fork 파일 직접 수정`보다 `overlay BUILD로 worker 경로 proto 패키지의 non-CC target 생성을 끄는 첫 구조 실험`까지 진행했다

## 지금 서버 상태

현재 서버는 다음처럼 이해하면 된다.

- `POSE_CPP_WORKER_ENABLED=false`
  - 기존 Python MediaPipe 경로는 사용 가능
- `POSE_CPP_WORKER_ENABLED=true`
  - 아직 `mediapipe_pose_worker.exe`가 없어서 실패

즉 지금은 아직 C++ worker 경로로 서버를 돌릴 수 없다.

## 다음 세션에서 우선 할 일

다음 Codex 세션에서는 아래 순서가 가장 효율적이다.

1. 이 문서와 [build-worker.ps1](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\build-worker.ps1), [patch_protobuf_runtime_alias_to_core.ps1](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\patch_protobuf_runtime_alias_to_core.ps1), [main.cc](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\src\main.cc) 를 먼저 읽기
2. `CPU-only를 먼저 완성`이라는 오래된 가정을 버리고, 사용자의 최신 지시대로 `GPU 빌드 방향`을 목표로 삼기
3. 현재 `build-worker.ps1`는 기본으로 GPU disable define을 넣지 않으므로, 이 기본값을 유지한 채 query/build를 재개할지 점검하기
4. GPU 방향이라면 Windows에서 실제로 쓸 backend가 무엇인지 먼저 정리하기
   - MediaPipe Tasks GPU
   - TensorFlow Lite GPU delegate
   - Windows에서 필요한 EGL/GL/D3D 관련 repo/BUILD/라이브러리
5. 그 다음 현재 worker 타깃이 GPU 관련 의존을 어느 경로로 끌고 오는지 Bazel query 또는 BUILD 읽기로 확인하기
6. 필요하면 CPU-only patch 세트와 GPU-target patch 세트를 분리하기
7. 최신 전략 기준으로는 더 이상 `protobuf compiler`를 patch로 계속 살리는 방향을 기본값으로 두지 않기
8. `bazel query` 또는 관련 `BUILD.bazel` 읽기로 `pose_landmarker worker -> mediapipe tasks -> protobuf compiler` 경로가 어디서 연결되는지 먼저 확인하기
9. 특히 `@com_google_protobuf//src/google/protobuf/compiler/...` 계열이 왜 graph에 포함되는지 원인 타깃을 찾기
10. 이번 세션에서 추가한 `protobuf` legacy alias slimming patch만으로 graph가 얼마나 줄어드는지 먼저 확인하기
11. 그래도 compiler graph가 많이 남으면 `@com_google_protobuf//:protobuf` 직접 의존 BUILD들을 더 좁은 runtime/WKT deps로 바꾸는 2차 전략으로 가기
12. 새로 추가한 overlay BUILD 3종이 실제 build/query graph를 얼마나 줄이는지 먼저 확인하기
13. query가 계속 hermetic Python 단계에서 막히면, build/query 공통으로 먹는 최소 래퍼 또는 repo_env 전달 방식을 `build-worker.ps1` 쪽에 추가해 재현성을 높이기
14. 그 구조 변경이 어려울 때만 차선책으로 `packet.cc` 같은 MediaPipe 본체 MSVC patch를 이어서 적용하기
15. GPU 경로가 현실적으로 너무 크면, `worker는 CPU delegate로 먼저 exe 생성 + 이후 GPU delegate branch`로 전략을 분리할지 사용자와 맞추기

## 상태 체크포인트

- 진행 상황 요약: `build-worker.ps1`를 바탕으로 patch 스크립트를 새로 정리했고 `MEDIAPIPE_DISABLE_GPU` 기본값을 제거한 채 반복해서 빌드를 돌리며 더 이상 `protobuf compiler` 오류에 막히지 않도록 그래프 얇아지게 했다. 그 과정에서 inference exe는 여전히 생성되지 않았고, 가장 최근에는 `mediapipe/framework/packet.cc`의 `MP_STATUS_MACROS_IMPL_REM` 선언 오류에서 멈춰 있다.
- 핵심 판단: GPU 빌드 방향으로 목표를 못박았고, 이전처럼 매크로 하나하나를 패치하기보단 builder graph에서 `protobuf compiler`/language generator 의존을 먼저 축소하는 것이 더 효과적이라고 결론내렸다.
- 제약 조건: `_virtual_includes`와 legacy alias로 인한 stale artifact가 주기적으로 Bazel clean을 부르고 있고, 현재 빌드 실패는 MediaPipe core의 MSVC 전용 상태 매크로(`MP_STATUS_MACROS_IMPL_REM`)에서 나오므로 patch descriptor를 계속 더 생산해야 한다.
- patch descriptor: `packet.cc` 매크로에 대응하는 파편적 패치가 아직 완성되지 않아서 빌드가 중단되고 있으며, 추후에도 `MP_ASSIGN_OR_RETURN` 계열 매크로에 대한 추가 스크립트를 만들어야 한다.
- 다음 단계: `build-worker.ps1`를 다시 돌려 빌드 로그를 캡처하고, 그 로그를 바탕으로 Windows/MSVC용 매크로 patch를 계속 작성하는 한편, 격주로 `bazel query`를 다시 실행해 `@com_google_protobuf//src/google/protobuf/compiler` 의존을 얼마나 줄일 수 있는지 확인한다.

## 권장 전략

다음 세션에서는 아래 전략을 우선 고려하는 것이 맞다.

- 먼저 "Windows에서 MediaPipe Pose Landmarker GPU를 실제로 어떤 backend로 빌드할 것인가"를 확정한다
- `MEDIAPIPE_DISABLE_GPU=1`를 제거하기 전에, 그 define이 막고 있던 의존 그래프가 무엇인지 확인한다
- GPU 그래프를 여는 순간 추가되는 외부 의존성과 플랫폼 제약을 먼저 문서화한다
- protobuf/csharp 같은 noise blocker는 계속 패치할 수 있지만, GPU 목표로 바뀐 이상 이제는 그래프 자체 설계가 우선이다

최신 전략 우선순위는 이보다 더 구체적으로 아래처럼 바뀌었다.

- 1순위는 `protobuf compiler 제거 또는 최소화`
- 2순위는 `pose worker runtime에 실제 필요한 deps만 남기는 graph 축소`
- 3순위가 그 다음 개별 source patch다

즉 최신 판단은 다음과 같다.

- `protobuf java / rust / csharp`를 계속 patch하는 것은 근본 해결이 아니다
- 지금 하루 이상 걸리는 핵심 원인은 worker 코드가 아니라 `불필요한 compiler/tooling dependency를 함께 빌드하는 구조`
- 따라서 다음 세션의 올바른 시작점은 `개별 compile error 수정`이 아니라 `BUILD graph slimming`이다

이유:

- 지금까지의 대부분 실패는 worker 코드가 아니라 불필요하거나 간접적인 tool/codegen/build graph에서 발생했다
- GPU 목표로 전환한 뒤에도 같은 식으로 external cache include만 계속 땜질하면 다시 비효율적인 수정 패턴에 빠질 가능성이 높다
- 사용자가 그 패턴이 반복되면 중단하라고 이미 명시했다

## 참고 메모

- Windows Developer Mode는 이미 켜졌다고 가정하고 작업했다
- `opencv-prebuilt`는 이미 정상 설치/압축해제된 상태다
- 새 세션에서는 `mediapipe-forked`가 `git safe.directory` 경고를 낼 수 있다
- `cmd` 셸이라 PowerShell cmdlet은 항상 절대 경로 PowerShell로 실행하는 편이 안전하다
- 현재 `build-worker.ps1`는 external cache와 `mediapipe-forked` 모두에 patch를 적용하므로, 새 세션에서 먼저 이 스크립트 자체를 읽는 것이 중요하다
- 이번 후속 세션에서 `build-worker.ps1`는 patch 순서가 여러 번 조정되었다
  - 범용 protobuf include rewrite는 제거됨
  - `protobuf java generator variants`, `protobuf java lite field generator includes`, `protobuf java internal helpers`, `protobuf java BUILD internal_helpers hdrs`는 뒤쪽 단계에서 적용되도록 정리됨
- 현재 세션에서는 여기에 더해 `patch_protobuf_runtime_alias_to_core.ps1`가 추가되었고 `build-worker.ps1` 기본 hermetic Python 버전은 `3.11`로 바뀌었다
- 또한 현재 `build-worker.ps1`는 `-DisableGpu`를 주지 않으면 `MEDIAPIPE_DISABLE_GPU=1`를 기본으로 넣지 않는다
- 현재 세션에서는 여기에 더해 `cpp_worker\overlays\...` 경로가 추가되었고, `build-worker.ps1`가 이 overlay들을 `mediapipe-forked`로 복사한다
- 이번 세션 overlay는 worker 경로 proto BUILD 3개뿐 아니라 `pose_landmarker` worker 전용 source overlay 2개도 포함한다
- 목적은 `protobuf compiler 제거 또는 최소화` 전략의 첫 실제 코드 변경으로, worker 경로에서 사용하지 않는 non-CC proto target 생성을 줄여 보는 것이다
- 이어진 다음 단계 목적은 worker가 실제로 쓰는 runtime graph 자체도 `IMAGE + single pose + no segmentation` 전제로 더 작게 만드는 것이다
- 하지만 이 patch 세트는 최신 판단 기준으로 임시 우회일 뿐이고, 다음 세션에서는 유지보수보다 `compiler graph 제거 가능성`을 먼저 점검해야 한다
- 세션 마지막 사용자 지시는 명확하다: `GPU 빌드 방향으로 목표를 바꿔서 그래프를 다시 설계`
- 그 다음 최신 사용자 지시는 더 구체적이다: `protobuf compiler 제거 전략으로 전환`
- 따라서 다음 세션에서는 더 이상 `MEDIAPIPE_DISABLE_GPU=1`를 무비판적으로 유지하면 안 된다
- 최신 `build-worker.ps1` 기본 호출은 더 이상 `--define MEDIAPIPE_DISABLE_GPU=1`를 넣지 않는다
- 현재 산출물 `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\bin\mediapipe_pose_worker.exe` 는 여전히 없다
## 2026-03-31 Direction Reset

This section supersedes the older 2026-03-31 patch-chasing notes below this handoff. The current direction is no longer "keep fixing the next failing `.cc` file". The current direction is "shrink the build graph so the worker stops pulling unnecessary MediaPipe and protobuf/tooling targets in the first place."

### Current status

- The worker runtime path was tightened to match the graph-slimming strategy:
  - `poseLandmarker_Python/cpp_worker/src/main.cc` now creates the task in `IMAGE` running mode internally.
  - The worker accepts `VIDEO` or `IMAGE` as protocol input, but processes extracted frames independently and calls `MpPoseLandmarkerDetectImage(...)`.
  - The worker still enforces `numPoses=1` and `outputSegmentationMasks=false`.
- Worker-specific source overlays were added under `poseLandmarker_Python/cpp_worker/overlays/mediapipe/tasks/cc/vision/pose_landmarker/`:
  - `pose_landmarker_graph.cc`
  - `pose_landmarks_detector_graph.cc`
- Those overlays intentionally collapse the default task graph to the worker's actual runtime assumptions:
  - no stream-mode tracking path
  - no multi-pose loop path
  - no segmentation path
  - `PoseDetectorGraph -> SinglePoseLandmarksDetectorGraph` direct path for the worker build
- `poseLandmarker_Python/cpp_worker/build-worker.ps1` was rerun multiple times.
- The worker executable still does not exist:
  - `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\bin\mediapipe_pose_worker.exe`
- The build graph did shrink again after these overlays:
  - the analyzed target count dropped to about `296` in the latest rerun
  - the build advanced past `inference_interpreter_delegate_runner.cc` after adding a focused fallback patch
- Latest observed fatal source failure:
  - `C:\Users\neighbor\Documents\Code\Github\mediapipe-forked\mediapipe\calculators\tensor\image_to_tensor_calculator.cc`
  - around lines 171 and 262
  - `MP_ASSIGN_OR_RETURN` / `MP_STATUS_MACROS_IMPL_REM` failure pattern
- At this point, `image_to_tensor_calculator.cc` should be treated differently from earlier patch-loop blockers:
  - it is not just another random leaf compile error
  - it is on the actual runtime path of `ImagePreprocessingGraph`
  - both `PoseDetectorGraph` and `SinglePoseLandmarksDetectorGraph` still require it

### Current directive

- Do not continue the default workflow of:
  - open latest failing `.cc` or `.h`
  - add another dedicated patch script
  - rerun build
- Treat the current compile failure as evidence that the graph is still too wide, not as the primary work item.
- Prioritize BUILD graph slimming for the pose worker path.

### Required next-session priority

1. Map the actual dependency path from `//mediapipe/tasks/c/vision/pose_landmarker/worker:mediapipe_pose_worker` to the calculator and proto/tooling targets that are not required at runtime.
2. Verify which worker-path targets are bringing in broad calculator packages such as tensor/image preprocessing, utility calculators, and non-CC proto outputs.
3. Reduce graph width before adding any new source patch:
   - narrow worker BUILD deps
   - narrow task graph deps
   - expand or refine overlay BUILD targets
   - remove non-runtime proto/codegen targets from the worker path where possible
4. Only if graph slimming stalls on a clearly unavoidable runtime dependency should a new source-level MSVC patch be added.

### Newly confirmed unavoidable runtime dependencies

- `mediapipe/tasks/cc/components/processors/image_preprocessing_graph.cc` directly instantiates `ImageToTensorCalculator`.
- `PoseDetectorGraph` uses `ImagePreprocessingGraph`.
- The worker-specific `SinglePoseLandmarksDetectorGraph` overlay also still uses `ImagePreprocessingGraph`.
- Therefore `mediapipe/calculators/tensor:image_to_tensor_calculator` is now effectively confirmed as an unavoidable runtime dependency for this worker path.
- That means the next source-level fallback patch, if needed, should target `image_to_tensor_calculator.cc` rather than reopening broader BUILD questions around that calculator.

### Explicitly deprioritized

- Continuing the previous patch-by-patch loop as the default plan
- Treating the latest failing source file as the primary next task
- Growing the patch script set first and asking graph questions later

### Repo files most relevant to the new direction

- `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\build-worker.ps1`
- `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\overlays\...`
- `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\BUILD.bazel`
- relevant `BUILD` / `.bzl` files in `mediapipe-forked` along the worker dependency path

### Notes kept only as context

- Existing patch scripts remain in the repo because they document what has already been tried and what sources were confirmed to fail under MSVC.
- Those scripts are now fallback tools, not the main plan.
