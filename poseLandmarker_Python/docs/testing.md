# poseLandmarker_Python 테스트 방법

이 문서는 `poseLandmarker_Python` 백엔드를 로컬에서 직접 실행하고,
헬스 체크, job 생성, 결과 조회까지 확인하는 가장 기본적인 테스트 절차를 정리한 문서입니다.

## 무엇을 테스트하나요?

이 프로젝트는 FastAPI 백엔드입니다.
즉, 테스트의 핵심은 아래 3가지를 확인하는 것입니다.

- 서버가 정상적으로 실행되는지
- `POST /jobs` 요청이 정상적으로 들어가는지
- 생성된 job의 상태, 결과, benchmark를 조회할 수 있는지

현재 버전에서는 업로드 파일이 없어도 내부 목업 비디오를 사용해서 테스트할 수 있습니다.

- 기본 목업 비디오: `src/video/backSquat.mp4`

## 사전 준비

아래 조건이 맞아야 테스트가 편합니다.

- `uv`가 설치되어 있어야 합니다.
- 프로젝트 폴더로 이동한 상태여야 합니다.
- 처음 실행이라면 의존성 설치가 필요합니다.

프로젝트 폴더:

```powershell
cd C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python
```

처음 실행하거나 환경을 다시 맞춰야 한다면:

```powershell
uv sync
```

## 1. 서버 실행

아래 명령으로 FastAPI 서버를 실행합니다.

```powershell
uv run main.py
```

정상적으로 실행되면 서버는 기본적으로 아래 주소에서 열립니다.

- `http://127.0.0.1:8000`

터미널 창은 서버가 켜져 있는 동안 계속 실행 중 상태로 남아 있습니다.
이 창을 닫으면 서버도 함께 종료됩니다.

## 2. 가장 먼저 확인할 것: 헬스 체크

브라우저에서 아래 주소를 엽니다.

- `http://127.0.0.1:8000/`

정상 응답 예시:

```json
{"message":"Motion Analysis Backend is running."}
```

이 응답이 보이면 서버 자체는 정상적으로 켜진 것입니다.

## 3. Swagger UI에서 직접 테스트하기

가장 쉬운 방법은 Swagger UI를 사용하는 것입니다.

주소:

- `http://127.0.0.1:8000/docs`

여기서 각 API를 브라우저에서 직접 실행할 수 있습니다.

### 3-1. `POST /jobs` 테스트

`POST /jobs`를 열고 `Try it out`을 누른 뒤 아래처럼 입력합니다.

- `fps`: 필수 입력, 예시 `10`
- `exerciseType`: 선택 입력, 예시 `back_squat`
- `video`: 비워도 됨
- `modelAssetPath`: 보통 비워도 됨
- `modelVariant`: 필요하면 `lite`, `full`, `heavy`
- `delegate`: 필요하면 입력

중요한 점:

- 현재 구현에서는 `video`를 비워도 job 생성이 가능합니다.
- 파일을 업로드하지 않으면 내부적으로 `src/video/backSquat.mp4`를 사용합니다.

정상 응답 예시:

```json
{
  "jobId": "job_xxxxxxxx",
  "status": "queued"
}
```

### 3-2. `GET /jobs/{job_id}`로 상태 확인

위에서 받은 `jobId`를 사용해 상태를 조회합니다.

처음에는 아래와 비슷한 상태가 보일 수 있습니다.

- `queued`
- `extracting`
- `analyzing`
- `generating_feedback`
- `completed`

즉, 완료될 때까지 몇 번 새로 호출해 보면 됩니다.

### 3-3. `GET /jobs/{job_id}/result`로 최종 결과 확인

job 상태가 `completed`가 되면 최종 결과를 조회할 수 있습니다.

여기서 확인할 수 있는 대표 항목은 아래와 같습니다.

- `skeleton.videoInfo`
- `skeleton.nextTimestampCursorMs`
- `analysis`
- `llmFeedback`
- `benchmark`

아직 완료 전인데 이 API를 호출하면 `409` 응답이 날 수 있습니다.

### 3-4. `GET /jobs/{job_id}/skeleton`로 frame 페이지 확인

대용량 skeleton frame은 페이지 단위로 확인합니다.

- `offset`: 시작 프레임 인덱스
- `limit`: 한 번에 가져올 프레임 수, 기본값 `30`

### 3-5. `GET /jobs/{job_id}/skeleton/download`로 전체 skeleton 다운로드

Swagger UI에서는 이 엔드포인트를 파일 다운로드 용도로 사용합니다.

### 3-6. benchmark 확인

추가로 아래 API도 확인할 수 있습니다.

- `GET /jobs/{job_id}/benchmark`
- `GET /jobs/{job_id}/benchmark/frames`

이 응답은 성능 측정이나 품질 확인에 사용합니다.

## 4. PowerShell로 테스트하기

브라우저 대신 PowerShell로도 바로 테스트할 수 있습니다.

### 4-1. 헬스 체크

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
```

### 4-2. job 생성

```powershell
$job = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/jobs `
  -Form @{ fps = 10; exerciseType = 'back_squat' }
```

생성된 job ID 확인:

```powershell
$job.jobId
```

### 4-3. 상태 조회

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/jobs/$($job.jobId)"
```

### 4-4. 최종 결과 조회

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/jobs/$($job.jobId)/result"
```

### 4-5. skeleton 페이지 조회

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/jobs/$($job.jobId)/skeleton?offset=0&limit=30"
```

### 4-6. skeleton 파일 다운로드

```powershell
Invoke-WebRequest "http://127.0.0.1:8000/jobs/$($job.jobId)/skeleton/download" -OutFile "$($job.jobId).skeleton.json"
```

### 4-7. benchmark 조회

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/jobs/$($job.jobId)/benchmark"
Invoke-RestMethod "http://127.0.0.1:8000/jobs/$($job.jobId)/benchmark/frames"
```

## 5. 실제 업로드 파일로 테스트하고 싶다면

현재 구현에서는 `video` 파일 업로드도 지원합니다.
Swagger UI에서 `video`에 mp4 등의 파일을 넣어 호출하면 됩니다.

허용 확장자는 아래와 같습니다.

- `.mp4`
- `.mov`
- `.avi`
- `.mkv`
- `.webm`

업로드된 파일은 임시로 아래 경로에 저장됩니다.

- `tmp/uploads`

## 6. 결과 파일은 어디에 쌓이나요?

테스트 중 생성되는 임시 산출물은 주로 아래 폴더를 확인하면 됩니다.

- `tmp/uploads`: 업로드된 원본 비디오
- `tmp/frames`: 추출 프레임 관련 산출물
- `tmp/benchmarks`: benchmark 결과 JSON

특히 benchmark 결과는 아래 위치에 저장됩니다.

- `tmp/benchmarks/*.summary.json`
- `tmp/benchmarks/*.frames.json`

## 7. 자주 확인할 문제

### 서버가 안 켜질 때

아래를 먼저 확인합니다.

- 현재 위치가 `poseLandmarker_Python` 폴더가 맞는지
- `uv`가 설치되어 있는지
- 처음 실행인데 `uv sync`를 하지 않았는지

### `POST /jobs`가 실패할 때

아래를 확인합니다.

- `fps`를 입력했는지
- 업로드한 파일 확장자가 허용 목록에 있는지
- 모델 파일 경로를 직접 넣었다면 경로가 실제로 존재하는지

### 결과 조회가 안 될 때

아직 job이 끝나지 않았을 수 있습니다.
먼저 `GET /jobs/{job_id}`로 상태가 `completed`인지 확인한 뒤
`GET /jobs/{job_id}/result`를 호출해야 합니다.
전체 skeleton이 필요하면 그 다음에 `GET /jobs/{job_id}/skeleton` 또는
`GET /jobs/{job_id}/skeleton/download`를 호출합니다.

## 8. 가장 추천하는 테스트 순서

처음 테스트한다면 아래 순서가 가장 단순합니다.

1. `uv sync`
2. `uv run main.py`
3. `http://127.0.0.1:8000/` 접속
4. `http://127.0.0.1:8000/docs` 접속
5. `POST /jobs`에서 `fps=10`으로 호출
6. `GET /jobs/{job_id}`로 완료 여부 확인
7. `GET /jobs/{job_id}/result` 확인
8. 필요하면 `GET /jobs/{job_id}/skeleton?offset=0&limit=30` 확인
9. 필요하면 `benchmark` API 확인

이 순서대로 되면 현재 구축된 백엔드의 기본 동작은 정상이라고 보면 됩니다.
