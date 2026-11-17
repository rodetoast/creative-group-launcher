# 첫 LAN 시험 운영 결함 수정 및 재시험 준비

2026-11-04. 이번 작업은 시간 계산과 PowerShell 상태 파일 처리에 한정했다.
실제 LAN 서버 시작, 방화벽 변경, 기존 설치·업데이트 엔진 변경은 하지 않았다.

## 1. 확인된 조기 종료 원인

첫 시험 기록은 `.test-results/lan-approved-192168019/`에 보존했다.

- `process.local.json`: StartedUtc `2026-11-04T02:04:09.4029234Z`.
- `finished.local.json`: 최종 수정 UTC `2026-11-04T02:08:16.2331783Z`.
- 두 시각의 차이는 약 4분 7초다. 약 3분이라는 기억보다 파일 기록을 기준으로 판단한다.
- `server.stdout.local.log`에는 OFF 메시지만 있고 stderr는 비어 있다.
- `actual-trial-progress.local.json`에 LAN_ON_attempted=false, 자동 만료 미도달,
  외부 조정 명령의 잘못된 만료 판단 및 종료 요청이 기록돼 있다.

결함은 서버의 30분 타이머가 아니라 조정 과정의 다음 임시 명령이었다.

```powershell
# 사용 금지: PS7의 DateTime을 다시 문자열로 바꿔 파싱한다.
[datetime]::Parse($state.StartedUtc).ToUniversalTime()
```

같은 실제 파일을 PowerShell 7.6.5에서 읽어 재현했다.
ConvertFrom-Json의 StartedUtc는 `System.DateTime`, Kind=Utc이고 원래 값은
`2026-11-04T02:04:09.4029234Z`다. 위 재파싱 결과는
`2026-11-03T17:04:09.0000000Z`로 9시간 이전이 된다.
문자열 변환 과정에서 시간대와 소수 초 정보가 사라지고 로컬 KST로 다시 해석됐기 때문이다.
이 잘못된 값으로 만료를 판단해 stop.request를 기록했다. 실제 타이머가 조기 만료됐다는 증거는 없다.
해당 명령은 저장된 제품/운영 스크립트 내부에 있지 않았으므로 외부 명령을 그대로 패치할 파일도 없다.
재사용 가능한 UTC 함수와 명시된 절차로 이 임시 명령을 대체했다.

## 2. 시간 처리 변경과 30분 상한

근거 파일: 원래 시험 폴더의 `trial-common.ps1`, `proposed-trial-start.ps1`, `trial-server.py`.
동일한 운영 코드의 재시험 복사본은 `.test-results/lan-retry-192168019/`다.

- ConvertTo-TrialUtc: DateTime은 Kind를 보존해 변환하고 DateTimeOffset은 UTC로 정규화한다.
  문자열은 Z 또는 명시적 offset을 요구한다. 시간대 없는 값은 거부한다.
- Get-TrialElapsedSeconds: PS5.1의 문자열과 PS7의 DateTime을 모두 처리한다.
  표시·감사용이며 세션을 중지하거나 연장하는 판단에 사용하지 않는다.
- 부모의 기존 Stopwatch 감시와 자기 자식만 종료하는 정리 코드를 Wait-TrialChild,
  Stop-TrialChild로 추출해 같은 로직을 짧게 검증했다.
- Python의 기존 monotonic 기반 루프를 run_session으로 추출했다.
  테스트에서만 가짜 controller와 짧은 제한시간을 주입한다. 실제 CLI는 시간을 받지 않는다.
- 운영 기본값 유지: Python 정상 종료 1770초, 자기 프로세스 hard stop 1790초,
  부모 감시 1795초 + 정리 최대 2초 + 종료 확인 최대 2초. 1800초로 늘리지 않았다.
  OS 실행 정지/스케줄링 지연까지 실시간 보장한다는 뜻은 아니다.
- UTC 직렬화는 기존 ISO 8601 Z 기록을 유지한다. Python은 종료 제한에 wall clock을 쓰지 않는다.
  모드 변경으로 타이머를 재시작하지 않는다. sleep이나 재시도 루프를 추가하지 않았다.

## 3. PowerShell 5.1 상태 파일

원인: Save-NewState는 BOM 없는 UTF-8을 쓰는데 PS5.1의 Get-Content 기본 ANSI 해석이
한글 경로를 손상시켰다. 실제 process.local.json 기본 읽기에서 unrecognized escape sequence를
재현했고 `-Encoding UTF8`으로 경로가 정확하게 일치함을 확인했다.

Read-State의 기존 UTF-8 명시 수정을 유지하고 ConvertFrom-Json도 ErrorAction Stop으로
처리했다. 누락/빈 파일/손상/읽기 잠금은 파일명을 포함한 오류를 내고 중단한다.
Save-NewState의 임시 파일 작성 후 Move, 기존 파일 덮어쓰기 거부는 유지한다.
상태 파일 손상을 무시하거나 삭제 후 재시작하지 않는다. 실패 시 생성 기록을 보존하며
제거 스크립트는 소유권·전체 조건 확인 전 규칙을 삭제하지 않는다.

시험 당시 관리자 콘솔이 인코딩 수정 후 동일 파일을 읽고 규칙 제거에 성공했다는 사용자 결과가 있다.
이번 자동 검증은 일반 사용자 컨텍스트의 PS5.1 및 PS7에서 수행했다.
이번에는 실제 관리자 콘솔을 새로 조작하지 않았으므로 관리자/일반 콘솔 간 ACL까지 다시
실측했다고 주장하지 않는다. 다음 실제 시험 전 관리자 콘솔에서도 정책·파일 접근을 확인한다.

## 4. 자동 검증 결과

| 검증 | 결과 | 범위 |
|---|---|---|
| 기존 전체 회귀 | 최종 81/81 통과, 19.596초 | 기존 소스 수정 없음, 더미 및 loopback |
| Python 운영 테스트 | 6/6 통과 | 가짜 controller, 실제 소켓 없음 |
| Windows PowerShell 5.1.26100.9711 | 20/20 검사 통과 | 실제 UTF-8 파일과 자기 더미 프로세스 |
| PowerShell 7.6.5 | 20/20 검사 통과 | 같은 검사, 날짜 JSON 형식 차이 포함 |
| 기존 방화벽 모의/구문 검사 | 11/11 통과 | 실제 방화벽 호출 0, 서버 시작 0 |

신규 파일:
`.test-results/lan-approved-192168019/test-operations.py`, `test-state.ps1`.
Python은 0.6초 정상 제한과 조기 종료 방지, wall clock 변화 무관성, stop.request,
모드 오류/누락 후 정리, 응답 없는 가짜 child의 실제 os._exit watchdog, 운영 기본값/CLI 가드를 검사했다.
PowerShell은 한글 JSON 왕복, BOM 없는 UTF-8, 기존 파일 덮어쓰기 거부, 누락/손상/빈 파일,
배타 잠금 시 중단·해제 후 복구, 공유 핸들 읽기, Z/KST/UTC·Local DateTime 변환,
시간대 없는 값 거부, 0.6초 부모 감시와 자기 자식 종료를 검사했다.
30분 실시간 시험과 실제 LAN 성공을 의미하지 않는다.

실패 이력도 보존했다.

1. 첫 sandbox 실행은 loopback 접근 WinError 10013으로 5개 오류.
   `suite-sandbox-denied.json/.log`에 보존. 정책 변경 없이 sandbox 밖에서 재검증했다.
2. 다음 전체 실행은 journal 교체 WinError 5로 2개 오류.
   `suite-winerror5.json/.log`에 원래 스택과 파일 경로를 보존했다.
   실패한 두 테스트 개별 재실행은 2/2 통과, 후속 전체 실행은 81/81 통과했다.
   정확한 잠금 주체는 확인되지 않았다. 이번 두 운영 결함 수정으로 해결됐다고 판단하지 않는다.
3. 실패 로그 출력 중 cp949에서 UnicodeEncodeError도 발생했다. 파일 로그는 정상 UTF-8로 남았다.
   후속 실행은 프로세스 한정 PYTHONUTF8=1로 출력했다. 시스템 설정/테스트 소스 변경은 없다.

## 5. 보존과 최종 상태

최종 근거: `.test-results/lan-approved-192168019/operation-fix-results.local.json`,
`.test-results/unit-tests.json`, `docs/existing-projects-verification.local.json`.

- 8765 리스너 0개, 시험 규칙 0개. 기존 Python 규칙과 방화벽 프로필이 첫 시험 baseline과 일치.
- 기존 다섯 저장소 292개 파일, HEAD/tags/status 보존. 확인 가능한 승인 ZIP 4개 해시 보존.
  TagMaster 승인 ZIP은 여전히 부재이며 검증했다고 표시하지 않는다.
- 실제 LAN 요청/서버 실행/방화벽 적용 0. Windows Use 0. 사용자 프로그램 조작 없음.
- master, HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5`, remote 없음.
  stage/commit/push/tag/amend/remote 변경 없음.
- 기존 미커밋 변경: README.md, ROADMAP.md, docs/ARCHITECTURE.md,
  docs/CATALOG_TRUST_DESIGN.md, docs/LAN_ENVIRONMENT_PREPARATION.md 유지.
- 기존 untracked: docs/CREATIVE_LAN_TRIAL_STATUS.md, docs/FIREWALL_RULE_REVIEW.md,
  docs/WINERROR5_PREFLIGHT_REPORT.md, tests/test_journal_sharing.py 유지.
- 이번 일반 문서 신규 파일은 본 보고서뿐이다. 설치·업데이트 엔진과 기존 테스트는 수정하지 않았다.

## 6. 수정 및 신규 파일

첫 시험 폴더 `.test-results/lan-approved-192168019/` 내부:

- 수정: trial-common.ps1, proposed-trial-start.ps1, trial-server.py, RUN_COMMANDS.ko.md.
- 신규: test-state.ps1, test-operations.py, RETRY_RUN_COMMANDS.ko.md,
  operation-fix-results.local.json, 실패 이력 suite-*.json/.log.
- 검사 도구가 남긴 mock-*/state-test-*는 격리 결과이며 실제 방화벽 기록과 별도다.
  원래 intent/created/process/finished/removed 및 오류 로그는 보존했다.

새 재시험 폴더 `.test-results/lan-retry-192168019/` 내부:

- trial-common.ps1, proposed-firewall-add.ps1, proposed-firewall-remove.ps1,
  proposed-trial-start.ps1, trial-server.py: 검증된 운영 코드 복사본.
- RUN_COMMANDS.ko.md: 정확한 시작/ON/OFF/종료/관리자 정리 절차.
- prepared-manifest.local.json: 파일 SHA-256. 과거 스크립트 준비 manifest는 역사 자료이며 현재 해시는 이 파일 기준.
- intent/created/process/stop/finished/토큰/배포 ZIP은 복사하지 않았다.
  기존 격리된 lan-lab의 더미 catalog와 시험용 설정만 사용한다.

`.test-results`는 Git ignore 대상이다. 이번 운영 수정과 신규 검사는 아직 Git 추적 대상이 아니며
커밋·Push하지 않았다. 향후 체크포인트 검토 시 비밀정보 없는 스크립트/검사를 추적 위치로 옮길지
별도 검토해야 한다. 현재는 이 로컬 폴더를 보존해야 재현 가능하다.

## 7. 재시험 판단과 명령

두 운영 결함에 대한 준비·격리 검증은 완료했다. 더미 LAN 재시험을 준비할 수 있지만
실제 시험 성공, 30분 실시간 검증, journal 간헐 오류 해결, 실제 앱 배포 준비 완료를 뜻하지 않는다.
journal 오류가 다시 나면 설치·업데이트를 성공으로 기록하지 말고 중단·보존한다.
unsigned HTTP/서버 신원 미검증은 그대로다. TLS·카탈로그 서명·신규 기능은 추가하지 않았다.

사용할 절차: `.test-results/lan-retry-192168019/RUN_COMMANDS.ko.md`.
새 시험 최종 승인 후 관리자 환경/정책 검사 및 add → 일반 사용자 start(OFF) →
192.168.0.19 OFF 확인 → 환경 재확인 후 ON → 인증/더미 v1/v2 →
stop.request → 리스너 0 확인 및 오프라인 실행 → 관리자 remove → 규칙 0 확인 순서다.
자동 타이머는 방화벽 규칙을 제거하지 않는다. 예상치 못한 오류/정책 거부/범위 차이는 중단한다.
이번 작업에서 실제 시험으로 진행하지 않았다.
