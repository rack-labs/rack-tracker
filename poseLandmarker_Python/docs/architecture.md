# Motion Analysis Backend Architecture

## 1. 목적

이 문서는 `poseLandmarker_Python`을 단순 MediaPipe 실험 폴더가 아니라, `uv` 기반 FastAPI 백엔드 프로젝트로 정리하기 위한 아키텍처 기준 문서다.

참고한 스타일은 아래 예제다.

- `C:\Users\neighbor\Documents\Code\Github\FastAPI\uv-based-fastapi\example`

위 예제에서 가져올 핵심은 다음 네 가지다.

1. `uv`를 기준으로 Python 실행 환경을 고정한다.
2. `main.py`를 서버 실행 진입점으로 둔다.
3. `app.py`에서 FastAPI 앱과 라우터를 조립한다.
4. 기능별 폴더를 나눠서 API, 설정, 서비스 코드를 분리한다.

우리 프로젝트는 예제보다 범위가 더 크다.

- 예제: FastAPI 입문, 라우터 분리, MySQL 실습
- 현재 프로젝트: 비디오 업로드, 포즈 추론, 운동역학 분석, LLM 피드백

즉, 예제의 "실행 구조"는 그대로 참고하고, 도메인 로직만 우리 목적에 맞게 확장한다.

## 2. 프로젝트 목표

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

## 3. 범위

### 포함

- 로컬 Python 서버 구현
- `uv` 기반 의존성 관리
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

## 4. `uv` 기반 프로젝트 구조

참고 예제의 `uv-based-fastapi/example`처럼, 이 프로젝트도 "한 폴더 안에서 `uv sync` 후 `uv run main.py`"가 되는 구조를 목표로 한다.

권장 구조는 아래와 같다.

```text
poseLandmarker_Python/
├─ pyproject.toml
├─ uv.lock
├─ README.md
├─ main.py
├─ app.py
├─ config/
│  └─ config.py
├─ controller/
│  ├─ jobs.py
│  ├─ health.py
│  └─ results.py
├─ schema/
│  ├─ job.py
│  └─ result.py
├─ service/
│  ├─ job_manager.py
│  ├─ video_reader.py
│  ├─ pose_inference.py
│  ├─ skeleton_mapper.py
│  ├─ analysis_pipeline.py
│  └─ llm_feedback.py
├─ adapter/
│  ├─ opencv_adapter.py
│  └─ mediapipe_adapter.py
├─ docs/
│  └─ architecture.md
└─ tmp/
```

핵심 역할은 아래처럼 본다.

- `main.py`
  서버 실행 진입점
- `app.py`
  FastAPI 앱 생성과 라우터 등록
- `config/config.py`
  포트, 임시 디렉터리, 모델 경로, 외부 참조 경로 같은 설정
- `controller/`
  HTTP 엔드포인트
- `schema/`
  요청과 응답 모델
- `service/`
  실제 비즈니스 로직
- `adapter/`
  OpenCV와 MediaPipe 같은 외부 라이브러리 결합부

참고 예제의 `controller`, `config`, `model` 분리 원칙은 그대로 유지하되, 현재 프로젝트에서는 DB 대신 비디오 처리와 추론 파이프라인이 핵심이므로 `service`와 `adapter` 비중이 더 커진다.

## 5. 실행 방식

FastAPI 예제의 흐름을 그대로 따라간다.

1. 프로젝트 루트에 `pyproject.toml`을 둔다.
2. `uv sync`로 의존성을 맞춘다.
3. `uv run main.py`로 서버를 실행한다.
4. `main.py`는 `uvicorn.run(app="app:app", ...)` 형태로 `app.py`의 `app` 객체를 로딩한다.
5. `app.py`는 각 라우터를 등록한다.

예상 실행 흐름:

```text
uv run main.py
-> main.py
-> uvicorn.run("app:app")
-> app.py
-> controller/jobs.py 등 라우터 등록
-> service 계층 호출
```

초기 실행 명령은 아래 기준으로 문서화한다.

```bash
cd poseLandmarker_Python
uv sync
uv run main.py
```

개발 중 브라우저 확인 주소:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

포트는 `config/config.py`에서 관리한다.

## 6. 초기 의존성 기준

참고 예제의 `pyproject.toml`처럼 의존성을 `uv`에서 관리한다.

초기 후보는 아래와 같다.

- `fastapi`
- `uvicorn`
- `python-multipart`
- `opencv-python`
- `mediapipe`
- `pydantic`
- `numpy`
- LLM 연동용 SDK 또는 HTTP 클라이언트

원칙은 아래와 같다.

- 실행과 직접 관련된 패키지는 `pyproject.toml`에 명시한다.
- 버전 잠금은 `uv.lock`으로 관리한다.
- 로컬 개발 재현성은 `uv sync` 한 번으로 맞춘다.

## 7. 읽는 순서

FastAPI 예제처럼 이 프로젝트도 처음 보는 사람이 아래 순서로 읽을 수 있어야 한다.

1. `main.py`
   서버를 어떻게 켜는지 확인
2. `app.py`
   라우터가 어디서 연결되는지 확인
3. `controller/jobs.py`
   업로드와 상태 조회 API 확인
4. `service/job_manager.py`
   job 상태가 어떻게 관리되는지 확인
5. `service/video_reader.py`
   비디오 프레임 추출 확인
6. `service/pose_inference.py`
   MediaPipe 추론 흐름 확인
7. `service/analysis_pipeline.py`
   분석 로직 확인
8. `service/llm_feedback.py`
   LLM 피드백 생성 확인
9. `/docs`
   API를 브라우저에서 확인

즉, "서버 실행 -> 라우터 -> 서비스 -> 외부 라이브러리 결합부" 순서로 읽게 만드는 것이 목표다.

## 8. 핵심 결정

### 8.1 처리 위치

- 브라우저: 업로드, 상태 표시, 오버레이 재생, 대시보드 렌더링, 시각화, 다운로드
- Python 서버: 비디오 처리, 포즈 추론, 운동역학 분석, 지표 계산, LLM 피드백 생성, 결과 조립

### 8.2 처리 방식

단일 요청-응답이 아니라 job 기반 비동기 처리로 간다.

이유는 다음과 같다.

- 영상 길이에 따라 추출 시간이 길어질 수 있다.
- 분석 파이프라인과 LLM 피드백 생성까지 포함하면 처리 시간이 더 길어진다.
- 프런트에서 진행률을 보여줘야 한다.
- 추출 단계와 분석 단계를 분리해 상태를 보여주는 것이 디버깅에 유리하다.

### 8.3 결과 기준

백엔드의 최종 결과는 단순 스켈레톤 JSON이 아니라 아래 세 층을 모두 포함한 분석 결과다.

- 원본 스켈레톤 런타임 데이터
- 운동역학 핵심 지표와 시계열 분석 데이터
- LLM 피드백

### 8.4 응답 구성 원칙

프런트가 다음 세 가지 UI를 모두 구성할 수 있어야 한다.

- 비디오 오버레이
- 대시보드 KPI 카드
- 차트 및 시각화

따라서 API 결과는 다음 세 블록을 포함해야 한다.

- `skeleton`
- `analysis`
- `llmFeedback`

### 8.5 외부 참조 저장소 정책

- OpenCV는 이 저장소 내부의 Git submodule로 유지한다.
- MediaPipe는 Windows 경로 길이 제한 때문에 이 저장소 내부 submodule로 두지 않는다.
- MediaPipe는 짧은 외부 로컬 경로에 별도 클론한 저장소를 참조한다.
- 현재 기준 MediaPipe 로컬 참조 경로는 `C:\src\mediapipe-forked`다.
- 문서와 구현 참조는 이 외부 경로를 기준으로 유지한다.

## 9. 백엔드 계층 구조

참고 예제의 `app.py -> controller -> model/config` 구조를 현재 프로젝트에 맞춰 확장하면 아래 6개 레이어가 된다.

### 9.1 Entry Layer

파일:

- `main.py`

책임:

- `uv run main.py`의 시작점
- `uvicorn.run(...)` 호출
- 개발 모드용 host, port, reload 설정

예상 형태:

```python
import uvicorn
from config import config

def main():
    uvicorn.run(
        app="app:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
    )

if __name__ == "__main__":
    main()
```

### 9.2 App Layer

파일:

- `app.py`

책임:

- `FastAPI()` 앱 생성
- 라우터 등록
- 루트 health endpoint 제공

예상 형태:

```python
from fastapi import FastAPI
from controller import health, jobs, results

app = FastAPI()

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(results.router)
```

### 9.3 API Layer

파일:

- `controller/jobs.py`
- `controller/results.py`
- `controller/health.py`

책임:

- 파일 업로드 받기
- job 생성
- 상태 조회 응답
- 결과 조회 응답

예상 엔드포인트:

- `GET /`
- `POST /jobs`
- `GET /jobs/{jobId}`
- `GET /jobs/{jobId}/result`

### 9.4 Service Layer

파일:

- `service/job_manager.py`
- `service/video_reader.py`
- `service/pose_inference.py`
- `service/skeleton_mapper.py`
- `service/analysis_pipeline.py`
- `service/llm_feedback.py`

책임:

- HTTP와 무관한 도메인 로직 수행
- 단계별 파이프라인 조립
- 에러와 진행률 상태 관리

### 9.5 Adapter Layer

파일:

- `adapter/opencv_adapter.py`
- `adapter/mediapipe_adapter.py`

책임:

- 외부 라이브러리 API 차이를 내부 인터페이스로 감춤
- OpenCV 프레임 읽기와 MediaPipe 입력 변환을 분리

### 9.6 Schema Layer

파일:

- `schema/job.py`
- `schema/result.py`

책임:

- 요청 검증
- 응답 직렬화
- 프런트와의 계약 고정

## 10. 전체 흐름

현재 백엔드와 프런트엔드가 완전히 연결되기 전까지는, 업로드 파일을 실제 처리하는 대신 `src/video/backSquat.mp4`를 목업 입력 소스로 사용한다.

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

## 11. 세부 서비스 설계

### 11.1 Job 관리 레이어

책임:

- job 상태 저장
- 단계별 진행률 저장
- 에러 저장
- 중간 결과와 최종 결과 메모리 보관
- 임시 파일 정리

초기 구현은 인메모리 딕셔너리로 충분하다.

FastAPI 예제의 DB 접근 코드처럼 별도 파일로 분리하되, 현재는 영속 저장소 대신 메모리 저장을 사용한다.

### 11.2 비디오 처리 레이어

책임:

- OpenCV로 비디오 열기
- FPS 기준 프레임 샘플링
- 프레임 인덱스와 timestamp 계산

초기 구현은 OpenCV만 사용한다.

구현 참조:

- OpenCV 공개 API 선언: `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\third_party\opencv\opencv-forked\modules\videoio\include\opencv2\videoio.hpp`
- 프레임 단위 위치 제어 상수: `CAP_PROP_POS_FRAMES`
- OpenCV `VideoCapture` 구현 진입점: `C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\third_party\opencv\opencv-forked\modules\videoio\src\cap.cpp`

설계 포인트:

- 브라우저 내부 seek 기반 추출을 유지하지 않고, 서버에서 OpenCV로 프레임을 직접 읽는다.
- 목표 FPS가 원본 FPS보다 낮으면 모든 프레임을 저장하지 말고 서버에서 샘플링한다.
- timestamp는 원본 FPS와 샘플링 규칙을 함께 기록해 재현 가능하게 만든다.

### 11.3 포즈 추론 레이어

책임:

- MediaPipe Pose Landmarker 초기화
- 각 프레임에 대해 추론 실행
- landmark 배열을 런타임 스키마에 맞게 변환

구현 참조:

- Python 태스크 래퍼: `C:\src\mediapipe-forked\mediapipe\tasks\python\vision\pose_landmarker.py`
- C++ 태스크 구현: `C:\src\mediapipe-forked\mediapipe\tasks\cc\vision\pose_landmarker\pose_landmarker.cc`
- 내부 그래프 정의: `C:\src\mediapipe-forked\mediapipe\tasks\cc\vision\pose_landmarker\pose_landmarker_graph.cc`

설계 포인트:

- 서버는 비디오 입력에 맞는 `detect_for_video()` timestamp 규약을 유지한다.
- 추론 입력은 OpenCV 프레임을 MediaPipe가 요구하는 이미지 타입으로 변환하는 어댑터 레이어를 둔다.
- MediaPipe 결과 객체를 바로 프런트 포맷으로 노출하지 말고, 프로젝트 런타임 스키마로 한 번 정규화한다.

### 11.4 운동역학 분석 레이어

책임:

- 스켈레톤 JSON을 입력으로 받기
- 관절 각도, 바 경로, 대칭성, 속도, 타이밍 등 핵심 지표 계산
- rep 또는 phase 단위 구간 분할
- 시계열 기반 분석 결과 생성
- 대시보드와 차트용 데이터 구조 조립

이 레이어는 LLM 없이도 독립적으로 동작해야 한다.

### 11.5 LLM 피드백 레이어

책임:

- 운동역학 분석 결과를 입력으로 받기
- 핵심 문제 요약 생성
- 자세 개선 포인트 생성
- 프런트에 바로 노출 가능한 피드백 문장 생성

LLM은 원본 프레임 전체를 직접 해석하는 것이 아니라, 분석 레이어가 정제한 구조화 데이터를 입력으로 받는다.

## 12. Job 상태 모델

job 상태는 아래 단계로 관리한다.

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

## 13. API 계약

### 13.1 `POST /jobs`

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

### 13.2 `GET /jobs/{jobId}`

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

### 13.3 `GET /jobs/{jobId}/result`

설명:

- 완료된 job의 최종 분석 결과 조회

성공 조건:

- `status == completed` 인 경우에만 200 반환

응답은 아래 세 블록을 포함한다.

- `skeleton`
- `analysis`
- `llmFeedback`

## 14. 데이터 계약

### 14.1 `skeleton`

오버레이 렌더링용 데이터다.

포함 필드:

- `frames`
- `videoInfo`
- `nextTimestampCursorMs`

### 14.2 `analysis`

대시보드와 차트용 데이터다.

포함 필드:

- `summary`
- `kpis`
- `timeseries`
- `events`
- `repSegments`
- `issues`

### 14.3 `llmFeedback`

사용자 친화적 텍스트 피드백이다.

포함 필드:

- `version`
- `model`
- `overallComment`
- `highlights`
- `corrections`
- `coachCue`

LLM 응답은 원본 사실을 새로 만들어내는 것이 아니라 `analysis`에 근거한 설명이어야 한다.

## 15. 구현 원칙

### 15.1 FastAPI 예제에서 그대로 가져올 원칙

- 실행 진입점은 `main.py` 하나로 고정한다.
- 앱 조립은 `app.py`에서만 한다.
- 엔드포인트는 `controller`로 분리한다.
- 설정은 `config`로 분리한다.
- 로컬 개발자는 `uv sync`, `uv run main.py`, `/docs` 이 세 가지만 먼저 기억하면 된다.

### 15.2 현재 프로젝트에서 추가로 필요한 원칙

- 무거운 로직은 controller에서 처리하지 않고 service로 넘긴다.
- 외부 라이브러리 결합부는 adapter로 감싼다.
- 결과 포맷은 schema로 고정한다.
- 정량 분석은 LLM 이전에 끝낸다.
- 같은 입력에 대한 `analysis` 결과는 deterministic 해야 한다.

## 16. 구현 순서

1. `poseLandmarker_Python`를 `uv` 프로젝트로 초기화한다.
2. `pyproject.toml`, `main.py`, `app.py`, `config/config.py`를 만든다.
3. `POST /jobs`, `GET /jobs/{jobId}`, `GET /jobs/{jobId}/result`를 구현한다.
4. 인메모리 job manager를 만든다.
5. OpenCV 프레임 추출을 붙인다.
6. MediaPipe Pose Landmarker를 붙인다.
7. 스켈레톤 런타임 포맷 변환기를 구현한다.
8. 운동역학 분석 파이프라인 골격을 구현한다.
9. LLM 입력과 응답 스키마를 정의한다.
10. 프런트 polling 및 결과 소비 구조를 연결한다.

## 17. 완료 기준

아래 조건을 만족하면 1차 목표를 달성한 것으로 본다.

- `poseLandmarker_Python` 폴더에서 `uv sync`가 된다.
- `uv run main.py`로 FastAPI 서버가 뜬다.
- `/docs`에서 API 확인이 된다.
- 웹에서 로컬 비디오 업로드가 가능하다.
- job 상태가 polling으로 보인다.
- 완료 시 오버레이가 정상 작동한다.
- 대시보드 KPI가 표시된다.
- 시계열 차트가 렌더링된다.
- 분석 이슈가 표시된다.
- LLM 피드백이 함께 표시된다.
- 브라우저 내부 seek 기반 추출 로직이 제거된다.
