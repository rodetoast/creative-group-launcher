# Windows onedir 패키징과 Bootstrap 연결 보고서

2026-11-05. 격리 개발 프로필. 제품 EXE는 빌드/정적 검사만 했고 실행하지 않았다.
**신규 Windows 검증 12개는 통과했지만 전체 회귀는 journal WinError 5로 미통과다.**
운영 키·직원 배포·제품 GUI 연동 완료로 표시하지 않는다.

## 패키징 선택과 실제 도구

| 후보 | 판단 |
|---|---|
| PyInstaller onedir | 선택. EXE/DLL/리소스를 한 버전 폴더로 검증하고 보존하기 쉽다. 현재 버전별 포인터 구조와 맞는다. |
| PyInstaller onefile | 파일 전달은 간단하지만 시작 시 임시 추출과 프로세스/수명 처리가 추가된다. 이번 안정 Bootstrap에는 선택하지 않았다. |
| Python 소스와 별도 런타임 | 개발 시험에는 사용 가능하지만 직원 PC의 런타임/의존성 관리 부담이 남아 EXE 배포 구조로 선택하지 않았다. |

상용 유료 서비스나 설치 관리자를 추가하지 않았다. 라이선스 조건은 번들 의존성까지 별도로 유지해야 한다.
근거: [PyInstaller 동작 방식](https://pyinstaller.org/en/stable/operating-mode.html),
[옵션과 onedir 리소스](https://pyinstaller.org/en/stable/usage.html),
[공식 라이선스](https://pyinstaller.org/en/stable/license.html).

실제 Windows x64 Python 3.13.7, PySide6 6.11.0, cryptography 50.0.2,
PyInstaller 6.22.3, hooks-contrib 2026.9로 빌드했다.
기존 전역 PyInstaller 6.16.0/cryptography 46.0.3을 갱신하지 않고 ignored 빌드 의존성 경로를 사용했다.
빌드 의존성 버전은 packaging/requirements-build.txt에 고정했다.
생성 시 source hash·파일별 SHA256·도구 버전·로그·spec를 남긴다. 비트 단위 동일 빌드를 보장한다는 뜻은 아니다.
처음 추가 빌드에서 기존 JSON을 cp949로 읽는 오류를 발견해 UTF-8 명시로 수정했다. 원본 결과는 덮어쓰지 않았다.

## 산출물과 검사 수준

최종 파일 집합은 `.test-results/windows-packaging-20261105/verified-artifacts.local.json`이 기준이다.
이 파일은 빌드 중간 결과를 보존하면서 최종 Bootstrap과 제품 manifest 조립 결과를 가리킨다.

| 역할 | 결과 | 실행 여부 |
|---|---|---|
| CGLBootstrap.exe + _internal | 안정 영역 onedir, 75개 파일 | 격리된 시험 home에서 실제 실행 |
| CGLFixtureR1.exe + _internal | 무해한 시험 릴리스 1, 55개 파일 | 실제 실행 |
| CGLFixtureR2.exe + _internal | 무해한 시험 릴리스 2, 55개 파일 | 실제 실행 |
| CreativeGroupLauncher.exe + _internal + manifest | windowed 제품 onedir, 232개 파일 | 실행하지 않음 |

제품은 x64 PE/GUI subsystem, python313.dll, Qt6Core/Gui/Widgets, qwindows.dll,
cryptography _rust 네이티브 모듈, 카탈로그/빈 운영 신뢰키 정책/아이콘을 확인했다.
launcher-package.json은 배포 폴더의 전체 파일 해시를 포함하는 개발용 manifest다.
개발 release_id는 windows-dev-0.1.0이며 서명된 운영 게시물로 만들지 않았다.
정적 PE import 119개 네이티브 파일의 일반 import를 검사했고 현재 번들 또는 호스트 System32에서
찾지 못한 이름은 0개였다. delay-load, 실제 Qt 플러그인 초기화, 클린 Windows 실행을 확인한 것은 아니다.
제품 GUI 초기화 호환성까지 검증됐다고 주장하지 않는다.

## 안정 영역과 버전별 영역

```text
stable-bootstrap/                     버전 업데이트 대상으로 포함하지 않음
  CGLBootstrap.exe                    시작 역할과 별도 worker 역할을 같은 안정 EXE로 실행
  _internal/                         Bootstrap 전용 Python/cryptography/DLL

launcher-home/                        현재는 .test-results 전용
  current.json                       기존 활성 포인터
  layout.json / catalog-trust.json    기존 레이아웃과 고정 서명 신뢰 상태
  test-public-policy.json             시험용 공개키; 운영 키 아님
  windows-fixture-policy.json         실행 승인된 무해한 EXE의 해시만 허용
  locks/bootstrap.lock               중복 Bootstrap 차단
  locks/update.lock                  기존 준비/적용/복구 잠금
  locks/running.lock                 실제 실행된 정상 child가 평생 보유
  sessions/<id>/                     context/ready/confirmed/stopped/종료 요청/프로세스 신원
  probe-owner.json                   미완료 시작 검사 child의 PID/생성시각/이미지
  bootstrap-runs/<id>.json            단계별 실행 기록
  transactions/<id>.json              기존 자체 업데이트 journal
  store/apps/creative-group-launcher/releases/<release_id>/payload/
    <런처 EXE>
    _internal/
    launcher-package.json

user-data/                           프로그램 영역과 겹치지 않는 기존 AppPaths 영역
  settings.json / apps/<다섯 도구>/ 작업 파일
```

운영 경로 후보는 `%LOCALAPPDATA%\SouthpawGames\ToolsLauncherRuntime`의 안정/버전 영역과
기존 `%LOCALAPPDATA%\SouthpawGames\ToolsLauncher` 사용자 데이터다. 실제 AppData에 생성/이동하지 않았다.
시험 신뢰 상태는 버전 폴더 밖 launcher-home/catalog-trust.json에 고정한다.
운영 채택 때 일반 앱 카탈로그 캐시와 공유할지, 서명 정책/순번 수명과 함께 결정해야 한다.
네트워크가 제공한 키를 자동 채택하지 않는다.

현재 frozen 진입점에는 소스 프로젝트의 격리 시험 범위를 빌드 상수로 넣었다.
패키징 후 __file__ 위치가 _internal로 바뀌어도 기존 .test-results 보호를 해제하지 않기 위함이다.
이는 이동 가능한 직원용 운영 프로필이 아니다. 운영 경로/키 채택은 별도 승인과 설계 검토가 필요하다.
관련 근거: [PyInstaller 런타임 파일 위치](https://pyinstaller.org/en/stable/runtime-information.html).

## 실제 실행 관계와 생명주기

1. Bootstrap은 bootstrap.lock을 획득하고 기존 복구 함수로 미완료 전환을 확인한다.
2. update.lock 아래 current/receipt/manifest/실제 해시를 검증하고 실행 승인된 시험 EXE인지 검사한다.
3. 해당 버전 EXE를 절대 경로·정확한 cwd·shell 없이 생성한다.
4. 정상 child는 running.lock을 획득한 뒤 current와 자기 이미지 해시/내장 릴리스를 확인한다.
5. Bootstrap은 ready/confirmed와 실제 프로세스 신원을 확인한 뒤 update.lock을 해제한다.
   실제 child가 running.lock을 계속 보유하므로 Bootstrap만 죽어도 다른 업데이트가 실행 중 파일을 전환하지 못한다.
6. 사용자가 이미 승인한 requested journal이 있는 경우에만 정상 child에 업데이트 종료 요청을 보낸다.
7. child가 종료 요청 증거를 남기고 exit 20으로 완전히 종료한 것을 wait로 확인한다.
8. 그 후 별도 CGLBootstrap.exe worker 프로세스를 시작한다. 실행 중 child를 강제 종료하지 않는다.
9. worker는 WindowsUpdater(SelfUpdater의 얇은 어댑터)로 기존 apply를 호출한다.
10. 실제 새 시험 EXE 시작 확인이 끝나면 기존 journal을 committed로 확정한다.
11. Bootstrap은 새 current를 다시 검증해 새 버전의 정상 프로세스를 실행한다.
12. 적용 실패가 복구됐다면 이전 버전을 한 번 실행하고, 전체 결과는 exit 2로 실패를 구분한다. 자동 업데이트 재시도는 없다.

기존 self_update.py와 self_update_worker.py는 수정하지 않았다.
다운로드/서명/ZIP/버전 비교/포인터/journal/복구는 기존 구현이고, Python 더미 probe만 실제 EXE 세션으로 대체했다.
업데이트 EXE를 덮어쓰지 않으며 Bootstrap 및 안정 worker 파일도 자체 업데이트하지 않는다.
안정 영역 손상 시 신뢰된 별도 배포물로의 재설치/복구가 필요하다. Bootstrap 자체 업데이트는 미구현이다.

## Windows 프로세스 시작 확인

실제 Popen PID와 OpenProcess/QueryFullProcessImageName/GetProcessTimes로 이미지 경로·생성 시각을 확인한다.
PID 재사용은 이미지·생성 시각이 달라 기존 프로세스로 취급하지 않는다. 조회 실패는 종료로 추정하지 않는다.
ready와 confirmed는 세션 ID·nonce·실제 PID·릴리스 ID·버전·EXE SHA256·단계가 모두 같아야 한다.
시험 EXE의 릴리스와 버전은 빌드 진입점에 내장하며 단순히 서버 주장을 그대로 응답하지 않는다.
health 세션의 nonce는 기존 업데이트 journal의 해당 트랜잭션 nonce를 재사용한다.
제한 시간은 monotonic 기준이며 응답 불일치·시간 초과·즉시 종료를 실패로 처리한다.

CreateProcess 성공이나 ready 파일 하나만으로 정상 시작을 확정하지 않는다.
두 단계 응답 후에도 프로세스가 살아 있어야 하며 health 모드는 정상 stop 요청/응답과 exit 0까지 확인한다.
적용 확정 뒤 실제 정상 모드 새 버전을 별도로 시작해 실행 생명주기를 다시 확인한다.
health 프로세스가 남으면 PID/생성시각/이미지 기록으로 포인터 복구를 차단한다.
정상 종료를 확인할 수 없으면 강제 종료하거나 무작정 이전 버전으로 전환하지 않는다.

이는 무해한 Windows 시험 EXE의 시작 프로토콜이다. 제품 QApplication/창/리소스 초기화 성공 신호는 아직 연결하지 않았다.
이번 fixture는 버전마다 EXE 이름도 다르다. 실제 제품 파일명·동일 이름의 버전 폴더·GUI 인계를 별도로 확인해야 한다.
Bootstrap/fixture는 콘솔형 시험 프로필이지만 CREATE_NO_WINDOW로 시험한다. 제품은 windowed 빌드다.
직원용 Bootstrap의 오류 표시 UX도 운영 전 검토가 필요하다.

## 검증 결과와 WinError 5

신규 실제 Windows 검증 12개는 두 전체 실행에서 모두 통과했다:
빌드 파일/DLL/리소스, frozen Bootstrap 선택/정상 종료, 구버전 종료→worker→신버전 실행,
running.lock, 중복 Bootstrap/적용, 응답 nonce/내장 릴리스 불일치, 시간 초과, 즉시 종료,
실패 후 이전 버전 실제 재시작, 남은 health 프로세스 신원 확인, 제품 EXE 실행 차단.
제품 manifest 조립 후 정적 구성 시험 1개도 다시 통과했다.

**전체 회귀는 통과하지 않았다.** 기존 149개는 제거/수정하지 않았다.

| 실행 | 결과 |
|---|---|
| 첫 전체 실행 | 161개 중 159개 통과, 기존 자체 업데이트 준비 시험 2개 오류, 92.772초 |
| 한 번의 제한적 재확인 | 161개 중 160개 통과, 기존 journal 공유 시험 1개 오류, 91.444초 |
| 신규 native 12개 | 두 실행 모두 12개 통과, 건너뜀 없음 |

오류는 기존 installer._phase → common.atomic_json/atomic_bytes → os.replace에서 journal JSON 교체 시 WinError 5다.
첫 실행은 activating/preparing에서 발생했고, 재확인은 의도적 잠금 해제 후 명시 재설치 단계에서 재발했다.
실제 새 Windows EXE 검증 단계에서 발생한 오류는 아니다. 잠금 주체와 실제 원인은 미확인이다.
기존 엔진/파일 잠금 정책은 수정하지 않았고 sleep·자동 재시도·보안 설정 변경을 추가하지 않았다.
추가 전체 회귀 재실행은 중단했다. 기존 간헐적 WinError 5를 해결한 것으로 표시하지 않는다.

첫 실행의 원본 격리 폴더는 기존 unittest cleanup으로 정리돼 로그/traceback만 남아 있다.
재확인은 cleanup 전에 파일을 복사해 failure-snapshots/346e49883955627f6a6e에 보존했다.
이는 엔진 자체 복구가 실행된 뒤의 사본이며, 실패 순간 journal 원본을 모두 확보한 것은 아니다.
사본에서 활성 r1·receipt·Dummy.exe/asset.json 해시는 일치했고 transaction JSON은 없었다.
원본/사본을 복구 시험에 다시 사용하거나 수정하지 않았다. 전체 회귀 게이트는 계속 미통과다.

별도 native-evidence.local.json에는 실제 성공(r1→r2, committed, exit 0)과
새 EXE nonce 실패(이전 r1 재시작, rolled_back, exit 2)를 기록했다.
관련 프로그램/세션/worker 로그/확인 응답은 e/n과 e/f에 보존했다.
두 시나리오 모두 시험 사용자 데이터와 다른 앱의 설치 정보 해시는 유지됐다.

SAC 상태는 읽기 전용 조회에서 0이었고 시험 EXE 차단은 관측되지 않았다.
정책을 끄거나 Unblock-File/ACL/실행 정책/관리자 실행으로 우회하지 않았다.
실제 제품 EXE, 직원 PC, 운영 키, LAN 서버/방화벽은 사용하지 않았다.

## 재현 가능한 개발 빌드/테스트

Windows x64 Python 3.13 가상환경에 requirements.txt와 packaging/requirements-build.txt를 설치한다.
이번에는 기존 전역 환경을 유지하고 .test-results의 빌드/cryptography 의존성을 사용했다.

```powershell
python -B -m tools.build_windows --root .test-results/windows-build-new --roles fixture-r1 fixture-r2 launcher bootstrap
$env:CGL_WINDOWS_ARTIFACTS = (Resolve-Path '.test-results/windows-build-new/artifacts.json').Path
$env:QT_QPA_PLATFORM = 'offscreen'
python -B -m unittest discover -s tests -v
```

빌드 루트는 새 경로만 사용한다. 기존 역할별 출력과 spec/log는 덮어쓰지 않는다.
사용자에게 제품 EXE 실행을 요구하는 명령은 포함하지 않는다.
환경변수가 없으면 native 시험은 명시적으로 건너뛴다. 이번 기록은 실제 artifact를 지정해 실행한 결과다.
SAC/실행 제어 차단 코드가 나오면 native 시험은 추가 실행을 멈추며 우회하지 않는다.
제품 명령행/GUI 실행 승인은 별도로 받아야 한다.

## 변경 파일과 운영 전 남은 작업

추가: southpaw_tools/bootstrap.py, runtime_protocol.py, windows_process.py,
tools/build_windows.py, packaging/requirements-build.txt,
tests/windows_bootstrap_support.py, tests/test_windows_bootstrap.py, 이 보고서.
README 안내를 추가한다. 기존 실행/설치/게시/서명/self_update 엔진은 그대로 보존한다.

운영 전 필수 항목은 journal WinError 5 원인 조사와 전체 회귀 통과,
제품 GUI 준비 완료 신호·정상 종료/취소·사용자 업데이트 확인 연결,
실제 제품 EXE 실행 승인 및 동일 파일명/DLL/Qt·클린 Windows·배율 검증,
고정 운영 경로·공개키·최소 순번·키 교체·Bootstrap 별도 복구/배포 방식 승인이다.
Bootstrap/worker 자체 업데이트, 운영 키 적용, 실제 직원 배포를 자동 진행하지 않는다.

## 최종 보존 및 Git 확인

- 기존 다섯 프로젝트 292개 파일과 HEAD/tags/status 동일.
- 존재하는 원본 승인 ZIP 4개 해시 동일. AsepriteTagMaster 승인 ZIP은 기존과 같이 없어 미확인이다.
- 이전 LAN·서명·GUI·자체 업데이트 시험 증거 및 distribution 기준 파일 1,072개 해시 동일.
- 기존 self_update.py/self_update_worker.py와 설치·게시·서명 엔진은 변경하지 않았다.
- 이번 수정은 README 안내와 위에 명시한 새 파일뿐이다. 이전 미커밋 변경을 보존했다.
- master / HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5`, remote 없음.
  stage/commit/push/remote 변경 없음.
- 최종 읽기 전용 조회: 관리자 False, 8765 리스너 0개, 시험 규칙 0개,
  이번 Bootstrap/시험/제품 EXE 이름의 잔여 프로세스 0개.
- 최종 frozen 파일 집합의 모든 해시를 대조했다. 제품 실행 여부는 False다.
- Windows Use 미사용. 실제 사용자 AppData·직원 PC·다섯 앱 설치 데이터·운영 키를 변경하지 않았다.

세부 증거는 `.test-results/windows-packaging-20261105`의 FINAL_VERIFICATION.local.json,
existing-projects-verification.local.json, verified-artifacts.local.json,
product-static-imports.local.json, native-evidence.local.json에 있다.
전체 오류 로그는 full-tests.log와 repeat-tests.log, 재확인 사본 상태는
failure-snapshots/346e49883955627f6a6e/state-inspection.local.json을 따른다.

실제 제품 GUI 준비 신호를 연결할 때는 프로세스 생성 직후 신원 기록 전 중단 등 추가 시작 경계,
사용자가 정상 종료를 취소하는 경우, 장기 실행·Bootstrap 손상·클린 PC/SAC 정책을 별도로 검증해야 한다.
현재 결과를 전체 회귀 통과나 직원 배포 승인으로 해석하지 않는다.
