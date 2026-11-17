# Southpaw 도구 런처 0.1.3 최종 브랜딩 후보

2026-11-12. 사용자가 직접 여백을 잘라 교체한 최근 아이콘을 적용했다. 이전 0.1.2 빌드와 기록은 이력으로 보존한다. 운영 게시와 직원 배포는 하지 않았다.

## 이름과 아이콘

표시 이름은 `Southpaw 도구 런처`, 설명은 `사내 제작 도구 설치·실행·업데이트`다. 내부 app_id, AppUserModelID, CGLBootstrap.exe 및 CreativeGroupLauncher.exe 이름은 유지한다. GUI 제목/상단, 제품 메타데이터, Setup/제거 프로그램, 바로가기 표시 이름에 반영했다.

원본 PNG는 1032×1059 RGBA이며 SHA-256은 `5bc28e3b7832bb6aad1c4c3ae135f16f03bda46ec03f61b582cf9621552ce73c`다. 원본을 보존하고 정식 자산에 복사했다. 16/24/32/48/64/128/256px ICO는 비율을 유지하도록 투명 정사각형에 배치했다. ICO SHA-256은 `8b4a25cce9981b3b9d884577941ce3378ed06802923546a1bb0fbe0968a1b426`이다. PNG의 부분 투명 픽셀을 완전 투명 배경으로 취급하지 않았다.

실제 PE 6개의 GUI Subsystem과 이름·버전 리소스, ICO 7개 크기의 RGBA 일치를 검사했다. NSIS Modern UI의 기본 아이콘 덮어쓰기는 MUI_ICON/MUI_UNICON 지정으로 바로잡았다. Bootstrap과 런처는 콘솔 없는 빌드이며 파일 로그와 시작 확인은 유지한다.

## 산출물

시험 Setup: https://github.com/toast-source/creative-group-trial-releases/releases/tag/setup-trial-0.1.3.0

| 파일 | 바이트 | SHA-256 |
|---|---:|---|
| SouthpawToolsLauncherSetup.exe | 82881647 | db0b9bbf688c2c20303f3ced634b9df7cb537989bb94de904a526f7034443409 |
| SouthpawToolsLauncherUpgradeTrialSetup.exe | 83038384 | fb0d5ade77d4d92669c5f373efd66380a60c31b116749b4cb316148fa495f8a0 |
| SHA256SUMS.txt | 208 | 4089f69042eac98a4e3a3077b6f1a89d37aa0ea3aea5e5d64244e3b70a847c7b |

일반 Setup의 seed는 0.1.3이며 운영 저장소/최소 순번 4 정책을 사용한다. 운영용 자체 업데이트 ZIP은 52626739바이트, SHA-256 `8867eb1e4c8777f8aa05a141ecab9888c3cc613541f04b2ab55b5f18405c25e5`다. 신규 운영 카탈로그는 로컬 후보 순번 6이다. 이전 0.1.2 후보의 순번 5와 다른 바이트를 같은 순번으로 재사용하지 않는다. 운영 Latest는 여전히 production-catalog-000004다.

시험 업데이트 Setup은 실제 이전 빌드 0.1.2 seed와 최신 Bootstrap을 포함한다. 시험 Latest는 https://github.com/toast-source/creative-group-trial-releases/releases/tag/trial-catalog-000009 이며 순번 9다. 시험 ZIP은 52626843바이트, SHA-256 `09a7c32c60a8a07c28d3a1f8355886a786b2d27556e90ccdc2c7856c3235ea7b`다. 새 제품 EXE SHA-256은 `aaa3bec7bb5a1012943a64d2be50f4765abd0d86888c8bb103ffb3e34230a5f9`다. 시험 키와 운영 키/신뢰 상태는 분리했다.

## 검증과 한계

- 전체 287개 회귀 통과, 실패/skip 없음. 승인된 Bootstrap 12개 포함.
- 격리 등록 변형 Setup으로 한글 경로 설치, 실제 0.1.3 GUI 창 생성, 운영 카탈로그 읽기 전용 서명 확인, 정상 종료 코드 0을 확인했다. 실행 중 설치/제거 거부, 재설치, 정상 제거 및 합성 데이터/포인터 보존을 확인했다.
- 게시 자산 재다운로드, 크기/SHA-256, 카탈로그 Ed25519 서명 및 순번을 검증했다. 기존 시험/운영 Release와 자산 보존 비교도 통과했다.
- 이전 0.1.1→0.1.2의 실제 GUI 업데이트 결과는 별도 기록이다. 새 0.1.2→0.1.3 GUI 업데이트, 작업표시줄 고정 동작, DPI 192 화면, 실제 회사 앱 5개 설치 상태 보존은 테스트 PC에서 확인해야 한다. 개발 PC에서 이를 대신 통과했다고 주장하지 않는다.
- 이전 0.1.2 회귀 실행의 journal WinError 5 두 건은 보존했다. 이후 회귀 통과로 근본 원인 해결을 주장하지 않는다.
- 기존 회사 앱 ZIP/프로젝트, 사용자 AppData, 보안 정책을 변경하지 않았다. Git master/HEAD 32afb846d0bc69b38203a259dad71180cd4a14b5 유지, 기존 미커밋 변경 보존, stage/commit/push/remote 변경 없음.

검증 증거는 `.test-results/branding-013-20261112`의 full-tests.log, resource-verification.log, final-installed-branding.json, github/result.json 및 각 plan.json에 있다. 인계서는 같은 폴더의 CLIENT_HANDOFF.ko.md다. 내부 경로가 포함된 인계서 전체를 공개 Release 본문에 게시하는 작업은 자동 승인 검토에서 거절되어 실행하지 않았다. 인계서는 로컬로 제공한다.
