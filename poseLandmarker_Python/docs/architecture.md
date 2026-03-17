# Motion Analysis Backend Architecture

## 1. 목적

이 프로젝트는 웹에서 업로드한 운동 영상을 로컬 Python 서버로 보내고, 서버에서 다음 파이프라인을 수행하는 것을 목표로 한다.

1. 비디오에서 프레임별 스켈레톤 데이터를 추출한다.
2. 추출된 스켈레톤 JSON을 기반으로 운동역학 분석 파이프라인을 수행한다.
3. 핵심 지표를 계산한다.
4. 계산된 지표와 시계열 데이터를 바탕으로 LLM 피드백을 생성한다.
5. 프런트엔드는 이 결과를 사용해 대시보드와 시각화를 렌더링한다.

즉, 스켈레톤 추출은 최종 목적이 아니라 분석 파이프라인의 입력 단계다.

기준이 되는 MVP 프런트 코드는 다음 경로를 참고한다.

- `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\MVP.v1\video-pose-mvp\src`
- `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\MVP.v1\video-pose-mvp\index.html`

## 2. 범위

### 포함

- 로컬 Python 서버 구현
- 비디오 업로드
- 비동기 job 생성 및 상태 조회
- OpenCV 기반 프레임 추출
- MediaPipe Pose Landmarker 추론
- 스켈레톤 런타임 포맷 생성
- 운동역학 분석 파이프라인
- 핵심 지표 계산
- LLM 피드백 생성
- 프런트엔드에서 polling 후 분석 결과 반영
- 프런트 대시보드와 시각화가 소비할 응답 포맷 정의

### 제외

- 배포용 서버 설계
- 인증, 사용자 계정, 멀티유저 처리
- DB 저장
- 영구 파일 저장
- 운영 환경 스케일링
- 실시간 스트리밍 처리

이 문서는 검증 목적 프로젝트를 전제로 하며, Python 서비스는 로컬 서버에서만 실행한다.

## 3. 핵심 결정

### 3.1 처리 위치

- 브라우저: 업로드, 상태 표시, 오버레이 재생, 대시보드 렌더링, 시각화, 다운로드
- Python 서버: 비디오 처리, 포즈 추론, 운동역학 분석, 지표 계산, LLM 피드백 생성, 결과 조립

### 3.2 처리 방식

단일 요청-응답이 아니라 job 기반 비동기 처리로 간다.

이유는 다음과 같다.

- 영상 길이에 따라 추출 시간이 길어질 수 있다.
- 분석 파이프라인과 LLM 피드백 생성까지 포함하면 처리 시간이 더 길어진다.
- 프런트에서 진행률을 보여줘야 한다.
- 추출 단계와 분석 단계를 분리해 상태를 보여주는 것이 디버깅에 유리하다.

### 3.3 결과 기준

백엔드의 최종 결과는 단순 스켈레톤 JSON이 아니라 아래 세 층을 모두 포함한 분석 결과다.

- 원본 스켈레톤 런타임 데이터
- 운동역학 핵심 지표와 시계열 분석 데이터
- LLM 피드백

### 3.4 응답 구성 원칙

프런트가 다음 세 가지 UI를 모두 구성할 수 있어야 한다.

- 비디오 오버레이
- 대시보드 KPI 카드
- 차트 및 시각화

따라서 API 결과는 다음 세 블록을 포함해야 한다.

- `skeleton`
- `analysis`
- `llmFeedback`

### 3.5 외부 참조 저장소 정책

- OpenCV는 이 저장소 내부의 Git submodule로 유지한다.
- MediaPipe는 Windows 경로 길이 제한 때문에 이 저장소 내부 submodule로 두지 않는다.
- MediaPipe는 짧은 외부 로컬 경로에 별도 클론한 저장소를 참조한다.
- 현재 기준 MediaPipe 로컬 참조 경로는 `C:\src\mediapipe-forked`다.
- 문서와 구현 참조는 이 외부 경로를 기준으로 유지한다.

## 4. 전체 흐름

1. 사용자가 웹에서 비디오 파일과 FPS를 선택한다.
2. 프런트가 `POST /jobs`로 파일과 옵션을 업로드한다.
3. 서버는 job을 생성하고 즉시 `jobId`를 반환한다.
4. 프런트는 `GET /jobs/{jobId}`를 polling 하며 상태와 진행률을 표시한다.
5. 서버는 백그라운드에서 비디오를 디코딩하고 프레임별로 포즈를 추출한다.
6. 서버는 추출된 스켈레톤 데이터를 운동역학 분석 파이프라인에 전달한다.
7. 서버는 분석 결과에서 핵심 지표와 시계열 데이터를 계산한다.
8. 서버는 계산된 지표와 분석 결과를 바탕으로 LLM 피드백을 생성한다.
9. 모든 단계가 완료되면 job 상태를 `completed`로 바꾼다.
10. 프런트는 `GET /jobs/{jobId}/result`를 호출한다.
11. 프런트는 `skeleton` 데이터를 오버레이에 쓰고, `analysis`와 `llmFeedback`을 대시보드와 시각화에 사용한다.

## 5. 백엔드 구성

최소 구성은 다음 6개 레이어로 나눈다.

### 5.1 API 레이어

책임:

- 파일 업로드 받기
- job 생성
- 상태 조회 응답
- 결과 조회 응답

예상 엔드포인트:

- `POST /jobs`
- `GET /jobs/{jobId}`
- `GET /jobs/{jobId}/result`

### 5.2 Job 관리 레이어

책임:

- job 상태 저장
- 단계별 진행률 저장
- 에러 저장
- 중간 결과와 최종 결과 메모리 보관
- 임시 파일 정리

초기 구현은 인메모리 딕셔너리로 충분하다.

### 5.3 비디오 처리 레이어

책임:

- OpenCV로 비디오 열기
- FPS 기준 프레임 샘플링
- 프레임 인덱스와 timestamp 계산

초기 구현은 OpenCV만 사용한다.

추후 최적화가 필요하면 디코딩만 ffmpeg로 교체할 수 있지만, 현재 범위에는 포함하지 않는다.

구현 참조:

- OpenCV 공개 API 선언: `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\third_party\opencv\opencv-forked\modules\videoio\include\opencv2\videoio.hpp`
- 프레임 단위 위치 제어 상수: `CAP_PROP_POS_FRAMES`
- OpenCV `VideoCapture` 구현 진입점: `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\third_party\opencv\opencv-forked\modules\videoio\src\cap.cpp`
- 실제 읽기 흐름은 `VideoCapture::read()`가 `grab()`와 `retrieve()`를 묶는 구조다.
- 따라서 우리 Python 백엔드의 프레임 추출 레이어도 "영상 열기 -> 필요 시 seek 또는 샘플링 -> 프레임 읽기 -> timestamp 계산" 순서로 맞추는 것이 자연스럽다.

현재 프로젝트에서 참고해야 할 설계 포인트:

- 브라우저 내부 seek 기반 추출을 유지하지 않고, 서버에서 OpenCV로 프레임을 직접 읽는다.
- 목표 FPS가 원본 FPS보다 낮으면 모든 프레임을 저장하지 말고 서버에서 샘플링한다.
- timestamp는 프레임 카운터만 믿지 말고 원본 FPS와 샘플링 규칙을 함께 기록해 재현 가능하게 만든다.

### 5.4 포즈 추론 레이어

책임:

- MediaPipe Pose Landmarker 초기화
- 각 프레임에 대해 추론 실행
- landmark 배열을 런타임 스키마에 맞게 변환

구현 참조:

- Python 태스크 래퍼: `C:\src\mediapipe-forked\mediapipe\tasks\python\vision\pose_landmarker.py`
- `PoseLandmarker` 클래스 정의가 이 파일에 있고, `create_from_options()`로 태스크를 만들고 `detect_for_video()`로 비디오 모드 추론을 수행한다.
- Python 래퍼는 내부적으로 `MpPoseLandmarkerDetectForVideo` 네이티브 엔트리포인트를 호출하고 결과를 `PoseLandmarkerResult`로 변환한다.
- C++ 태스크 구현: `C:\src\mediapipe-forked\mediapipe\tasks\cc\vision\pose_landmarker\pose_landmarker.cc`
- 내부 그래프 정의: `C:\src\mediapipe-forked\mediapipe\tasks\cc\vision\pose_landmarker\pose_landmarker_graph.cc`
- MediaPipe 내부적으로는 `PoseLandmarkerGraph`를 구성해 detector와 landmark tracking 파이프라인을 실행한다.

현재 프로젝트에서 참고해야 할 설계 포인트:

- 서버는 프레임마다 `detect()`를 새로 호출하는 방식보다, 비디오 입력이면 `detect_for_video()` 모드에 맞는 timestamp 규약을 유지하는 편이 맞다.
- 추론 입력은 OpenCV `Mat`을 그대로 쓰지 않고 MediaPipe가 요구하는 이미지 타입으로 변환하는 어댑터 레이어가 필요하다.
- 결과 저장 시 normalized landmark와 world landmark 중 어떤 것을 분석 파이프라인 표준 입력으로 쓸지 초기에 고정해야 한다.
- MediaPipe 결과 객체를 바로 프런트 포맷으로 누출하지 말고, 프로젝트 런타임 스키마로 한 번 정규화한다.

### 5.5 운동역학 분석 레이어

책임:

- 스켈레톤 JSON을 입력으로 받기
- 관절 각도, 바 경로, 대칭성, 속도, 타이밍 등 핵심 지표 계산
- rep 또는 phase 단위 구간 분할
- 시계열 기반 분석 결과 생성
- 대시보드와 차트용 데이터 구조 조립

이 레이어는 LLM 없이도 독립적으로 동작해야 한다.

즉, 분석 지표는 규칙 기반 또는 수치 계산 기반으로 먼저 산출되어야 한다.

### 5.6 LLM 피드백 레이어

책임:

- 운동역학 분석 결과를 입력으로 받기
- 핵심 문제 요약 생성
- 자세 개선 포인트 생성
- 프런트에 바로 노출 가능한 피드백 문장 생성

LLM은 원본 프레임 전체를 직접 해석하는 것이 아니라, 분석 레이어가 정제한 구조화 데이터를 입력으로 받는다.

## 6. Job 상태 모델

job 상태는 아래 다섯 단계로 관리한다.

- `queued`
- `extracting`
- `analyzing`
- `generating_feedback`
- `completed`
- `failed`

상태 전이:

- `queued -> extracting -> analyzing -> generating_feedback -> completed`
- 어느 단계에서든 오류 발생 시 `failed`

취소 기능은 현재 범위에서 제외한다.

## 7. API 계약

### 7.1 `POST /jobs`

설명:

- 비디오 파일 업로드와 전체 분석 job 생성

요청 형식:

- `multipart/form-data`
- 필드:
  - `video`: 업로드 파일
  - `fps`: 목표 FPS
  - `exerciseType`: 운동 종류 식별자, 예: `squat`

응답 예시:

```json
{
  "jobId": "job_0001",
  "status": "queued"
}
```

검증 규칙:

- `video` 누락 시 400
- `fps`가 숫자가 아니거나 0 이하이면 400
- `exerciseType`이 없으면 기본 운동 분류 또는 단일 운동 전제 정책 적용

### 7.2 `GET /jobs/{jobId}`

설명:

- job 현재 상태와 진행률 조회

응답 예시:

```json
{
  "jobId": "job_0001",
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

실패 시 예시:

```json
{
  "jobId": "job_0001",
  "status": "failed",
  "progress": null,
  "error": {
    "code": "POSE_INFERENCE_FAILED",
    "message": "Pose inference failed for the uploaded video."
  }
}
```

### 7.3 `GET /jobs/{jobId}/result`

설명:

- 완료된 job의 최종 분석 결과 조회

성공 조건:

- `status == completed` 인 경우에만 200 반환

응답 형식:

```json
{
  "skeleton": {
    "frames": [
      {
        "frameIndex": 0,
        "time": 0.0,
        "landmarks": [
          {
            "id": 0,
            "jointName": "nose",
            "x": 0.5,
            "y": 0.4,
            "z": -0.1,
            "visibility": 0.98
          }
        ]
      }
    ],
    "videoInfo": {
      "videoSrc": "local-upload.mp4",
      "fps": 30,
      "duration": 12.34,
      "createdAt": "2026-03-18T00:00:00.000Z"
    },
    "nextTimestampCursorMs": 13340
  },
  "analysis": {
    "summary": {
      "exerciseType": "squat",
      "repCount": 5,
      "qualityScore": 78
    },
    "kpis": [
      {
        "key": "max_knee_flexion_deg",
        "label": "Max Knee Flexion",
        "value": 112.4,
        "unit": "deg"
      }
    ],
    "timeseries": [
      {
        "key": "hip_angle_deg",
        "label": "Hip Angle",
        "unit": "deg",
        "points": [
          {
            "time": 0.0,
            "value": 165.0
          }
        ]
      }
    ],
    "events": [
      {
        "key": "bottom_position",
        "label": "Bottom Position",
        "time": 1.42
      }
    ],
    "repSegments": [
      {
        "repIndex": 0,
        "startTime": 0.3,
        "endTime": 2.1
      }
    ],
    "issues": [
      {
        "code": "KNEE_VALGUS",
        "severity": "medium",
        "message": "Knees move inward near the bottom position."
      }
    ]
  },
  "llmFeedback": {
    "version": "v1",
    "model": "local-or-api-model",
    "overallComment": "Depth is sufficient, but knee tracking becomes unstable near the bottom.",
    "highlights": [
      "Hip depth is generally consistent across reps."
    ],
    "corrections": [
      "Keep knees aligned with toes during descent."
    ],
    "coachCue": "Push the knees out and keep the chest stacked over the mid-foot."
  }
}
```

주의:

- `skeleton`은 오버레이용이다.
- `analysis`는 대시보드와 차트용이다.
- `llmFeedback`은 텍스트 피드백 UI용이다.
- 다운로드 포맷이 필요하면 프런트에서 별도로 생성한다.

## 8. 데이터 계약

## 8.1 `skeleton`

기존 프런트 내부 런타임 포맷을 유지한다.

포함 필드:

- `frames`
- `videoInfo`
- `nextTimestampCursorMs`

### 8.2 `analysis.summary`

대시보드 상단 요약 정보다.

예상 필드:

- `exerciseType`
- `repCount`
- `qualityScore`
- `analysisVersion`

### 8.3 `analysis.kpis`

핵심 지표 카드용 데이터다.

각 항목은 아래 필드를 가진다.

- `key`
- `label`
- `value`
- `unit`
- `benchmark` 또는 `referenceRange` 선택적 포함

### 8.4 `analysis.timeseries`

차트 렌더링용 시계열 데이터다.

각 항목은 아래 필드를 가진다.

- `key`
- `label`
- `unit`
- `points`

각 point는 아래 필드를 가진다.

- `time`
- `value`

### 8.5 `analysis.events`

중요 포지션 또는 이벤트 마커용 데이터다.

예:

- 바닥 지점
- 최대 속도 지점
- 락아웃 시점

### 8.6 `analysis.repSegments`

반복 동작 구간 분할 정보다.

프런트는 이 데이터를 기반으로 rep 단위 탐색 UI를 만들 수 있다.

### 8.7 `analysis.issues`

규칙 기반 분석으로 탐지한 문제 목록이다.

각 항목은 아래 필드를 가진다.

- `code`
- `severity`
- `message`
- `timeRange` 또는 `repIndex` 선택적 포함

### 8.8 `llmFeedback`

LLM이 생성한 사용자 친화적 피드백이다.

포함 필드:

- `version`
- `model`
- `overallComment`
- `highlights`
- `corrections`
- `coachCue`

LLM 응답은 원본 사실을 새로 만들어내는 것이 아니라 `analysis`에 근거한 설명이어야 한다.

## 9. 분석 파이프라인 설계 원칙

### 9.1 단계 분리

분석 파이프라인은 아래 순서로 분리한다.

1. 스켈레톤 정규화
2. 파생 특징 계산
3. 운동 구간 분할
4. 핵심 지표 계산
5. 문제 패턴 탐지
6. 대시보드용 구조화
7. LLM 프롬프트 입력 조립
8. LLM 피드백 생성

### 9.2 LLM 의존성 최소화

정량 지표와 문제 탐지는 LLM 이전에 계산 완료되어야 한다.

즉, 아래는 LLM 책임이 아니다.

- 관절각 계산
- rep count 계산
- 이벤트 타이밍 검출
- 품질 점수 계산

LLM 책임은 아래로 제한한다.

- 핵심 지표 요약
- 사용자 친화적 설명
- 교정 큐 생성

### 9.3 재현 가능성

같은 입력 JSON에 대해 분석 결과는 동일해야 한다.

LLM 피드백은 일부 표현 차이가 있을 수 있으나, 근거가 되는 `analysis` 데이터는 deterministic 해야 한다.

## 10. 프런트엔드 소비 기준

프런트는 결과를 세 영역으로 소비한다.

### 10.1 오버레이

- `result.skeleton.frames`
- `result.skeleton.videoInfo`

### 10.2 대시보드 KPI

- `result.analysis.summary`
- `result.analysis.kpis`
- `result.analysis.issues`

### 10.3 시각화

- `result.analysis.timeseries`
- `result.analysis.events`
- `result.analysis.repSegments`

### 10.4 피드백 패널

- `result.llmFeedback.overallComment`
- `result.llmFeedback.highlights`
- `result.llmFeedback.corrections`
- `result.llmFeedback.coachCue`

## 11. 파일 처리 정책

로컬 서버 한정 프로젝트이므로 단순한 정책을 사용한다.

- 업로드 파일은 임시 디렉터리에 저장한다.
- job 완료 또는 실패 후 임시 파일을 삭제한다.
- 프레임 이미지는 디스크에 저장하지 않는다.
- 스켈레톤 JSON과 분석 결과는 메모리에서 조립한다.

대용량 파일 대응은 현재 범위 밖이지만, 최소한 업로드 크기 제한은 둔다.

## 12. 에러 처리 원칙

백엔드는 내부 예외를 그대로 노출하지 않고, 프런트가 표시 가능한 코드와 메시지로 변환한다.

최소 에러 코드 예시:

- `INVALID_REQUEST`
- `UNSUPPORTED_VIDEO`
- `VIDEO_DECODE_FAILED`
- `POSE_INFERENCE_FAILED`
- `ANALYSIS_FAILED`
- `LLM_FEEDBACK_FAILED`
- `JOB_NOT_FOUND`
- `JOB_NOT_COMPLETED`

LLM 피드백 단계가 실패했을 때의 정책은 둘 중 하나로 고정해야 한다.

- 엄격 모드: LLM 실패 시 job 전체를 `failed`
- 완화 모드: `analysis`만 반환하고 `llmFeedback`은 빈 값으로 반환

현재 검증 목적 단계에서는 완화 모드가 더 실용적이다.

## 13. 구현 순서

1. Python 로컬 서버 뼈대 생성
2. `POST /jobs`, `GET /jobs/{jobId}`, `GET /jobs/{jobId}/result` 구현
3. OpenCV 프레임 추출 구현
4. MediaPipe Pose Landmarker 연결
5. 스켈레톤 런타임 포맷 변환기 구현
6. 운동역학 분석 파이프라인 골격 구현
7. KPI, 시계열, 이벤트, 이슈 구조 정의
8. LLM 입력 프롬프트와 응답 스키마 정의
9. 프런트 polling 및 결과 소비 구조 연결
10. 오버레이, 대시보드, 시각화, 피드백 UI 회귀 확인

## 14. 완료 기준

아래 조건을 만족하면 1차 목표를 달성한 것으로 본다.

- 웹에서 로컬 비디오 업로드 가능
- job 상태가 polling으로 보임
- 완료 시 오버레이가 정상 작동
- 대시보드 KPI가 표시됨
- 시계열 차트가 렌더링됨
- 분석 이슈가 표시됨
- LLM 피드백이 함께 표시됨
- 브라우저 내부 seek 기반 추출 로직이 제거됨
