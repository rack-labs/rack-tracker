# MediaPipe 기반 포즈 랜드마커 기능 명세

> 문서 동기화 강제 프롬프트
>
> 이 문서를 수정하는 AI 또는 작성자는 반드시 아래 짝 문서를 함께 확인해야 한다.
>
> - `docs/mvp-v1/features/mediapipe/architecture.md`
>
> 규칙:
>
> - 명세가 바뀌면 아키텍처 문서도 즉시 확인하고, 불일치가 있으면 함께 수정한다.
> - 아키텍처가 바뀌어 명세 설명과 충돌하면, 이 문서도 즉시 수정한다.
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
> - 이 문서를 수정한 뒤에는 반드시 짝 문서를 다시 읽고, 동일한 변경이 반영되어야 하는지 점검하라.
> - 필요하면 두 문서를 같은 커밋 또는 같은 작업 단위에서 함께 수정하라.

## 1. 이 기능은 무엇인가

이 기능은 운동 영상을 받아 사람의 자세를 읽고, 관절 좌표와 분석용 메타데이터를 정리해 주는 백엔드 기능이다.

현재 구현 기준으로 이 기능은 단순히 관절 좌표만 뽑아 주지 않는다. 아래까지 한 번에 수행한다.

- 비디오 입력 선택 또는 업로드 저장
- 프레임 추출
- MediaPipe Pose Landmarker 추론
- 스켈레톤 JSON 생성
- 기본 분석 결과 생성
- benchmark 생성
- placeholder 피드백 생성

즉, 지금의 MediaPipe 기능은 전체 motion-analysis 파이프라인의 중심 추론 단계다.

## 2. 입력

### 2.1 사용자가 넣는 입력

현재 `POST /jobs`에서 받을 수 있는 입력은 아래와 같다.

- `video`
- `fps`
- `samplingFps`
- `exerciseType`
- `modelAssetPath`
- `modelVariant`
- `delegate`

설명:

- `video`
  - 업로드한 영상 파일
  - 없으면 기본 목업 비디오를 사용한다.
- `fps` 또는 `samplingFps`
  - 추론 전에 프레임을 얼마나 촘촘히 샘플링할지 정하는 값
  - 실제 내부에서는 `samplingFps`를 우선 사용하고, 없으면 `fps`를 쓴다.
- `exerciseType`
  - 현재 분석 summary와 feedback 문구에 반영된다.
- `modelAssetPath`
  - 특정 `.task` 파일을 직접 지정하고 싶을 때 사용
- `modelVariant`
  - `lite`, `full`, `heavy`
- `delegate`
  - `GPU` 또는 `CPU`

### 2.2 입력 기본값

업로드가 없으면 아래 기본 비디오를 사용한다.

- `poseLandmarker_Python/src/video/backSquat.mp4`

기본 모델 관련 설정은 아래와 같다.

- 기본 모델 변형: `full`
- 기본 모델 경로: `poseLandmarker_Python/models/mediapipe/pose_landmarker_full.task`
- 기본 delegate: `GPU`

### 2.3 입력 검증 규칙

현재 구현의 검증 규칙은 아래와 같다.

- `samplingFps`는 `0`보다 커야 한다.
- `modelVariant`는 `lite`, `full`, `heavy`만 허용한다.
- `delegate`는 `GPU`, `CPU`만 허용한다.
- 빈 문자열은 미입력으로 본다.
- Swagger UI placeholder인 `"string"`도 미입력으로 본다.

잘못된 값이면 비동기 job을 만들기 전에 즉시 `HTTP 400`을 반환한다.

## 3. 내부 처리 흐름

이 기능 안에서 데이터는 아래 순서로 이동한다.

1. 요청을 받는다.
2. 업로드 파일을 저장하거나 기본 비디오를 선택한다.
3. 비디오에서 프레임을 추출한다.
4. 각 프레임을 MediaPipe가 읽을 수 있는 형식으로 바꾼다.
5. MediaPipe Pose Landmarker로 프레임별 포즈를 추론한다.
6. 추론 결과를 공통 JSON 구조로 직렬화한다.
7. 이를 `skeleton` 구조로 묶는다.
8. 기본 분석 결과와 benchmark를 만든다.
9. placeholder 피드백을 만든다.
10. 완료된 job 결과를 조회 API로 노출한다.

쉬운 비유로 보면:

- 비디오를 넣으면
- 프레임 분해기, 자세 판독기, 결과 정리기, 요약기, 계측기가 순서대로 작동하고
- 마지막에 분석 꾸러미를 내보낸다.

## 4. MediaPipe 추론 동작

### 4.1 실행 모드

현재 백엔드의 실제 주 실행 모드는 `VIDEO`다.

이유:

- 프레임마다 `timestamp_ms`가 이미 있다.
- 배치 비디오 분석 흐름과 가장 잘 맞는다.
- 후속 `analysis`와 `benchmark`가 시간축 정보를 그대로 쓸 수 있다.

코드상 지원 개념은 아래 세 가지다.

- `IMAGE`
- `VIDEO`
- `LIVE_STREAM`

하지만 현재 job 파이프라인에서 실제로 쓰는 것은 `VIDEO`다.

### 4.2 이미지 변환

추론 직전 각 프레임은 아래 과정을 거친다.

1. 이미지가 존재하는지 확인한다.
2. 3채널 이미지인지 검사한다.
3. BGR 이미지를 RGB로 바꾼다.
4. `mp.Image` 객체로 감싼다.
5. 프레임의 `timestamp_ms`를 정수 밀리초로 정리한다.

### 4.3 delegate 정책

기본 정책은 GPU 우선이다.

- 요청 delegate가 `GPU`면:
  - 먼저 GPU로 초기화
  - 실패하면 CPU로 한 번 더 시도
- 요청 delegate가 `CPU`면:
  - CPU만 시도

초기화 결과는 benchmark와 inference 메타데이터에 아래 형태로 남는다.

- `requestedDelegate`
- `actualDelegate`
- `delegateFallbackApplied`
- `delegateErrors`

### 4.4 모델 정책

현재 지원 모델은 아래 세 가지다.

- `lite`
- `full`
- `heavy`

권장 해석:

- `lite`: 속도 우선
- `full`: 기본 운영값
- `heavy`: 정확도 우선

현재 백엔드 기본값은 `full`이다.

## 5. 출력

### 5.1 프레임별 추론 결과

프레임마다 아래 정보가 만들어진다.

- `frameIndex`
- `timestampMs`
- `poseDetected`
- `landmarks`

각 landmark는 아래 정보를 가진다.

- `name`
- `x`
- `y`
- `z`
- `visibility`
- `presence`

현재 구현은 첫 번째 pose만 사용한다. 여러 사람을 동시에 직렬화하지 않는다.

### 5.2 스켈레톤 결과

추론 결과는 `skeleton` 구조로 정리된다.

- `frames`
- `videoInfo`
- `nextTimestampCursorMs`

`videoInfo`에는 아래 메타데이터가 포함된다.

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

### 5.3 분석 결과

현재 `analysis`는 기본 골격만 제공한다.

- `summary`
- `kpis`
- `timeseries`
- `events`
- `repSegments`
- `issues`

현재는 정교한 운동 판정 엔진이라기보다, 스켈레톤 데이터를 후속 소비하기 쉬운 형식으로 정리하는 역할에 가깝다.

### 5.4 피드백 결과

현재 `llmFeedback`는 실제 LLM 응답이 아니다.

- `version: "v1"`
- `model: "rule-based-placeholder"`
- `overallComment`
- `highlights`
- `corrections`
- `coachCue`

즉, 피드백 포트는 이미 응답 계약에 들어가 있지만 현재 내용은 임시 placeholder다.

### 5.5 benchmark 결과

benchmark는 두 갈래로 제공된다.

- summary
- frame-level detail

summary에는 주로 아래가 들어간다.

- run metadata
- timing summary
- quality summary
- comparison tags

frame-level detail에는 프레임별 계측값이 들어간다.

- `rgbConversionMs`
- `inferenceMs`
- `serializationMs`
- `totalFramePipelineMs`
- `poseDetected`
- `landmarkCount`
- `avgVisibility`
- `minVisibility`

## 6. API에서 보는 결과물

### 6.1 상태 조회

`GET /jobs/{job_id}`

현재 노출되는 상태는 아래다.

- `queued`
- `extracting`
- `analyzing`
- `generating_feedback`
- `completed`
- `failed`

중요한 점:

- `extracting` 상태 안에 실제 pose inference와 skeleton 저장도 포함되어 있다.
- 아직 `inferring` 같은 별도 외부 상태는 없다.

### 6.2 최종 결과 조회

`GET /jobs/{job_id}/result`

반환 최상위 구조:

```json
{
  "skeleton": {},
  "analysis": {},
  "llmFeedback": {},
  "benchmark": {}
}
```

### 6.3 스켈레톤 페이지 조회

`GET /jobs/{job_id}/skeleton?offset=0&limit=30`

반환 항목:

- `frames`
- `videoInfo`
- `nextTimestampCursorMs`
- `offset`
- `limit`
- `totalFrames`

### 6.4 스켈레톤 다운로드

`GET /jobs/{job_id}/skeleton/download`

job 완료 후 저장된 `tmp/skeletons/{job_id}.json` 파일을 내려준다.

### 6.5 benchmark 조회

- `GET /jobs/{job_id}/benchmark`
- `GET /jobs/{job_id}/benchmark/frames`

완료 전 조회하면 `HTTP 409`를 반환한다.

## 7. 실패 정책

현재 구현은 보수적으로 실패한다.

- 잘못된 요청 값: 즉시 `HTTP 400`
- 존재하지 않는 job 조회: `HTTP 404`
- 결과 준비 전 조회: `HTTP 409`
- 모델 파일 없음: job 실패
- MediaPipe import 실패: job 실패
- landmarker 초기화 실패: job 실패
- 프레임 입력 이상: job 실패
- 특정 프레임 추론 실패: job 전체 실패
- 결과 직렬화 실패: job 전체 실패

즉, 현재는 부분 성공보다 일관된 실패 처리를 우선한다.

## 8. 성능 및 운영 관점에서 알아둘 점

- `samplingFps`는 추론 비용을 줄이는 가장 직접적인 입력이다.
- 프레임 추출, RGB 변환, 추론, 직렬화, 분석 시간은 benchmark로 남는다.
- GPU를 기본으로 쓰지만, 환경에 따라 CPU fallback이 실제 동작 delegate가 될 수 있다.
- 현재 결과는 메모리 내 리스트로 누적되므로 초장시간 영상에는 추가 최적화가 필요하다.
- benchmark summary와 frame detail이 분리돼 있어 비교 화면과 상세 진단 화면을 따로 만들기 쉽다.

## 9. 현재 범위 밖

현재 문서 기준으로 아직 실사용 범위 밖인 항목은 아래다.

- 단일 이미지 분석 전용 API
- `LIVE_STREAM` 기반 실시간 분석 API
- world landmarks 외부 반환
- segmentation mask 외부 반환
- 프레임 일부 실패 후 계속 진행하는 partial failure 정책
- 실제 LLM 기반 코칭 피드백
