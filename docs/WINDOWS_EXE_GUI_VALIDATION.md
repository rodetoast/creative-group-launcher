# 실제 Windows 제품 EXE 및 GUI 검증 — 2026-11-06

## 최종 결과

최종 제품 EXE는 개발 PC에서 실제 Windows qwindows GUI로 시작·표시·조작·종료했다. Qt offscreen 실행 결과와 구분한다. 제품 코드서명이나 보안 정책 변경은 하지 않았다.

- EXE: `.test-results/product-exe-gui-20261106/build-final/dist/CreativeGroupLauncher/CreativeGroupLauncher.exe`
- SHA-256: `eabaaeee8e01e59106c2cdb964e897af32a3faedcd8c084625dff4d06b597203`
- 형식: Windows x64, GUI subsystem, PyInstaller onedir, 번들 185개 파일. manifest와 파일별 해시 일치.
- Python 3.13.7 / PyInstaller 6.22.3 / hooks-contrib 2026.9 / PySide6·Qt 6.11.0 / cryptography 50.0.2.
- 기존 빌드와 현재 소스 5개가 달라 기존 빌드 도구로 새 격리 빌드를 생성했다. 이전 빌드·로그는 보존했다.

## 확인된 문제와 최소 수정

### 1. 최초 실제 실행의 QtCore DLL 오류

최초 빌드는 `ImportError: DLL load failed while importing QtCore: 지정된 프로시저를 찾을 수 없습니다`로 종료했다. 화면·stderr·실패 빌드를 보존했다.

PyInstaller Analysis-00.toc에서 ICU DLL 원본이 Codex 런타임의 Poppler 디렉터리임을 확인했다. 이 ICU 78 DLL에는 Qt가 요구하는 `UCNV_TO_U_CALLBACK_SUBSTITUTE` 등의 함수가 없었다. 정상 Python은 Windows System32 ICU를 사용했다.

`tools/build_windows.py`의 빌드 자식 프로세스 PATH만 System32·Windows·해당 Python과 Scripts로 제한했다. 사용자·시스템 PATH는 변경하지 않았다. 최종 번들에는 잘못된 ICU가 없으며 실제 제품 프로세스에서도 ICU는 System32, Python·Qt·qwindows는 시험 번들에서 로드됨을 확인했다. 단순 DLL 존재 검사만으로 성공을 판단하지 않았다.

초기 정적 분석에서 나온 Qt6Core export 누락 일부는 pefile 기본 8,192개 파싱 상한에 따른 오탐이었다. 이를 Qt 파일 불일치의 증거로 사용하지 않았다.

### 2. 최소 창 크기의 정보 패널 글자 잘림

980×700 논리 크기에서 정보 패널 라벨 높이가 필요한 높이보다 작아짐을 실제 화면과 Qt 측정으로 확인했다. 패널 내부 간격·항목 구분 간격만 2px로 줄였다. 화면 구조·엔진·기능은 유지했다. 글자 높이 회귀 테스트와 최종 실제 화면에서 개선을 확인했다.

## 실제 GUI 검증

- 실제 창 제목: `Southpaw Tools Launcher · v0.1.0`. 기존 브랜딩·다크 테마 유지.
- 다섯 프로그램 목록, 앱 아이콘·한국어 폰트·설명·릴리스 노트·버튼 표시 확인.
- 연결 설정 창에서 GitHub 저장소와 기존 LAN 입력의 상태를 확인하고 저장하지 않고 취소.
- AsepriteTagMaster의 배포 패키지 미확인·설치 비활성 유지.
- 기본 1240×820 및 최소 약 980×700 논리 크기, 현재 모니터 최대화 상태 확인. 긴 노트는 기존 스크롤 영역 사용.
- 실제 화면 캡처의 테두리 포함 크기는 기본 약 1243×851, 최소 약 983×731, 최대화 1440×2560. Qt 직접 저장 화면은 DPI 배율을 반영한 1860×1230이다.
- 빈 운영 신뢰키 상태로 실제 공개 r3를 조회했을 때 서명 검증 실패·알 수 없는 서명키 오류 표시, 설치 버튼 비활성 확인.
- 별도 격리 실행에서 존재하지 않는 시험 저장소를 읽기 전용으로 조회해 실제 HTTP 404 오류 안내 확인. 실제 인터넷 단절/DNS 장애 시험은 아니다.
- 최종 정상 저장소 실행 및 404 실행 모두 Alt+F4 정상 종료, 종료 코드 0. 최종 stdout/stderr 모두 비어 있음.
- 실제 제품/Dummy Tool 실행 버튼은 누르지 않았고 다른 프로그램 EXE를 실행하지 않았다.

실제 창 확인에는 computer-use:computer-use 스킬의 sky API를 사용했다. offscreen은 자동 회귀에만 사용했다. 창 전환 애니메이션 중 화면은 최종 증거로 채택하지 않았다.

## 격리와 종료 검사

기존 `--data-dir`를 사용해 실행별 시험 경로를 지정했다. 코드 확인 결과 Installer·신뢰 상태·설정은 이 경로에 전달된다. 실행 프로세스의 LOCALAPPDATA·APPDATA·TEMP/TMP·Qt 캐시도 시험 폴더로 지정했다. 부모/사용자/시스템 환경과 정책은 변경하지 않았다.

각 실행 전후 실제 `%LOCALAPPDATA%/SouthpawGames/ToolsLauncher` 존재 여부·전체 파일 해시 동일. AppData 전체를 파일 시스템 추적으로 감시한 결과는 아니며 명시 경로·프로세스 환경 격리와 기존 런처 데이터 보존을 확인한 결과다.

최종 잔여 제품 프로세스·창은 각각 0개다. 번들 185개 파일 모두 읽기 전용·공유 없음으로 열고 닫는 검사 통과. 최초 검사에서는 검사 코드의 pefile reader를 닫지 않아 EXE 자체에 오류32가 나왔다. 같은 프로세스에서 PE reader 열림/닫힘에 따라 오류32/성공을 확인하고 reader를 닫은 정확한 검사로 구분해 기록했다. 제품 잔여 잠금으로 판정하지 않았다. 파일 삭제·이동·외부 프로세스 강제 종료는 사용하지 않았다.

## 회귀 및 WinError 5

| 실행 | 결과 |
|---|---|
| 첫 전체 회귀 | 기존 233 + 빌드 환경 회귀 1 = 234개 중 233 통과, 오류 1, 실패·skip 0 |
| 정보 패널 수정 후 최종 회귀 | 기존 233 + 신규 2 = 235개 전부 통과, 오류·실패·skip 0 |
| Bootstrap 12개 | 최종 회귀에 포함, 기존 승인 빌드·해시로 모두 통과 |
| 실제 최종 제품 GUI | 정상 저장소·404 실행 모두 시작·표시·종료 코드 0 |

첫 회귀의 `test_installer.InstallerTests.test_cancelled_update_keeps_old` 최초 설치에서 `_phase(preparing) → atomic_json/atomic_bytes → os.replace`의 WinError 5가 재발했다. 임시 journal은 preparing, 대상은 download_verified였고 writer는 닫힌 상태였다. 예상하지 못한 오류 1건으로 기록했다. full/ 아래 실패 파일·스냅샷을 보존했다.

최종 회귀는 별도의 UI 수정 이후 실행했다. 첫 실패를 덮어쓰거나 통과할 때까지 반복하지 않았다. 최종 실행에서 예상 밖 WinError 5는 0건이며 의도적 잠금 주입 4건과 구분했다. 근본 원인은 여전히 미확정이다. sleep·무조건적 재시도·예외 무시·skip 추가 없음.

## 변경·보존

기존 파일 수정:

- `tools/build_windows.py`: 빌드 자식의 DLL 탐색 PATH 제한.
- `southpaw_tools/ui.py`: 정보 패널 내부 간격 축소.
- `tests/test_ui.py`: 최소 창에서 정보 글자 높이 회귀 추가.

신규:

- `tests/test_windows_build_environment.py`: 외부 DLL PATH 오염 방지·부모 환경 보존 회귀.
- `docs/WINDOWS_EXE_GUI_VALIDATION.md`: 이 보고서.
- `.test-results/product-exe-gui-20261106/`: 새 격리 빌드·실행 기록·화면·실패 증거·회귀·보존 검사. Git 제외 대상.

시작 시 기존 4,705개 파일을 기준으로 대조해 위 허용된 기존 파일 3개 외 변경 없음. 기존 미커밋 변경과 이전 시험 기록 보존. 다섯 프로젝트 292개 파일·Git HEAD·tag·상태, 실제 승인 ZIP 4개 동일. AsepriteTagMaster ZIP 미확인 유지. 운영 신뢰키는 소스·번들 모두 빈 상태이며 시험 키를 등록하지 않았다.

Git master / HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5` / remote 없음 / staging 없음. commit/push/remote 변경 없음. LAN 서버·방화벽·SAC·ACL·보안 정책 변경, 새 관리자 권한 획득 없음. 새 Release 생성·기존 Release 수정·삭제 없음.

## 증거와 남은 작업

`.test-results/product-exe-gui-20261106/`의 주요 자료:

- `final-build-checks-corrected.json`, `final-native-modules.json`
- `normal-final-process.json`, `missing-repository-process.json`
- `native-minimum-final.png`, `native-connection.png`, `native-http404.png`
- `full.log`, `full-result.json`, `final.log`, `final-result.json`
- `existing-projects-after.json`, `preservation-after.json`, `lock-probe-handle-diagnosis.json`

이 개발 PC에서의 실제 EXE 검증은 통과했다. 직원 배포 전에는 클린 Windows·DPI/해상도·SAC/제품 코드서명 환경 검증, 번들 의존성·라이선스 검토, 운영 신뢰키와 실제 프로그램 게시 승인, 제품 EXE와 Bootstrap 자체 업데이트 통합 검증이 남아 있다. 간헐적 WinError 5 원인도 남아 있다.

실제 직원 PC 배포·회사 프로그램 실행·운영 키 채택·다음 개발은 수행하지 않았다.
