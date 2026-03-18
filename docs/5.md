[feature] 비디오 기반 스켈레톤 데이터 추출 기능 구현

feat: 비디오 기반 스켈레톤 데이터 추출 기능 구현 (#4)

- 비디오 업로드/선택, FPS 설정, 추출 실행 UI 추가
- MediaPipe PoseLandmarker 기반 프레임 단위 스켈레톤 추출 로직 구현
- 스켈레톤 오버레이 재생 및 JSON 다운로드 기능 추가

[feature] 비디오 기반 스켈레톤 데이터 추출 기능 구현 (#4)

## 관련 Issue
Closes #4

## 작업 내용
- 비디오 소스 선택, FPS 입력, 추출/재생/다운로드 버튼이 포함된 Video Skeleton Extractor UI를 추가했습니다.
- MediaPipe PoseLandmarker의 VIDEO 모드를 사용해 프레임 단위 스켈레톤 좌표를 추출하도록 구현했습니다.
- 추출 결과를 캔버스 오버레이로 재생하고 JSON 번들로 다운로드할 수 있도록 처리했습니다.

## 변경 사항 상세
- `index.html`에 video skeleton extractor 섹션과 비디오/캔버스 영역을 추가했습니다.
- `poseLandmarker/src/videoPose.js`에 비디오 메타데이터 로딩, seek 기반 프레임 추출, 스켈레톤 직렬화, 오버레이 렌더링 로직을 구현했습니다.
- `poseLandmarker/styles/main.css`에 비디오 추출 UI, 상태 버튼, 반응형 레이아웃 스타일을 추가했습니다.
- `poseLandmarker/src/main.js`에서 이미지 추출 버튼 선택자를 분리해 이미지/비디오 기능이 충돌하지 않도록 수정했습니다.

## 테스트 방법
1. `index.html`을 브라우저에서 실행합니다.
2. Video Skeleton Extractor 영역에서 `Extract Video Skeleton` 버튼을 클릭합니다.
3. 추출 완료 후 `Play Video + Skeleton`으로 오버레이 재생이 되는지 확인합니다.
4. `Download Skeleton JSON` 버튼 클릭 시 JSON 파일이 내려받아지는지 확인합니다.

## 스크린샷 / 결과
- `backSquat.mp4` 기준 스켈레톤 프레임 데이터 추출 및 JSON 번들 다운로드가 동작합니다.
