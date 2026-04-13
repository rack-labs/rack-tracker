# [AI 기반 랙 운동 자세 추적 및 분석 프로젝트]

> 컴퓨터 비전과 AI 포즈 추정을 활용한 랙 기반 근력 운동 모션 트래킹 시스템

---

# 팀 구성 및 역할 분담

## 팀원 소개 및 역할

| 프로필 | 이름 | 담당 영역 | 핵심 책임 | 주요 개발 산출물 |
| :---: | :--- | :--- | :--- | :--- |
| <img src="https://github.com/lhk0721.png" width="100" height="100" style="object-fit: cover; border-radius: 50%;"> | **이&nbsp;현&nbsp;규** | Core / AI | 프로젝트 리드, 포즈 추정 파이프라인 설계 및 구현, 협업 시스템 구축 | PoseLandmarker 통합, 랙 추적 알고리즘, 문서 체계 수립 |
| — | **이&nbsp;지&nbsp;원** | | | |
| — | **장&nbsp;효&nbsp;인** | | | |
| — | **전&nbsp;효&nbsp;원** | | | |
| — | **신&nbsp;은&nbsp;수** | | | |

---

# 프로젝트 관리 (Collaboration & Process)

```mermaid
graph TD
    %% 1단계: 사전 기획
    subgraph Phase1 [1. 사전 기획]
        A[요구사항 분석] --> B[작업 단위 분해]
        B --> C[팀 공통 기준 정렬]
    end

    %% 2단계: GitHub Issues
    subgraph Phase2 [2. GitHub Issue 기반 설계]
        C --> D[GitHub Issue 생성]
        D --> E{작업 세부 정의}
        E -->|Who| E1[담당자 지정]
        E -->|When| E2[선후 관계/일정]
        E -->|Priority| E3[우선순위 설정]
    end

    %% 3단계: GitHub Kanban
    subgraph Phase3 [3. GitHub Kanban 운영]
        E1 & E2 & E3 --> F[Kanban 컬럼 매핑]
        F --> G1[To Do]
        F --> G2[In Progress]
        F --> G3[Review]
        F --> G4[Done]
    end

    Phase3 --> H[점진적 협업 프로세스 고도화]

    style Phase1 fill:#f9f9f9,stroke:#333,stroke-width:2px
    style Phase2 fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style Phase3 fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style H fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,stroke-dasharray: 5 5
```

> 본 프로젝트는 AI 기능 구현과 더불어, 이슈 기반 GitHub 협업 시스템을 실제로 설계하고 운영하는 과정을 중점적으로 다룹니다.

---

# 협업 프로세스 (Collaboration Process)

## Collaboration Strategy & Philosophy

### Convention First, Code Later

기능 개발에 앞서 협업의 토대를 먼저 견고히 합니다. 저장소 생성 직후, 브랜치 전략과 커밋 컨벤션을 먼저 확정하고 문서화합니다.

- **브랜치 전략:** 이슈 번호 기반 브랜치 생성, `develop` 브랜치 중심 통합
- **커밋 규칙:** 타입 기반 커밋 메시지로 변경 의도 명확화
- **PR 프로세스:** 모든 변경은 PR을 통해 공유, 리뷰 승인 후 병합

---

# Repository Architecture

```mermaid
flowchart TD
    subgraph Upstream ["🌐 Upstream (Organization Remote)"]
        direction TB
        U_MAIN["● main (운영)"]
        U_DEV["● develop (개발/통합)"]
        U_FEAT["issue-number-type-description (이슈 기반 브랜치)"]

        U_MAIN --> U_DEV
        U_DEV -- "① Branch 생성" --> U_FEAT
    end

    subgraph Local ["💻 Local Workstation"]
        direction TB
        L_FEAT["issue-number-type-description (실제 작업/Commit)"]
    end

    subgraph Origin ["🍴 Origin (Personal Fork Remote)"]
        direction TB
        O_FEAT["issue-number-type-description (PR 대기/백업)"]
        O_MAIN["main (Forked)"]
    end

    U_FEAT -- "② git fetch / checkout" --> L_FEAT
    L_FEAT -- "③ git push origin" --> O_FEAT
    O_FEAT == "④ Pull Request (Merge)" ==> U_DEV
    U_DEV -. "⑤ git pull (Sync)" .-> L_FEAT

    style U_MAIN fill:#ff7675,stroke:#fff,stroke-width:2px,color:#fff
    style U_DEV fill:#74b9ff,stroke:#fff,stroke-width:2px,color:#fff
    style U_FEAT fill:#636e72,stroke:#fff,stroke-dasharray: 5 5,color:#fff
    style L_FEAT fill:#ffeaa7,stroke:#fdcb6e,stroke-width:2px,color:#000
    style O_FEAT fill:#55efc4,stroke:#fff,stroke-width:2px,color:#000
    style O_MAIN fill:#b2bec3,stroke:#636e72,color:#000
    style Upstream fill:#1e1e1e,stroke:#ecf0f1,stroke-width:3px,color:#fff
    style Origin fill:#1e1e1e,stroke:#ecf0f1,color:#fff
    style Local fill:#1e1e1e,stroke:#ecf0f1,color:#fff
```

> 원본 레포지토리의 안정성을 최우선으로 유지하면서, 개인 단위 자유로운 개발과 팀 단위 통제된 통합을 동시에 달성하기 위한 협업 구조입니다.

---

## Branch Workflow

> 모든 작업은 **`develop` 브랜치**를 기준으로 진행합니다.

| 구분 | 내용 |
| --- | --- |
| **기준 브랜치** | `develop` (Single Source of Truth) |
| **작업 브랜치** | 로컬 환경의 `issue-number-type-short-description` |
| **Push 대상** | `origin` (개인 Fork 레포지토리) |
| **PR 대상** | `origin/작업-브랜치` → `upstream/develop` |

```mermaid
graph LR
    subgraph Upstream [Central Repository - upstream]
        U_Dev[develop branch]
    end

    subgraph Origin [Personal Fork - origin]
        O_Dev[develop branch]
        O_Feat[issue-number-type-xxx branch]
    end

    subgraph Local [Developer Machine]
        L_Dev[develop branch]
        L_Feat[issue-number-type-xxx branch]
    end

    U_Dev -- "1. Fork" --> O_Dev
    O_Dev -- "2. Clone" --> L_Dev
    L_Dev -- "3. Checkout" --> L_Feat
    L_Feat -- "4. Push" --> O_Feat
    O_Feat -- "5. Pull Request" --> U_Dev
    U_Dev -- "6. Sync (Fetch/Rebase)" --> L_Dev
```

---

### Branch Naming Convention

`<issue-number>-<type>-<short-description>`

| 타입 (Type) | 설명 | 예시 |
| --- | --- | --- |
| `feature` | 새로운 기능 추가 | `41-feature-video-upload-api` |
| `fix` | 버그 수정 | `52-fix-webcam-crash` |
| `hotfix` | 운영 중 발생한 긴급 버그 수정 | `hotfix/78-login-error` |
| `chore` | 설정 변경, 유지보수 등 기능 무관 작업 | `26-chore-clean-up-repository` |
| `docs` | 문서 수정 | `30-docs-update-readme` |
| `test` | 테스트 코드 추가 또는 수정 | `35-test-pose-estimator` |
| `refactor` | 기능 변경 없는 코드 구조 개선 | `44-refactor-tracker-module` |
| `ci` | CI/CD 설정 및 자동화 파이프라인 수정 | `60-ci-update-github-actions` |

---

### 커밋 컨벤션 (Commit Convention)

```
type: short summary (#<issue-number>)

- change item 1
- change item 2
- change item 3
```

| Type | Description |
| --- | --- |
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 |
| `style` | 코드 포맷, 세미콜론 등 스타일 수정 |
| `refactor` | 기능 변경 없는 구조 개선 |
| `perf` | 성능 개선 |
| `test` | 테스트 코드 추가 또는 수정 |
| `build` | 빌드 설정 변경 |
| `ci` | CI 설정 변경 |
| `chore` | 설정, 빌드, 기타 유지보수 작업 |
| `revert` | 이전 커밋 되돌리기 |
| `repo` | 저장소 구조 변경 (아카이브, 이동, 제거) |

---

### 이슈 기반 작업 관리

- 모든 작업은 GitHub Issue 생성 후 진행
- Issue 단위로 브랜치 생성 (`issue-number-type-description`)
- 작업 범위, 완료 조건, 체크리스트를 Issue에 명시
- PR은 반드시 관련 Issue를 연결하여 생성

**이슈 타입**

| Type | Description |
| --- | --- |
| `feature` | 새로운 기능 작업 |
| `fix` | 버그 수정 |
| `refactor` | 내부 구조 개선 |
| `docs` | 문서 작업 |
| `test` | 테스트 작업 |
| `chore` | 환경 설정, 유지보수 |
| `ci` | CI/CD 작업 |
| `perf` | 성능 개선 |

---

### 코드 리뷰 프로세스

```mermaid
graph TD
    Start([1. 기능 개발 완료]) --> PR[2. Pull Request 생성<br/>feature → develop]
    PR --> Verify[3. PR 히스토리 및 브랜치 구조 검증]
    Verify --> Review[4. 코드 리뷰 진행<br/>가독성/컨벤션/사이드이펙트 검토]

    Review --> Decision{5. 모든 리뷰어<br/>승인 완료?}

    Decision -- "NO (수정 필요)" --> Feedback[수정 요청 코멘트]
    Feedback --> Fix[수정 반영 및 추가 커밋 push]
    Fix --> Review

    Decision -- "YES (Approve)" --> Approve[Review Approve 처리]
    Approve --> Merge[Merge 수행<br/>feature → develop 병합 및 브랜치 삭제]
    Merge --> End([프로세스 종료])

    style Decision fill:#fff9c4,stroke:#fbc02d
    style Feedback fill:#ffebee,stroke:#b71c1c
    style Approve fill:#e8f5e9,stroke:#2e7d32
    style Merge fill:#e1f5fe,stroke:#0288d1
```

> 코드 리뷰 시 중점 검토 사항
> - 코드 가독성 및 컨벤션 준수 여부
> - 공통 모듈 영향도
> - 사이드 이펙트 발생 가능성
> - 불필요한 중복 코드 여부

---

# 프로젝트 개요

### 프로젝트 목표와 범위

- AI 포즈 추정(MediaPipe PoseLandmarker) 기반 랙 운동 자세 분석 시스템 구현
- 컴퓨터 비전을 활용한 실시간 모션 트래킹 파이프라인 구축
- 이슈 기반 GitHub 협업 프로세스 실습 및 정착

---

### 프로젝트 범위 (Project Scope)

```mermaid
graph TD
    Root[<b>rack-tracker</b>]

    Root --> Vision[<b>1. 컴퓨터 비전 파이프라인</b>]
    Root --> Analysis[<b>2. 자세 분석</b>]
    Root --> Infra[<b>3. 인프라 / 환경</b>]

    Vision --> PoseEst[포즈 추정: MediaPipe PoseLandmarker]
    Vision --> VideoInput[입력 처리: 웹캠 / 동영상 파일]

    Analysis --> RackTrack[랙 추적: 바벨 및 신체 랜드마크 연동]
    Analysis --> FormCheck[자세 검증: 관절 각도 / 이동 경로 분석]

    Infra --> PythonEnv[Python 가상 환경 구성]
    Infra --> Docs[문서 관리: docs/mvp-v1, docs/mvp-v2]

    style Root fill:#000,stroke:#000,stroke-width:2px,color:#fff
    style Vision fill:#fff,stroke:#000,stroke-width:2px,color:#000
    style Analysis fill:#fff,stroke:#000,stroke-width:2px,color:#000
    style Infra fill:#fff,stroke:#000,stroke-width:2px,color:#000
    style PoseEst fill:#f9f9f9,stroke:#333,color:#000
    style VideoInput fill:#f9f9f9,stroke:#333,color:#000
    style RackTrack fill:#f9f9f9,stroke:#333,color:#000
    style FormCheck fill:#f9f9f9,stroke:#333,color:#000
    style PythonEnv fill:#f9f9f9,stroke:#333,color:#000
    style Docs fill:#f9f9f9,stroke:#333,color:#000
```

---

### 저장소 구조

| 경로 | 설명 |
| --- | --- |
| `poseLandmarker_Python/` | 메인 구현 (Python, MediaPipe) |
| `docs/mvp-v2/` | MVP v2 기획 및 이슈 추적 |
| `docs/mvp-v1/` | MVP v1 레거시 문서 참조 |
| `docs/agent-workflow/` | 협업 워크플로우 및 컨벤션 |
| `archive/` | 레거시 실험 산출물 보존 |

---

### Start Here

- 저장소 문서 인덱스: `docs/README.md`
- MVP v2 진입점: `docs/mvp-v2/README.md`
- MVP v2 이슈 추적: `docs/mvp-v2/issues/README.md`
- 협업 워크플로우: `docs/agent-workflow/README.md`

---

# 백엔드 아키텍처 (Backend Architecture)

> `poseLandmarker_Python/` — FastAPI 기반 동작 분석 백엔드

```mermaid
flowchart TD
    Client(["클라이언트 (Frontend / API)"])

    subgraph FastAPI ["⚡ FastAPI (uv)"]
        direction TB
        Router_A["POST /analysis/preview\n동기 분석 실행"]
        Router_J["POST /jobs\n비동기 잡 생성"]
        Router_JS["GET /jobs/{job_id}\n잡 상태 폴링"]
        Router_R["GET /jobs/{job_id}/result\n결과 조회"]
        JobMgr["JobManager\n파이프라인 오케스트레이션"]
    end

    subgraph OpenCV ["📹 OpenCV"]
        direction TB
        OcvAdapter["OpenCvAdapter\nVideoCapture 래퍼"]
        VideoReader["VideoReaderService\n프레임 샘플링 (target_fps)"]
    end

    subgraph MediaPipe ["🦴 MediaPipe"]
        direction TB
        MpAdapter["MediaPipeAdapter\nPoseLandmarker 래퍼\n(CPU / GPU delegate)"]
        PoseInfer["PoseInferenceService\n33개 랜드마크 추출\n& 직렬화"]
        SkeletonMapper["SkeletonMapperService\n랜드마크 → Skeleton JSON"]
    end

    subgraph Pipeline ["📊 데이터 분석 파이프라인"]
        direction TB
        Preprocess["analysis_preprocess\n프레임 정제 & 필터링"]
        BodyProfile["analysis_body_profile\n신체 프로필 추정\n(limb ratio, height)"]
        COP["analysis_cop\n촬영 시점 감지\n& 무게중심(CoP) 산출"]
        Features["analysis_features\n관절 각도 / 바 궤적\n시계열 특징 추출"]
        Reps["analysis_reps\n렙 구간 감지\n(descent / ascent)"]
        KPIs["analysis_kpis\nKPI 계산\n(ROM, bar_path_deviation 등)"]
        Thresholds["analysis_thresholds\n개인화 임계값 산출"]
        Events["analysis_events\n이벤트 감지\n(descent_start 등)"]
        Issues["analysis_issues\n자세 이슈 감지\n(knee_cave, forward_lean 등)"]
        Viz["analysis_visualization\n시각화 데이터 생성"]
        LLM["llm_feedback\nClaude API\n코치 피드백 생성"]
    end

    Client --> Router_A & Router_J & Router_JS & Router_R
    Router_A & Router_J --> JobMgr
    JobMgr --> VideoReader --> OcvAdapter
    JobMgr --> PoseInfer --> MpAdapter
    PoseInfer --> SkeletonMapper
    JobMgr --> Preprocess
    Preprocess --> BodyProfile --> COP --> Features
    Features --> Reps --> KPIs --> Thresholds
    KPIs --> Events
    KPIs & Thresholds --> Issues
    Issues --> Viz
    Issues --> LLM

    style FastAPI fill:#1e1e2e,stroke:#89b4fa,color:#cdd6f4,stroke-width:2px
    style OpenCV fill:#1e2e1e,stroke:#a6e3a1,color:#cdd6f4,stroke-width:2px
    style MediaPipe fill:#2e1e2e,stroke:#cba6f7,color:#cdd6f4,stroke-width:2px
    style Pipeline fill:#2e2e1e,stroke:#f9e2af,color:#cdd6f4,stroke-width:2px
    style Client fill:#313244,stroke:#89dceb,color:#cdd6f4,stroke-width:2px
```

---

## uv / FastAPI

> 패키지 관리(uv) + REST API 서버

```mermaid
flowchart LR
    subgraph Entry ["진입점"]
        Main["main.py\nuvicorn 실행"]
        AppPy["app.py\nFastAPI 앱 초기화\nCORS / GZip 미들웨어"]
    end

    subgraph Routers ["controller/"]
        R1["analysis.py\nPOST /analysis/preview"]
        R2["jobs.py\nPOST /jobs\nGET /jobs/{id}"]
        R3["results.py\nGET /jobs/{id}/result"]
        R4["health.py\nGET /health"]
    end

    subgraph Schema ["schema/ (Pydantic)"]
        S1["frame.py\nExtractedFrame\nFrameExtractionOptions"]
        S2["pose.py\nPoseInferenceOptions\nPoseLandmarkPoint"]
        S3["job.py\nJobCreateResponse\nJobStatusResponse"]
        S4["result.py\nMotionAnalysisResult\nMotionAnalysisSummary"]
    end

    Main --> AppPy --> Routers
    Routers --> Schema
```

| 파일 | 역할 |
| --- | --- |
| `main.py` | uvicorn 서버 진입점 |
| `app.py` | FastAPI 앱, CORS / GZip 미들웨어 등록 |
| `controller/analysis.py` | `POST /analysis/preview` — 동기 분석 실행 |
| `controller/jobs.py` | `POST /jobs` — 비동기 잡 생성, `GET /jobs/{id}` — 상태 폴링 |
| `controller/results.py` | `GET /jobs/{id}/result` — 최종 결과 조회 |
| `service/job_manager.py` | 전체 파이프라인 오케스트레이션 |
| `schema/` | Pydantic 요청/응답 모델 |
| `pyproject.toml` | uv 의존성 관리 (`fastapi`, `uvicorn`, `pydantic` 등) |

---

## OpenCV

> 비디오 프레임 추출 레이어

```mermaid
flowchart LR
    VideoFile["동영상 파일\n(.mp4 등)"]

    subgraph CV ["adapter/ + service/"]
        OcvAdapter["OpenCvAdapter\ncv2.VideoCapture 래퍼\n메타데이터 읽기 / 프레임 순회"]
        VideoReader["VideoReaderService\n샘플링 모드 결정\n(target_fps / all_frames)\n타임스탬프 계산"]
        ExtractedFrame["ExtractedFrame\nindex / timestamp_ms / image(ndarray)"]
    end

    VideoFile --> OcvAdapter --> VideoReader --> ExtractedFrame
```

| 파일 | 역할 |
| --- | --- |
| `adapter/opencv_adapter.py` | `cv2.VideoCapture` 래퍼, fps / 해상도 / 프레임 수 메타데이터 제공 |
| `service/video_reader.py` | 샘플링 모드(`target_fps` / `all_frames`)에 따른 프레임 필터링 및 `ExtractedFrame` 생성 |

---

## MediaPipe

> 포즈 추정(Pose Estimation) 레이어

```mermaid
flowchart LR
    Frames["ExtractedFrame 리스트\n(numpy ndarray)"]

    subgraph MP ["adapter/ + service/"]
        MpAdapter["MediaPipeAdapter\nPoseLandmarker 초기화\nCPU / GPU delegate 자동 선택\nmp.Image 변환"]
        PoseInfer["PoseInferenceService\n프레임별 추론 실행\n33개 랜드마크 (x, y, z, visibility)\n벤치마크 계측"]
        SkeletonMapper["SkeletonMapperService\nPoseFrameResult →\nSkeleton JSON 변환"]
    end

    Model[".task 모델 파일\n(lite / full / heavy)"]

    Frames --> PoseInfer
    Model --> MpAdapter
    MpAdapter --> PoseInfer --> SkeletonMapper
```

| 파일 | 역할 |
| --- | --- |
| `adapter/mediapipe_adapter.py` | `PoseLandmarker` 생성/해제, CPU·GPU delegate 자동 폴백, `mp.Image` 변환 |
| `service/pose_inference.py` | 프레임 배치 추론, 33개 랜드마크 직렬화, 추론 벤치마크 기록 |
| `service/skeleton_mapper.py` | 추론 결과를 분석 파이프라인이 소비하는 Skeleton JSON 포맷으로 변환 |

---

## 데이터 분석 파이프라인

> Skeleton JSON → 자세 분석 결과

```mermaid
flowchart TD
    Skeleton["Skeleton JSON\n(프레임별 랜드마크)"]

    subgraph Pipeline ["service/analysis_*"]
        Preprocess["analysis_preprocess\n이상 프레임 필터링\n가시성 기준 정제"]
        BodyProfile["analysis_body_profile\n팔다리 비율 추정\n신체 높이 추정"]
        COP["analysis_cop\n촬영 시점 분류 (정면/측면)\n무게중심(CoP) 시계열 산출"]
        Features["analysis_features\n관절 각도 계산\n바 궤적 추출\n시계열 특징 벡터 생성"]
        Reps["analysis_reps\n렙 구간 감지\n(descent / bottom / ascent)"]
        KPIs["analysis_kpis\nROM · bar_path_deviation\n· 좌우 대칭 등 KPI 계산"]
        Thresholds["analysis_thresholds\n신체 프로필 기반\n개인화 임계값 산출"]
        Events["analysis_events\n렙 구간별 이벤트 시점 추출"]
        Issues["analysis_issues\nknee_cave / forward_lean 등\n자세 이슈 감지"]
        Viz["analysis_visualization\n클라이언트용 시각화 데이터"]
        LLM["llm_feedback\nClaude API 호출\n강점 · 교정 · 코치 큐 생성"]
    end

    Result(["MotionAnalysisResult\n(summary / kpis / repSegments\n/ issues / visualization / llmFeedback)"])

    Skeleton --> Preprocess --> BodyProfile --> COP --> Features
    Features --> Reps --> KPIs --> Thresholds
    KPIs --> Events
    KPIs & Thresholds --> Issues --> Viz & LLM
    Viz & LLM --> Result

    style Preprocess fill:#313244,stroke:#89b4fa,color:#cdd6f4
    style BodyProfile fill:#313244,stroke:#89b4fa,color:#cdd6f4
    style COP fill:#313244,stroke:#89b4fa,color:#cdd6f4
    style Features fill:#313244,stroke:#a6e3a1,color:#cdd6f4
    style Reps fill:#313244,stroke:#a6e3a1,color:#cdd6f4
    style KPIs fill:#313244,stroke:#f9e2af,color:#cdd6f4
    style Thresholds fill:#313244,stroke:#f9e2af,color:#cdd6f4
    style Events fill:#313244,stroke:#fab387,color:#cdd6f4
    style Issues fill:#313244,stroke:#f38ba8,color:#cdd6f4
    style Viz fill:#313244,stroke:#cba6f7,color:#cdd6f4
    style LLM fill:#313244,stroke:#cba6f7,color:#cdd6f4
```

| 파일 | 역할 |
| --- | --- |
| `analysis_preprocess.py` | 가시성 임계값 이하 프레임 정제, 이상 프레임 마킹 |
| `analysis_body_profile.py` | 팔다리 비율 · 신체 높이 추정으로 개인 신체 프로필 생성 |
| `analysis_cop.py` | 촬영 시점 분류(정면/측면), 무게중심(CoP) 시계열 산출 |
| `analysis_features.py` | 관절 각도, 바 궤적, 좌우 대칭 등 시계열 특징 벡터 추출 |
| `analysis_reps.py` | 하강·최저점·상승 구간 감지, 렙 세그먼트 분리 |
| `analysis_kpis.py` | ROM, 바 경로 편차, 속도 등 핵심 KPI 계산 |
| `analysis_thresholds.py` | 신체 프로필 기반 개인화 자세 임계값 산출 |
| `analysis_events.py` | 렙 구간별 주요 이벤트 시점(descent_start 등) 추출 |
| `analysis_issues.py` | knee_cave, forward_lean 등 자세 이슈 판정 |
| `analysis_visualization.py` | 클라이언트용 시각화 오버레이 데이터 생성 |
| `llm_feedback.py` | Claude API 호출 → 강점 / 교정 / 코치 큐 생성 |
