# 관리자 GitHub 전달 GUI와 시험 실행 차단

2026-11-06. **기존 관리자 GUI에서 서명 묶음 준비 → 초안 → 업로드 → 재다운로드 검증 → 공개 확인을 구분했다. 전체 흐름은 모의 gh 어댑터로만 검증했으며 실제 GitHub 쓰기는 잠겨 있다.** 직원 시험 GUI의 EXE 실행은 버튼·메서드·프로세스 시작 경계에서 차단했다.

**추가 승인 후 최신 결과: 전체 223개 통과, 오류·실패·skip 0. Bootstrap 12개 포함, 104.174초.** 이전 제한 실행과 WinError 5 실패 기록은 아래에 그대로 구분해 남겼다. 간헐적 WinError 5의 근본 원인을 해결했다고 주장하지 않는다.

## 직원 시험 GUI 안전성

`southpaw_tools/ui.py`에서 명시적 github_test_mode인 경우만 변경했다.

- 배지를 테스트 배포본으로 표시한다.
- 설치된 최신 버전의 주 버튼은 시험 실행 차단으로 비활성화하고, 현재 버전 실행 버튼도 숨기고 차단한다.
- launch()를 직접 호출하거나 primary_action()을 직접 호출해도 실행하지 않는다.
- 시험 화면에는 기존 Installer를 별도 인스턴스로 연결하고 프로세스 어댑터의 start()에서 다시 거부한다. window.installer.launch()를 직접 호출해도 EXE가 시작되지 않는다. 주입받은 원래 Installer와 일반 모드에는 이 어댑터를 적용하지 않는다.
- 설치·업데이트·복구는 기존 Installer로 계속 허용한다. 완료 안내도 실행 버튼을 누르라는 문구 대신 시험 실행 차단을 명시한다.
- 일반 모드의 팀 승인 배포본 표기와 로컬 실행 동작은 유지한다. 테스트에서는 FakeProcesses로만 일반 실행 요청을 확인했다.

기존 Installer·Processes·서명 검증 엔진을 수정하거나 새 설치 엔진을 만들지 않았다. 실제 회사 프로그램과 GitHub Dummy Tool EXE는 실행하지 않았다. 별도로 승인된 Bootstrap 시험 EXE의 실행 결과는 아래 추가 검증 기록과 구분한다.

## 관리자 GUI 흐름

기존 앱 선택·승인 ZIP 선택·검사·EXE 경로·버전·release_id·노트·순번·외부 키 선택·최종 검토 화면을 유지한다. 다섯 앱의 이름과 AsepriteTagMaster 게시 잠금도 유지한다. 해시는 검증 수단이며 회사 승인 여부를 자동 판정하지 않는다. 승인 완성 ZIP 확인란은 계속 필요하다.

새 흐름은 모의 CLI가 주입된 격리 관리자 세션에서만 선택할 수 있다. 기본 GUI에는 실제 외부 게시 잠금이 표시된다. 고정 대상은 toast-source/creative-group-releases이며 편집 가능한 저장소 입력은 제공하지 않는다.

1. 기존 ZIP 검사와 최종 검토를 통과한 뒤 **서명 묶음 준비**를 누른다.
2. 전용 작업 사본에서 기존 AdminSession.publish → admin.publish를 호출한다. 원래 로컬 저장소는 변경하지 않는다.
3. 새 카탈로그와 분리 서명, 현재 published 앱 전체 ZIP을 자산 폴더에 복사한다. 변경되지 않은 ZIP은 원래 해시·바이트를 유지한다. 모든 ZIP에 기존 안전 추출 검사도 적용한다.
4. GUI에 고정 저장소·tag와 전체 자산 이름·크기·SHA-256을 표시한다.
5. 별도 확인 후 초안 생성, 다음 버튼으로 자산 업로드, 다음 버튼으로 재다운로드 검증을 수행한다.
6. 모든 자산의 크기·해시·서명·ZIP 검사 통과 후에만 공개 최종 확인 버튼을 활성화한다. 공개 확인은 초안 생성 확인과 별도다.
7. 모의 공개 결과와 Latest 응답까지 검사한다. GUI는 모의 완료·실제 GitHub 미변경을 표시한다.

원래 로컬 카탈로그를 갱신하지 않는 것은 이번 모의 시험의 의도적 경계다. 원격 게시가 검증되기 전에 로컬의 실제 게시 상태를 성공한 것처럼 변경하지 않는다. 실제 운영 상태 동기화와 실제 게시 권한 활성화는 이번에 구현하지 않았다.

## CLI 연결과 외부 쓰기 방지

신규 `southpaw_tools/admin_github.py`는 기존 서명 게시 엔진의 전달 어댑터다. 새 인증 시스템·서버·빌드 엔진이 아니다.

GhCliTransport는 개발자 gh의 api 명령을 배열 인자로 구성하고 종료 코드·HTTP 상태·JSON 응답을 검사한다. 사용자명, 초안 ID·tag·상태, 업로드 이름·크기, 자산 목록·ID·digest, 최종 공개/Latest를 확인한다. 명령에 토큰이나 개인키를 넣지 않고 auth token·로그인 명령도 사용하지 않는다. --github-cli로 개발자 PC의 기존 실행 파일 경로를 명시할 수 있지만 실제 쓰기 잠금은 해제되지 않는다.

테스트에서는 `tests/admin_github_support.py`의 인메모리 runner를 주입한다. gh가 호출될 명령과 동일한 요청 형태 및 종료 코드·응답으로 검증하지만 gh 프로세스와 네트워크는 사용하지 않는다. 실제 transport의 POST/PATCH는 runner가 없는 상태에서 거부되며, GitHubPublication도 격리 AdminSession + dry-run이 아니면 거부된다. 실제 직원용 Provider에는 이 인증·게시 경로를 연결하지 않았다.

원격 조회 범위는 승인 저장소와 계정 조회에 한정한다. 실제 쓰기가 있는 흐름도 코드의 현재 기본 상태에서는 실행할 수 없다. 이번 작업은 실제 cli 로그인·API 읽기·Release 생성·업로드·공개·수정·삭제를 수행하지 않았다. 기존 공개 r1/r2는 변경하지 않았다.

## 실패·변경·덮어쓰기 방어

- 검사 후 원본 ZIP, 카탈로그, 키·순번·검토 정보 변경을 다시 검사한다.
- 묶음 파일의 이름·크기·해시가 달라지면 다음 단계를 막는다. 개인키는 자산 폴더에 복사하지 않는다.
- 동일 tag가 이미 존재하거나 초안에 자산이 있으면 자동 덮어쓰기하지 않는다. 목록이 100개여서 부재를 완전히 확인할 수 없는 경우도 보수적으로 거부한다.
- 같은 앱의 중복 release_id, 잘못된 서명·순번, TagMaster·허용 목록 밖 실제 프로그램 ZIP은 기존 검사와 시험 허용 목록에서 차단한다.
- 업로드 중 실패하면 부분 업로드와 초안을 그대로 두고 실패로 표시한다. 재다운로드·서명·해시가 다르면 공개 버튼을 활성화하지 않는다.
- 검증 뒤 자산 ID가 바뀌어도 공개하지 않는다.
- 공개 요청 후 응답/Latest 확인에 실패하면 실제 공개가 반영됐을 수도 있는 미확정 상태로 기록한다. 성공이나 초안 유지로 단정하지 않고 수동 확인을 안내한다.
- 상태·단계·초안 ID·CLI 종료 코드·HTTP 상태는 각 작업의 publication-state.json에 남긴다. 키 경로·키 내용·토큰을 저장하지 않는다. 자동 재시도·삭제·롤백하지 않는다.

공개 성공 전에는 실제 GitHub 상태를 관측하지 못했는데 성공했다고 표시하지 않는다. 현재 테스트의 published는 오직 인메모리 모의 상태다.

## 검증 결과

기존 203개 테스트 정의를 유지하고, 관리자 흐름 17개와 시험 실행 차단 3개를 추가했다. 기존 tests/test_github_ui.py의 기대값은 새 시험 실행 차단 정책에 맞게 갱신했으며 일반 모드 실행 보존도 같은 테스트에서 확인한다.

| 실행 | 결과 |
|---|---|
| 최초 관련 51개 | 모두 통과 |
| 허용된 회귀 210개 | 모두 통과, 54.135초 |
| GUI 문구·파일 선택 경로 보완 뒤 관련 51개 | 모두 통과 |
| 공개 응답 미확정 보호 테스트 추가 후 최종 허용 회귀 | **211개 실행, 210개 통과·오류 1개·skip 0**, 50.682초 |
| 신규 20개 | 최종 허용 회귀에서 모두 통과 |
| Windows Bootstrap 그룹 12개 | 최초에는 미실시. 이후 명시적 추가 승인 뒤 12개 모두 통과 |
| 추가 승인 뒤 전체 회귀 | **223개 통과, 오류·실패·skip 0**, 104.174초 |

전체 정의 수는 223개다. 추가 승인 전에는 실제 EXE 실행 제한 때문에 전체 회귀 완료·합격으로 표시하지 않았고, WindowsBootstrap 그룹 12개를 미실시 목록으로 구분했다. 테스트 정의를 삭제하거나 skip 표시를 추가하지 않았다. 이후 사용자가 기존 CGLBootstrap/CGLFixtureR1/R2만 예외로 명시 승인한 뒤 전체 223개를 실행했다. 이전 미실시 목록은 당시의 기록으로 보존한다.

최종 오류는 기존 RecoveryTests.test_cleanup_denial_is_warning_and_next_update_still_works의 setUp 최초 설치 중 preparing journal 교체에서 발생한 실제 WinError 5다. 의도적 cleanup 실패 주입 전에 발생했다. 호출은 installer._phase → common.atomic_json/atomic_bytes → os.replace다. 원본·대상 모두 존재하고 writer.closed=true였으나 원인을 특정하지 않았다. 실패 순간의 journal 바이트·PID·스레드·호출 스택과 테스트 파일 사본을 보존했다. 의도적으로 주입한 공유 잠금 4건과 자연 발생 1건을 구분했다. 재시도해 성공으로 바꾸지 않았다.

근거 폴더: `.test-results/admin-github-20261106/`. targeted-tests.log, permitted.log, final-related.log, final-permitted.log 및 각 result.json, final-permitted-not-executed.json, final-permitted/event-004/, 실패 스냅샷을 보존했다. 기존 journal 문제와 이전 stage.rename 문제 모두 해결됐다고 주장하지 않는다.

### Bootstrap 추가 승인 후 전체 회귀

검증된 기존 CGLBootstrap(75개 파일), CGLFixtureR1(55개), CGLFixtureR2(55개)의 전체 파일 목록·해시 185개가 기존 verified-artifacts.local.json과 일치하는 것을 먼저 확인했다. 재다운로드·재빌드·관리자 권한 상승·시스템 설정 변경 없이 기존 격리 시험 경로에서만 실행했다. GitHub Dummy Tool과 실제 제품 EXE는 실행하지 않았다.

기존 실행기에서 전체 테스트를 새 로그로 한 번 실행했다. 결과는 223개 통과, 오류 0, 실패 0, skip 0이다. Bootstrap 12개와 신규 20개 모두 포함됐다. 의도적 공유 잠금 WinError 5 관측 4건만 있었고, 예상하지 않은 WinError 5는 이번 전체 실행에서 관측되지 않았다. 직전 실패를 삭제하거나 제품 재시도로 성공 처리한 것이 아니며, 기존 간헐적 오류는 미해결로 유지한다.

근거는 `.test-results/admin-github-20261106/bootstrap-approved-regression/`의 approved-build-verification.json, full.log, full-result.json, FINAL_RESULT.json이다. 제품 코드와 테스트는 이 추가 실행에서 변경하지 않았고 이 보고서만 갱신했다. Git HEAD·브랜치·remote·stage와 기존 미커밋 항목을 보존했다. 기존 격리 시험의 일반적인 기술 선택은 승인 범위 안에서 진행하며, 실제 외부 공개·삭제·운영 데이터·권한 상승·보안 정책 변경은 별도 확인 경계로 유지한다.

전체 모의 게시 흐름의 영구 증거는 complete-dry-run-result.json과 persistent-dry-run/github-plans 아래 publication-state.json이다. 모의 CLI 요청 14개를 검증했고 원래 로컬 저장소는 유지됐다. 실제 GitHub 요청·외부 쓰기는 0이다. 이미지 admin-github-preview-verified.png, staff-test-execution-blocked-final.png도 확인했다. 실제 GitHub 게시 성공으로 확대 해석하지 않는다.

## 변경과 보존

수정: southpaw_tools/ui.py, southpaw_tools/admin_gui.py, tests/test_github_ui.py.

신규: southpaw_tools/admin_github.py, tests/admin_github_support.py, tests/test_admin_github.py, tests/test_testmode_safety.py, 이 문서. 실행기·로그·시험 키·ZIP·작업 사본·이미지는 새 Git 제외 폴더에만 생성했다.

작업 시작의 파일 해시와 비교해 위 세 수정 파일 외 기존 파일·이전 LAN/GitHub/서명/GUI/Bootstrap 시험 자료가 유지됐는지 preservation.json에 기록한다. 기존 다섯 프로젝트와 승인 ZIP은 별도 existing-projects.json으로 검증한다. 기존 미커밋 작업을 리셋하지 않았고 Git HEAD·master·remote·stage/commit/push를 변경하지 않았다.

## 실제 Draft 시험 전에 필요한 승인

현재 구현은 시험용 모의 단계이며 실제 전송 잠금 해제는 별도다. 실환경 시험에는 승인 저장소의 현재 서명 상태·sequence와 중복 없는 새 tag, 정확한 더미 자산 목록, 시험 키 정책, CLI 계정 권한, 초안 생성 범위를 먼저 확인하고 별도 승인을 받아야 한다. 기존 r1/r2와 충돌하는 tag를 재사용하지 않는다. 공개는 초안 재다운로드 검증 후 다시 최종 승인을 받아야 한다.

운영 키 채택·회사 승인 ZIP 공개·직원 배포·관리자 실게시 활성화·다음 개발은 자동 진행하지 않는다.
