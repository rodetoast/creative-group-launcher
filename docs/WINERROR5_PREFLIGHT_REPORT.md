# WinError 5 조사와 LAN/GitHub 사전 점검

2026-11-03 KST. 첫 체크포인트32afb846d0bc69b38203a259dad71180cd4a14b5를 보존했다. **최초 오류를 일으킨 실제 핸들/프로세스는 특정하지 못했다.** 같은 오류를 만드는 파일 잠금 조건과 실패 후 보존·복구는 격리 디렉터리에서 재현했다. sleep/자동 재시도/제품 동작 변경은 추가하지 않았다.

## 1. 기존 로그에서 확정한 사실

근거는 Git 제외 .test-results/checkpoint-initial-tests.log 및 .json이다. 요청에서 “소스 복사본 최초 실행”으로 표현한 오류는 실제 로그상 **원래 작업 폴더**의 .test-results/tmp 아래에서 발생했다. 이후 소스 복사본 검증은 별도 경로이고 통과 기록이 있다.

호출 경로:

~~~text
RecoveryUiTests.test_refresh_conflict_does_not_overwrite_cache_or_local_pointer
  -> installed_window (UI 생성 전 더미 최초 설치)
  -> Installer.install
  -> Installer._phase(journal, "download_verified")
  -> atomic_json
  -> os.replace(temp, path): PermissionError, WinError 5
~~~

정확한 상대 경로:

~~~text
.test-results/tmp/southpaw-ui-dd4o_yj3/client/apps/dummy/transactions/
  source: .pending-jzsjjd_z.json
  target: 20a84440f6e84316bd9fae1a563ea89b.json
~~~

당시 전체78개 중오류1,19.677초였다. 이 테스트는 새 client 디렉터리에 r1을 최초 설치하는 준비 단계였으므로, 해당 테스트의 이전 active 설치는 없었다. 특정 테스트의 이름이 카탈로그 충돌 검사를 가리켜도 실제 오류는 그 검사나 창 생성 전에 발생했다.

## 2. 교체 순서와 동시 접근

[atomic_json](../southpaw_tools/common.py)은 대상과 같은 디렉터리에 mkstemp→UTF-8 JSON 쓰기→flush/fsync→쓰기 핸들 닫기→os.replace→잔여 temp unlink 순서다. 쓰기 핸들이 열린 상태에서 교체하는 코드는 아니다. 대상이 존재할 때의 교체가 실패했으며 기존 journal은 앞서 저장한 downloading 단계일 것으로 코드 흐름상 판단된다.

[read_json](../southpaw_tools/common.py)은 Path.read_text로 잠시 읽기 핸들을 열고 닫는다. [pending_recovery/render](../southpaw_tools/ui.py)는 설치 worker와 겹쳐 journal을 읽을 수 있다. 따라서 실행 중 GUI에서 같은 파일의 읽기와 교체가 겹칠 가능성은 있다. 그러나 **최초 실패 테스트는 아직 자기 UI를 만들기 전이고 경로도 독립적이므로, 이를 최초 원인이라고 단정할 수 없다.** 다른 프로세스/보안 제품/파일시스템 필터 역시 기록 없이 원인으로 확정하지 않는다.

Microsoft 문서는 파일 공유 모드가 핸들 종료까지 적용되고, FILE_SHARE_DELETE가 rename/delete 접근에 관계한다고 설명한다. 근거: [CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew). 이것만으로 모든 교체 실패의 원인을 확정하거나 공유 플래그 변경을 해결책이라고 볼 수는 없다.

## 3. 제한적 재현과 권한 조사

테스트가 직접 생성한 파일/핸들/스레드만 사용했다. 다른 프로세스의 핸들 조사·종료나 ACL/보안 설정 변경은 하지 않았다.

| 검사 | 실측 |
|---|---|
| 대상 JSON을 Python rb 핸들로 연 채 교체 | 실제 WinError5 재현, 이전 JSON은 완전한 값으로 보존, pending temp0 |
| 그 핸들을 닫은 뒤 명시적 재시도 | 성공 |
| read_json의 읽기 구간을 barrier로 유지하면서 다른 thread가 교체 | 실제 WinError5 재현, reader 오류 없음 |
| 충돌 핸들 없는 atomic write/read200회 | 200회 성공, 자연 발생 오류0 |
| 최초 실패 UI 테스트를 매번 새 temp에서20회 | 20회 통과, 실패/오류0 |
| 현재 .test-results ACL 읽기 | 실행 사용자 Full Control, sandbox 그룹 Read/Execute 등 상속 항목 확인. ACL 변경 없음 |
| 당시 시각 주변의 해당 경로 CFA1123/1124 로그 조회 | 일치 이벤트 없음. Defender/다른 필터 원인을 배제하는 증거는 아님 |

원래 실패 디렉터리는 테스트 종료 때 정리되어 당시의 ACL/핸들 상태를 직접 조사할 수 없다. 현재 ACL과 반복 성공은 영구 권한 거부가 현재 재현되지 않는다는 정보만 준다. 사용자 프로그램이나 보안 제품을 임의 종료하여 우회하지 않았다.

공유 플래그를 바꿔 읽는 실험도 했으나 이 PC에서 열린 대상 교체를 안정적으로 성공시키지 못했다. 검증하지 못한 개선안을 제품에 남기지 않고 common.py를 원래 체크포인트 내용으로 돌렸다. 무조건 덮어쓰기, 권한 확대, sleep 또는 횟수 제한 없는 재시도를 추가하지 않았다.

## 4. 오류 시 상태와 재시도 안전성

신규 [회귀 테스트3개](../tests/test_journal_sharing.py)로 실제 OS 파일 잠금을 사용해 확인했다.

1. 교체 실패 시 이전 JSON이 유지되고 미완성 temp는 정리된다. 핸들 종료 후 새 명시적 atomic write는 성공한다.
2. r1 설치·사용자 설정이 있는 상태에서 r2의 download_verified journal 교체만 실제 WinError5로 실패시켰다. 기존 active 포인터 bytes, r1 실행 경로, 사용자 설정이 보존됐고 r2는 활성화되지 않았다. 잠금 종료 후 새 Installer 요청으로 r2 설치가 성공했다.
3. 복구 기록 쓰기까지 계속 막는 핸들을 유지했다. 작업은 성공을 주장하지 않고 “복구 필요”를 반환했다. 기존 active/r1은 유지됐고 이전 downloading journal이 남았다. 핸들 종료 후 recover→설치 재시도가 성공했다.

일반 오류 복구가 완료되면 failed 기록과 자신이 소유한 임시 ZIP은 정리될 수 있으므로 모든 실패에서 journal이 영구 보존되는 것은 아니다. 복구 자체도 거부되면 이전 정상 journal·다운로드 등 후속 복구 자료를 남긴다. Windows 잠금이 계속되면 복구가 완료되지 않을 수 있고 원인을 없앤 뒤 명시적으로 재시도해야 한다. 파일 손상/전원 손실/모든 권한 장애를 보장하는 검증은 아니다.

실험 결과는 Git 제외 winerror5-before.local.json, winerror5-ui-repeat.local.json/.log, 최신 unit-tests.json/.log에 있다.

## 5. 최종 테스트와 변경

**기존78개 + 신규3개 = 총81개, failures0/errors0/skipped0,19.762초 PASS.** Windows11 build26200, Python3.13.7, PySide6/Qt6.11.0. 원래78개 테스트 소스는 변경하지 않았다.

최종 남긴 파일은 tests/test_journal_sharing.py와 이 문서뿐이며 모두 unstaged/untracked 상태다. 제품 소스·설치 엔진·원래 문서·기존 배포 메타데이터는 첫 체크포인트와 동일하다. 기존5개 repo 검사 대상292개 파일과 Git 상태·승인 ZIP4개를 재확인했다. 읽기 공유 실험 코드는 최종 결과에 포함하지 않았다.

## 6. GitHub 읽기 전용 조회

대상: [toast-source/creative-group-launcher](https://github.com/toast-source/creative-group-launcher).

브라우징 경로에서 내용을 얻지 못해 공개 GitHub REST API GET과 credential helper/인증 프롬프트를 끈 git ls-remote로 확인했다. 인증정보를 읽거나 인증 흐름을 시작하지 않았다.

| 항목 | 확인 결과 |
|---|---|
| 접근 | 비인증 공개 조회 성공, git ls-remote exit0 |
| 실제 owner.login | toast-source |
| 공개 여부 | public, private=false |
| 기본 브랜치 설정 | main |
| 초기 커밋 | API commits409(empty), ls-remote 참조 없음. 초기 커밋/실제 브랜치 ref 없음 |
| 로컬 | master, HEAD32afb846d0bc69b38203a259dad71180cd4a14b5 |
| author | 유준상 / toast@southpaw.games, 기존 로컬 설정 유지 |
| remote | 미등록 유지 |

API의 기본 브랜치 이름 설정이 main이어도 빈 저장소에 main ref가 이미 존재한다는 뜻은 아니다. 공개 조회 성공은 현재 사용자의 push 권한 확인도 아니다. 상세 응답은 Git 제외 github-readonly-preflight.local.json에 있다.

향후 승인 시 연결 방법은 로컬 master를 유지하고 원격 main으로 매핑하거나, 별도 승인 후 로컬 브랜치를 main으로 정리하는 두 방식이 있다. 이번에는 실행하지 않았다. 최초 push 직전에 원격 ref/커밋을 다시 읽어 그동안 변경됐는지 확인해야 하며 force push로 해결하지 않는다.

이 저장소는 **공개** 상태이므로 최초 push 전에 회사 코드·아이콘·문서의 공개 권한, 배포 고지, author 이메일 노출, private token/설정/배포물 제외를 다시 확인해야 한다. 서명/TLS/서버 진위 검증 미구현 및 일반 프로그램 배포 보류 상태를 숨기지 않는다. 현재 공개 계정으로의 업로드와 나중의 회사→개인 소유권 이전은 별도 승인 사항이다.

## 7. LAN과 종료 상태

더미 환경의 현재 catalog는 lan-smoke-r1 한 개이며 LAN OFF/인터넷 OFF, 토큰은 ignore된 server.local.json에만 있다. 실제 승인 패키지 이름4개의 Distribution.package 요청 거부와 실제 ZIP SHA-256을 재확인했다. 현재8765 listener0, 이더넷 Public 프로필 유지. 실제 LAN 리스너/다른 PC 접속/방화벽·프로필 변경은 하지 않았다.

더미 시험 준비와 기존 [LAN 절차](LAN_ENVIRONMENT_PREPARATION.md)는 유지한다. 회사 담당자의 시험 PC/네트워크 정책/시험 시간 승인 후 제한된 더미로만 진행할 수 있다. 원래 WinError5의 발생 주체는 미확정이므로 “원인 해결 완료”로 승인 근거를 대체하지 않는다. 시험 중 같은 오류가 나면 기존 데이터와 로그를 보존하고 중단·확인한다.

HEAD와 master를 보존했고 stage/commit/amend/remote 변경/push/태그/정식 배포는 수행하지 않았다. Windows Use0, 기존 사용자 프로그램 실행/종료0. 이번 결과를 보고한 뒤 다음 단계로 자동 진행하지 않는다.
