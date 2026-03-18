# poseLandmarker_Python

비디오 업로드, 포즈 추론, 분석, 피드백 생성을 위한 `uv` 기반 FastAPI 백엔드 프로젝트입니다.

## 이 프로젝트는 무엇인가요?

이 프로젝트는 FastAPI로 만든 백엔드 서버입니다.

개발자가 아니라면 아래처럼 이해하면 됩니다.

- 프론트엔드: 브라우저에서 보이는 화면
- 백엔드: 요청을 받아 처리하고 결과를 돌려주는 서버

즉, 이 프로젝트에서 백엔드를 실행한다는 것은 내 컴퓨터에서 로컬 서버를 켜서 프론트엔드나 API 테스트 도구가 이 서버와 통신할 수 있게 만든다는 뜻입니다.

## 실행 전에 알아둘 점

이 프로젝트는 `uv`로 Python 패키지를 관리하고 앱을 실행합니다.

`uv`를 사용한다면 보통 Python 가상환경을 직접 켤 필요는 없습니다.
`uv sync`, `uv run ...` 같은 명령을 실행할 때 `uv`가 필요한 환경을 알아서 맞춰줍니다.

## 백엔드 실행 방법

프로젝트 폴더에서 아래 명령을 실행하면 됩니다.

```bash
uv sync
uv run main.py
```

### `uv sync`는 무엇인가요?

`uv sync`는 이 프로젝트를 실행하는 데 필요한 Python 환경을 준비하는 명령입니다.

쉽게 말하면 `pyproject.toml`과 `uv.lock` 파일을 기준으로, 이 프로젝트에 필요한 라이브러리를 설치해 줍니다.

한마디로 보면:

- "이 프로젝트가 실행되기 전에 필요한 준비를 하는 단계"

보통 아래 경우에 `uv sync`가 필요합니다.

- 처음 실행할 때
- 프로젝트 의존성이 바뀌었을 때
- 다른 개발자가 환경을 다시 맞추라고 했을 때

이미 한 번 설치했고 환경이 바뀌지 않았다면, 매번 `uv sync`를 다시 할 필요는 없는 경우가 많습니다.

### `uv run main.py`는 무엇인가요?

`uv run main.py`는 실제로 백엔드 서버를 켜는 명령입니다.

이 프로젝트에서 `main.py`는 Uvicorn으로 FastAPI 앱을 실행합니다. 즉, 이 명령은 "백엔드 서버를 켠다"는 뜻입니다.

프론트 작업에서 `Live Server`를 켜는 것에 익숙하다면, 아래처럼 생각하면 됩니다.

- `Live Server`는 프론트엔드용 로컬 서버를 켭니다.
- `uv run main.py`는 이 프로젝트의 백엔드 로컬 서버를 켭니다.

## 서버가 정상 실행됐는지 확인하는 방법

백엔드가 정상적으로 실행되면 아래 주소에서 동작합니다.

`http://127.0.0.1:8000`

브라우저에서 아래 주소를 열어보세요.

`http://127.0.0.1:8000/`

정상 실행 중이라면 아래와 비슷한 응답이 보입니다.

```json
{"message":"Motion Analysis Backend is running."}
```

이 응답이 보이면 백엔드 서버가 켜져 있고 요청을 받을 준비가 된 상태입니다.

## 추가로 켜야 하는 것이 있나요?

현재 버전의 이 프로젝트 기준으로는 보통 **없습니다**.

현재 코드에는 MySQL, Redis, RabbitMQ 같은 별도 서버가 연결되어 있지 않습니다.
그래서 일반적인 로컬 테스트에서는 `uv run main.py`만 실행해도 충분합니다.

## 보통은 이렇게 실행하면 됩니다

처음 실행하는 경우:

```bash
uv sync
uv run main.py
```

이미 한 번 환경을 맞췄고 바뀐 것이 없다면:

```bash
uv run main.py
```

## Windows에서 실제로 실행하는 순서

Windows 기준으로는 보통 아래 순서대로 하면 됩니다.

1. 터미널을 엽니다.
2. 이 프로젝트 폴더로 이동합니다.
3. 처음이면 `uv sync`를 실행합니다.
4. `uv run main.py`를 실행합니다.
5. 브라우저에서 `http://127.0.0.1:8000/`에 접속해 서버가 켜졌는지 확인합니다.

예시:

```powershell
cd C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python
uv sync
uv run main.py
```

이미 한 번 설치가 끝났고 환경이 바뀌지 않았다면 아래처럼 실행해도 됩니다.

```powershell
cd C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python
uv run main.py
```

## 실행 중일 때 보이는 모습

서버가 정상적으로 켜지면 터미널 창이 계속 실행 중인 상태로 남아 있습니다.
이 창을 닫으면 백엔드 서버도 함께 종료됩니다.

즉:

- 터미널 창이 켜져 있고
- `uv run main.py`가 종료되지 않은 상태이며
- `http://127.0.0.1:8000/` 접속이 된다면

백엔드 서버가 켜져 있는 것입니다.

## 간단한 테스트 방법

가장 쉬운 테스트는 브라우저에서 아래 주소를 여는 것입니다.

`http://127.0.0.1:8000/`

응답이 보이면 서버는 정상입니다.

조금 더 확인하고 싶다면 PowerShell에서 아래처럼 요청을 보낼 수도 있습니다.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
```

정상이라면 비슷한 결과가 나옵니다.

```text
message
-------
Motion Analysis Backend is running.
```

## 엔드포인트

- `GET /` : 백엔드 서버가 켜져 있는지 확인하는 간단한 주소
- `POST /jobs` : 새 작업을 생성하는 API
- `GET /jobs/{job_id}` : 작업 진행 상태를 확인하는 API
- `GET /jobs/{job_id}/result` : 작업 결과를 가져오는 API

## 팀 협업용 안내

이 프로젝트는 팀원 전체가 모든 코드를 다 이해해야 하는 구조를 목표로 하지 않습니다.
오히려 각자 필요한 부분만 이해해도 협업할 수 있게 폴더를 나눠 둔 상태입니다.

이 프로젝트에서 가장 중요한 생각은 아래 한 줄입니다.

- `controller`는 "입구"
- `service`는 "실제 작업"
- `schema`는 "주고받는 데이터 형식"
- `adapter`는 "외부 라이브러리 연결부"

즉, 브라우저나 프론트엔드에서 요청이 들어오면 `controller`가 받고, 실제 처리는 `service`가 하고, 결과 형식은 `schema`가 정하고, OpenCV나 MediaPipe 같은 외부 도구 연결은 `adapter`가 맡습니다.

## `uv`는 무엇인가요?

`uv`는 Python 프로젝트를 실행하기 쉽게 도와주는 도구입니다.

개발자가 아닌 팀원 입장에서는 아래 정도로 이해하면 충분합니다.

- 필요한 Python 패키지를 설치해 줍니다.
- 프로젝트에 맞는 실행 환경을 맞춰 줍니다.
- 복잡한 가상환경 활성화 과정을 많이 줄여 줍니다.

이 프로젝트에서는 아래 두 명령만 먼저 기억하면 됩니다.

- `uv sync` : 필요한 패키지 설치
- `uv run main.py` : 백엔드 서버 실행

즉, "Python 환경을 준비하고 실행하는 도구"라고 이해하면 됩니다.

## 폴더를 어떻게 보면 되나요?

프로젝트의 주요 폴더는 아래처럼 보면 됩니다.

- `main.py` : 서버를 켜는 시작 파일
- `app.py` : 전체 FastAPI 앱을 조립하는 파일
- `config/` : 포트 번호나 경로 같은 설정
- `controller/` : API 주소를 정의하는 곳
- `schema/` : 요청과 응답 데이터 형식을 정하는 곳
- `service/` : 실제 처리 로직이 들어가는 곳
- `adapter/` : OpenCV, MediaPipe 같은 외부 라이브러리 연결부
- `docs/` : 구조와 설계 문서

처음 보는 팀원이라면 아래 순서로 읽는 것이 가장 쉽습니다.

1. `README.md`
2. `main.py`
3. `app.py`
4. `controller/jobs.py`
5. `service/job_manager.py`
6. 내가 맡은 기능의 `service` 파일

## 각 폴더의 역할

### `main.py`

서버를 실제로 켜는 파일입니다.

이 프로젝트에서 `uv run main.py`를 실행하면 이 파일이 시작점이 됩니다.

### `app.py`

백엔드 앱 전체를 조립하는 파일입니다.

어떤 API를 열지, 어떤 라우터를 등록할지 여기서 연결합니다.

### `controller/`

외부에서 들어오는 요청을 받는 곳입니다.

예를 들면:

- `GET /` 요청 받기
- `POST /jobs` 요청 받기
- `GET /jobs/{job_id}` 요청 받기

중요한 점은, `controller`에서는 복잡한 계산을 많이 하지 않는다는 것입니다.
보통은 요청을 받은 뒤 `service`로 넘깁니다.

### `service/`

이 프로젝트에서 실제 핵심 작업이 들어가는 곳입니다.

예를 들면:

- job 상태 관리
- 비디오 읽기
- 포즈 추론
- 스켈레톤 데이터 정리
- 운동 분석
- LLM 피드백 생성

즉, "무슨 처리를 할 것인가"는 대부분 이 폴더 안에 들어갑니다.

### `schema/`

프론트엔드와 백엔드가 어떤 형식으로 데이터를 주고받을지 정하는 곳입니다.

예를 들어:

- job 상태 응답은 어떤 필드를 가져야 하는지
- 최종 분석 결과는 어떤 구조여야 하는지

이 폴더는 팀원 간 협업에서 특히 중요합니다.
왜냐하면 프론트엔드와 분석 로직이 서로 같은 데이터 구조를 보고 작업해야 하기 때문입니다.

### `adapter/`

OpenCV, MediaPipe 같은 외부 라이브러리를 프로젝트 코드와 연결하는 곳입니다.

팀원 입장에서는 아래처럼 보면 됩니다.

- 외부 도구를 직접 만지는 경계선
- 나중에 라이브러리를 바꾸더라도 영향 범위를 줄이기 위한 분리

## 데이터분석 담당 팀원은 어디를 보면 되나요?

데이터분석 담당 팀원은 모든 파일을 이해할 필요가 없습니다.
우선 아래 파일들만 보면 됩니다.

- `service/analysis_pipeline.py`
- `schema/result.py`
- 필요하면 `service/skeleton_mapper.py`
- 필요하면 `service/pose_inference.py`

핵심은 `service/analysis_pipeline.py`입니다.
분석 로직은 기본적으로 여기에 들어가야 합니다.

쉽게 말하면:

- 입력: `skeleton` 데이터
- 처리: 관절 각도, 반복 구간, KPI, 문제 탐지 같은 분석
- 출력: `analysis` 블록에 들어갈 결과

즉, 데이터분석 파이프라인은 `service/analysis_pipeline.py`에 넣는 것이 맞습니다.

## 데이터분석 파이프라인은 어디에 넣어야 하나요?

분석 코드는 원칙적으로 `service/analysis_pipeline.py`에 넣습니다.

이유는 아래와 같습니다.

- `controller`는 요청을 받는 곳이지 분석 계산을 하는 곳이 아님
- `schema`는 데이터 형식을 정하는 곳이지 계산을 하는 곳이 아님
- `adapter`는 외부 라이브러리 연결부이지 운동 분석 알고리즘을 넣는 곳이 아님

따라서 운동 분석 로직, KPI 계산, 반복 구간 분리, 이슈 탐지 같은 것은 `service/analysis_pipeline.py`가 중심이 되어야 합니다.

만약 분석 코드가 커진다면 나중에는 아래처럼 더 쪼갤 수 있습니다.

- `service/analysis_pipeline.py` : 전체 흐름 조립
- `service/analysis_angles.py` : 각도 계산
- `service/analysis_reps.py` : 반복 구간 분리
- `service/analysis_kpis.py` : KPI 계산
- `service/analysis_issues.py` : 문제 탐지

지금 단계에서는 우선 `service/analysis_pipeline.py`에 모으고, 커지면 나누는 방식이 가장 이해하기 쉽습니다.

## 협업할 때 각자 어디까지 보면 되나요?

### 데이터분석 담당 팀원

주로 보면 되는 곳:

- `service/analysis_pipeline.py`
- `schema/result.py`
- 분석 입력 형식을 확인하려면 `service/skeleton_mapper.py`

굳이 깊게 안 봐도 되는 곳:

- `main.py`
- `app.py`
- `controller/`
- `adapter/` 내부 세부 구현

즉, 분석 담당자는 "입력 데이터가 어떤 구조로 들어오고, 내가 어떤 결과 구조를 만들어야 하는가"만 먼저 이해하면 됩니다.

### 그 외 기능을 개발하는 사람(팀장, 그 외 관심있는 분은 말씀 주세요!)

주로 보면 되는 곳:

- `main.py`
- `app.py`
- `controller/`
- `service/job_manager.py`
- `adapter/`

즉, 서버 실행, API 연결, 업로드 흐름, 상태 관리, 외부 라이브러리 연결을 담당하면 됩니다.

## 실제 데이터 흐름은 어떻게 되나요?

이 프로젝트의 큰 흐름은 아래와 같습니다.

1. 사용자가 비디오를 업로드합니다.
2. `controller/jobs.py`가 요청을 받습니다.
3. `service/job_manager.py`가 job을 만들고 상태를 관리합니다.
4. 비디오에서 프레임을 읽습니다.
5. 포즈를 추론해서 스켈레톤 데이터를 만듭니다.
6. 분석 파이프라인이 스켈레톤 데이터를 받아 분석합니다.
7. 분석 결과를 바탕으로 필요하면 LLM 피드백을 만듭니다.
8. 최종 결과를 `GET /jobs/{job_id}/result`로 돌려줍니다.

여기서 데이터분석 담당자가 가장 중요하게 볼 부분은 5번 이후입니다.
즉, "스켈레톤 데이터가 만들어진 뒤 어떤 분석 결과를 만들 것인가"가 핵심입니다.

## 팀원들이 최소한 기억하면 되는 것

모든 팀원이 처음부터 자세히 알 필요는 없고, 아래만 먼저 기억하면 충분합니다.

1. `uv sync`는 실행 준비
2. `uv run main.py`는 백엔드 실행
3. 분석 로직은 `service/analysis_pipeline.py`
4. API 입구는 `controller/`
5. 결과 형식은 `schema/`

## 추천 협업 방식

비개발자 팀이 협업할 때는 아래 방식이 가장 안전합니다.

- 서버 실행과 API 연결 담당은 `controller`, `job_manager`, `adapter` 중심으로 작업
- 데이터분석 담당은 `service/analysis_pipeline.py` 중심으로 작업
- 프론트엔드와 데이터 형식 약속은 `schema/result.py`를 기준으로 맞추기
- 새로운 분석 항목을 추가할 때는 먼저 `analysis` 결과에 어떤 필드를 넣을지부터 정한 뒤 구현하기

즉, 코드를 먼저 막 추가하기보다 "결과 형식부터 합의하고, 그다음 분석 로직을 넣는 방식"이 협업에 가장 유리합니다.
