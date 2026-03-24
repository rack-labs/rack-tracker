# 데이터분석 파이프라인 작업 가이드

## 1. 문서 목적

이 문서는 `poseLandmarker_Python`에서 포즈 추출 결과 JSON을 받아 의미 있는 분석 결과를 만드는 작업을 팀에 넘기기 위한 안내서다.

이 문서에서 다루는 범위:

- 현재 프로젝트에서 분석 대상 데이터가 어디서 만들어지는지
- 어떤 파일이 입력 포트이고 어떤 파일이 출력 포트인지
- 어떤 디렉토리에 어떤 성격의 코드를 넣어야 하는지
- 분석 파이프라인 작업을 어떤 순서로 나누면 되는지

이 문서에서 다루지 않는 범위:

- 실제 분석 항목 정의
- KPI 상세 공식
- 운동별 판정 기준

그 부분은 다음 작업에서 별도로 정립한다.

## 2. 현재 시스템 한 줄 요약

현재 백엔드 흐름은 아래와 같다.

```text
비디오 입력
  -> 프레임 추출
  -> 포즈 추론
  -> skeleton JSON 생성
  -> analysis 파이프라인 실행
  -> 최종 API 응답 반환
```

분석 담당 팀원이 집중해야 하는 핵심 구간은 아래다.

```text
skeleton JSON
  -> analysis 파이프라인
  -> analysis 결과 JSON
```

즉, 포즈 추론 자체를 수정하는 작업이 아니라 이미 만들어진 `skeleton` 구조를 입력으로 받아 `analysis` 블록을 완성하는 작업으로 이해하면 된다.

## 3. 현재 디렉토리 구조에서 어디를 보면 되는가

분석 작업과 직접 관련 있는 폴더는 아래 정도다.

```text
poseLandmarker_Python/
  app.py
  main.py
  controller/
    jobs.py
    results.py
  schema/
    result.py
    frame.py
    pose.py
  service/
    job_manager.py
    skeleton_mapper.py
    analysis_pipeline.py
    pose_inference.py
    video_reader.py
    benchmarking.py
  docs/
    architecture/
    testing.md
```

역할은 아래처럼 보면 된다.

- `controller/`: API 입구와 출구
- `service/`: 실제 처리 로직
- `schema/`: 주고받는 데이터 형식
- `docs/`: 협업용 설명 문서

분석 담당자가 우선적으로 읽어야 하는 파일은 아래 4개다.

- `service/analysis_pipeline.py`
- `service/skeleton_mapper.py`
- `service/job_manager.py`
- `schema/result.py`

## 4. 모듈 입구와 출구

### 4.1 분석 모듈의 현재 입구

현재 분석 입구는 [`analysis_pipeline.py`](C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/service/analysis_pipeline.py) 의 아래 메서드다.

```python
class AnalysisPipelineService:
    def analyze(self, skeleton: dict, exercise_type: str | None = None) -> dict:
        ...
```

입력:

- `skeleton: dict`
- `exercise_type: str | None`

출력:

- `dict`
- 이 반환값이 최종 결과의 `analysis` 필드에 들어간다.

즉, 분석 작업의 1차 공식 입구는 `AnalysisPipelineService.analyze()`다.

### 4.2 분석 모듈의 현재 호출 위치

분석 파이프라인은 [`job_manager.py`](C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/service/job_manager.py) 에서 호출된다.

흐름은 아래와 같다.

1. 프레임 추출
2. 포즈 추론
3. `skeleton` 생성
4. `analyze(skeleton, exercise_type)` 호출
5. 반환값을 `job.result.analysis`에 저장

즉, `job_manager.py`는 분석 담당자가 계산 로직을 넣는 파일이 아니다.
여기는 분석 파이프라인을 호출하는 오케스트레이션 레이어다.

### 4.3 분석 결과의 최종 출구

최종 결과 출구는 [`results.py`](C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/controller/results.py) 의 아래 API다.

- `GET /jobs/{job_id}/result`

이 응답 구조는 [`result.py`](C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/schema/result.py) 의 `MotionAnalysisResult`를 따른다.

```python
class MotionAnalysisResult(BaseModel):
    skeleton: dict
    analysis: dict
    llmFeedback: dict
    benchmark: dict
```

즉, 프론트엔드나 다른 소비자가 보게 되는 분석 결과 출구는 `MotionAnalysisResult.analysis`다.

## 5. 분석 입력 데이터는 어디서 만들어지는가

분석 입력인 `skeleton`은 [`skeleton_mapper.py`](C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/service/skeleton_mapper.py) 에서 만들어진다.

현재 구조는 크게 아래 3개 블록이다.

- `frames`
- `videoInfo`
- `nextTimestampCursorMs`

예시 형태:

```json
{
  "frames": [
    {
      "frameIndex": 0,
      "timestampMs": 0,
      "poseDetected": true,
      "landmarks": [
        {
          "name": "left_shoulder",
          "x": 0.42,
          "y": 0.31,
          "z": -0.12,
          "visibility": 0.98,
          "presence": 0.99
        }
      ]
    }
  ],
  "videoInfo": {
    "videoSrc": "path/to/video.mp4",
    "displayName": "backSquat.mp4",
    "sourceFps": 30,
    "frameCount": 322,
    "width": 1280,
    "height": 720,
    "backend": "opencv",
    "extractedCount": 322,
    "runningMode": "VIDEO",
    "modelName": "pose_landmarker_full.task",
    "detectedFrameCount": 300
  },
  "nextTimestampCursorMs": 10731
}
```

분석 담당자는 이 구조를 기준으로 계산 로직을 작성하면 된다.

## 6. `skeleton` 데이터에서 꼭 이해해야 하는 필드

### 6.1 `frames`

시간축 분석의 핵심 배열이다.

각 원소는 한 프레임을 뜻한다.

- `frameIndex`: 프레임 순번
- `timestampMs`: 시간축 위치
- `poseDetected`: 해당 프레임에서 포즈 감지 성공 여부
- `landmarks`: 관절 포인트 목록

### 6.2 `landmarks`

포즈 포인트 목록이다.

각 포인트는 아래 필드를 가진다.

- `name`: 관절 이름
- `x`, `y`, `z`: 좌표
- `visibility`: 가시성
- `presence`: 존재 확률 계열 값

주의할 점:

- 모든 프레임이 항상 완전한 품질을 가지는 것은 아니다.
- `poseDetected=false`인 프레임이 있을 수 있다.
- `visibility`, `presence`는 품질 필터링에 사용할 수 있지만, 해석 기준은 분석 설계에서 따로 정해야 한다.

### 6.3 `videoInfo`

분석 계산보다 메타데이터에 가깝지만, 결과 요약을 만들 때 중요하다.

- 원본 FPS
- 추출 프레임 수
- 감지 성공 프레임 수
- 비디오 크기
- 모델 이름

요약 KPI나 품질 경고 메시지를 만들 때 유용하다.

## 7. 현재 분석 결과 형식

현재 `analysis_pipeline.py`는 임시 구조를 반환하고 있다.

현재 반환 블록(수정 가능):

- `summary`
- `kpis`
- `timeseries`
- `events`
- `repSegments`
- `issues`

## 8. 팀원이 실제로 수정해야 하는 파일

### 8.1 1순위

- [`analysis_pipeline.py`](C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/service/analysis_pipeline.py)

여기에 넣어야 하는 것:

- `skeleton` 입력 해석
- 전처리 흐름
- 시계열 생성
- KPI 계산 호출
- 이벤트 생성 호출
- rep segment 생성 호출
- issue 생성 호출
- 최종 `analysis` dict 조립

여기에 넣지 말아야 하는 것:

- FastAPI 라우팅
- MediaPipe 직접 호출
- 파일 저장 처리
- 업로드 처리

### 8.2 2순위

- [`result.py`](C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/schema/result.py)

여기서 할 수 있는 것:

- `analysis` 구조를 더 명확한 Pydantic 모델로 바꾸기
- 프론트엔드와 합의된 응답 형식을 타입으로 고정하기

현재는 `dict` 기반이라 빠르게 움직이기 쉽지만, 협업이 커지면 타입 모델을 세우는 것이 안전하다.

### 8.3 필요 시 분리할 신규 파일

분석 코드가 커지면 `service/` 아래를 아래처럼 나누는 것을 권장한다.

```text
service/
  analysis_pipeline.py
  analysis_preprocess.py
  analysis_timeseries.py
  analysis_kpis.py
  analysis_events.py
  analysis_reps.py
  analysis_issues.py
```

권장 역할:

- `analysis_pipeline.py`: 전체 흐름 조립
- `analysis_preprocess.py`: 입력 정규화, 프레임 필터링, landmark lookup 유틸
- `analysis_timeseries.py`: 시간축 데이터 생성
- `analysis_kpis.py`: 집계 지표 계산
- `analysis_events.py`: 이벤트 포인트 검출
- `analysis_reps.py`: 반복 구간 분할
- `analysis_issues.py`: 경고/문제 탐지

핵심 원칙은 아래다.

- `analysis_pipeline.py`는 조립
- 나머지 파일은 계산

## 9. 팀원 작업 단위 가이드

비개발자 팀원에게 작업을 나눌 때는 아래처럼 쪼개는 것이 안전하다.

### 작업 단위 A. 입력 데이터 해설 정리

목표:

- `skeleton.frames`와 `landmarks` 구조를 사람이 읽기 쉽게 설명

산출물:

- 문서
- 샘플 JSON 주석

권장 위치:

- `docs/data/` 또는 `poseLandmarker_Python/docs/architecture/`

### 작업 단위 B. 전처리 레이어 설계

목표:

- 분석 전에 공통으로 필요한 정리 작업 정의

예:

- landmark 이름 기준 조회 방식
- 누락 프레임 처리 정책
- 저품질 프레임 제외 정책
- 시간축 정렬 보장

권장 위치:

- `service/analysis_preprocess.py`

### 작업 단위 C. 출력 스키마 합의

목표:

- `summary`, `kpis`, `timeseries`, `events`, `repSegments`, `issues`에 어떤 필드를 둘지 먼저 합의

권장 위치:

- `schema/result.py`
- 별도 설계 문서

중요:

- 구현보다 먼저 결과 shape를 합의하는 편이 훨씬 안전하다.

### 작업 단위 D. 계산 모듈 구현

목표:

- 각 분석 함수를 독립 모듈로 분리

권장 위치:

- `service/analysis_*.py`

### 작업 단위 E. 파이프라인 조립

목표:

- 계산 모듈들을 `AnalysisPipelineService.analyze()`에서 연결

권장 위치:

- `service/analysis_pipeline.py`

### 작업 단위 F. 검증 데이터와 회귀 테스트

목표:

- 샘플 입력에 대해 항상 같은 출력 구조가 나오는지 확인

권장 위치:

- `poseLandmarker_Python/docs/testing.md`에 절차 추가
- 이후 테스트 코드가 생기면 `tests/` 디렉토리 신설

## 10. 권장 로드맵

### Phase 1. 입력과 출력 고정

해야 할 일:

- `skeleton` 입력 형식 문서화
- `analysis` 출력 형식 초안 합의
- 용어 사전 합의

완료 기준:

- 팀원이 코드 없이도 입력 JSON과 출력 JSON을 설명할 수 있음

### Phase 2. 파이프라인 뼈대 분리

해야 할 일:

- `analysis_pipeline.py`를 조립 전용으로 단순화
- 전처리, 시계열, KPI, 이벤트, 세그먼트, 이슈 모듈 분리

완료 기준:

- 분석 흐름이 파일 책임 단위로 구분됨

### Phase 3. 샘플 기반 계산 연결

해야 할 일:

- 실제 분석 공식 대신 임시 계산이라도 각 모듈 입출구를 고정
- 샘플 `skeleton` 입력으로 end-to-end 실행 확인

완료 기준:

- `GET /jobs/{job_id}/result`의 `analysis`가 빈 값이 아닌 구조화된 결과를 반환함

### Phase 4. 품질 기준과 예외 정책 추가

해야 할 일:

- `poseDetected=false` 프레임 처리 방침 결정
- landmark 누락 시 처리 정책 결정
- 저품질 프레임 처리 정책 결정

완료 기준:

- 입력 이상 상황에서 출력이 어떻게 나오는지 문서로 설명 가능

### Phase 5. 스키마 고정과 프론트 연동

해야 할 일:

- `analysis`를 typed schema로 전환 검토
- 프론트엔드가 바로 쓸 수 있는 필드명 정리

완료 기준:

- 프론트와 분석 팀이 같은 응답 계약을 기준으로 작업함

## 11. 구현 원칙

### 원칙 1. 계산 로직은 `service/`에 둔다

분석 계산은 `service/analysis_*` 파일에 둔다.

`controller/`에는 두지 않는다.

### 원칙 2. 데이터 형식 정의는 `schema/`에 둔다

응답 구조를 고정해야 할 때는 `schema/`에 둔다.

### 원칙 3. 외부 라이브러리 세부사항과 분석 로직을 섞지 않는다

MediaPipe 관련 코드는 `adapter/`, `pose_inference.py` 쪽에 있고, 분석 팀은 가급적 `skeleton` 이후만 다루는 편이 맞다.

### 원칙 4. 계산 함수는 작은 단위로 나눈다

한 파일에 모든 분석 공식을 몰아넣기보다, 목적별 함수로 나누는 편이 유지보수에 유리하다.

### 원칙 5. 먼저 shape, 그다음 계산

무엇을 반환할지 먼저 정한 뒤 계산을 붙여야 협업 충돌이 줄어든다.

## 12. 작업 시작 체크리스트

작업 시작 전에 아래를 확인하면 된다.

1. `service/skeleton_mapper.py`를 읽고 입력 JSON 구조를 이해한다.
2. `service/analysis_pipeline.py`를 읽고 현재 반환 구조를 확인한다.
3. `schema/result.py`를 보고 최종 응답 위치를 확인한다.
4. 새 분석 모듈을 만들지, `analysis_pipeline.py` 안에서 시작할지 결정한다.
5. 출력 필드명을 먼저 문서로 합의한다.

## 13. 권장 시작점

팀원이 바로 시작하려면 아래 순서가 가장 안전하다.

1. `analysis_pipeline.py`를 읽는다.
2. `skeleton_mapper.py`의 출력 예시를 기준으로 샘플 입력을 만든다.
3. `analysis` 출력 초안 문서를 먼저 쓴다.
4. `analysis_preprocess.py`와 `analysis_timeseries.py`부터 분리한다.
5. 마지막에 `analysis_pipeline.py`에서 합친다.

## 14. 지금 기준 결론

현재 프로젝트에서 데이터분석 파이프라인의 공식 입구는 `AnalysisPipelineService.analyze()`이고, 공식 입력은 `skeleton` JSON이며, 공식 출구는 `MotionAnalysisResult.analysis`다.

따라서 팀원에게 맡길 작업의 중심 파일은 `service/analysis_pipeline.py`이고, 코드가 커질 경우 `service/analysis_*.py` 계열로 분리하는 방식이 가장 자연스럽다.

분석 내용 정의는 다음 단계에서 정하고, 이번 단계에서는 아래 3가지만 먼저 고정하면 된다.

- 입력 데이터 구조
- 출력 데이터 구조
- 파일별 책임 경계
