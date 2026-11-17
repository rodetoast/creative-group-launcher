# 직원 GUI의 GitHub Releases 연결

2026-11-06. 기존 레이아웃과 다크 테마, Installer·서명 검증기·LAN 연결을 유지했다. 운영 기본값에 테스트 저장소나 테스트 키를 등록하지 않았다. **격리 GUI의 실제 GitHub r2 조회·설치와 모의 GitHub의 GUI r1 → r2 버튼 동작을 검증했다. 전체 회귀는 파일 활성화 WinError 5로 미통과다.**

## 연결과 사용 흐름

`southpaw_tools/ui.py`의 기존 연결 설정에 배포 방식 선택과 OWNER/REPO 입력만 추가했다. GitHub 모드에서는 LAN 주소·토큰 입력을 비활성화한다. 기존 LAN 설정과 Provider 경로는 보존한다. 기본 연결은 기존 LAN으로 남겨 두었으며 GitHub 저장소를 자동 채우거나 운영 배포처로 활성화하지 않는다.

GitHub 모드의 흐름은 기존 목록·버튼·QThread 작업을 사용한다.

1. GitHubReleasesProvider.catalog()를 한 번 호출하고 기존 CatalogVerifier로 서명·순번·자산을 검증한다. GitHub health()를 따로 호출하지 않는다.
2. 설치된 앱 목록을 합쳐 표시하고 기존 AppRelease.is_new_release로 비교한다. 같은 버전의 다른 release_id도 기존 의미를 유지한다.
3. 설치 필요·업데이트 가능·최신 버전·업데이트 확인 중 상태를 기존 정보 영역에 표시한다.
4. 기존 설치/업데이트 버튼에서 사용자가 확인한 경우에만 Installer를 실행한다. 자동 확인은 자동 설치가 아니다.
5. 다운로드 진행률·취소·설치 실패·서명/해시 실패를 기존 작업 영역에 표시한다. 설치 이후 EXE를 자동 실행하지 않는다.
6. 인터넷 연결 실패·GitHub 호출 제한·접근 거부·서명 검증 실패는 구분한다. 실패하더라도 기존 로컬 설치와 실행 버튼을 유지한다.

설치·복구 엔진, admin.publish와 관리자 GUI, Windows Bootstrap은 수정하지 않았다. 실제 직원 AppData나 운영 키 파일도 수정하지 않았다.

## 호출 수와 검증 경계

`southpaw_tools/github_provider.py`에 해당 명시적 설치 작업 안에서만 사용하는 installation_session(app)을 추가했다. 일반 catalog()의 동작은 이전처럼 실제 네트워크를 조회한다.

- GUI 목록 확인: API 1회 + 카탈로그/서명 자산 각 1회.
- 설치/업데이트 직전: 선택한 릴리스가 여전히 최신 서명 목록과 일치하는지 새 API 조회 1회와 두 자산으로 다시 검사한다. 달라졌으면 설치 전에 거부한다.
- 그 작업 안에서 Installer가 validate_release를 반복 호출해도 같은 검증 바이트를 다시 Ed25519 검증하고, 자산 바인딩과 디스크의 이전 신뢰 순번을 다시 대조한다. 이 단계는 HTTP만 생략하며 서명 검증을 생략하지 않는다.
- 작업 종료·실패 시 작업 한정 스냅샷과 전송 바인딩을 폐기한다. 다음 작업에서는 반드시 새 네트워크 조회가 필요하다. 다른 프로세스가 순번을 올렸다면 이전 스냅샷도 거부한다.
- 설치 도중 새 Release가 게시되면 이미 작업 시작 시 확인한 일관된 릴리스를 사용한다. 무기한 최신성이나 서버의 게시를 실시간 감시한다고 주장하지 않는다.

GUI 시작 시 중복 health/catalog 조회를 제거했다. 자동 확인은 1시간마다, 수동 새로고침은 최소 5분 간격이다. 작업 중 재조회는 하지 않는다. 403의 호출 한도 소진·Retry-After 또는 429를 받으면 최소 1시간 조회를 보류한다. 버튼/직접 refresh 호출 모두 제한을 적용한다. 창 종료 시 자동 타이머도 중지한다. 무조건 재시도·토큰 로그인·PAT 저장은 없다.

이는 클라이언트별 간격일 뿐 회사 NAT 전체의 시간당 60회 예산을 보장하지 않는다. 직원 수와 시작 시간 집중, 수동 설치 수에 따라 호출 제한이 발생할 수 있다. 운영에서는 이 간격과 조회 예산을 별도로 검토해야 한다. 이번에는 ETag·백그라운드 다운로드 관리자·별도 서버를 추가하지 않았다.

## 테스트 키와 운영 차단

`southpaw_tools/__main__.py`에 --github-repository 및 --github-test-policy를 연결했다. 시험 공개키는 명시적 CLI/생성자 인자로만 받으며 settings.json에 있는 시험 키 경로는 신뢰하지 않는다.

시험 모드는 명시한 데이터 루트와 공개키 파일 모두 소스 프로젝트의 .test-results 내부에 있어야 하며, 저장소는 toast-source/creative-group-releases로 고정한다. 실제 AppData, 다른 저장소, 불일치 Installer 경로를 거부한다. 시험 모드임을 연결 상태에 표시하며 시험 중 연결 저장소를 바꾸지 못하게 한다. 현재 구현은 소스 개발 시험용 경계이며 배포 EXE에서 시험 모드를 제공한다고 주장하지 않는다.

운영 모드는 계속 bundled trusted_catalog_keys.json을 사용하고 현재 키 목록은 비어 있다. 실제 공개 더미 Release라도 운영 기본 정책으로는 서명 검증 단계에서 설치가 차단된다. 테스트 공개키를 제품에 자동 등록하지 않았다. LAN과 GitHub의 고정 catalog-trust.json과 순번 방어도 유지한다.

격리 시험을 다시 열어 볼 때 사용하는 형태는 아래와 같다. 데이터 루트는 기존 시험 자료를 덮어쓰지 않는 새 경로여야 한다. 이번 검증 명령은 Codex가 직접 수행했으며 사용자가 실행해야만 검증되는 상태가 아니다.

```powershell
# 프로젝트 작업 폴더에서, 준비된 Python 및 의존성 환경 사용
python -B -m southpaw_tools `
  --data-dir .test-results\새-격리-시험\client `
  --github-repository toast-source/creative-group-releases `
  --github-test-policy .test-results\github-live-20261106\keys\test-public-policy.json
```

## 검증 결과

| 범위 | 결과 |
|---|---|
| 기존 UI·LAN GUI·GitHub Provider 38개 | 통과 |
| 신규 GUI 12개 + 설치 작업 범위 5개 | 관련 재확인·전체·최종 17개 모두 통과 |
| 관련 묶음 55개 | 통과, 오류·skip 없음 |
| 전체 기존 186개 + 신규 17개 | **203개 실행, 202개 통과·1개 오류, skip 0**, 99.340초 |
| 기존 Windows Bootstrap | 12개 모두 통과 |
| 종료 타이머 보완 후 | 신규 17개 통과. 이 작은 보완 후 전체를 다시 반복하지 않음 |
| 실제 공개 GitHub + offscreen GUI | r2 조회·설치 성공. API 2회, 자산 요청 5회, 모두 HTTP 200 |

신규 테스트는 tests/test_github_ui.py와 tests/test_github_session.py에 있다. 버튼을 통한 더미 설치/업데이트, 버전 상태, 서명·해시 실패, 네트워크 실패 후 FakeProcesses를 통한 실행 요청, 호출 제한, 중복 조회, 취소, 운영 키 공백 차단, 시험 경계, 변조·신뢰 순번 변경 시 작업 스냅샷 거부를 다룬다. 실제 EXE를 실행하지 않았다.

초기 신규 17개 실행에서는 인터넷 실패 후 버튼 검사가 1건 실패했다. 당시 선행 설치 성공의 세부 오류는 보존되지 않아 원인을 확정하지 못했다. 해당 테스트에 설치 성공 전제와 오류 문구 확인을 추가했고, 단독·관련·전체·최종 실행에서 통과했다. 원인이 확인되어 해결됐다고 주장하지 않는다. 최초 로그도 new-tests.log에 보존했다.

전체에서 실패한 테스트는 RecoveryUiTests.test_offline_ui_can_restore_interrupted_removal_before_executing이다. **자기 UI 생성 전 최초 r1 설치**에서 기존 installer.py:160의 stage.rename(target)가 WinError 5를 반환했다. journal os.replace 실패와 구분한다. 관련 경로는 full.log에 있고 작업 파일은 full/f-d8c1892d7b/에 보존했다. 실패 후에만 동작하는 이전 journal 진단기를 재사용했으나 이번 폴더 rename은 그 진단 범위 밖이다. 기존 journal WinError 5와 이번 폴더 활성화 오류 모두 미해결이며 재시도·skip·오류 무시·보안 설정 변경은 하지 않았다.

모든 실행 로그는 .test-results/github-gui-20261106 아래에 분리했다. 관련/전체/최종 결과는 related-result.json, full-result.json, final-new-result.json이다.

## 실제 GUI 확인의 범위

격리 live-gui-data에 테스트 공개키를 명시 주입하고 실제 toast-source/creative-group-releases Latest를 읽었다. 현재 최신 github-smoke-r2 / 0.0.2를 표시한 뒤 기존 설치 버튼으로 설치했다. 목록 조회 1회와 설치 직전 검증 1회, 총 API 2회였다. 실제 CDN은 release-assets.githubusercontent.com이었고 모든 요청이 200이었다. 설치 후 최신 버전/실행 버튼, 복구 대기 없음·경고 없음을 확인했다.

증거는 live-gui-result.json과 live-github-gui.png다. 기존 다크 테마와 레이아웃에서 연결 상태·목록·버튼이 정상 표시되는 것을 이미지로 확인했다. GUI의 r1 → r2 버튼 전환은 모의 API와 실제 ZIP·Installer로 검증했다. 이번 실제 네트워크 GUI 시험은 r2 신규 설치이며, 이전 단계의 실제 GitHub r1 → r2 CLI 시험을 이번 GUI 업데이트 성공으로 혼동하지 않는다.

## 변경 파일과 보존

수정: southpaw_tools/ui.py, southpaw_tools/github_provider.py, southpaw_tools/__main__.py.

신규: tests/test_github_ui.py, tests/test_github_session.py, 이 문서. Git 제외 폴더에 원본 세 파일 사본, 실행기·로그·스크린샷·격리 설치 자료를 추가했다. 기존 미커밋 작업을 리셋하거나 되돌리지 않았다.

작업 시작 시점의 기존 4,443개 파일과 이전 실제 GitHub/LAN 시험 기록을 해시 대조하고, 예상한 위 세 제품 파일 외 변경 여부를 preservation.json에 기록한다. 외부 다섯 프로젝트 292개 파일·HEAD·태그·Git 상태 및 승인 ZIP 4개는 existing-projects.json으로 확인한다. Git HEAD·master·remote·stage를 그대로 유지한다. GitHub Release 생성·수정·삭제, 실제 사용자 자료·운영 키·LAN 서버·방화벽·SAC·ACL·시스템 PATH 변경은 하지 않았다.

## 직원 배포 전에 남은 사항

운영 공개키 채택, 실제 다섯 프로그램의 공개 게시 승인, 직원 UI의 운영 저장소 활성화는 별도 승인 사항이다. 기존 파일 작업 WinError 5 원인과 전체 회귀도 해결해야 한다. 실제 Windows 제품 GUI·EXE 실행·SAC 호환성과 직원 PC 데이터는 별도 검증이 필요하다. 회사 공인 IP를 공유하는 API 예산도 검토해야 한다.

관리자 GitHub 게시 GUI·Bootstrap·직원 배포·다음 개발 단계는 자동으로 진행하지 않는다.
