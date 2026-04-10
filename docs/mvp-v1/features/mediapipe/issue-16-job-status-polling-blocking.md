[fix] MediaPipe 백엔드 job status polling 응답 지연 수정

브랜치명: `fix/11-job-status-polling-blocking`

## 작업 목적
`GET /jobs/{job_id}` 자체는 가벼운 상태 조회 API지만, 실제 job 실행 중 포즈 추론과 분석 단계가 이벤트 루프를 오래 점유하면서 브라우저 polling 응답이 끊기거나 과도하게 지연되는 문제가 있었다. 이 작업의 목적은 백그라운드 job 처리와 상태 조회 경로를 분리해, 분석 중에도 status polling이 지속적으로 응답되도록 만드는 것이다.

## 작업 내용
- `service/job_manager.py`의 백그라운드 job 실행 흐름에서 CPU 점유 시간이 긴 단계를 이벤트 루프 밖으로 분리한다.
- 프레임 추출뿐 아니라 pose inference, skeleton mapping, analysis, benchmark 생성, feedback 생성 단계도 non-blocking orchestration 구조로 정리한다.
- job이 실행 중이어도 `GET /jobs/{job_id}` 상태 조회가 브라우저 polling 환경에서 안정적으로 응답되도록 보장한다.
- 향후 대용량 결과 조회와 status polling을 분리해서 볼 수 있도록 성능 관점 권고를 문서에 반영한다.

## 완료 조건
- job 실행 중 `GET /jobs/{job_id}` 요청이 장시간 pending 상태로 묶이지 않는다.
- 브라우저 또는 API 클라이언트에서 polling 요청을 반복해도 서버 전체 응답성이 급격히 떨어지지 않는다.
- job 완료 전후 상태 전이가 기존과 동일하게 유지된다.
- 문서 기준으로도 백그라운드 무거운 단계는 이벤트 루프를 직접 점유하지 않는다는 원칙이 반영된다.

## 참고 자료
- `poseLandmarker_Python/service/job_manager.py`
- `docs/mvp-v1/features/mediapipe/spec.md`
- `docs/mvp-v1/features/mediapipe/architecture.md`

fix: MediaPipe 백엔드 job status polling 응답 지연 수정 (#11)

- background job의 CPU 바운드 단계를 `asyncio.to_thread()`로 분리해 이벤트 루프 블로킹을 줄인다.
- 분석 중에도 `GET /jobs/{job_id}` polling 요청이 지속적으로 응답되도록 오케스트레이션 구조를 정리한다.
- MediaPipe 문서에 polling 응답성과 백그라운드 실행 원칙을 반영한다.

[fix] MediaPipe 백엔드 job status polling 응답 지연 수정 (#11)

## 관련 Issue
Closes #11

## 작업 내용
- `JobManager._run_job()`에서 프레임 추출 이후의 무거운 동기 단계를 스레드로 오프로딩한다.
- pose inference, skeleton mapping, analysis, benchmark 생성, feedback 생성이 이벤트 루프를 장시간 점유하지 않도록 수정한다.
- status polling 시나리오에서 `/jobs/{job_id}`가 분석 작업과 분리되어 응답될 수 있도록 구조를 정리한다.

## 변경 사항 상세
- `poseLandmarker_Python/service/job_manager.py`에서 `PoseInferenceService.run()` 호출을 `asyncio.to_thread()`로 감쌌다.
- `poseLandmarker_Python/service/job_manager.py`에서 `SkeletonMapperService.map_landmarks()`, `AnalysisPipelineService.analyze()`, `BenchmarkService.build_result()`, `LlmFeedbackService.generate()` 호출도 동일하게 스레드 오프로딩으로 변경했다.
- `docs/mvp-v1/features/mediapipe/architecture.md`에 background job의 CPU 바운드 단계는 이벤트 루프 밖에서 실행해야 한다는 원칙과 polling 응답성 관련 권고를 추가했다.
- `docs/mvp-v1/features/mediapipe/spec.md`에 status polling과 무거운 분석 단계 분리 원칙을 성능 관점 설명에 반영했다.

## 테스트 방법
1. 백엔드 서버를 실행한다.
2. `POST /jobs`로 job을 생성한다.
3. job이 실행 중일 때 `GET /jobs/{job_id}`를 반복 호출한다.
4. 상태 조회 응답이 장시간 끊기지 않고 `queued`, `extracting`, `analyzing`, `generating_feedback`, `completed` 순서로 확인되는지 본다.
5. 필요하면 `GET /jobs/{job_id}/result`는 완료 이후에만 호출해 status polling과 대용량 결과 조회를 분리해서 확인한다.

## 스크린샷 / 결과
- job 실행 중 브라우저 polling 환경에서 `/jobs/{job_id}` 응답이 끊기지 않고 유지됨
- 분석 작업이 진행되는 동안에도 상태 조회가 정상적으로 갱신됨
