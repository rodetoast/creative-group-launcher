# Southpaw Tools Launcher 0.2.3 Bootstrap v4

2026-11-26 · 구현 기준 dca7897c2cdec30af638e2206f5516ef36ed902b

## 최소 변경

0.2.3에 포함되는 Bootstrap은 4세대 런타임 _cgl_b4, 작업 기록 .bootstrap-v4 및 서명 대상 bootstrap-v4.zip을 사용합니다. 기존 v2·v3 작업 기록은 읽기 전용으로 확인합니다. 진행 중이면 새 교체를 보류하고 구세대 기록의 세대·형식이 올바르지 않으면 교체를 중단합니다. 새 작업자가 기존 프로세스들의 종료를 확인하고 잠금을 확보한 뒤 다시 확인합니다.

기존 Rod 직접 설치와 Toast Bridge 홈 해석, 승인 거래, 서명 및 파일 해시 검증, 원자적 진입점 교체와 ready/confirmed 확인 절차를 사용합니다. 후보 서명 명세의 Rod·Bridge 허용 목록에는 Rod13·14·15에서 배포한 v3 SHA-256 b2a6bcc178c6da9ef8394d5f0b5eaa3f5a41d1bdad9aae7e294165ecf71a67f4를 넣었습니다. 경로별 공식 초기 진입점 및 공통 공식 v2 해시도 유지했습니다. 사용자의 기존 CGLBootstrap.exe 경로와 바로가기 인수를 유지하며, 실패하면 확인된 이전 EXE를 복원합니다. 동일 세대 실패 기록은 기존 정책에 따라 남겨 자동 재시도를 막습니다.

## 시험 후보

운영 0.2.2 GUI와 배포된 v3 EXE 원본 바이트로 시작했습니다. v2/v3 완료 기록과 기존 런타임은 과거 격리 Rod 검증 사본에서 복제했습니다. 시험 사본에만 별도 Ed25519 공개키를 고정하고 승인 GUI의 두 공개 신뢰 자료와 manifest를 다시 구성했습니다. 운영 서명키와 운영 카탈로그는 사용·변경하지 않았습니다. 합성 도구 v1/v2 ZIP은 기존 첫 v3 시험과 같은 바이트입니다. 빌드에서 사용한 0.2.3 버전 표기를 후속 기록 커밋의 소스와 프로젝트 메타데이터에도 반영했습니다.

| 시험 자산 | SHA-256 |
| --- | --- |
| 전체 묶음 Southpaw-workspace-v4-trial.zip (180,569,542바이트) | 34eb62953b45a62df5f2d86e7b2b0b121504888a2b5e35aebf905d9b4124cb26 |
| GUI 0.2.3 시험 ZIP | 09a6ec275e58a36fe6f3ec9b0260813bd82459b9adaae9c517614fc1b41cf0b5 |
| 새 v4 Bootstrap EXE | 66671ec5d219a7f1a781cba8c300551875f267ce525cf41cacc9e1bd9b17aba6 |

이 묶음은 개발 PC의 격리 재현용이며 운영 서명·배포에 사용하지 않습니다. 별도 화면 캡처, 실제 Desktop 링크나 작업 표시줄 고정 변경, Windows Setup 빌드는 이번 범위에 없습니다. [기존 최초 v3 시험 보관본](WORKSPACE_WINDOWS_HANDOFF.ko.md)

## 검증

- 관련 소스 시험 31개 통과. 명령은 python -B -m unittest tests.test_bootstrap_upgrade tests.test_bootstrap_diagnostics입니다.
- 개발 PC Windows에서 신규 프로그램·데이터 루트와 대체 Desktop 폴더를 사용했습니다. 실제 배포 v3 EXE의 관리형 GUI worker가 시험 0.2.3을 적용하고, 동일한 CGLBootstrap.exe 경로에서 v4가 ready/confirmed 및 committed에 도달했습니다. 구세대 기록·런타임과 시험 설정의 해시가 보존됐습니다.
- 중복 실행은 종료 코드 0으로 돌아왔고 새 GUI를 만들지 않았습니다. 현재 실행 또는 준비 중이라는 안내를 확인했습니다. 이 실행에서는 기존 창의 전경 전환 성공이 확인되지 않았습니다.
- Windows Shell로 시험 폴더의 동일 .lnk를 실행했습니다. GUI를 종료한 뒤에도 합성 도구 v1이 살아 있었고, 같은 링크로 v2를 시작했습니다. 링크와 고정 ICO의 해시 및 합성 도구 설정이 보존됐습니다. 실제 바탕화면·작업 표시줄의 아이콘 표시·고정·그룹화와 회사 도구 5개 실기동은 미검증입니다.
- 같은 후보의 별도 복제본에서 새 Bootstrap 시험 시작에만 Windows 파일 잠금으로 실패를 유도했습니다. 자동 복원이 원래 v3 EXE의 정확한 해시를 되돌렸고, 복원된 v3가 GUI 0.2.3을 다시 시작해 confirmed에 도달했습니다. 이전 기록·런타임·설정 등 기준 파일 186개 해시가 일치했습니다.
- 실제 Toast Bridge 설치의 v3→v4 전환과 공개 카탈로그의 온라인 업데이트 버튼은 이번 시험에 포함하지 않았습니다. Toast 홈 해석과 명세 허용 목록은 기존 계약을 재사용하며 관련 소스 시험을 통과했습니다.
