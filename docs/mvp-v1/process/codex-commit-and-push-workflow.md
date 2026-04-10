# Codex Commit and Push Workflow

## 목적

Codex가 이 저장소에서 커밋, 푸시, PR 초안을 만들 때 따라야 하는 실행 지침이다.

## 커밋 전 필수 확인 순서

커밋 작업을 시작하면 아래 순서로 먼저 확인한다.

1. `docs/mvp-v1/process/git-collaboration-convention.md`를 읽는다.
2. 이 문서 `docs/mvp-v1/process/codex-commit-and-push-workflow.md`를 읽는다.
3. 현재 브랜치명, 변경 파일, 최근 커밋 메시지 형식을 확인한다.

## 커밋 메시지 작성 규칙

커밋 메시지 형식은 아래 규칙을 따른다.

`type: 요약 설명 (#issue번호)`

- 변경 내용 1
- 변경 내용 2
- 변경 내용 3

`type`은 반드시 `docs/mvp-v1/process/git-collaboration-convention.md`의 Commit Type 표를 따른다.

## Codex 커밋 실행 규칙

Codex는 이 저장소에서 `git commit -m ...` 방식으로 커밋을 시도하지 않는다.

이유:

- Windows `cmd` 환경에서 한글과 따옴표가 섞인 다중 `-m` 인자가 쉽게 깨질 수 있다.
- 협업 규칙상 본문 bullet을 포함한 커밋 메시지를 안정적으로 남겨야 한다.

항상 아래 순서로 처리한다.

1. 임시 커밋 메시지 파일을 작업 트리 바깥이 아닌 저장소 내부의 안전한 임시 파일명으로 만든다.
2. 제목과 본문 bullet을 그 파일에 작성한다.
3. `git commit -F <임시파일>`로 커밋한다.

예시 흐름:

```text
임시 메시지 파일 작성
-> git commit -F <temp-message-file>
-> 커밋 후 임시 파일 정리 여부 확인
```

## origin 푸시 구조

이 저장소에서 Codex가 푸시할 때 기본 구조는 아래와 같다.

1. 현재 체크아웃된 작업 브랜치를 확인한다.
2. 푸시 대상은 `origin`이다.
3. 브랜치 전체를 아래 형식으로 푸시한다.

```bash
git push origin <current-branch>
```

예시:

```bash
git push origin feature/8-feature-mediapipe-python-기반-백엔드-poselandmarker-구현
```

## PR 초안 작성 규칙

PR 제목은 아래 형식을 따른다.

`[TYPE] 작업 요약 (#issue번호)`

PR 본문은 `docs/mvp-v1/process/git-collaboration-convention.md`의 PR Description Template을 따른다.

기본 항목:

- `## 관련 Issue`
- `## 작업 내용`
- `## 변경 사항 상세`
- `## 테스트 방법`
- `## 스크린샷 / 결과`

## 작업 점검 항목

커밋 또는 푸시 요청을 받으면 아래를 함께 확인한다.

- 현재 브랜치가 규칙에 맞는지
- 최근 커밋 메시지 톤이 저장소 규칙과 맞는지
- 스테이징 대상이 요청 범위와 맞는지
- 푸시 대상이 `origin`인지
- PR 대상 브랜치가 `upstream develop`인지
