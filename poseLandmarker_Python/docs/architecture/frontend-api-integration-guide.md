# Frontend API Integration Guide

## 1. 목적

이 문서는 `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python`를 기준으로
`C:\Users\neighbor\Documents\Code\Github\racl-labs-frontend-forked`를 개편할 때 필요한 프론트엔드 계약을 정리한 문서다.

문서의 목표는 다음과 같다.

- 프론트가 호출해야 하는 API 규약을 코드 기준으로 고정한다.
- 요청 형식, 응답 형식, 기본값, 에러 규칙을 정리한다.
- 동기/비동기 처리 경계를 분명히 한다.
- 화면 상태머신, polling 전략, 결과 로딩 전략을 정의한다.
- 프론트 구현 시 주의해야 할 현재 백엔드 제약을 명시한다.

기준 소스는 현재 `poseLandmarker_Python`의 실제 코드다.
즉 문서보다 코드가 우선이며, 아래 내용은 2026-04-09 기준 코드와 맞춰 작성되었다.

## 2. 백엔드 개요

백엔드는 FastAPI 기반이며 기본 실행 주소는 아래와 같다.

- Base URL: `http://127.0.0.1:8000`
- Health check: `GET /`
- Swagger: `GET /docs`

현재 CORS 허용 origin:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

즉 Vite 개발 서버 기준 연동은 바로 가능하다.

## 3. 프론트가 알아야 하는 처리 모델

### 3.1 처리 방식 분류

현재 백엔드에는 두 가지 분석 진입점이 있다.

1. 비동기 잡 방식
   - `POST /jobs`
   - `GET /jobs/{jobId}`
   - `GET /jobs/{jobId}/result`
   - 대용량 비디오 업로드, 긴 분석 시간, 진행률 UI가 필요한 기본 경로

2. 동기 프리뷰 방식
   - `POST /analysis/preview`
   - 요청 하나로 끝나지만, 응답이 돌아올 때까지 HTTP 연결이 유지된다.
   - 빠른 실험용이나 내부 QA 용도에는 쓸 수 있지만, 실제 사용자 UX 기준 메인 경로로 쓰기엔 부적합하다.

프론트 개편 기준으로는 `POST /jobs` 기반 비동기 설계를 메인 플로우로 잡는 것이 맞다.

### 3.2 실제 파이프라인

비동기 잡이 생성되면 내부적으로 아래 순서로 처리된다.

1. 비디오 업로드 저장
2. 프레임 추출
3. 포즈 추론
4. skeleton JSON 매핑
5. 동작 분석
6. LLM 피드백 생성
7. benchmark 요약 생성
8. 완료 상태 전환

프론트는 이 전체 파이프라인을 하나의 업로드 요청으로 보지 말고, 아래 세 구간으로 나눠 생각해야 한다.

- 업로드 구간
- 백엔드 작업 진행 구간
- 결과 fetch 및 시각화 구간

## 4. 프론트 권장 상태머신

현재 프론트에서 사용할 상태는 아래처럼 잡는 것이 안전하다.

```ts
type AnalysisStatus =
  | 'idle'
  | 'uploading'
  | 'queued'
  | 'extracting'
  | 'analyzing'
  | 'generating_feedback'
  | 'completed'
  | 'error'
```

권장 store shape:

```ts
type AnalysisStore = {
  status: AnalysisStatus
  selectedVideoFile: File | null
  form: {
    samplingFps: number | null
    exerciseType: 'squat'
    bodyweightKg: number | null
    externalLoadKg: number | null
    barPlacementMode: 'auto' | 'high_bar' | 'low_bar'
    modelVariant: 'lite' | 'full' | 'heavy' | null
    delegate: 'CPU' | 'GPU' | null
  }
  jobId: string | null
  progress: {
    stage: string
    currentStep: number
    totalSteps: number
    ratio: number
  } | null
  error: {
    code: string
    message: string
  } | null
  result: MotionAnalysisSummary | null
  skeletonPage: SkeletonPageResponse | null
}
```

주의:

- `uploading`은 프론트 로컬 상태다. 백엔드는 이 상태를 내려주지 않는다.
- 백엔드 status는 `queued`, `extracting`, `analyzing`, `generating_feedback`, `completed`, `failed`만 사용한다.
- 프론트의 `error` 상태는 백엔드 `failed` 또는 네트워크 실패를 모두 포괄하는 UI 상태다.

## 5. 엔드포인트 요약

### 5.1 필수 엔드포인트

| Method | Path | 용도 | 프론트 사용도 |
|---|---|---|---|
| `POST` | `/jobs` | 분석 job 생성 | 필수 |
| `GET` | `/jobs/{job_id}` | 상태 polling | 필수 |
| `GET` | `/jobs/{job_id}/result` | 최종 요약 결과 조회 | 필수 |

### 5.2 선택 엔드포인트

| Method | Path | 용도 | 프론트 사용도 |
|---|---|---|---|
| `GET` | `/jobs/{job_id}/skeleton` | skeleton frame 페이지 조회 | 강력 권장 |
| `GET` | `/jobs/{job_id}/skeleton/download` | 전체 skeleton JSON 다운로드 | 선택 |
| `GET` | `/jobs/{job_id}/benchmark` | benchmark summary 조회 | 선택 |
| `GET` | `/jobs/{job_id}/benchmark/frames` | frame-level benchmark 조회 | 선택 |
| `POST` | `/analysis/preview` | 동기 preview 실행 | 선택 |

핵심 포인트는 아래다.

- `/result`에는 전체 skeleton frames가 없다.
- 실제 skeleton overlay 렌더링이 필요하면 `/skeleton`을 추가로 호출해야 한다.
- 따라서 프론트는 "완료 후 1회 결과 fetch"가 아니라 "완료 후 summary fetch + skeleton fetch" 구조로 가는 것이 맞다.

## 6. 요청 규약

### 6.1 `POST /jobs`

Content-Type:

- `multipart/form-data`

폼 필드:

| 필드명 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `video` | file | 아니오 | 업로드 비디오 파일 |
| `fps` | number | 아니오 | 구버전 호환 필드 |
| `samplingFps` | number | 아니오 | 실제 권장 필드 |
| `exerciseType` | string | 아니오 | 현재는 `squat`만 지원 |
| `bodyweightKg` | number | 아니오 | 체중 |
| `externalLoadKg` | number | 아니오 | 바벨/플레이트 등 외부 부하 |
| `barPlacementMode` | string | 아니오 | `auto`, `high_bar`, `low_bar` |
| `modelAssetPath` | string | 아니오 | 커스텀 모델 경로 |
| `modelVariant` | string | 아니오 | `lite`, `full`, `heavy` |
| `delegate` | string | 아니오 | `CPU`, `GPU` |

실제 프론트에서는 `fps` 대신 `samplingFps`만 보내는 것을 권장한다.

### 6.2 기본값 및 서버 보정 규칙

서버 동작 기준:

- `samplingFps`가 없고 `fps`가 있으면 `fps`를 사용
- 둘 다 없으면 원본 source FPS 기준으로 처리
- `exerciseType`이 비어 있으면 mock video 사용 시 `squat`로 채움
- `bodyweightKg`, `externalLoadKg`도 mock video 사용 시 기본값으로 채움
- `barPlacementMode`가 없으면 내부적으로 `high_bar`로 정규화됨
- `modelVariant` 기본값은 `full`
- `delegate`를 보내지 않으면 백엔드 기본 경로 사용

중요한 제약:

- `exerciseType`은 현재 `squat` 외 값이 들어오면 분석 단계에서 실패한다.
- 즉 프론트 드롭다운은 당분간 `squat`만 노출하는 것이 맞다.

### 6.3 업로드 없는 호출

`video`를 보내지 않아도 API는 동작한다.
이 경우 서버는 내장 샘플 비디오 `src/video/backSquat.mp4`를 사용한다.

이 기능은 개발/QA에는 유용하지만, 실제 사용자용 UI에서는 명시적 dev mode가 아니라면 숨기는 편이 낫다.

## 7. 응답 규약

### 7.1 `POST /jobs` 응답

```json
{
  "jobId": "job_ab12cd34",
  "status": "queued"
}
```

프론트 처리:

- `jobId` 저장
- 즉시 polling 시작
- UI status는 `uploading -> queued` 또는 `uploading -> polling`으로 전환

### 7.2 `GET /jobs/{job_id}` 응답

```json
{
  "jobId": "job_ab12cd34",
  "status": "analyzing",
  "progress": {
    "stage": "analyzing",
    "currentStep": 2,
    "totalSteps": 4,
    "ratio": 0.75
  },
  "error": null
}
```

실패 예시:

```json
{
  "jobId": "job_ab12cd34",
  "status": "failed",
  "progress": {
    "stage": "failed",
    "currentStep": 0,
    "totalSteps": 4,
    "ratio": 0.0
  },
  "error": {
    "code": "ValueError",
    "message": "Unsupported exercise_type 'deadlift'. Only 'squat' is currently implemented."
  }
}
```

프론트 처리 원칙:

- `status === completed`면 polling 종료 후 결과 fetch
- `status === failed`면 polling 종료 후 에러 UI
- 그 외 status는 진행률 UI 갱신

### 7.3 `GET /jobs/{job_id}/result` 응답

응답 타입은 `MotionAnalysisSummary`다.
구조상 `skeleton`, `analysis`, `llmFeedback`, `benchmark` 4개 블록을 가진다.

중요:

- 여기의 `skeleton`은 전체 frame 배열이 아니다.
- `videoInfo`와 `nextTimestampCursorMs`만 포함된다.
- 즉 이 응답만으로 canvas skeleton overlay를 그릴 수 없다.

예시:

```json
{
  "skeleton": {
    "videoInfo": {
      "videoSrc": "C:\\path\\to\\video.mp4",
      "displayName": "backSquat.mp4",
      "sourceFps": 30.0,
      "frameCount": 320,
      "width": 1920,
      "height": 1080,
      "backend": "opencv",
      "extractedCount": 320,
      "requestedSamplingFps": 30.0,
      "effectiveSamplingFps": 30.0,
      "runningMode": "VIDEO",
      "modelName": "pose_landmarker_full.task",
      "detectedFrameCount": 320
    },
    "nextTimestampCursorMs": 10634.333333333334
  },
  "analysis": {},
  "llmFeedback": {},
  "benchmark": {}
}
```

## 8. skeleton 관련 계약

### 8.1 `GET /jobs/{job_id}/skeleton`

Query params:

| 이름 | 타입 | 기본값 | 제약 |
|---|---|---|---|
| `offset` | integer | `0` | `>= 0` |
| `limit` | integer | `30` | `1 <= limit <= 300` |

응답 타입:

```json
{
  "frames": [
    {
      "frameIndex": 0,
      "timestampMs": 0.0,
      "poseDetected": true,
      "landmarks": [
        {
          "name": "nose",
          "x": 0.355381,
          "y": 0.144323,
          "z": -0.419512,
          "visibility": 0.999905,
          "presence": 0.999856
        }
      ]
    }
  ],
  "videoInfo": {
    "videoSrc": "C:\\path\\to\\video.mp4",
    "displayName": "backSquat.mp4",
    "sourceFps": 30.0,
    "frameCount": 320,
    "width": 1920,
    "height": 1080,
    "backend": "opencv",
    "extractedCount": 320,
    "requestedSamplingFps": 30.0,
    "effectiveSamplingFps": 30.0,
    "runningMode": "VIDEO",
    "modelName": "pose_landmarker_full.task",
    "detectedFrameCount": 320
  },
  "nextTimestampCursorMs": 1001.0,
  "offset": 0,
  "limit": 30,
  "totalFrames": 320
}
```

### 8.2 프론트 권장 사용 방식

옵션 A:

- 완료 직후 `limit=300` 등으로 큰 페이지를 한 번에 가져와 메모리에 적재
- 짧은 영상 데모에는 단순하고 구현이 쉽다

옵션 B:

- 현재 재생 시간 근처만 windowing 방식으로 가져온다
- 긴 영상 대응, 메모리 절감, 실제 서비스용으로 더 적합하다

현재 백엔드 구조를 보면 옵션 B까지 가능하지만, 우선 프론트 개편 1차 목표는 옵션 A가 더 현실적이다.

### 8.3 `GET /jobs/{job_id}/skeleton/download`

전체 skeleton JSON을 attachment로 내려준다.
개발자 도구, JSON download 버튼, 디버그 화면 정도에 적합하다.

일반 사용자 메인 플로우에서는 필요성이 낮다.

## 9. `analysis` 블록 계약

`analysis`는 프론트 대시보드의 핵심 데이터다.

최상위 구성:

- `summary`
- `bodyProfile`
- `groundRef`
- `kpis`
- `timeseries`
- `repSegments`
- `events`
- `issues`
- `visualization`

### 9.1 `summary`

대표 필드:

- `exerciseType`
- `repCount`
- `frameCount`
- `durationMs`
- `sourceFps`
- `sampledFps`
- `detectionRatio`
- `usableFrameCount`
- `bodyweightKg`
- `externalLoadKg`
- `barPlacementMode`
- `barPlacementResolved`
- `totalSystemMassKg`

프론트 활용:

- 상단 KPI 카드
- 세션 메타 정보
- 영상 품질/신뢰도 표시

### 9.2 `kpis`

배열 구조다.
각 항목은 아래 필드를 가진다.

- `key`
- `label`
- `value`
- `unit`
- `description`
- `personalContext`

중요:

- KPI는 고정 object가 아니라 배열이다.
- 즉 프론트는 key 기반 dictionary로 재가공하거나, 정렬 기준을 별도로 가져야 한다.

권장 방식:

```ts
const kpiMap = Object.fromEntries(kpis.map(kpi => [kpi.key, kpi]))
```

### 9.3 `timeseries`

시계열 차트용 데이터다.
현재 스키마는 `extra="allow"`라서, 분석 항목이 추가될 수 있다.

즉 프론트는 다음 전제를 가져야 한다.

- `timestamps_ms`는 기준 축으로 항상 기대
- 나머지 시계열 키는 증가할 수 있음
- 특정 키가 없을 수 있으므로 optional 접근 필요

현재 코드상 대표 키:

- `timestamps_ms`
- `hip_height`
- `bar_x`
- `bar_y`
- `bar_confidence`
- `bar_com_offset`
- `body_com_x`
- `body_com_y`
- `com_x`
- `com_y`
- `cop_ap_normalized`
- `cop_ml_normalized`
- `bar_over_midfoot`

테스트 fixture 기준으로는 아래와 같은 확장 키도 등장한다.

- `trunk_lean_angle`
- `left_knee_angle`
- `right_knee_angle`
- `left_hip_angle`
- `right_hip_angle`
- `hip_height_velocity`
- `load_ratio_knee`

따라서 프론트는 "정해진 몇 개 필드만 하드코딩"보다 아래 2계층 구조가 안전하다.

1. 기본 지원 차트 목록
2. 존재하는 키만 렌더하는 fallback 차트 목록

### 9.4 `repSegments`

반복 동작 구간이다.

대표 필드:

- `repIndex`
- `startMs`
- `endMs`
- `bottomMs`
- `phaseEccentricMs`
- `phaseConcentricMs`
- `depthAngleDeg`

프론트 활용:

- 타임라인 구간 표시
- rep selector
- rep 별 세부 카드

### 9.5 `events`

포즈/동작 이벤트 배열이다.

대표 필드:

- `type`
- `timestampMs`
- `repIndex`
- `metadata`

프론트 활용:

- 타임라인 마커
- 특정 시점 jump
- 디버그 툴팁

### 9.6 `issues`

코칭 경고, 문제 구간, 품질 이슈를 표현한다.

대표 필드:

- `severity`
- `code`
- `message`
- `timestampMs`
- `repIndex`
- `context`

프론트 활용:

- warning list
- rep 별 issue badge
- 영상 scrubber marker

## 10. `llmFeedback` 블록 계약

현재 구조:

- `version`
- `model`
- `overallComment`
- `highlights`
- `corrections`
- `coachCue`

프론트 규칙:

- `overallComment`는 메인 요약 문단
- `highlights`는 잘한 점 목록
- `corrections`는 교정 포인트 목록
- `coachCue`는 짧은 1줄 cue

주의:

- LLM이 꺼져 있어도 응답 블록은 존재할 수 있다.
- 즉 null 여부보다 문자열 비어 있음 여부를 기준으로 렌더 fallback을 설계해야 한다.

권장 fallback:

- `overallComment`가 비어 있으면 "LLM feedback unavailable" 계열 안내 문구 노출
- 대신 `analysis.issues`와 `analysis.kpis`는 계속 렌더

## 11. benchmark 블록 계약

일반 사용자 화면에는 필수가 아니지만, 프론트 개편 시 개발자 패널이나 실험 화면에는 유용하다.

최상위 구조:

- `run`
- `timingSummary`
- `qualitySummary`
- `comparisonTags`
- `llmPromptDiagnostics`
- `llmCallResult`
- `storage`

실제 활용 가치가 큰 필드:

- `run.requestedDelegate`
- `run.actualDelegate`
- `run.delegateFallbackApplied`
- `timingSummary.totalElapsedMs`
- `qualitySummary.poseDetectedRatio`
- `qualitySummary.avgVisibility`

중요한 현재 동작:

- `delegate=GPU`를 요청해도 실제 실행은 CPU fallback이 발생할 수 있다.
- 이 정보는 benchmark에 기록된다.
- 따라서 프론트가 "GPU로 분석 중" 같은 확정적 문구를 노출하면 안 된다.

## 12. 에러 처리 규약

### 12.1 대표 HTTP 상태

| 상태코드 | 상황 |
|---|---|
| `200` | 정상 |
| `400` | 잘못된 입력값 |
| `404` | job 없음 |
| `409` | 결과가 아직 준비되지 않음 |
| `500` | preview 실패 또는 내부 오류 |

### 12.2 실제 주요 에러 조건

- 지원하지 않는 비디오 확장자
- `samplingFps <= 0`
- `bodyweightKg <= 0`
- `externalLoadKg <= 0`
- `barPlacementMode`가 허용값 아님
- `modelVariant`가 허용값 아님
- `delegate`가 허용값 아님
- `exerciseType != squat`
- 완료 전 `/result`, `/skeleton`, `/benchmark` 접근

### 12.3 프론트 메시지 분리 원칙

사용자 메시지와 개발자 메시지를 분리하는 것이 좋다.

예시:

- 사용자 메시지: "분석 설정을 다시 확인해 주세요."
- 개발자 메시지: 서버 detail 원문 표시

특히 `failed` 상태의 `error.message`는 개발자 친화적이므로, 그대로 최종 사용자 메인 카피로 쓰지 않는 편이 낫다.

## 13. polling 전략

권장 polling 알고리즘:

1. `POST /jobs`
2. `jobId` 저장
3. 1초 간격으로 `GET /jobs/{jobId}`
4. `completed`면 polling 중단
5. `GET /jobs/{jobId}/result`
6. 이어서 `GET /jobs/{jobId}/skeleton?offset=0&limit=300`

권장 세부 정책:

- 기본 interval: `1000ms`
- 최대 대기 시간: UX 기준 2분 또는 별도 설정
- 탭 비활성화 시 interval 증가 고려 가능
- 중복 polling 금지
- 새 업로드 시작 시 이전 polling 즉시 중단

주의:

- `/result`를 먼저 요청하면 skeleton overlay 데이터가 없다.
- 즉 "완료 -> 결과 한 번만 fetch"로 설계하면 현재 `SkeletonViewer` 요구사항을 충족하지 못한다.

## 14. 프론트 구현 권장 분리

### 14.1 API 모듈

권장 함수:

```ts
createJob(form: AnalysisForm, file: File | null): Promise<JobCreateResponse>
getJobStatus(jobId: string): Promise<JobStatusResponse>
getJobResult(jobId: string): Promise<MotionAnalysisSummary>
getSkeletonPage(jobId: string, offset?: number, limit?: number): Promise<SkeletonPageResponse>
getBenchmark(jobId: string): Promise<BenchmarkSummary>
previewAnalysis(form: AnalysisForm, file: File | null): Promise<MotionAnalysisSummary>
```

원칙:

- API 모듈은 store를 직접 수정하지 않는다.
- 네트워크 호출과 응답 parsing만 담당한다.

### 14.2 store / orchestration 모듈

권장 책임:

- 상태 전이
- polling lifecycle
- 요청 취소
- 결과 병합
- 화면용 selector 제공

### 14.3 컴포넌트 계층

권장 책임:

- `VideoUpload`: 파일 선택만
- `FpsSelector`: samplingFps 선택만
- `CoreDemoSection`: submit 진입
- `SkeletonViewer`: skeleton page 데이터 렌더
- `AnalysisDashboard`: `analysis`, `llmFeedback`, `benchmark` 렌더

## 15. 현재 프론트 개편 시 바로 반영해야 할 사항

### 15.1 필드명 정리

프론트 폼 필드명은 서버 규약과 완전히 맞춰야 한다.

권장 전송 키:

- `video`
- `samplingFps`
- `exerciseType`
- `bodyweightKg`
- `externalLoadKg`
- `barPlacementMode`
- `modelVariant`
- `delegate`

`fps`는 보내지 않는 편이 낫다.

### 15.2 결과 데이터 분리 저장

프론트 store는 아래처럼 나누는 것이 좋다.

- `jobMeta`: `jobId`, `status`, `progress`, `error`
- `summaryResult`: `/result` 응답
- `skeletonFrames`: `/skeleton` 응답의 `frames`
- `benchmarkDetails`: 선택적 추가 응답

### 15.3 화면 로딩 분리

완료 후 한 번에 전부 붙이지 말고 아래처럼 나누는 것이 UX상 낫다.

1. `completed` 직후 summary 먼저 로드
2. 곧바로 skeleton page 로드
3. benchmark는 필요 화면에서 lazy load

이렇게 하면 대시보드 텍스트/KPI는 먼저 뜨고, skeleton overlay는 뒤이어 붙일 수 있다.

## 16. 현재 백엔드 제약 및 프론트 영향

### 16.1 운동 종류

- 현재 `squat`만 지원
- 프론트에서 다른 종목 선택 UI를 열면 실제 서버 실패로 이어진다

### 16.2 skeleton 전체 응답 미포함

- `/result`만으로는 skeleton viewer 구현 불가
- `/skeleton` 별도 호출이 필수

### 16.3 비디오 경로

- `videoInfo.videoSrc`는 로컬 파일 시스템 경로다
- 브라우저가 이 경로를 직접 재생할 수 있다고 가정하면 안 된다
- 프론트는 업로드한 `File` 객체의 local object URL을 계속 보관해서 viewer에 써야 한다

즉 `SkeletonViewer`의 video source는 서버 응답이 아니라 프론트가 가지고 있던 원본 `File`에서 만들어야 한다.

### 16.4 LLM 가용성

- API 키가 없으면 LLM 출력이 비어 있거나 fallback 결과가 나올 수 있다
- 프론트는 LLM 블록을 필수 데이터로 가정하면 안 된다

### 16.5 대용량 영상

- skeleton은 frame 단위 배열이라 payload가 커질 수 있다
- 긴 영상에서 한 번에 전체 로드 전략은 곧 병목이 될 수 있다
- 1차 구현은 큰 페이지 1회 fetch로 가더라도, 이후 windowed fetch 전환을 고려해야 한다

## 17. 권장 구현 순서

1. 프론트 `api/analysisClient` 작성
2. `multipart/form-data` 업로드 구현
3. job polling store 액션 구현
4. `/result` 응답 store 반영
5. `/skeleton` 첫 페이지 로드 및 `SkeletonViewer` 연결
6. `analysis.kpis`, `analysis.issues`, `llmFeedback` 대시보드 연결
7. benchmark 개발자 패널 연결
8. preview endpoint는 dev-only 도구로 별도 분리

## 18. 프론트용 최종 결론

프론트는 아래 전제로 재설계하면 된다.

- 메인 플로우는 `POST /jobs` 기반 비동기 구조다.
- polling 대상은 `GET /jobs/{jobId}`다.
- 완료 후 최소 2번 fetch 해야 한다.
  - `GET /jobs/{jobId}/result`
  - `GET /jobs/{jobId}/skeleton`
- `analysis`는 대시보드 데이터다.
- `llmFeedback`는 보조 설명 블록이다.
- `benchmark`는 개발자/실험용 부가 데이터다.
- 실제 비디오 playback source는 서버 경로가 아니라 프론트가 가진 원본 `File`이어야 한다.
- 현재 운동 종목은 `squat`만 열어야 한다.

이 문서를 기준으로 `racl-labs-frontend-forked`에서는 최소한 아래 세 모듈을 새로 잡으면 된다.

- `api/`
- `store/analysis`
- `features/analysis-session` 또는 동등한 orchestration 레이어
