# 직원용 Windows Setup과 콘솔 없는 시작

2026-11-11. 운영 Release를 변경하지 않는 시험용 설치 프로그램이다. 최종 제품 이름과 아이콘은 미확정이다.

## 구현과 배치

NSIS 3.13 Unicode를 사용한다. 무료 사용과 재배포가 가능하고, 일반 사용자 설치·한국어 UI·HKCU 등록·전용 제거 프로그램을 한 파일로 제공한다. 도구는 공식 SourceForge NSIS 프로젝트에서 받은 격리 ZIP이며 시스템 설치나 PATH 변경을 하지 않았다. [공식 다운로드](https://nsis.sourceforge.io/Download), [라이선스](https://nsis.sourceforge.io/Docs/AppendixI.html).

Setup 버전은 **0.1.1.2**이다. 관리형 제품 GUI와 서명된 seed는 기존 운영 **0.1.1** 원본 바이트를 유지한다. 안정 Bootstrap은 창/작업표시줄 연결과 콘솔 없는 시작을 위해 새로 빌드했다. 이 Bootstrap을 기존 운영 ZIP과 같은 산출물로 취급하지 않는다. 기존 `employee-bootstrap-0.1.1`이나 운영 카탈로그 자산은 교체하지 않았다. 최초 시험본 Setup 0.1.1.1도 이력으로 보존했다.

- 기본 프로그램 위치: `%USERPROFILE%\CGL`. 사용자가 설치 위치를 선택한다. 너무 깊은 경로는 기존 Windows 경로 예산 검사로 거부한다.
- 안정 시작점: `<설치 위치>\CGLBootstrap.exe`.
- 설치 관리 파일: `_internal`, `seed`, `launcher.ico`, `setup-shell.json`, `setup-state.json`, `Uninstall.exe`.
- 버전별 제품과 포인터: `<설치 위치>\launcher-home\store` 및 `launcher-home\current.json`.
- 회사 앱·설정·작업 데이터: 기존 `%LOCALAPPDATA%\SouthpawGames\ToolsLauncher`. 버전 폴더와 분리한다.
- 격리 시험의 `/DATA=<별도 경로>`는 회사 사용자 AppData를 사용하지 않기 위한 옵션이다. 기존 설치의 데이터 위치를 임의 변경하지 않는다.

시작 메뉴/선택적 바탕화면 바로가기는 안정 Bootstrap과 `--data-dir`를 가리킨다. 고정 AppUserModelID는 `SouthpawGames.ToolsLauncher`이다. 설치 표식이 있는 Bootstrap만 제품 창의 ID, 아이콘 및 재실행 명령을 같은 안정 경로로 설정한다. 자동 작업표시줄 고정은 하지 않는다. 버전 EXE를 직접 고정하지 않도록 별도 PC에서 실제 고정/재실행 결과를 확인해야 한다.

같은 설치를 기억하는 HKCU 설정과 설치 소유권 표식을 검증한다. 현재 버전 저장소와 포인터는 덮어쓰지 않는다. Bootstrap/running/update 잠금을 잡지 못하거나 실행 중인 소유 프로그램이 있으면 설치·제거를 중단한다. 강제 종료하지 않는다. 경로에 공백·한글이 있어도 인자를 분리해 전달한다. 복사/삭제 후 전체 관리 파일의 존재와 해시/제거 여부를 다시 검사한다.

제거는 manifest에 기록한 정적 시작 파일, 소유 바로가기와 Windows 제거 등록을 정리한다. 변경된 관리 파일이 있으면 안전하게 중단한다. 사용자가 대상을 바꾼 바로가기와 알 수 없는 파일은 삭제하지 않는다. **회사 앱 데이터뿐 아니라 `launcher-home` 버전 저장소, 소유권 표식과 위치 기억 설정도 보존**한다. 따라서 제거 후 프로그램 폴더가 완전히 비지는 않는다. 이는 재설치 시 이미 업데이트된 버전을 되돌리지 않기 위한 정책이다. 전체 저장소 삭제나 데이터 삭제 옵션은 이번에 만들지 않았다.

## 콘솔 발생 원인과 수정

기존 빌드 도구는 Bootstrap에 `--console`을 적용한다. 제품 GUI는 이미 `--windowed`이고, Bootstrap이 제품 및 작업자를 실행할 때는 `CREATE_NO_WINDOW`를 사용한다. 해당 경로에서 cmd/PowerShell/Windows Terminal 호출이나 `CREATE_NEW_CONSOLE`은 발견되지 않았다. 콘솔용 Bootstrap을 Explorer나 바로가기에서 시작하면 Windows가 콘솔 호스트를 제공할 수 있는 구조다. 사용자 화면의 당시 프로세스 트리는 없으므로 과거 창의 PID까지 확정한 것은 아니다.

Setup에 포함한 Bootstrap은 **`--windowed` / PE Subsystem 2**로 빌드한다. 제품 GUI도 Subsystem 2다. 자식 실행 옵션과 ready/confirmed/복구 프로토콜은 유지한다. [PyInstaller 공식 설명](https://www.pyinstaller.org/en/stable/usage.html).

표준 출력이 없는 빌드에서도 다음 파일을 유지한다.

- `launcher-home/bootstrap-runs/*.json`: 단계 및 종료/실패.
- `launcher-home/bootstrap-runs/*.worker.log`: 업데이트 작업자 출력.
- `launcher-home/sessions/*/{stdout,stderr}.log`: 관리형 제품 출력.
- `launcher-home/bootstrap-errors/*.json`: 초기화 단계 오류. 오류 대화상자에 기록 위치를 안내한다. 기록 자체가 실패하면 그 실패도 표시한다.

현재 서명된 GUI/seed를 수정하지 않았으므로 운영 카탈로그 서명, 최소 순번 4와 운영 키는 동일하다. 시험 순번 7을 운영 정책에 넣지 않았다.

## 이름 조사와 변경 영향

최종 이름이 결정되기 전 일괄 변경하지 않았다.

| 위치 | 현재 값 | 향후 변경 범위 |
|---|---|---|
| 설치 파일 | SouthpawToolsLauncherSetup.exe | 다운로드 이름/체크섬/인계 문서 |
| 설치 마법사/제거 목록 | Southpaw Tools Launcher | NSIS 표시 문자열/버전 리소스 |
| 시작 메뉴/바탕화면 | Southpaw Tools Launcher | 소유 바로가기 이행·기존 바로가기 정리 정책 |
| GUI 제목 | Southpaw Tools Launcher · v0.1.1 | GUI 소스, 새 제품 버전 빌드 및 서명 ZIP |
| 상단 브랜드/보조 문구 | SOUTHPAW / TOOLS / TEAM WORKSPACE | GUI 표시 문자열 |
| 작업표시줄 | 제품 창 + 안정 Bootstrap 재실행 정보 | 표시 이름·아이콘. AppUserModelID는 유지 권장 |
| 안정 시작 EXE | CGLBootstrap.exe | 변경하지 않는 것이 호환성 비용이 작음 |
| 관리형 EXE | CreativeGroupLauncher.exe | 현재 서명 메타데이터/시작 확인에서 검증하는 파일명 |
| 내부 app_id | creative-group-launcher | 유지 |

후보 중 `Southpaw 도구 관리자`는 설치·업데이트·버전 선택 용도가 직접 드러난다. `Southpaw 프로그램 관리자`는 명확하나 일반 Windows 프로그램 전체를 관리하는 것으로 오해할 수 있다. `Southpaw 제작 도구 허브`는 제작용 맥락이 좋지만 길다. `Southpaw Tools`는 짧으나 기능 설명이 적다. `Southpaw 도구 런처`는 실행 기능에 비중이 있다. 최종 선택은 사용자 결정 사항이다.

표시 이름만 먼저 통일하고 기존 EXE 이름과 AppUserModelID를 유지하는 안을 권한다. EXE 이름까지 바꾸려면 self_update/bootstrap의 경로 검증, launcher-package.json, 서명 카탈로그, receipt/current.json, seed, 시작 PID·해시 확인, Setup manifest/바로가기/제거를 함께 새 버전으로 이행해야 한다. 기존 signed seed를 직접 고치면 안 된다.

## 아이콘 준비

`packaging/windows/branding.json`에 기존 ICO와 추후 승인할 투명 PNG 위치를 분리해 둔다. PNG는 아직 null이며 새 이미지를 만들지 않았다. 현재 임시 아이콘은 `southpaw_tools/assets/bridge.ico`이며 내장 프레임은 16×15, 32×30, 64×59다. 최종 정사각형 16/32px 식별성이나 디자인 품질을 합격 처리하지 않았다.

Setup 빌드는 이 설정의 ICO를 Setup/제거, Bootstrap, `launcher.ico`, 바로가기와 작업표시줄에 공유한다. `tools.build_windows --product-icon <승인된.ico>`는 다음 정식 제품·Bootstrap 빌드의 PE 아이콘을 동일하게 지정할 수 있다. 기존 `--bootstrap-icon`도 유지한다. 현재 원본 서명 GUI EXE의 PE 리소스는 불변이므로 최종 아이콘을 바꾸려면 새 서명 제품 빌드가 필요하다. 투명 PNG는 추후 GUI 리소스로 사용할 입력 위치만 준비했으며 기존 GUI 자산을 몰래 바꾸지 않는다. 최종 ICO는 16/24/32/48/64/128/256px을 권장하고 작은 크기를 실제 화면에서 확인한다.

## 검증 및 한계

개발 PC 검증과 별도 PC 사용자 검증은 구분한다. `.test-results/setup-20261111`에 NSIS 빌드 로그, 전체 회귀, 실제 설치·재설치·제거, Shell 속성 및 관리형 GUI 시작/종료 기록을 보존한다. 개발 PC 검증은 별도 시험 등록명과 격리 데이터 경로를 쓴다. 제품 GUI는 포커스·키 입력·크기 변경 없이 최소 실행했다. 실제 창 존재/ready/confirmed/종료 코드와 PE Subsystem을 확인했다. 전체 화면 시각 검증이나 Windows Terminal의 다른 PID까지 부재를 입증한 것은 아니다.

별도 PC에서는 최종 Setup 바이트로 마법사/바로가기/작업표시줄 고정/GUI 표시/업데이트 재실행/제거/재설치를 확인해야 한다. 현재 운영 최신 0.1.1에서 가짜 신버전을 만들지 않는다. S7의 서로 다른 실제 시험 빌드 업데이트 성공과 새 Setup Bootstrap의 실제 업데이트 통합 시험을 동일한 결과로 표시하지 않는다. 원인 미확정 WinError 5는 별도 이슈로 유지한다.

### 최종 개발 PC 결과

- 기존 274개 + 신규 9개 = **283개 통과**, 실패/skip 0. 승인된 무해한 Windows Bootstrap 12개 포함. 최종 로그: `.test-results/setup-20261111/final-utf8.log`.
- 앞선 실행의 테스트 결과는 OK였으나 테스트가 UTF-8로 읽는 Python 자식 출력이 Windows 기본 인코딩이라 수집 스레드에 UnicodeDecodeError가 있었다. 이 로그를 지우지 않았다. 마지막 실행은 `PYTHONIOENCODING=utf-8`을 시험 프로세스와 자식에게만 지정해 출력 계약을 맞췄으며, 수집 스레드 오류도 없었다. 제품 소스/시스템 환경을 인코딩 때문에 바꾸지 않았다.
- Setup 0.1.1.2: 61,070,837바이트, SHA-256 `6cc8c09de1ff1664479c1f08ab4e4fe0ba90c7f267925b7ed78a2bde91f4faf7`.
- SHA256SUMS.txt: 98바이트, SHA-256 `cd4c272782da5f3f82862d4ab350745f10197c9fe37d261d7b3950028841115b`.
- 새 Bootstrap SHA-256: `f6edf4be390fdd118ca9809bd87c40e7be293989e93671f835a6d2993a3656df`, GUI용 Subsystem 2. 원본 서명 GUI EXE도 Subsystem 2이며 SHA-256 `bae7160629f4a2d5fc4b1eb39a764d263e96cc34b3cdb5b244dd2ff6e6549e8d`를 유지했다.
- 같은 payload/NSIS 스크립트에 별도 시험 등록명만 적용한 Setup으로 한글·공백 경로에서 실제 설치/재설치/제거/재설치를 검증했다. 충돌 바로가기와 실행 잠금은 종료 코드 1로 차단했다. 성공 단계는 0이었다. current.json, 합성 설정/작업 파일, 알 수 없는 메모, 서명 seed/설치 파일을 보존했다.
- 새 Bootstrap의 실제 원본 GUI 창/ready/confirmed/정상 종료 코드 0 확인. 해당 PID의 보이는 창은 Qt 창 하나였다. 별도 PC에서 시각적으로 콘솔 부재를 확인한 결과는 아니다. 보조 GUI 검사 스크립트의 str/Path 형식 오류를 보존하고, 동일 프로세스에 연결하여 검증/정상 종료를 마쳤다.
- 실제 Shell 창 속성의 AppID/안정 재실행 명령/아이콘과 `.lnk` AppID를 Windows API로 검사했다. 강제 고정이나 기존 업무 창 조작은 하지 않았다.
- 예상하지 못한 WinError 5는 이번 최종 실행에서 발생하지 않았다. 의도적 주입·실제 잠금 회귀 테스트는 유지했다.

시험 Release: [setup-trial-0.1.1.2](https://github.com/toast-source/creative-group-trial-releases/releases/tag/setup-trial-0.1.1.2). 정식 운영 배포가 아닌 Pre-release이며, Setup/체크섬 2개만 있다. GitHub API digest, Draft 재다운로드 및 공개 HTTPS/CDN 재다운로드 크기·SHA-256이 일치한다. 이전 시험본 0.1.1.1도 보존했다.

시험 Latest는 `trial-catalog-000007`, 운영 Latest는 `production-catalog-000004` 그대로다. 기존 시험/운영 Release의 ID·태그·상태·자산 ID/크기/digest를 게시 전후 대조했다. 제품 원본 ZIP은 기존 `605afa20380a80e4fb5646b7b714a424b0ab9257c81076edacd8aea4b942365d`를 검증해 사용했고 회사 ZIP/프로젝트는 수정하지 않았다. Git master/HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5`, 기존 미커밋 변경을 보존하며 stage/commit/push/remote 변경을 하지 않았다.

변경 파일은 `southpaw_tools/bootstrap.py`, 신규 `windows_shell.py`/`setup_support.py`, `tools/build_windows.py`, 신규 `build_setup.py`/`setup_guard.py`, `packaging/windows/setup.nsi`/`branding.json`, `tests/test_setup_support.py`, 이 문서다. 이전 설치/서명/회사 앱 엔진과 GUI 레이아웃을 재작성하지 않았다.

테스트 PC 인계 원문은 `.test-results/setup-20261111/CLIENT_HANDOFF.ko.md`와 위 시험 Release 본문에 있다. 별도 PC의 새 Setup 실사용 및 업데이트 시 콘솔·작업표시줄 유지 검증은 **미실시**다. 기존 S7 결과만으로 이 항목을 통과 처리하지 않는다.
