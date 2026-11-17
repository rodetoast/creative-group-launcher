# Southpaw 도구 런처 0.1.4 UI·진단·Setup 후보

2026-11-12. 운영 저장소는 변경하지 않는다. 별도 PC의 0.1.3 자체 업데이트 성공 결과는 기준으로 재사용하며 회사 프로그램 내부 기능은 재시험하지 않는다.

## 직원 화면

사이드바는 작은 SOUTHPAW와 큰 도구 런처의 두 줄로 구성했다. 전체 제품 표시 이름과 창 제목은 Southpaw 도구 런처다. 기존 21px 제목 크기를 유지하고 좁은 폭에서 어절이 어색하게 나뉘는 문제를 없앴다. 기존 레이아웃·최소 980×700·테마를 유지한다.

일반 화면의 팀 승인 배포본 배지, 제목 아래 반복 설명, 하단 상시 설치 안내, 성공한 목록 조회의 장문 안내를 제거했다. 시험 모드의 테스트 배포본 구분은 유지했다. 연결 요약은 한 줄로 표시하고 저장소·서명·순번 검증 상태·조회 시각·간격은 툴팁 및 상세 정보 창으로 옮겼다. 오류/진행/설치·업데이트 상태와 주요 버튼은 유지한다.

프로그램 정보의 승인 버전 표시명은 최신 버전으로 바꾸고 세부 릴리스 ID는 기본 화면에서 숨겼다. 상세 정보에서 앱 ID·릴리스 ID·SHA-256·연결 상세·릴리스 노트 원문을 확인할 수 있다. 내부 데이터 키는 기존 테스트/호출 호환성을 유지한다. 이전 버전 선택 상태는 이전 버전 사용 중 · 업데이트 가능으로 요약한다.

릴리스 노트는 Qt Markdown으로 표시한다. 알려진 Build source commit 및 뒤따르는 커밋 해시는 기본 미리보기에서만 제외하며 서명된 원문과 상세 창의 내용은 바꾸지 않는다. HTML·링크 자동 이동·이미지/파일 리소스 로딩을 차단했다. QTextBrowser 훅만 차단하면 실제 로컬 이미지가 읽히는 경로를 실험으로 확인하여 QTextDocument 자체의 loadResource도 차단했다. 실제 존재하는 이미지의 document.resource 조회로 회귀를 검증한다. [Qt Markdown 기능 문서](https://doc.qt.io/qt-6.12/qtextdocument.html)

## CLI 진단

```powershell
python tools/launcher_diagnostics.py --data-dir <격리 데이터 폴더> --launcher-home <설치 폴더>\launcher-home --summary
python tools/launcher_diagnostics.py --data-dir <격리 데이터 폴더> --launcher-home <설치 폴더>\launcher-home --json
```

진단은 읽기 전용·오프라인이다. Qt 창, 설치/복구 엔진, 네트워크 요청을 시작하지 않는다. current.json, 앱별 active/receipt/journal, 보관된 카탈로그, Bootstrap 실행 단계·오류 유형·세션 확인 파일, Setup 제거 등록의 32/64비트 뷰를 읽는다. PID/생성 시각/이미지 신원 검사를 사용할 수 있을 때만 프로세스 상태를 판정한다. 설치 파일 전체 해시 검사나 건강 상태를 이 요약으로 대신하지 않는다.

GUI는 완료한 작업의 제한된 진단 스냅샷을 기록한다. 관리형 실행에서는 기존 sessions/<세션>/gui-status.json에 기록하므로 회사 앱 데이터 영역을 바꾸지 않는다. 비관리형 실행에서는 지정된 데이터 폴더의 diagnostics/gui-<PID>.json을 사용한다. 스냅샷은 작업 범주·성공/실패·시각만 보관하며 토큰·nonce·원문 오류·명령행을 복사하지 않는다. 진단 기록 실패는 상세 정보에 오류 유형으로 남기고 설치 결과를 바꾸지 않는다.

기존 버전에 조회 기록이 없다면 기록 없음으로 표시한다. 카탈로그 파일 수정 시각을 실제 네트워크 조회 시각으로 간주하지 않는다. 이전 정상 서명 캐시와 최근 조회 실패는 별도로 표시한다. 독립된 스크립트만 받은 PC에서도 기본 상태를 읽을 수 있지만, 기존 모듈/cryptography가 없으면 서명 및 업데이트 여부를 검증 불가로 표시한다. 이를 제품의 서명 실패나 성공으로 확대하지 않는다. 추가 Python/pip 설치는 필요하지 않다.

## Setup 제거 등록

기존 코드는 일반 사용자 HKCU Uninstall 경로, 64비트 뷰에 DisplayName/DisplayVersion/Publisher/InstallLocation/DisplayIcon/UninstallString/QuietUninstallString/NoModify/NoRepair를 기록했다. SystemComponent=1을 쓰는 코드는 없었다. 따라서 정적 코드만으로 별도 PC의 목록 비노출 원인을 확정할 수 없다. 등록 존재와 Windows 설정/제어판 실제 노출은 다르다.

이번 후보는 DisplayVersion을 숫자형 제품 버전으로 단순화하고 SetupVersion을 별도 값으로 분리했다. 자기 제거 키에만 SystemComponent=0과 실제 설치 디렉터리 기반 EstimatedSize를 명시했다. HKCU 사용자별 설치, 기존 제거 명령/소유권/잠금/데이터 보존 정책과 64비트 뷰는 유지한다. 시스템 정책이나 다른 앱의 키는 변경하지 않는다. [Microsoft 제거 등록 필드 설명](https://learn.microsoft.com/en-us/windows/win32/msi/uninstall-registry-key)

이 보완으로 Windows 목록 비노출의 근본 원인을 해결했다고 주장하지 않는다. 새 격리 Setup의 실제 등록 및 제거는 CLI로 확인하고, 목록 표시 자체는 테스트 PC에서 설치 직후·제거 전에 동일 Windows 사용자로 확인해야 한다. 표시 버전은 Setup의 seed 버전이며 자체 업데이트된 실제 버전은 current.json/실행 EXE가 기준이다.

기존 설치 선호 경로는 제거 후에도 보존하는 정책이다. 실제 기존 설치나 바로가기를 지워 새 시험을 강제하지 않는다. 별도 시험 등록의 IsolatedSetup으로 새 0.1.4 화면을 확인하고 UpgradeTrialSetup으로 실제 0.1.3→0.1.4 자체 업데이트를 확인한다. 정상 배포용 Setup과 동일 NSIS 로직을 사용하며 시험 등록/바로가기 소유권만 분리한다.

## 검증 판정

- 원래 287개 테스트를 보존하고 UI·진단 10개를 추가했다.
- 최종 소스 전체 297개 중 296개 통과, 오류 1개, skip 없음. Bootstrap 12개 및 신규 UI·진단 테스트는 통과했다.
- 오류는 test_catalog_signing.CatalogSigningTests.test_partial_publish_fails_closed_without_overwriting_old_catalog의 준비 단계에서 common.atomic_bytes → os.replace의 catalog.json 교체 WinError 5다. 이후 의도된 부분 게시 실패를 주입하기 전 발생했다. 로그를 보존했다.
- 같은 테스트를 파일 보존 조건으로 단 한 번 격리 실행했을 때는 통과했다. 이는 원인 확인/해결이나 전체 회귀 합격 증거가 아니다. 무조건 재시도·sleep·예외 무시·skip을 제품에 추가하지 않았다.
- 중간 회귀에서는 관리형 진단 파일이 사용자 데이터에 추가되는 문제가 발견돼 세션 폴더로 수정했다. 이전 실패 로그도 보존했다.
- 제한된 실행 환경의 loopback WinError 10013 및 NSIS 버전 조회 단계 WinError 623은 일반 사용자 실행 환경과 비교하여 구분했다. NSIS 같은 파일은 후자의 /VERSION에서 정상 동작했다. 관리자 권한이나 시스템 설정 변경은 사용하지 않았다.
- 100/150/200% Qt offscreen 배율에서 980×700 및 1240×820의 제목/버튼 글자 경계를 확인하고 이미지를 남겼다. 실제 모니터 DPI 시험과 구분한다. 이 작업에서 Windows Use는 사용하지 않았다.
- 실제 작업표시줄 고정 아이콘 클릭·재실행·자체 업데이트 후 재실행, Windows 설치된 앱 및 제어판 목록은 별도 PC에서 아직 확인해야 한다. AppUserModelID와 안정 Bootstrap 경로 및 바로가기 소유권 테스트를 이 실제 클릭 시험의 대체로 취급하지 않는다.

## 버전·배포·보존

제품 0.1.4 / Setup 0.1.4.0. 내부 app_id creative-group-launcher, AppUserModelID SouthpawGames.ToolsLauncher, CGLBootstrap.exe/CreativeGroupLauncher.exe는 유지한다. GUI는 콘솔 없는 PE 빌드를 유지한다. 회사 앱 5개 ZIP/릴리스 메타데이터는 변경하지 않는다.

새 시험 카탈로그 순번은 10, 운영용 로컬 후보 순번은 7이다. 기존 공개 Setup에 포함된 후보 순번을 다른 바이트에 재사용하지 않는다. 운영 서버 Latest production-catalog-000004와 기존 운영/시험 Release는 보존한다. 시험 후보는 전체 회귀 합격/직원 배포 승인본이 아니다.

증거 루트: .test-results/ui-diagnostics-014-20261112. 최종 패키지는 candidate 아래에 별도로 보존한다. full-tests-approved.log가 최종 전체 회귀이며 앞선 통과 실행으로 이 오류를 덮지 않는다. 공개 자산 해시는 candidate/github/result.json 및 CLIENT_HANDOFF.ko.md를 확인한다.

Git HEAD/branch/refs 보존 결과와 실제 게시 자산 검증 결과는 최종 산출물에 기록한다. stage/commit/push/remote 변경, 운영 GitHub 쓰기, 회사 프로그램 실행, 사용자 AppData 및 보안 설정 변경은 수행하지 않는다.

## 최종 산출물과 실제 확인

- [Setup 0.1.4.0 시험 자산 5개](https://github.com/toast-source/creative-group-trial-releases/releases/tag/setup-trial-0.1.4.0)
- [시험 Latest S10, 카탈로그 자산 8개](https://github.com/toast-source/creative-group-trial-releases/releases/tag/trial-catalog-000010)
- 자산별 바이트/SHA-256: .test-results/ui-diagnostics-014-20261112/ASSET_SHA256.ko.md. GitHub Draft 재다운로드·크기/해시/서명·게시 후 digest를 대조했다. Setup 5개와 카탈로그/서명은 공개 HTTPS에서 재다운로드했다.
- 실제 격리 등록 Setup의 설치 종료 코드 0, HKCU 32/64비트 양쪽 조회 결과 일치, DisplayName Southpaw 도구 런처, DisplayVersion 0.1.4, SystemComponent 0, EstimatedSize 90595KB, 올바른 자기 제거 EXE/ICO 경로를 확인했다. 제거 등록 정리와 합성 작업 파일 보존도 통과했다. 이 시험은 런처 GUI를 실행하지 않았다.
- 기존 운영/시험 Release 및 자산 비교가 통과했고 운영 Latest는 production-catalog-000004다. Git master/HEAD 32afb846d0bc69b38203a259dad71180cd4a14b5와 refs가 동일하다.
- Installer/Archive/Common/Provider/서명/Bootstrap/SelfUpdate/ManagedUpdate/WindowsShell/SetupSupport 런타임 파일은 0.1.3 빌드 스냅샷과 해시가 동일하다. 기존 원자적 교체/보호 로직을 바꾸지 않았다.

이번 변경 파일: southpaw_tools/ui.py, southpaw_tools/__init__.py, pyproject.toml, tools/build_setup.py, packaging/windows/setup.nsi, tools/launcher_diagnostics.py, tests/test_ui_cleanup.py, tests/test_diagnostics.py, tests/test_branding.py, tests/test_employee_settings.py, tests/test_testmode_safety.py, tests/test_local_versions.py, 이 보고서와 격리 증거/인계 문서. 기존 미커밋 작업 위에 필요한 수정만 적용했다.

남은 별도 PC 최소 항목은 실제 DPI 화면, 설치 직후 Windows 설치된 앱/제어판 노출, 시험용 고정 아이콘 직접 클릭/재실행, 실제 0.1.3→0.1.4 자체 업데이트 후 동일 고정 아이콘 재실행 및 앱/합성 데이터 보존이다. 목록 비노출 원인과 WinError 5는 미확정으로 유지한다. 이번 후보를 운영 공개하지 않는다.
