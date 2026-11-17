# journal WinError 5 조사 결과

2026-11-05. 제품 코드와 기존 테스트는 변경하지 않았다. **예상하지 않은 오류를 재현했으나 잠금 주체와 근본 원인은 미확정이다. 해결 완료로 판단하지 않는다.**

## 기존 증거

기준 HEAD는 `32afb846d0bc69b38203a259dad71180cd4a14b5`, 브랜치는 master다. 기존 미커밋 변경은 이번 변경과 구분해 보존했다.

| 기존 로그 | 순서 | 실패 테스트 | 실제 실패 구간 |
|---|---:|---|---|
| `.test-results/windows-packaging-20261105/full-tests.log` | 133 | `SelfUpdateTests.test_preparing_journal_recovery_preserves_current` | setUp의 r1 bootstrap 설치, activating 기록 |
| 같은 로그 | 134 | `SelfUpdateTests.test_real_pointer_lock_failure_and_explicit_retry_after_release` | 의도적 pointer 잠금 시작 전 r2 준비, preparing 기록 |
| `.test-results/windows-packaging-20261105/repeat-tests.log` | 71 | `JournalSharingTests.test_persistent_lock_preserves_journal_then_recovers_after_release` | 의도한 핸들을 닫고 recover 이후 명시적 재설치, activating 기록 |

호출은 `Installer._phase → atomic_json → atomic_bytes → os.replace`다. 정확한 이전 source/target은 원본 로그 및 새 `historic-order.json`에 보존했다. 기존 두 전체 실행은 각각 161개 중 오류 2개와 1개였고, 단순한 의도적 오류 출력과 unittest ERROR를 구분했다.

기존 `failure-snapshots/346e49883955627f6a6e/`는 복구 후 r1 active/receipt/파일 해시 일치와 transactions 없음이 확인된 자료다. 실패 순간 핸들 상태를 담은 자료는 아니다. 앞선 두 실패의 원래 임시 디렉터리는 이미 정리되어 당시 파일 존재·ACL을 소급 확인할 수 없다. 이전 로그·스냅샷은 변경하지 않았다.

근거 코드: `southpaw_tools/common.py:39`, `southpaw_tools/installer.py:238`, `tests/test_journal_sharing.py:69`, `tests/test_self_update.py`, `tests/self_update_support.py`. 이전 조사: `docs/WINERROR5_PREFLIGHT_REPORT.md`.

## 쓰기 순서와 경합 분석

`atomic_bytes`는 같은 부모 디렉터리에 mkstemp로 고유 이름을 만들고, write → flush → fsync → with 종료로 핸들 close → os.replace 순서로 처리한다. 실패 뒤 finally에서 자기 임시 파일만 정리한다. 대상 journal을 먼저 삭제하지 않는다. 읽기 함수도 자기 읽기 구간을 닫는다.

테스트별 TemporaryDirectory와 journal UUID가 다르며, 설치 작업에는 앱 단위 OS 잠금이 있다. 동일 고정 임시 파일을 테스트끼리 공유하는 결함은 발견하지 못했다. UI의 journal 읽기와 설치 worker가 겹칠 가능성은 있지만, UI 생성 전 설치 및 GUI가 없는 테스트에서도 오류가 발생했으므로 이번 오류의 원인으로 확정할 수 없다.

## 이번 관측 방식

새 격리 폴더 `.test-results/journal-winerror5-20261105/`만 사용했다. `diagnose.py`는 os.replace를 한 번 호출하고 실패한 경우에만 관측한다. 정상 경로에 추가 파일 I/O·sleep·재시도를 넣지 않는다. 실패 이후 관측 시간은 복구 타이밍에 영향을 줄 수 있으며, 기존 실패 순간을 완벽하게 재현하는 도구는 아니다.

기록 항목은 테스트 ID, UTC, PID·스레드 ID, 호출 스택, 상대 source/target, 존재·크기·파일 속성, writer.closed, 원본·기존 journal 바이트, Python 열린 파일 객체, DELETE 접근 핸들 조회, Restart Manager 소유 프로세스 조회다. 토큰·개인키 내용이나 사용자 데이터를 출력하지 않는다.

DELETE 접근 조회는 FILE_SHARE_READ/WRITE/DELETE로 핸들을 열고 닫는 검사이며 삭제·삭제 예약을 수행하지 않는다. Restart Manager는 조회 후 세션만 종료하며 프로세스 종료·재시작 API는 호출하지 않는다. 일반 사용자 권한만 사용했다.

Microsoft 근거: [CreateFileW 공유 모드](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew), [RmRegisterResources](https://learn.microsoft.com/en-us/windows/win32/api/restartmanager/nf-restartmanager-rmregisterresources), [RmGetList](https://learn.microsoft.com/en-us/windows/win32/api/restartmanager/nf-restartmanager-rmgetlist). 핸들이 이미 닫혔거나 파일시스템 필터가 관여하면 사후 조회만으로 소유자를 찾지 못할 수 있다.

## 실제 재현과 확인 수준

### 의도적 잠금: 확인

기존 journal 공유 회귀 테스트에서 대상 rb 핸들이 열린 동안 실제 WinError 5가 발생했다. writer.closed=true, source/target 존재, 대상 DELETE 접근은 오류 32였고, Python의 해당 rb 객체가 확인됐다. 일반 실행 환경의 Restart Manager도 테스트 Python PID 8464를 소유자로 보고했다. 테스트가 보유한 잠금이라는 사실은 확인됐다.

핸들을 닫은 후 테스트가 수행하는 명시적 복구·재시도는 성공했다. 기존 active와 settings 보존, journal 유지/정리 의미는 기존 테스트로 검증했다. 이 결과를 자연 발생 오류의 잠금 주체 확인으로 확대하지 않는다.

### 자연 발생: 재현했으나 원인 미확정

1. `full-network-check/event-000/event.json`
   - `CatalogSigningTests.test_signed_r1_to_r2_update_and_offline_local_state`, `tests/test_catalog_signing.py:159`의 **최초 r1 설치**.
   - PID 29724, 스레드 16344, `2026-11-05T10:25:07.581004+00:00`.
   - source `.test-results/tmp/signed-catalog-cbg601rn/installed/apps/dummy/transactions/.pending-cd2tnf2l.json`.
   - target 같은 폴더 `90473be622cc43e7a23dea7e15ced8a7.json`.
   - source preparing 1114바이트, 기존 target download_verified 1122바이트. 둘 다 파일 속성 32, writer.closed=true.
2. `full-observed/event-004/event.json`
   - `RecoveryTests.test_each_precommit_phase_interruption_is_retryable`, `tests/test_recovery.py:303`의 중단 후 재설치. 의도한 SystemExit 주입과 다른 실제 OSError다.
   - PID 8464, 스레드 12268, `2026-11-05T10:25:53.016105+00:00`.
   - source `.test-results/tmp/southpaw-recovery-08vyvvw2/switching/apps/dummy/transactions/.pending-09c_pwwq.json`.
   - target 같은 폴더 `138920cf7280450fa04298c452b9faf3.json`.
   - source switching 2153바이트, 기존 target ready 2149바이트. 둘 다 파일 속성 32, writer.closed=true.

두 자연 발생 건 모두 실패 후 Python 열린 파일 객체가 발견되지 않았고 source/target DELETE 접근 핸들 열기·닫기는 성공했으며 Restart Manager 프로세스 목록은 비어 있었다. 따라서 쓰기 핸들 미종료·지속적인 읽기 전용 속성을 원인으로 확인하지 못했다. 반대로 일시적 공유 위반, 다른 프로세스·파일시스템 필터, 순간적인 접근 제어를 배제할 수도 없다. 백신·Search·Qt·Python 중 특정 주체를 원인으로 지목하지 않는다.

첫 자연 발생 건은 최초 설치이므로 보존할 이전 active가 없었다. 두 번째 기록의 journal에는 이전 r1 포인터가 포함돼 있다. 다만 이 두 건 모두 실패 시점 전체 active/receipt/사용자 파일 비교까지 확보한 것은 아니므로 데이터 안전성을 포괄적으로 확정하지 않는다. 별도의 기존 회귀 테스트와 과거 복구 스냅샷의 보존 결과를 구분한다.

## 진단 도구 오류와 실행 환경 구분

제한된 실행 환경에서 전체 161개를 완료했으나 루프백 HTTP connect가 WinError 10013으로 거부되어 5개가 오류였다. journal 자연 발생 오류는 그 실행에서 관측되지 않았다. Restart Manager도 해당 환경에서 세션 생성 오류 29를 반환했다.

같은 테스트를 샌드박스 밖 일반 사용자 실행으로 비교했을 때 자연 발생 WinError 5를 포착했다. 이 첫 비교 실행은 진단 스냅샷 이름에 전체 테스트 ID를 넣은 탓에 WinError 206이 발생하여 실행기가 중단됐다. 이 실행을 전체 테스트 결과로 계산하지 않는다. 원래 journal 오류 이벤트와 바이트는 먼저 저장되어 보존됐다.

진단기만 짧은 해시 폴더명과 스냅샷 실패 별도 기록으로 수정했다. 제품·기존 테스트는 변경하지 않았다. 이 보완 후 전체 실행 결과는 아래 검증 표와 원본 로그를 따른다. 기존 실패 자료를 덮어쓰지 않았다.

## 검증 결과

최종 수치는 `.test-results/journal-winerror5-20261105/*-result.json`과 각 로그를 근거로 아래에 기록한다.

| 실행 | 결과 | 시간 | 해석 |
|---|---|---:|---|
| 과거 실패 테스트 및 공유 잠금 5개, `isolated.log` | 5 통과 | 3.107초 | 의도적 journal 잠금 4회 관측, 예상 외 오류 없음 |
| 설치·journal·복구·자체 업데이트 78개, `related.log` | 78 통과 | 37.408초 | 의도적 journal 잠금만 관측 |
| 제한 환경 전체, `full.log` | 156 통과·5 오류, skip 0 | 109.197초 | 루프백 connect WinError 10013, journal 자연 발생 없음 |
| 일반 사용자 비교, `full-network-check.log` | 실행기 중단 | 전체 결과 없음 | 최초 r1 자연 발생 WinError 5 포착 후 진단 스냅샷 경로 WinError 206 |
| 진단기 경로 보완 후 전체, `full-observed.log` | **160 통과·1 오류, skip 0** | 90.422초 | recovery switching 하위 시험의 실제 journal WinError 5 |
| 새로 오류가 난 두 테스트 단독 비교, `newly-isolated.log` | 2 통과 | 0.907초 | 예상 외 오류 없음. 전체 실행의 실패를 취소하는 결과는 아님 |

최종 오류는 `RecoveryTests.test_each_precommit_phase_interruption_is_retryable (phase='switching')`다. `Installer.install:154 → _phase:238 → common.atomic_bytes:47 → os.replace`에서 발생했다. 성공을 얻기 위한 추가 전체 반복은 하지 않았다. **최종 전체 회귀는 미통과다.**

Bootstrap Windows 테스트 12개는 두 번의 완료된 전체 실행에서 모두 통과했고 기존 파일도 유지됐다. 제품 EXE는 실행하지 않았다. 최종 일반 실행에서는 네트워크 테스트도 통과했으므로 처음의 10013은 제한 실행 환경과 관련된 결과로 구분하며 journal 결함으로 합치지 않는다.

진단 스냅샷은 일반 테스트 addError/addFailure 시 보존한다. 최종 자연 발생 건은 subTest 오류여서 전체 디렉터리 자동 복사는 수행되지 않았다. 오류 직후 source/target journal 두 파일과 이벤트는 보존됐지만 원래 임시 트리는 unittest 정리로 삭제됐다. 이 수집 한계를 숨기지 않는다.

수집 누락을 줄이기 위해 조사 후 진단기에 addSubTest 스냅샷 처리도 추가했다. 이는 향후 수집용 보완이며 이번 실패 트리를 소급 복원하거나 추가 실증한 결과가 아니다.

## 변경과 보존

제품 코드 수정 없음. 근본 원인이 확인되지 않아 공유 플래그 변경·재시도 등의 추측성 수정을 적용하지 않았다. 기존 161개 테스트 및 Bootstrap 12개를 유지했고 테스트 skip·삭제·성공 처리 우회는 추가하지 않았다. 이미 실제 공유 잠금과 복구를 검증하는 테스트 3개가 있으므로 같은 조건의 중복 테스트도 추가하지 않았다.

이번 신규 파일은 이 보고서와 Git 제외 진단 폴더의 실행기·로그·이벤트·비교 자료뿐이다. `before-files.local.json`에 기록한 기존 파일 4,331개의 해시가 유지됐다. 별도 `existing-projects.json`에서 기존 5개 프로젝트 292개 파일·HEAD·태그·Git 상태, 확인된 원본 ZIP 4개가 유지됐다. AsepriteTagMaster 원본 승인 ZIP 미확인 상태도 그대로다.

최종 보존 근거는 `preservation-final.json`, `existing-projects.json`, `git-final.json`이다. 조사 폴더에는 `isolated`, `related`, `full`, `full-network-check`, `full-observed` 실행별 이벤트와 별도 로그·결과가 있다. 원래 시험 자료에는 추가 기록도 하지 않았다.

Git master와 최초 HEAD를 보존했고 remote는 없다. 기존 dirty 상태는 이번 작업 이전부터 존재했으며 stage/commit/push/remote 변경은 하지 않았다. 이번 보고서만 새 미추적 문서로 추가된다. 실제 제품 EXE·LAN 서버·방화벽 작업·정책·ACL 변경·관리자 도구·Windows Use는 수행하지 않았다. 자동 테스트의 격리 loopback 서버, offscreen Qt와 승인된 무해한 Windows fixture 프로세스는 실제 LAN/제품 GUI와 구분한다.

## 남은 위험과 추가 증거

자연 발생 WinError 5는 재현되지만 잠금 주체는 미확정이며, 전체 테스트의 안정적 통과를 보장하지 못한다. 사후 조회가 놓치는 순간적인 파일 접근을 확인하려면 실패 시각의 파일 열기·공유 모드·파일 이름 바꾸기 결과와 프로세스가 필요하다. 일반 사용자 Restart Manager 대안은 이번에 사용했지만 자연 발생 건의 주체를 찾지 못했다.

필요시 Process Monitor 등 실시간 파일 추적을 별도 승인 후 검토할 수 있다. 관리자 권한이나 외부 진단 도구는 자동 실행하지 않았다. 추적 시 시험 경로·실행 시간으로 범위를 제한하고 실제 사용자 파일을 수집하지 않아야 한다. 현재 증거로 보안 제품 예외·ACL 변경·sleep·재시도를 해결책으로 제시하지 않는다. 다음 개발 단계나 제품 GUI 연동으로 자동 진행하지 않는다.
