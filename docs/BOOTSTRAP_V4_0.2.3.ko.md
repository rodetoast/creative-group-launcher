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

## 운영 서명 후보 Rod16 (2026-11-26)

소스 5776e99024243d63a745242154e6d46c94e87ca0. v4 시험에서 실행한 GUI 및 Bootstrap EXE 바이트를 재사용했습니다. 두 바이너리의 외부 리소스에 Rod15에서 검증한 운영 공개 신뢰 정책을 적용하고 v4 교체 명세, 중첩 ZIP, GUI manifest를 다시 작성했습니다. 시험 공개키 및 합성 도구 데이터가 포함되지 않는지 확인했습니다. 새 제품 빌드나 Setup 제작은 없었습니다.

후보는 rodetoast/creative-group-releases (저장소 ID 1462539740)의 rodetoast-catalog-000016, 순번 16입니다. 현재 Rod Latest15 / Toast Latest9와 기존 자산을 대조했습니다. 아래 세 파일만 신규 바이트입니다. 회사 앱 5개 ZIP의 이름·크기·SHA-256·카탈로그 메타데이터가 Rod15와 일치합니다.

| 변경 자산 | 바이트 | SHA-256 |
| --- | --- | --- |
| creative-group-launcher--rodetoast-launcher-0.2.3.zip | 70,951,055 | f8af61ed21beec2382796e1bf10a51a59f1089cd9c8cfbfd4d02ca95c62f888e |
| catalog.json | 9,640 | 76162f84871fda7c41fde967bb1b165f3d7a0433576ed6747e6eea02643a82ed |
| catalog.sig.json | 239 | 28eb79ff8638a790b100c089cba58adce857b2a859b06a4a870804615791cb2f |

내부 v4 Bootstrap EXE SHA-256은 66671ec5d219a7f1a781cba8c300551875f267ce525cf41cacc9e1bd9b17aba6입니다. 서명된 manifest에 있는 초기 Rod·Toast 해시, 공통 v2, Rod13~15 공통 v3 해시를 확인했습니다. 기존 운영 Ed25519 서명으로 격리 상태에서 카탈로그 15 → 16 수락, 16 → 15 거부를 확인했습니다. Toast9 Bridge가 실제 번들에 고정한 Rod 저장소 ID와 서명 정책으로도 16을 수락했습니다. 회사 도구와 채널에 대한 Release 변경이나 게시를 실행하지 않았습니다.

### 최종 운영 바이트 검증

- **Rod 직접 설치**에서 실제 운영 v3 EXE와 Rod15 GUI를 격리 복제했습니다. 실제 구 Bootstrap worker가 서명된 GUI 0.2.3을 적용했고, 동일한 진입점에서 v4가 ready/confirmed 및 committed에 도달했습니다. 구세대 기록, 설치 기록 및 시험 설정을 포함한 기준 파일 187개의 해시가 유지됐습니다.
- **Toast Bridge 구조**를 Toast9 서명 Bridge 패키지의 바이트로 복원했습니다. 과거 v3 완료 기록의 테스트 토폴로지만 Bridge로 맞춰 바깥 진입점과 내부 Rod 홈을 검증했습니다. v4 committed와 정상 종료를 확인했으며, Toast 포인터·신뢰 상태 및 원래 하위 Rod 런타임을 포함한 기준 파일 337개가 유지됐습니다. 기존 Toast 설치에서 공개 채널을 따라 최초 Bridge에 진입하는 조작은 이번에 반복하지 않았습니다.
- **실제 운영 Pivot Fixer 0.3.3**을 관리형 설치한 상태에서 런처 업데이트를 적용했습니다. 설치 포인터와 영수증을 보존했고, 런처 GUI 종료 뒤 Windows Shell에서 시험 폴더의 .lnk를 사용해 서명 증거와 고정 ICO를 사용하는 실제 프로그램 창을 열었습니다. 호스트 연동은 실행하지 않았습니다.
- 새 운영 후보의 진입점 실패 복구는 같은 EXE의 이전 시험 서명 기반 복원 결과를 재사용했습니다. 실제 직원 바탕화면·전경 전환·작업 표시줄 그룹화와 공개 HTTPS 업데이트 버튼은 미검증입니다. 이 Windows 시험은 공개 전 운영 서명 후보를 대상으로 수행했습니다.

## 정식 운영 배포 Rod16 (2026-11-26)

사용자 승인으로 [rodetoast-catalog-000016](https://github.com/rodetoast/creative-group-releases/releases/tag/rodetoast-catalog-000016)을 공개하고 Rod Latest16으로 지정했습니다. 저장소 ID 1462539740, Release ID 458864111, 순번 16입니다. 승인 후보 계획 SHA-256은 8650493a9da12fb97bed5cd8962929ba6abe7e1741a7d813392df4b7da8b2051입니다.

- Draft와 공개 HTTPS에서 자산 8개를 각각 다시 다운로드하여 크기와 SHA-256, 운영 Ed25519 서명, GUI manifest 및 v4 중첩 ZIP의 전체 해시, 공식 초기·v2·v3 진입점 허용 목록과 Rod 신뢰 정책을 확인했습니다. 회사 도구 카탈로그 항목 5개와 ZIP 해시는 Rod15와 일치했습니다.
- Rod15 신뢰 상태로 초기화한 기존 업데이트 Provider에서 공개 Rod16을 조회하고 수락했습니다. Toast9 Bridge의 Rod 신뢰 정책과 최소 순번으로도 수락했으며 16 → 15 롤백은 차단됐습니다. 실제 Windows 교체·복원과 Pivot Fixer 링크 검증은 위에 기록한 기존 결과를 재사용했습니다. 정식 공개 자산을 직원 PC에서 적용하는 시험은 수행하지 않았습니다.
- 기존 Rod Release와 직원용 Setup 두 종류, Toast Latest9, 시험 Latest11 및 자산의 게시 전후 상태가 일치했습니다. 직원 PC나 설치 데이터에는 변경을 가하지 않았습니다.

[관리형 GUI 0.2.3 ZIP](https://github.com/rodetoast/creative-group-releases/releases/download/rodetoast-catalog-000016/creative-group-launcher--rodetoast-launcher-0.2.3.zip)
