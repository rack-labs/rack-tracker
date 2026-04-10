# [chore] MVP v2 전환 전 저장소 정리
Parent: #<mvp-v2-umbrella-issue-number>

## 문서 관계

- 이 문서는 저장소 정리 작업의 관리 문서다.
- 정리 작업 중 생긴 운영 규칙 변경은 관련 workflow 문서와 함께 갱신한다.
- 상위 또는 하위 문서가 단독으로 앞서가지 않도록, 규칙 변경 시 관련 문서도 같은 변경에 포함한다.

## 요약
MVP v2 구현을 본격적으로 시작하기 전에 현재 저장소를 정리해서 유지 자산, 제거 대상, 보존 자산을 구분한다.
목표는 단순 삭제가 아니라 v2 작업 기준에 맞는 디렉터리 구조와 문서 진입점을 다시 세우고, 이후 구현 범위가 v1 문서와 자산으로 다시 흩어지지 않도록 기준선을 만드는 것이다.

## 목표
- MVP v1 관련 문서, 실험 산출물, 임시 파일, 중복 구조를 식별한다.
- v2 진행에 필요한 자산과 더 이상 유지하지 않을 자산을 구분한다.
- 즉시 제거가 어려운 항목은 archive 또는 별도 보존 경로로 분리하는 기준을 정한다.
- 문서 인덱스와 디렉터리 구조를 v2 기준으로 읽히게 정리한다.
- 후속 정리 작업이 필요하면 별도 하위 이슈로 분리할 수 있는 기준을 만든다.

## 범위
- 저장소 최상단 디렉터리와 하위 주요 폴더를 점검한다.
- `docs/` 내 v1 문서와 v2 문서의 경계를 명확히 한다.
- 실험 산출물, 임시 결과물, 더 이상 유지하지 않는 자료를 정리 대상 기준으로 분류한다.
- 유지, 제거, 이동, archive 대상에 대한 기준을 문서화한다.
- 정리 후에도 참조가 필요한 문서와 진입 문서를 보강한다.

## 제외 범위
- MVP v2 기능 구현 자체
- 구조 정리와 직접 관련 없는 리팩터링
- 성능 개선, UI polish, 알고리즘 개선 같은 제품 기능 작업
- 외부 서브모듈이나 third-party 자산의 대규모 교체

## 성공 조건
- 저장소 정리 기준이 식별되고 유지/제거/이동/보존으로 분류돼 있다.
- v2 진행에 불필요한 파일, 문서, 구조가 정리돼 있다.
- 문서 진입점과 디렉터리 구조가 v2 기준으로 읽히게 정리돼 있다.
- archive 또는 보존 대상은 별도 기준으로 추적 가능하게 남아 있다.
- 추가 정리가 필요한 영역은 후속 하위 이슈로 분리 가능한 상태다.

<details>
<summary>작업 로그</summary>

## docs: docs index and legacy path cleanup (#26)

### 작업 단위
- 문서 진입점 정리
- `docs` 단계 분리 명시
- `docs/mvp-v1` 내부 구 경로 참조 정리

### 반영 내용
- 루트 `README.md`를 갱신해 현재 저장소의 중심 작업이 `docs/mvp-v2/`에 있음을 명시했다.
- `docs/README.md`를 v1/v2 단계 기준 인덱스로 재작성했다.
- `docs/mvp-v2/README.md`와 `docs/mvp-v2/issues/README.md`를 보강해 v2 문서 진입 흐름을 정리했다.
- `docs/mvp-v1/README.md`를 재작성해 v1 문서 세트를 legacy reference로 명확히 분리했다.
- `docs/mvp-v1/` 내부에 남아 있던 구 경로 참조를 현재 경로 기준으로 정리했다.
  - `docs/features/...`
  - `docs/process/...`
  - `docs/planning/todo.md`

### 검증
- `docs/mvp-v1/`, `docs/mvp-v2/`, `README.md`를 대상으로 구 경로 패턴 검색을 수행했다.
- `docs/features/`, `docs/process/`, `docs/planning/todo.md` 같은 이전 문서 경로 참조가 활성 문서 트리에서 제거됐음을 확인했다.

### 메모
- 이 작업은 문서 진입점과 이동된 문서 경로 정합성 확보에 초점을 맞췄다.
- 기존 worktree에 이미 존재하던 더 넓은 이동/삭제 작업은 이 로그 단위에서 되돌리거나 재분류하지 않았다.

## repo: archive legacy MVP-v0 prototype (#26)

### 작업 단위
- 루트 레벨 legacy 프로토타입 디렉터리 정리
- 삭제 대신 archive 보존 경로 적용

### 반영 내용
- 저장소 루트의 `MVP-v0/`를 `archive/MVP-v0/`로 이동했다.
- `MVP-v0`는 최초 프로토타입 코드로 분류하고, 현재 MVP v2 활성 구현 경로에서 분리했다.
- 즉시 삭제 대신 archive 보존 경로를 사용해 과거 구현 비교 및 참고 가능성은 유지했다.

### 검증
- 루트 레벨에서 `MVP-v0/`가 제거되고 `archive/MVP-v0/` 경로가 생성된 상태를 확인했다.
- `git status --short` 기준으로 기존 `MVP-v0/` 경로는 삭제, `archive/` 경로는 신규 추가로 추적되는 상태를 확인했다.

### 메모
- 이 이동은 git history만으로 legacy 코드를 보존하는 대신, 현재 worktree 안에서도 명시적 보존 위치를 두기 위한 판단이다.
- 후속 정리에서도 삭제가 부담되는 비활성 자산은 동일하게 `archive/` 기준 적용 여부를 우선 검토한다.

## repo: add agent workflow rules file (#26)

### 작업 단위
- 저장소 로컬 에이전트 작업 규칙 문서 추가
- 사람용 `README.md`와 운영 규칙 문서 역할 분리

### 반영 내용
- 루트에 `AGENTS.md`를 추가해 에이전트가 우선 확인할 저장소 로컬 작업 규칙을 정리했다.
- 커밋 전에는 현재 작업에 해당하는 관리 문서를 먼저 갱신하도록 기준을 명시했다.
- 정리 작업에서는 삭제보다 `archive/` 우선, 구조 변경 전 추적 문서 확인 같은 공통 규칙을 함께 명시했다.

### 검증
- 루트 경로에 `AGENTS.md`가 생성된 상태를 확인했다.
- `README.md`는 사람용 진입 문서로 유지하고, 운영 규칙은 별도 파일로 분리된 상태다.

### 메모
- 이 문서는 시스템 프롬프트를 대체하는 파일이 아니라, 저장소 안에서 반복적으로 참조할 로컬 작업 규칙 문서다.
- 새 세션이나 다른 에이전트에서도 루트 문서를 확인하면 같은 규칙을 재사용할 수 있도록 의도를 분리했다.

## docs: generalize agent workflow docs for codex and claude (#26)

### 작업 단위
- 에이전트 공통 git 작업 문서 정리
- 루트 운영 규칙과 세부 git 절차 문서 연결 보강

### 반영 내용
- `AGENTS.md`에 git 작업 전 확인해야 할 협업 문서와 상위 git 규칙을 추가했다.
- `docs/mvp-v1/process/codex-commit-and-push-workflow.md`를 `docs/mvp-v1/process/agent-commit-and-push-workflow.md`로 일반화했다.
- 문서 제목과 본문에서 `Codex` 전용 표현을 제거하고, 코딩 에이전트 공통 규칙으로 재작성했다.
- `git-collaboration-convention.md` 내부 참조도 새 문서 경로로 정리했다.

### 검증
- 루트 `AGENTS.md`에서 공통 규칙과 세부 git 문서 경로가 함께 보이도록 정리된 상태를 확인했다.
- 기존 process 문서 참조가 `agent-commit-and-push-workflow.md` 경로를 가리키도록 갱신했다.

### 메모
- 상위 운영 규칙은 `AGENTS.md`, git 실행 세부는 process 문서로 역할을 분리했다.
- 특정 도구 이름이 문서 제목과 규칙 범위를 좁히지 않도록 공통 표현으로 통일했다.

## docs: change branch naming convention to issue-first format (#26)

### 작업 단위
- 브랜치 네이밍 규칙 변경
- 에이전트 상위 규칙과 git workflow 예시 동기화

### 반영 내용
- 브랜치 이름 형식을 `type/issue-number-short-description`에서 `issue-number-type-short-description`으로 변경했다.
- `git-collaboration-convention.md`의 브랜치 예시와 협업 workflow 예시를 새 형식으로 갱신했다.
- `agent-commit-and-push-workflow.md`의 push 예시와 `AGENTS.md`의 상위 git 규칙도 같은 형식으로 맞췄다.

### 검증
- process 문서에서 기존 슬래시 기반 브랜치 예시가 새 issue-first 형식으로 치환된 상태를 확인했다.
- 루트 `AGENTS.md`에서도 현재 브랜치 형식을 한 줄로 확인할 수 있게 반영했다.

### 메모
- 이번 변경으로 `26-chore-clean-up-repository-before-mvp-v2` 같은 브랜치 이름이 공식 규칙과 일치한다.
- `release/*`, `hotfix/*` 예시는 기존 별도 버전/긴급 브랜치 성격을 유지했다.

## docs: require issue-number placeholders before github issue creation (#26)

### 작업 단위
- GitHub issue 번호 placeholder 규칙 문서화
- 에이전트 운영 규칙과 git workflow 문서 동기화

### 반영 내용
- 실제 GitHub Issue 또는 PR 생성 전에는 번호를 추정하지 않고 `#<issue-number>` placeholder를 유지하도록 규칙을 추가했다.
- 브랜치명, 커밋 메시지, PR 제목/본문, 관리 문서 초안 모두 같은 원칙을 따르도록 `git-collaboration-convention.md`에 반영했다.
- `AGENTS.md`와 `agent-commit-and-push-workflow.md`에도 번호 추정 금지와 placeholder 유지 규칙을 추가했다.

### 검증
- 루트 운영 규칙, 협업 컨벤션, 에이전트 git workflow 문서에서 같은 placeholder 원칙이 보이도록 정리된 상태를 확인했다.
- `#<issue-number>`와 `<issue-number>-type-short-description` 형태의 placeholder 기준이 문서에 명시된 상태다.

### 메모
- 이 규칙은 git log나 과거 GitHub 기록만으로 다음 번호를 예측할 수 없다는 점을 운영 규칙으로 고정한 것이다.
- 실제 번호는 GitHub에서 Issue 또는 PR이 생성된 뒤에만 확정값으로 반영한다.

## docs: split agent workflow hub from detailed rule documents (#26)

### 작업 단위
- `AGENTS.md`를 에이전트 진입 허브로 축소
- 세부 규칙과 양식을 별도 문서로 분리

### 반영 내용
- 루트 `AGENTS.md`를 짧은 진입점 문서로 재작성하고, 상세 규칙은 `docs/agent-workflow/` 아래로 이동했다.
- `docs/agent-workflow/README.md`, `git-rules.md`, `documentation-rules.md`, `templates.md`를 추가해 세부 규칙과 양식을 분리했다.
- 관련 process 문서 상단에도 새 agent workflow 문서와의 관계를 명시했다.

### 검증
- 에이전트 시작 규칙은 `AGENTS.md`에 남고, 세부 git/문서/템플릿 규칙은 `docs/agent-workflow/` 아래에서 분리된 상태를 확인했다.
- 상위 허브 문서만 먼저 읽고, 필요한 세부 문서만 추가로 열 수 있는 구조가 됐다.

### 메모
- 목적은 에이전트 세션마다 동일한 장문 규칙을 반복해서 읽지 않게 하고, 필요한 규칙만 좁혀 읽게 만드는 것이다.
- 기존 process 문서는 인간과 에이전트가 함께 참고하는 저장소 규칙 문서로 유지한다.

## docs: add document relationship and sync rule headers (#26)

### 작업 단위
- 관련 workflow 문서 상단 관계 헤더 추가
- 문서 간 동기화 의무 명시

### 반영 내용
- `AGENTS.md`, `docs/agent-workflow/*`, `docs/mvp-v1/process/*`, 현재 cleanup 관리 문서 상단에 문서 관계와 동기화 규칙을 추가했다.
- 상위 문서와 하위 문서가 독단적으로 앞서가지 않도록, 규칙 변경 시 관련 문서도 같은 변경에 포함하라는 지침을 명시했다.

### 검증
- 각 관련 문서 상단에서 부모/자식/참조 문서와 함께 동기화 규칙이 보이도록 정리된 상태를 확인했다.
- 문서 역할과 갱신 책임이 문서 첫 부분에서 바로 드러나는 상태다.

### 메모
- 이 규칙은 문서 간 불일치를 줄이기 위한 운영 장치다.
- 이후 규칙 변경 작업은 단일 문서 수정으로 끝내지 않고 연결된 문서를 함께 갱신하는 기준으로 처리한다.

## docs: add workflow rule for github check and management document lookup (#26)

### 작업 범위
- 작업 시작 시 GitHub 이슈 확인 절차와 로컬 관리 문서 검색 절차 연결
- 상대경로 기준 문서 참조 규칙 추가

### 반영 내용
- `AGENTS.md`에 GitHub 이슈 확인 뒤 `docs/mvp-v2/issues/` 및 `docs/mvp-v2/issues/sub-issues/`에서 같은 작업의 관리 문서를 먼저 찾도록 규칙을 추가한다.
- `docs/agent-workflow/` 문서들에 작업 재개 시 기존 관리 문서를 우선 탐색하고 갱신 대상으로 삼는 절차를 추가한다.
- GitHub 조회나 이슈 생성이 불가능할 때는 그 제약을 명시하고 로컬 관리 문서 탐색으로 이어가도록 정리한다.
- 워크플로 문서와 관리 문서에서 절대경로 대신 저장소 루트 기준 상대경로만 사용하도록 기준을 명시한다.

### 검증
- `AGENTS.md`, `docs/agent-workflow/git-rules.md`, `docs/agent-workflow/documentation-rules.md`, `docs/agent-workflow/git-collaboration-convention.md`, `docs/agent-workflow/agent-commit-and-push-workflow.md`, `docs/agent-workflow/templates.md`를 읽어 같은 규칙이 반영되었는지 확인한다.
- 경로 예시가 `docs/mvp-v2/...` 형태의 상대경로로만 남아 있는지 확인한다.

### 메모
- 현재 작업 환경에서는 `gh` 명령을 사용할 수 없어 live issue 조회 자동화는 불가능했고, 해당 제약을 워크플로 예외로 함께 기록한다.

## repo: archive legacy poseLandmarker JavaScript prototype (#26)

### 작업 범위
- 루트 레벨 브라우저 실험 디렉터리 정리
- 현재 활성 구현 경로와 legacy JavaScript 시행착오 결과 분리

### 반영 내용
- 저장소 루트의 `poseLandmarker_JavaScript/`를 `archive/poseLandmarker_JavaScript/`로 이동했다.
- 이 디렉터리는 브라우저 기반 MediaPipe 실험 코드와 샘플 산출물 중심의 legacy 자산으로 판단하고, 현재 활성 구현 경로 목록에서 제외했다.
- 루트 `README.md`에서 활성 구현 경로 설명을 `poseLandmarker_Python/`, `MVP.v1/` 중심으로 정리하고, legacy 실험 자산은 `archive/` 아래에 둔다는 기준을 함께 명시했다.

### 검증
- 루트 레벨에서 `poseLandmarker_JavaScript/`가 제거되고 `archive/poseLandmarker_JavaScript/` 경로가 생성된 상태를 확인했다.
- 저장소 전역 문자열 검색 기준으로 루트 `README.md`의 활성 구현 경로 안내가 실제 구조와 일치하도록 갱신된 상태를 확인했다.

### 메모
- `docs/mvp-v1/` 아래의 과거 설계 문서들은 이 디렉터리를 브라우저 전제 legacy 경로로만 언급하고 있어, 현재 정리 판단과 충돌하지 않는다.
- 후속 cleanup에서는 `archive/` 아래에 남긴 실험 자산 중 재사용 가치가 낮은 샘플 결과물의 추가 분리 여부를 다시 판단한다.

</details>

## repo: remove inactive third_party forks and document vendor policy (#26)

### scope
- remove the inactive `third_party/mediapipe/` placeholder directory
- stop tracking `third_party/opencv/opencv-forked` as a submodule
- keep a lightweight `third_party/README.md` policy file instead of storing large forked source trees
- replace developer-specific absolute-path references in `poseLandmarker_Python/docs/architecture/architecture.md`

### changes
- deleted `.gitmodules` because the repository no longer keeps the OpenCV fork submodule
- added `docs/repository-layout/third-party-policy.md` to define when vendored external sources are allowed in this repository
- changed architecture references from repo-local or machine-local absolute paths to package-manager and upstream-source guidance
- aligned the documentation with the current runtime dependency model based on `opencv-python-headless` and `mediapipe`
- removed the now-empty `third_party/` placeholder directory instead of keeping a docs-only shell

### verification
- confirmed the only tracked `third_party` entry was the OpenCV submodule gitlink
- removed remaining `third_party/opencv` and `C:\src\mediapipe-forked` references from repository documents

### note
- if upstream internals need inspection again, re-clone OpenCV or MediaPipe outside this repository instead of reintroducing large long-lived forks by default

## docs: split dense MVP v1 mediapipe docs by role (#26)

### scope
- reorganize `docs/mvp-v1/features/mediapipe/` by document role instead of keeping all major files in one directory
- preserve legacy content while improving scanability and entry points
- update affected references after the move

### changes
- added `docs/mvp-v1/features/mediapipe/README.md` as a local index for the MediaPipe legacy docs set
- moved canonical reference docs into `docs/mvp-v1/features/mediapipe/core/`
- moved issue writeups into `docs/mvp-v1/features/mediapipe/issues/`
- split exploration notes into `docs/mvp-v1/features/mediapipe/exploration/cpp-worker/` and `docs/mvp-v1/features/mediapipe/exploration/windows-gpu/`
- updated document references and the helper script under `poseLandmarker_Python/read_docs.py`

### verification
- checked the new tree under `docs/mvp-v1/features/mediapipe/` after the move
- re-searched repository references to confirm the old top-level MediaPipe doc paths were no longer used as canonical targets

### note
- `docs/mvp-v1/features/opencv/` remains intentionally shallow for now because its file count is still small enough not to justify another split

## fix: correct mpv-v2 typo to mvp-v2 across repository (#26)

### scope
- rename `docs/mpv-v2/` directory to `docs/mvp-v2/`
- rename `mpv-v2-umbrella.md` to `mvp-v2-umbrella.md`
- replace all `mpv-v2` string references in 12 files

### changes
- renamed directory `docs/mpv-v2/` → `docs/mvp-v2/`
- renamed `docs/mvp-v2/issues/umbrella/mpv-v2-umbrella.md` → `mvp-v2-umbrella.md`
- updated references in: `README.md`, `AGENTS.md`, `docs/README.md`, `docs/mvp-v1/README.md`, `docs/agent-workflow/README.md`, `docs/agent-workflow/git-rules.md`, `docs/agent-workflow/git-collaboration-convention.md`, `docs/agent-workflow/agent-commit-and-push-workflow.md`, `docs/agent-workflow/documentation-rules.md`, `docs/agent-workflow/templates.md`, `docs/mvp-v2/issues/README.md`, `docs/mvp-v2/issues/sub-issues/26-chore-clean-up-repository-before-mvp-v2.md`

### verification
- confirmed no remaining `mpv-v2` matches across the repository after substitution

### note
- pure naming fix; no content or structural changes

## docs: add pre-execution workflow gate and management-doc check script (#26)

### scope
- promote the management-document check from a startup hint to a pre-edit execution gate
- block "small task" self-exceptions in the shared workflow wording
- add a local verification script that detects file changes without a matching management-document update

### changes
- strengthen `AGENTS.md` and `docs/agent-workflow/README.md` so startup order and pre-execution order are separated explicitly
- update `docs/agent-workflow/documentation-rules.md`, related git workflow docs, templates, and legacy mirrors with no-size-exception wording
- align `CLAUDE.md` with the same pre-execution gate language
- add a repository-local script and hook instructions for fast correction when file edits happen without a management-document change

### verification
- read the updated workflow docs to confirm the same gate and exception-ban wording appears consistently
- run the new management-document check script against the current worktree to confirm it reports the expected state

### note
- this change reduces workflow slippage structurally, but it still does not create a hard guarantee by prompt wording alone
- the script and hook path are meant to shorten correction loops when an agent misses the gate anyway

## docs: add pre-commit review gate to agent workflow (#26)

### scope
- add explicit pre-commit review gate rule for both Claude and Codex
- consolidate review gate into AGENTS.md so it applies to all agents
- remove Claude-only duplicate from CLAUDE.md

### changes
- added `## Pre-Commit Review Gate` section to `AGENTS.md`
- removed `## 커밋 전 검토 게이트` section from `CLAUDE.md` (superseded by AGENTS.md)
- added review gate and immediate-commit rules to Work Log Rule in `docs/agent-workflow/documentation-rules.md`

### verification
- confirmed review gate wording appears in AGENTS.md and documentation-rules.md
- confirmed CLAUDE.md no longer duplicates the rule

### note
- rule applies to both Claude Code and Codex via AGENTS.md
- documentation-rules.md retains the rule as detail-level reference

## 남은 후속 정리 후보
- 루트 레벨 legacy 디렉터리와 현재 활성 구현 디렉터리의 역할 재정의
- 실험 산출물 및 샘플 결과물의 archive 정책 수립
- 문서 외 실제 파일 자산의 유지/이동/보존 기준 정리
- v2 진행과 무관한 임시 자산 또는 중복 구조 추가 정리

## 비고
- 이 이슈의 1차 목표는 저장소를 완전히 비우는 것이 아니라 v2 진행을 방해하는 구조 혼선을 줄이는 것이다.
- 즉시 삭제가 위험한 항목은 우선 archive 또는 명시적 보존 대상으로 남기고, v2 진행 중 재판단한다.
- 공통 기준이나 범위 변경 사항은 umbrella 이슈에도 함께 반영한다.

## 참고 자료
- `docs/mvp-v2/issues/umbrella/mvp-v2-umbrella.md`
- `docs/mvp-v1/process/git-collaboration-convention.md`
- `docs/README.md`
