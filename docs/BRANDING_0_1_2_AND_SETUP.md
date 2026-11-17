# Southpaw 도구 런처 0.1.2 / Setup 0.1.2.0 시험 기록

빌드·전체 회귀: 2026-11-11. 실제 업데이트 후속 대조·종료·정리: 2026-11-12.

## 표시 이름과 호환성

직원용 창 제목과 상단 브랜드, QApplication 표시 이름, 작업표시줄 재실행 표시 이름, Setup/제거 마법사·Windows 제거 목록, 새 시작 메뉴/바탕화면 바로가기에 `Southpaw 도구 런처`를 적용했다. 설명은 `사내 제작 도구 설치·실행·업데이트`다. Qt의 표시 이름 자동 덧붙임으로 처음 발견한 중복 제목은 창 제목을 제품명으로 정리해 해결했고 버전은 기존 하단에 표시한다. 레이아웃과 다크 테마는 유지했다.

내부 app_id `creative-group-launcher`, AppUserModelID `SouthpawGames.ToolsLauncher`, `CGLBootstrap.exe`와 `CreativeGroupLauncher.exe` 파일명, 데이터 기본 위치는 유지한다. 새 관리형 제품은 실제 0.1.2이며 기존 서명 0.1.1 ZIP을 직접 고치지 않았다. Windows PE 버전 리소스의 ProductName/FileDescription도 공식 이름이다.

## 아이콘 입력과 변환

작업 시작 시 Downloads에서 해당 이름의 파일은 PNG 한 개였다. 최초 파일은 1254×1254 RGBA, SHA-256 `c3c28dad2dd1f1c9934525955acf53376b785544edf27d44aeaa6b829f93fd26`이다. 알파 범위 0~255, 완전 투명 픽셀 537,502개, 부분 알파 1,034,147개를 확인했다. 단순히 검은 배경 표시를 보고 투명하다고 판단하지 않았다.

정식 사본은 `southpaw_tools/assets/southpaw-launcher.png`이며 첫 입력과 바이트가 같다. `southpaw-launcher.ico`에는 16/24/32/48/64/128/256px 프레임이 있다. ICO SHA-256은 `a5e1a21f562a776d0e7c89039fb3daf7fc5bb55f249c44e70e77990ef828e8d9`다. 기존 이미지를 리샘플링·ICO 인코딩했으며 새 그림·배경 제거·불투명도 보정은 하지 않았다. 작은 프레임에서는 장식 디테일이 줄지만 보라색 바탕과 흰 주 표식은 구분된다.

NSIS Modern UI가 일반 Icon 설정 뒤에 기본 아이콘을 적용하는 문제를 실제 PE 검사로 발견해 `MUI_ICON`/`MUI_UNICON`으로 수정했다. [NSIS 공식 설정](https://nsis.sourceforge.io/Docs/Modern%20UI%202/Readme.html)을 따랐다. Setup·제거 프로그램·Bootstrap·제품 EXE의 실제 내장 이미지 일곱 프레임을 원본 ICO의 RGBA와 대조했다. 단순 launcher.ico 교체로 합격 처리하지 않았다.

**후속 원본 변경:** 2026-11-12 최종 대조에서 Downloads의 같은 이름 파일은 1032×1059, SHA-256 `5bc28e3b7832bb6aad1c4c3ae135f16f03bda46ec03f61b582cf9621552ce73c`로 바뀌어 있었다. 최초 사본과 픽셀도 다르다. 이 작업에서 Downloads 파일을 쓰거나 복원하지 않았으며 변경 주체는 확인하지 않았다. 게시된 0.1.2는 최초 입력 사본을 사용한다. 현재 파일을 최종 후보에 반영할지는 사용자 확인을 요청한 상태다. 기존 서명/시험 산출물을 조용히 덮어쓰지 않는다.

## 공개 시험본과 로컬 운영 후보

시험 카탈로그: [trial-catalog-000008](https://github.com/toast-source/creative-group-trial-releases/releases/tag/trial-catalog-000008). 시험 키와 sequence 8을 사용한다. 회사 앱 ZIP 다섯 개의 버전·release_id·크기·SHA-256과 메타데이터는 S7과 같다.

설치 프로그램: [setup-trial-0.1.2.0](https://github.com/toast-source/creative-group-trial-releases/releases/tag/setup-trial-0.1.2.0). Pre-release이며 시험 Latest에 영향을 주지 않는다.

| 파일 | 크기 | SHA-256 |
|---|---:|---|
| SouthpawToolsLauncherSetup.exe | 82,853,427 | 41e043cbf1c2cce200214a145ccfb295fe2477e24b629cabcc92f7cf8d1b9285 |
| SouthpawToolsLauncherUpgradeTrialSetup.exe | 61,484,914 | 44431417b1a729993897a14f474b897531145da153c4c9e4b5775ae6ce760112 |
| SHA256SUMS.txt | 208 | 05a0ba469d5777e2f419e56eb0d861c1349a51bd9d529051659fe1d92a8978d5 |

일반 Setup은 운영 연결/기존 운영 공개키/최소 순번 4와 실제 0.1.2 seed를 포함한다. 운영 후보 카탈로그 순번 5와 8개 자산은 로컬에만 준비했다. 운영 Latest는 여전히 production-catalog-000004다. 향후 순번 5를 사용할 때는 이 후보의 정확한 바이트를 재사용해야 하며 같은 순번의 다른 카탈로그를 만들면 이미 seed를 신뢰한 클라이언트의 재전송 방어에 걸린다.

업데이트 전용 Setup은 별도 시험 등록·시험 저장소/키를 사용하고, 기존 실제 S7 0.1.1 seed로 시작한다. 정상/시험 정책을 섞지 않는다. 두 채널의 EXE 코드 해시는 같을 수 있지만 정책 파일·릴리스 manifest·ZIP 해시·서명은 분리돼 있다.

## 개발 PC 실제 검증

- 일반 후보와 같은 payload/NSIS 코드의 별도 시험 등록본으로 한글·공백 경로 설치, 시작 메뉴 링크 대상/AppID, Windows 제거 등록 이름/버전, 실제 Uninstall.exe 아이콘/메타데이터를 검증했다.
- 실제 관리형 0.1.2 GUI의 시작·ready/confirmed, 공식 창 제목, 운영 카탈로그 읽기와 앱 5개 목록, 정상 종료를 확인했다. 회사 프로그램 EXE는 실행하지 않았다.
- 실행 잠금 중 설치/제거는 종료 코드 1로 차단했다. 재설치·제거·재설치와 합성 작업 파일·활성 포인터 보존이 통과했다.
- 실제 GUI 업데이트 버튼과 0.1.1→0.1.2 확인창을 확인했다. 도구의 모달 요소 캐시/포커스 오류가 있었으나 이후 실제 기록에 GUI 요청, 기존 PID 종료, 작업자 종료 코드 0, committed, 새 버전 health/normal ready·confirmed와 실제 새 PID가 남아 있음을 검증했다. 모의 성공 로그를 사용하지 않았다.
- 실제 업데이트 파일 188개를 원본 ZIP/receipt/서명 증거와 대조했다. 새 EXE SHA-256은 `c752b0e4b4e1d76b41e9806d5ca95d27ef29f6556addc5ad9297a6a8df504691`다. 기존 0.1.1 파일도 원본 증거와 일치한다.
- 설정과 앱 ID별 합성 작업 파일은 유지됐다. 개발 PC의 이 데이터에는 실제 회사 앱 다섯 개가 설치된 것은 아니므로 그 보존을 검증했다고 확대하지 않는다.
- 후속 점검의 제한된 프로세스 목록을 그대로 신뢰하지 않고 일반 사용자 네이티브 조회로 원래 GUI가 여전히 실행 중임을 확인했다. 중복 Bootstrap은 올바르게 차단됐고 오류 확인창을 닫았다. 그 후 기존 GUI/Bootstrap을 정상 종료(둘 다 0)하고 같은 Bootstrap 재실행에서 0.1.2 유지와 실제 공식 이름/설명/버전/목록을 확인했다.
- 구 seed 0.1.1 시험 Setup 재설치 후에도 current 0.1.2가 유지됐다. 정상 제거 방식으로 시작 파일·등록·Uninstall.exe 자체를 제거했고 설정·합성 작업 파일·버전 저장소/포인터는 보존했다. 마지막 GUI/Bootstrap 종료 코드도 모두 0이며 시험 프로세스 잔여는 없다.

PE Subsystem은 Bootstrap/GUI 모두 2이고 기존 CREATE_NO_WINDOW와 로그·복구를 유지했다. 개발 PC의 전체 화면/작업표시줄 고정/전환 중 콘솔 부재를 별도 PC의 실사용 확인과 동일하게 취급하지 않는다. 특히 실제 회사 앱 5개 설치 상태 보존, 시작 메뉴·바탕화면 클릭, 고정·재실행, DPI 192 시각 검증은 테스트 PC에 인계한다.

## 회귀와 남은 이슈

기존 283개 + 브랜딩 4개 = 최종 **287개 통과**, 실패/skip 0. 승인된 Bootstrap 12개 포함. 앞선 전체 실행에서는 기존 RecoveryTests 두 개의 journal os.replace에서 WinError 5가 발생했다. 각 한 번의 단독 재현은 통과했고 원인·잠금 주체는 미확정이다. 최종 통과가 근본 원인 해결을 의미하지 않는다. Installer/common에 추측성 수정, sleep, 무조건 재시도, 예외 무시나 skip을 추가하지 않았다.

이름/아이콘 적용과 별개로 Test PC 실사용 확인 및 현재 변경된 아이콘 입력의 선택이 남아 있다. 최종 운영 공개·직원 배포는 진행하지 않았다.

## 보존과 변경 파일

기존 운영/시험 Release·자산은 신규 두 Release 외에 변경하지 않았다. 기존 v0.1.1 ZIP `605afa...2365d`, Setup 0.1.1.2 `6cc8c0...4faf7`를 재확인했다. 원본 회사 ZIP·프로젝트, 운영 키, Windows 정책·ACL·방화벽·PATH는 변경하지 않았다. 기존 master/HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5`와 미커밋 변경을 보존했고 stage/commit/push/remote 변경은 없다.

이번 변경: `southpaw_tools/branding.py`, `__init__.py`, `__main__.py`, `ui.py`, `windows_shell.py`, `bootstrap.py`, 공식 PNG/ICO 사본, `tools/build_windows.py`, `build_setup.py`, `packaging/windows/branding.json`, `setup.nsi`, `pyproject.toml`, `tests/test_branding.py`와 이 문서. 빌드·재현·해시·GUI 인계 로그는 `.test-results/branding-012-20261111`에 보존한다.

인계 원문은 위 결과 폴더의 `CLIENT_HANDOFF.ko.md`다. 공개 Release 본문에 이 전문을 추가하는 요청은 자동 승인 심사가 로컬 경로·내부 시험 정보 공개를 이유로 거절하여 실행하지 않았다. 공개 다운로드와 로컬 문서로 인계하며, 이 추가 공개는 별도 승인 없이 다른 방법으로 재시도하지 않는다.
