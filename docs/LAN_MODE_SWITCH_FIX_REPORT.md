# LAN 모드 전환 오류 수정 및 실파일 회귀 검증

2026-11-04. 프로젝트 루트:
`C:\Users\SOUTHPAW GAMES\Documents\ChatGPT\통합 클라이언트 만들기`.
아래 근거 경로는 이 루트 기준이다. 실제 LAN 서버·방화벽 적용/삭제는 수행하지 않았다.

## 1. 재현과 직접 원인

조사 자료:

- 두 번째 시험의 `.test-results/lan-retry-192168019/RUN_COMMANDS.ko.md`,
  `actual-trial-progress.local.json`, `server.stdout.local.log`, `server.stderr.local.log`.
- 실제 재현 코드 `.test-results/lan-mode-fix-20261104/reproduce-replace.ps1`.
- 환경별 원시 결과 `reproduction-ps5.local.json`, `reproduction-ps7.local.json`.

실패한 명령은 격리된 실파일에서도 재현됐다.

```powershell
[IO.File]::WriteAllText("$T\mode.next", 'ON', [Text.UTF8Encoding]::new($false))
[IO.File]::Replace("$T\mode.next", "$T\mode.txt", $null)
```

T와 두 경로는 정상적인 절대 경로였고, source=ON/destination=OFF가 모두 있어도 실패했다.
한글·공백 경로와 ASCII·공백 경로에서 같았다. source 누락/target 누락도 별도로 시험했다.
이는 운영 서버 mode.txt가 아닌 새 조사 디렉터리의 파일로만 재현했다.

런타임 reflection으로 확인한 오버로드는 다음 두 개다.

```text
Void Replace(System.String, System.String, System.String)
Void Replace(System.String, System.String, System.String, Boolean)
```

실패 호출은 인자가 세 개이므로 세 string 오버로드다. 네 번째 bool 오버로드와의 혼동이 아니다.
같은 세 string 서명의 C# probe에서 세 번째 인자의 실제 바인딩을 확인했다.
PowerShell `$null`은 null reference가 아닌 길이0 문자열이었다.
`[NullString]::Value`는 실제 null reference였다.
C# 내부에서 `File.Replace(a,b,null)`을 호출했을 때도 정상 동작했다.
따라서 정상 source/destination 대신 세 번째 backup 인자에 빈 문자열이 전달된 것이 직접 원인이다.

| 실행 환경 | `$null` 호출 | `[NullString]::Value` | C# 직접 null | 유효한 backup 경로 |
|---|---|---|---|---|
| Windows PowerShell 5.1.26100.9711 / .NET Framework 4.8.9363.0 | 실패: The path is not of a legal form. | 성공 | 성공 | 성공 |
| PowerShell 7.6.5 / .NET 10.0.11 | 실패: The path is empty. (Parameter 'path') | 성공 | 성공 | 성공 |

원시 결과는 inner exception/parameter/stack도 담는다.
PS7은 ArgumentException, ParamName=path와 Path.GetFullPath를 기록했다.
런타임에 따른 오류 문구 차이는 있지만 null 바인딩 문제는 양쪽에 있다.
경로 구분자·한글·PowerShell 버전만의 문제로 단정하지 않는다.

## 2. 최소 수정과 정확한 운영 명령

검증된 작은 전용 스크립트:
`.test-results/lan-third-192168019/set-trial-mode.ps1`.
구현 원본과 신규 검사는 `.test-results/lan-mode-fix-20261104/`에 보존했다.

핵심 수정은 다음과 같다.

```powershell
# 이전
[IO.File]::Replace($sourcePath, $targetPath, $null)
# 수정
[IO.File]::Replace($sourcePath, $targetPath, [NullString]::Value)
```

유효한 backup 경로 방식도 성공했지만 이 작업에는 새 backup 관리가 필요하지 않으므로
명시적인 typed null을 선택했다. mode.previous 같은 파일을 backup으로 덮어쓰지 않는다.
backup 경로 충돌에 대한 현재 구현의 판정은 "경로를 사용하지 않음"이다.
동명 파일을 미리 만들어 내용이 보존되는지도 확인했다.

운영 문서와 테스트는 같은 전용 스크립트를 호출한다. 최종 공통 변수와 전환 명령:

```powershell
$T = 'C:\Users\SOUTHPAW GAMES\Documents\ChatGPT\통합 클라이언트 만들기\.test-results\lan-third-192168019'
$TrialShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
& $TrialShell -NoProfile -NonInteractive -File "$T\set-trial-mode.ps1" -Mode ON
& $TrialShell -NoProfile -NonInteractive -File "$T\set-trial-mode.ps1" -Mode OFF
```

이 명령은 지금 실행하지 않았다. 테스트에서는 T만 격리 폴더로 지정하고 TrialShell을
해당 검증 대상 PowerShell 실행 파일로 지정해 같은 명령 본문을 실제 실행했다.
운영 문서의 기본 실행 파일은 Windows PowerShell5.1이며 PowerShell7도 별도 검증했다.

스크립트는 기존 파일의 정확한 OFF/ON 및 BOM 없는 UTF-8을 확인한다.
완성된 새 값을 같은 디렉터리의 고유 임시 파일에 CreateNew/UTF-8/Flush로 준비하고,
별도 파일인지 확인한 뒤 File.Replace로 교체한다. 기존 mode.txt를 먼저 삭제하지 않는다.
기존 이름의 파일을 덮어쓰지 않는다. 임시 파일은 완성·검증 전 서버에 노출되지 않는다.
교체 뒤 실제 mode.txt를 읽어 요청 값과 일치할 때만 Confirmed=true를 반환한다.
실패한 임시 파일은 진단용으로 보존하고 서버는 이 파일을 읽지 않는다.
명시적 후속 시도는 새 고유 파일을 쓰므로 무관한 파일을 삭제하지 않는다.
자동 재시도/sleep은 없다.

교체 자체가 성공한 뒤 사후 읽기만 실패하는 경우에는 이미 값이 바뀌었을 수 있다.
이 경우에도 확인되지 않은 성공을 알리지 않으며 실제 모드·로그·리스너를 확인하고 시험을 중단해야 한다.
다른 프로세스가 동시에 상태를 바꾸는 모든 경우에 이전 상태를 보장한다는 뜻은 아니다.
전용 스크립트의 성공은 파일 전환 확인이며 실제 서버/LAN 성공은 별도 확인이다.

## 3. 실제 운영 명령과 테스트의 일치 증거

운영 문서: `.test-results/lan-third-192168019/RUN_COMMANDS.ko.md`.
실파일 검사: `.test-results/lan-mode-fix-20261104/test-real-mode.ps1`.

테스트는 문서의 MODE-ON-BEGIN/END 및 MODE-OFF-BEGIN/END 사이 코드 블록을
그대로 추출해 실행한다. 별도 정상 동작용 명령을 테스트에 복제하지 않았다.
테스트 폴더에는 운영 스크립트의 동일 복사본을 둔다.
각 환경의 `real-mode-ps5.local.json`, `real-mode-ps7.local.json`에는 다음을 저장했다.

- 운영 문서 경로/SHA-256, 운영 스크립트 경로/SHA-256.
- 문서에서 추출한 정확한 명령과 실행한 격리 경로.
- 명령마다 변경 전후 내용, 실제 child 종료 코드, stdout/stderr.
- 실패 조건의 실제 예외 및 변경 전후 bytes의 base64.

완료 후 68회 명령이 사용한 모든 복사 스크립트의 해시도 운영 스크립트와 대조했다.
구문 검사나 문자열 검사만으로 합격 처리하지 않았다.

## 4. 실파일 회귀 결과

두 PowerShell 모두 일반 사용자 컨텍스트에서 최종 합격했다. 관리자 토큰은 사용하지 않았다.
각 환경에 16개 실파일 상황을 만들고 각 상황에서 명시적 OFF→ON→OFF 전환을 실행했다.
총 명령 실행은 환경별 34회: 정상 종료 코드0 32회, 의도한 실패 코드1 2회다.
원시 JSON의 59개 row는 증거 기록 수이며 59개 독립 테스트라는 뜻이 아니다.

| 조건 | 최종 관측 |
|---|---|
| OFF→ON→OFF, 한글·공백 경로 | 양쪽 성공. 최종 OFF bytes=79,70,70, BOM 없음 |
| source 임시 파일 누락 | 예외, 기존 target bytes 보존 |
| target 누락 | 예외, target 임의 재생성 없음 |
| source가 잘못된 UTF-8/부분 O/빈 내용 | 예외, target 보존 |
| target 내용 BROKEN/BOM 포함 | 거부, 손상된 원문도 임의 복구/삭제하지 않음 |
| 잘못된/빈 경로 | 거부, target 보존 |
| target/source 읽기 허용·삭제 금지 핸들 | 실제 교체 실패, target bytes 보존 |
| 읽기 전용 target | 실제 교체 실패, target bytes 보존 |
| 임시 파일 생성 위치가 디렉터리 | 실제 쓰기/생성 실패, mode.txt 보존 |
| 임시 파일 이름에 다른 소유 파일 존재 | CreateNew 실패, 다른 파일 원문 보존 |
| mode.previous/mode.next 기존 파일 | 사용하지 않음, 원문 보존, 정상 전환 성공 |
| 실제 문서 명령에 target 누락 | 종료 코드1, 성공 메시지 없음, target 없음 유지 |
| 실제 문서 명령에 target 잠금 | 종료 코드1, 기존 OFF 유지, 실패 임시 파일 보존 |
| 실패 조건 해제 후 명시적 재시도 | 같은 문서 명령으로 ON→OFF 성공, 이전 실패 임시 파일 보존 |
| 무관한 파일 | 모든 상황에서 KEEP 내용 보존 |

손상/누락 fixture는 보존을 먼저 확인한 후 테스트 코드가 의도적으로 자기 fixture만 다시 준비했다.
실제 운영 상태 파일을 복구한 결과가 아니다.

중간 검사 실패도 숨기지 않는다.

1. 첫 후보는 PowerShell 문자열 비교에서 BOM 문자를 정확히 구분하지 못했다.
   테스트가 이를 발견해 Ordinal 비교로 보완했다. 최종 양쪽 검사는 보완된 같은 파일로 수행했다.
2. PS7 sandbox 실행 중 별도의 교체 오류가 관측됐다. 한 기록은
   "바꿀 파일을 제거할 수 없습니다."이며 target은 기존 ON을 유지하고 명령은 코드1로 실패했다.
   해당 `real-files-ps7-*/document-progress.local.json` 및 임시 파일을 보존했다.
   이후 PS5.1과 같은 일반 사용자 호스트 환경에서 전체 실파일 검사를 실행해 통과했다.
   sandbox가 직접 원인이라고 확정하지 않으며, 빈 backup 경로 오류와도 구분한다.
   이런 운영체제/파일 잠금 오류가 실제 시험에 재발하면 중단·보존해야 한다.

## 5. 기존 테스트 및 안전장치

- 기존 런처 테스트: 81/81 통과, 19.788초, failures=0/errors=0/skipped=0.
  근거 `.test-results/unit-tests.json/.log`.
- 이전 Python 운영 테스트 6/6, PS5.1 및 PS7 상태/UTC/부모 감시 검사 각각20/20,
  방화벽 모의/구문 검사11/11 통과.
- 과거 검사 코드를 `.test-results/lan-mode-fix-20261104/previous-operation-tests/`로 복사해
  실행했다. 원래 첫 시험 폴더에 새 mock/상태 파일을 쓰지 않았다.
- 기존 81개 소스는 수정하지 않았다. journal 잠금 회귀에서 의도적으로 발생시키는
  WinError5 로그는 예상 결과다. 이번 전체 실행에는 비의도적인 journal 오류가 없었다.
  과거 간헐적 journal WinError5의 잠금 주체는 여전히 미확정이며 이번 수정으로 해결했다고 보지 않는다.
- 세 번째 시험의 기존 runtime 5개 파일은 두 번째 시험 파일과 해시가 같다.
  1770/1790/1795초와 부모 정리 제한, Stopwatch/monotonic, UTC 함수,
  UTF-8 Read-State, 방화벽 생성/소유권/전체 범위 검사, 자기 서버만 종료,
  서버 종료 후 리스너0·기록된 규칙만 삭제 로직을 바꾸지 않았다.
- 설치·업데이트·복구 엔진, 서버 아키텍처, 기존 다섯 도구는 변경하지 않았다.

## 6. 변경 파일과 기록 보존

기존 파일 변경 없이 새 위치에만 준비했다.

- 신규 보고서: `docs/LAN_MODE_SWITCH_FIX_REPORT.md`.
- 신규 조사/테스트: `.test-results/lan-mode-fix-20261104/`의
  reproduce-replace.ps1, set-trial-mode.ps1, test-real-mode.ps1,
  before-files.local.json, reproduction-ps5/ps7.local.json,
  real-mode-ps5/ps7.local.json, final-verification.local.json 및 격리 실파일 증거.
- 신규 세 번째 시험: `.test-results/lan-third-192168019/`의
  기존 runtime 5개 복사본, set-trial-mode.ps1, RUN_COMMANDS.ko.md,
  prepared-manifest.local.json.
- 세 번째 폴더에는 mode.txt/intent/created/process/stop/finished/토큰/배포 ZIP을 복사하지 않았다.
  기존 lan-lab의 격리된 더미 v1/v2와 시험 설정을 재사용한다.
- 첫 시험78개, 두 번째 시험18개 파일의 개수와 해시가 모두 작업 전과 일치한다.
  로그/진행 기록/상태 파일/실패한 mode.next를 덮어쓰거나 삭제하지 않았다.
- 기존 제품·테스트·미커밋 문서 및 과거 기록의 baseline184개 hash entry가 모두 일치했다.
  근거 새 조사 폴더의 before-files.local.json 및 final-verification.local.json.
- 기존 다섯 프로젝트292개 파일/HEAD/tags/status 및 확인 가능한 원본 승인 ZIP4개 보존.
  TagMaster 승인 ZIP은 부재이며 검증 완료로 표시하지 않는다.

테스트/운영 스크립트는 기존 관례대로 Git ignored `.test-results`에 있다.
현재 로컬 보존이 필요하며 Git 체크포인트에 포함됐다는 뜻은 아니다.
향후 스크립트 보존 위치를 검토할 때도 실제 토큰/상태/패키지는 Git에서 제외해야 한다.

## 7. 최종 시스템 및 Git 상태

- DESKTOP-1MK6D95, 일반 사용자 토큰, 관리자 권한 사용0.
- TCP8765 리스너0, 해당 임시 방화벽 규칙0.
- 기존 Python 방화벽 규칙 및 프로필은 두 번째 시험 baseline과 일치.
- 실제 LAN 서버 실행0, 실제 방화벽 규칙 적용/삭제0, Windows Use0.
  기존81개 테스트의 loopback 서버는 격리 자동 테스트 범위이며 LAN 서버가 아니다.
- master, HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5`, remote 없음.
- stage/commit/push/tag/amend/remote 변경 없음. 작업 트리는 원래 미커밋 상태를 유지한다.
- 기존 modified: README.md, ROADMAP.md, docs/ARCHITECTURE.md,
  docs/CATALOG_TRUST_DESIGN.md, docs/LAN_ENVIRONMENT_PREPARATION.md.
- 기존 untracked: docs/CREATIVE_LAN_TRIAL_STATUS.md, docs/FIREWALL_RULE_REVIEW.md,
  docs/LAN_TRIAL_OPERATION_FIX.md, docs/WINERROR5_PREFLIGHT_REPORT.md,
  tests/test_journal_sharing.py.
- 이번 추가 untracked 문서는 본 보고서뿐이다. ignored 조사/시험 파일은 status 기본 출력에 나타나지 않는다.

## 8. 세 번째 시험 준비 판단

실제 사용할 전환 명령을 두 PowerShell에서 실파일로 실행하는 합격 기준은 충족했다.
세 번째 시험 절차는 `.test-results/lan-third-192168019/RUN_COMMANDS.ko.md`에 준비했다.
최종 승인 후 호스트/IP/회사 허용 범위/정책과 초기 상태를 확인하고 다음 순서로 진행한다.

1. 서버 관리자 콘솔: 임시 규칙 하나 추가·전체 조건 검증.
2. 서버 일반 콘솔: OFF 시작, 최대30분 타이머.
3. 승인 클라이언트: OFF TCP차단 확인.
4. 서버 일반 콘솔: 검증된 set-trial-mode.ps1 -Mode ON, 로그·실제 수신 주소 확인.
5. 승인 클라이언트: TCP연결, 정상/잘못된 토큰 검사.
6. 승인 클라이언트: 더미v1 다운로드·설치·실행.
7. 서버 기존admin 게시 CLI로 더미v2 게시, 클라이언트 업데이트·실행.
8. 서버 종료, 클라이언트 더미 오프라인 실행.
9. 서버 리스너0 확인 후 관리자 콘솔에서 기록된 규칙 하나만 제거.
10. 규칙0·리스너0·기존 설정/파일 보존을 실제 조회로 확인.

첫 두 시험은 OFF 차단만 확인됐으며 LAN ON·인증·설치·업데이트·실제 클라이언트 오프라인
실행은 여전히 미검증이다. 이번 작업의 파일 전환 성공을 해당 항목의 성공으로 기록하지 않는다.
실제30분 경과/관리자 콘솔/실제 LAN 동작도 이번에는 시험하지 않았다.
unsigned HTTP, 카탈로그 서명/TLS/서버 신원 검증 부재는 그대로다. 실제 앱 일반 배포는 보류한다.
운영 중 WinError5 등 예상하지 못한 오류는 해당 작업을 중단하고 로그/journal/설치 상태를 보존한다.
서버·방화벽·인터넷 공개 등 실제 시험으로 자동 진행하지 않았다.
