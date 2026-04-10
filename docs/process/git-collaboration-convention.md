# Rack-Labs Git Collaboration Convention

## 1. Issue 규칙

Issue는 하나의 작업 단위(Task)를 의미한다.
모든 개발 작업은 반드시 Issue로 시작한다.

### Issue 제목 형식

[TYPE] 간단한 작업 설명

### Issue Type

| Type     | Description                     |
|----------|---------------------------------|
| feature  | 새로운 기능 개발                 |
| fix      | 버그 수정                        |
| refactor | 코드 구조 개선                   |
| docs     | 문서 작업                        |
| test     | 테스트 코드 작업                 |
| chore    | 설정 / 환경 / 사소한 작업        |
| ci       | CI/CD 관련 작업                  |
| perf     | 성능 개선                        |

### Issue 제목 예시

[feature] PoseLandmarker 초기 구현
[fix] video input 처리 오류 수정
[refactor] mediapipe 모듈 구조 분리

### Issue Description Template

## 작업 목적
이 작업이 왜 필요한지 설명

## 작업 내용
- 구현 또는 수정해야 할 항목
- 기능 또는 코드 변경 사항

## 완료 조건
- 작업이 완료되었다고 판단할 기준

## 참고 자료
관련 링크 / 문서 / 이슈



## 2. Branch Naming 규칙

브랜치 생성 위치

feature / fix / refactor / docs / test / chore / ci / perf
→ develop에서 생성

release
→ develop에서 생성

hotfix
→ main에서 생성


### 브랜치 이름 형식

type/issue-number-short-description

### 브랜치 이름 예시

feature/23-poselandmarker-init
feature/41-video-upload-api
fix/52-webcam-crash
refactor/33-mediapipe-module
docs/17-readme-update
test/29-pose-landmarker-test
ci/12-github-actions-build

release/1.0.0
hotfix/78-login-error



## 3. Commit Message 규칙

커밋 전에 반드시 아래 문서를 먼저 확인한다.

- `docs/process/codex-commit-and-push-workflow.md`

### 커밋 메시지 구조

type: 요약 설명 (#issue번호)

- 변경 내용 1
- 변경 내용 2
- 변경 내용 3

### Commit 예시

feat: PoseLandmarker 초기 구현 (#23)

- mediapipe poseLandmarker 로딩 로직 추가
- 이미지 기반 포즈 추출 기능 구현


fix: video input 처리 오류 수정 (#52)

- video element null 체크 추가
- detect loop 예외 처리 추가



### Commit Type

| Type     | Description                          |
|----------|--------------------------------------|
| feat     | 새로운 기능 추가                      |
| fix      | 버그 수정                             |
| docs     | 문서 수정                             |
| style    | 코드 포맷 수정                        |
| refactor | 기능 변화 없는 코드 구조 개선          |
| perf     | 성능 개선                             |
| test     | 테스트 코드                           |
| build    | 빌드 관련 수정                        |
| ci       | CI 설정 수정                          |
| chore    | 기타 작업                             |
| revert   | 이전 커밋 되돌리기                     |



## 4. Pull Request 규칙

### PR 대상 브랜치

feature / fix / refactor / docs / test
→ develop

release
→ main

hotfix
→ main


### PR Title 형식

[TYPE] 작업 요약 (#issue번호)

### PR Title 예시

[feature] PoseLandmarker 초기 구현 (#23)
[fix] webcam detection crash 수정 (#52)


### PR Description Template

## 관련 Issue
Closes #이슈번호

## 작업 내용
- 구현 또는 수정된 내용
- 주요 변경 사항

## 변경 사항 상세
- 코드 구조 변경
- 신규 모듈
- API 변경

## 테스트 방법
1. 실행 방법
2. 테스트 시나리오

## 스크린샷 / 결과
(선택 사항)



## 5. 협업 Workflow

1. Organization Repo에서 Issue 생성

2. Issue 기반 branch 생성
develop → feature/xx-xxx

3. 로컬 환경에서 작업

git fetch upstream
git checkout feature/xx-xxx

4. 작업 후 commit

commit 전에 아래 문서를 먼저 읽는다.

- `docs/process/git-collaboration-convention.md`
- `docs/process/codex-commit-and-push-workflow.md`

git add .
git commit

5. PR 전 최신 develop 반영

git fetch upstream
git merge upstream/develop

6. fork repository에 push

git push origin feature/xx-xxx

7. Pull Request 생성

origin feature/xx-xxx
→ upstream develop

8. Code Review 진행

Approve 또는 Comment

9. Merge

Squash Merge 권장

10. feature branch 삭제



## 6. Merge 규칙

PR 승인 최소 1명 이상 필요

Merge 방식
Squash and Merge 권장

Merge 완료 후
feature branch 삭제



## 7. 금지 사항

main 직접 push 금지
develop 직접 push 금지

반드시 Pull Request를 통해서만 merge

force push 금지
