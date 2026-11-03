# v0.1.0 MVP 안정성 결함 수정 및 재검증 결과

> 이 문서는 해당 개발 단계의 기록입니다. 이후 로컬 체크포인트 승인·검사 결과는 [LOCAL_CHECKPOINT_REVIEW.md](LOCAL_CHECKPOINT_REVIEW.md)를 따릅니다. 과거 Git 상태·제한 및 초기 설계 내용은 현재 상태와 다를 수 있습니다.

2026-11-03 KST. 대상은 Southpaw Tools Launcher 소스 개발본이다. 사용자 첨부 요청에 따라 설치·제거 복구와 최소 상태 표시를 수정했다. **78개 자동 테스트 통과. 실제 LAN 시험은 실행하지 않았으며 별도 승인 단계로 남긴다. 카탈로그 진위 검증 미구현으로 실제 회사 프로그램의 일반 팀원 배포는 계속 보류한다.**

## 1. Baseline과 재현

[개발 보고서](<DEVELOPMENT_REPORT.md>), [MVP 감사](<MVP_LAN_AUDIT.md>), [LAN 절차](<LAN_TEST_RUNBOOK.md>), [등록부](<../PROJECT_REGISTRY.md>), [README](<../README.md>)와 엔진·기존 테스트를 대조했다.

수정 전에 audit.mvp_probes를 실행해 이전 9개 관찰(안전한 경계2, 한계7)을 그대로 재현했다. 기존 런처 파일53개는 아래 baseline에 원문 복사와 SHA-256 manifest로 보존했다. Git에 커밋이 없고 모든 소스가 untracked였으므로 git diff만으로 이번 변경을 구분하지 않았다.

- [원문 backup/manifest](<../.test-results/stability-baseline-20261103-122942/manifest.json>)
- [이번 변경·보존 대조 결과](<../.test-results/stability-preservation.json>)
- [검토용 변경 diff](<../.test-results/stability-changes.diff>)

이전 MVP 감사와 audit/mvp_probes.py는 **수정 전 재현 자료로 보존**한다. 이 프로브는 결함이 발생한다고 assertion하는 도구라 수정 후 합격 검사로 사용하지 않는다. 이번 회귀 검사는 새 tests/test_recovery.py와 tests/test_recovery_ui.py이다. 이전 감사의 F01/F03/F04/F06/F07은 아래 범위에서 보완했고, F02(신뢰 모델)와 F05(관리형 롤백 부재)는 미해결로 유지한다.

## 2. 제거 실패 원인과 수정

원인은 관리 파일을 바로 순차 삭제하고 active.json을 마지막에 삭제하던 구조였다. EXE 삭제 후 다른 파일에 접근 거부가 발생하면 포인터가 남고 동일 release 재설치도 거부했다.

현재 [uninstall](<../southpaw_tools/installer.py#L407>)은 다음 순서를 사용한다.

1. 동일 앱 OS 잠금, 미완료 작업 복구, 실행 중 여부 확인.
2. 모든 영수증/안전 상대 경로/해시 확인. 사용자 보존 경로, 원본과 다른 파일, 미등록 파일은 삭제 대상에서 제외.
3. 제거 대상과 기존 active 포인터를 durable journal에 저장.
4. 대상 파일 전부를 앱별 recovery/<작업ID>/files에 복사하고 원본·백업 SHA-256을 검증. 백업 하나라도 실패하면 원본 삭제를 시작하지 않음.
5. removing 단계 기록, 실행 중 여부 재확인, 각 원본 해시 재확인 후 삭제.
6. 관리 파일이 실제로 사라졌는지 확인한 다음 active.json을 제거하고 uninstalled 단계 확정.

삭제/포인터 제거 실패 시 검증된 백업으로 빠진 파일과 포인터를 복원하고 **오류를 반환**한다. 재시도할 수 있고, 단순 실패를 성공으로 안내하지 않는다. 복원 중 rename/권한 오류가 나면 recovery_required 상태와 백업을 보존한다. 다음 작업 또는 UI의 **복구 확인**으로 다시 복원을 시도한다. 사용자가 새로 쓴 다른 내용의 파일은 덮어쓰지 않는다.

제거 성공 후에도 복구 백업·영수증·미등록 파일을 자동 일괄 삭제하지 않는다. 관리 파일의 활성 payload 삭제와 포인터 제거가 정상 제거의 기준이며, 보존 영역의 복구 사본은 설치된 앱으로 취급하지 않는다. 이 보수적인 정책은 디스크 공간을 사용한다. 자동 보존 기간/정리 기능은 추가하지 않았다.

## 3. 활성화 중단 후 재시도 및 설치 상태 정책

원인은 stage→release rename 직후 프로세스가 종료되면 release 폴더가 남고 다음 설치가 폴더 존재만으로 거부되던 구조였다.

현재 [install](<../southpaw_tools/installer.py#L98>)은 앱별 transactions/<UUID>.json을 원자적으로 저장한다. 영수증에도 transaction_id를 넣어 이 작업이 만든 release인지 확인한다.

| 단계 | 의미/복구 정책 |
|---|---|
| downloading | 전송 중. 중단 시 journal이 소유한 UUID 임시 ZIP을 후속 정리 |
| download_verified | ZIP 크기/SHA-256 검증 완료 |
| preparing | 추출/EXE/필수 경로 검사와 선언된 사용자 데이터 이전 중 |
| ready | 새 payload·영수증 준비 완료, 기존 활성 버전 유지 |
| switching | rename 직전 기록. 기존 폴더/repair 백업/새 target의 실제 위치 대조 |
| activating | active.json 교체 직전. 포인터·작업 영수증·실행 파일을 대조 |
| activated | 포인터와 로컬 실행 파일 검증 후 활성화 확정 |
| failed | 이전 상태로 돌아온 실패. 임시 정리만 남으면 후속 재시도 |
| recovery_required | 파일·포인터 충돌/권한/손상 등으로 자동 복구를 확정할 수 없음. 보존 후 명확히 오류 |

다음 설치·업데이트·제거·실행과 명시적 recover 요청은 동일 앱 잠금 아래 journal을 먼저 대조한다. UI는 미완료 기록이 있으면 서버 없이 **복구 확인**을 제공한다. 복구 확인 자체가 프로그램을 자동 실행하지 않으며 완료 후 사용자가 실행/설치를 다시 선택한다.

새 active 포인터가 실제 새 영수증/정상 EXE와 일치하면 완료로 인정한다. _activate가 포인터 저장 후 예외를 내더라도 읽기 검증 후 성공과 사후 경고를 구분한다. 정상 이전 버전이 있고 새 활성 파일이 손상되거나 포인터가 읽히지 않으면 검증 가능한 이전 포인터로 복원을 시도한다. 모르는 포인터/폴더를 무조건 덮어쓰지 않는다.

활성화 전 남은 새 target/staging은 소유권을 확인해 recovery/<작업ID>/aborted-release 또는 aborted-stage로 이동해 보존한다. 기존 정상 버전은 지우지 않으며, 다음 명시적 설치 요청이 같은 ID로 다시 진행될 수 있다. 출처를 입증할 journal이 없는 기존 폴더는 자동 삭제/덮어쓰지 않는다.

**기존 버전 보존과 오류 복원은 관리형 롤백 기능이 아니다.** 임의의 이전 정상 release를 선택하는 API/UI는 구현하지 않았다. journal 손상, 계속되는 디스크/권한 오류, 백업 손상, 외부에서 만든 포인터/파일 충돌은 자동 복구가 불가능할 수 있으며 운영자 확인이 필요하다. 전원 손실·파일시스템 손상 전체를 보장하는 것은 아니다.

## 4. EXE 누락과 사용자 파일 보존

작업 기록 없이 EXE만 사라졌지만 설치 포인터는 남아 있는 경우, UI는 실행 가능으로 표시하지 않고 **복구 필요**로 표시한다. 서버에서 받은 정보가 기존 설치 기록과 정확히 같은 승인 배포본이면 **복구 설치**할 수 있다. 동일 ID의 ZIP 해시 변경은 계속 거부한다.

복구 설치도 먼저 ZIP/EXE를 검증하고 새 staging을 준비한다. 기존 payload 전체는 recovery/<작업ID>/previous-release에 보존한 후 새 payload로 전환한다. 이전 폴더를 무조건 삭제하거나 그 위에 추출하지 않는다. 알려진 보존 경로만 새 payload로 복사하고, 미등록 작업물은 이전 보존 폴더에 남겨 경고/로그로 위치를 알린다.

외부 QSettings/AppData/작업 파일과 기존 Desktop 설치본은 건드리지 않는다. 설정·로그·프리셋은 기존 preserve_paths와 해시/미등록 파일 보호 정책을 유지한다. 복구 사본에서 사용자 데이터까지 자동 일괄 정리하지 않는다. [데이터 정책](<DATA_POLICY.md>)을 보완했다.

## 5. 성공 후 정리 실패

[사후 정리](<../southpaw_tools/installer.py#L261>)는 활성화 결과와 분리했다. 새 포인터와 실행 파일을 확인한 후 다운로드 ZIP 삭제가 실패하면 정상 설치는 성공으로 유지하고, UI 경고·logging·apps/<app_id>/recovery-warnings.log에 정리 보류를 기록한다. 로그 파일 자체가 쓰기 불가여도 검증된 성공 결과를 실패로 뒤집지 않는다.

정리되지 않은 journal은 후속 앱 작업에서 다시 확인한다. 완료 journal은 다른 새 버전을 되돌리지 않고 자신이 소유한 UUID 다운로드만 정리한다. 중단 payload/사용자 변경 파일은 이 자동 정리 대상으로 삼지 않는다. 쓰기 권한이 계속 없어 기록/정리를 모두 할 수 없는 환경에서는 운영자 확인이 필요할 수 있다.

## 6. 카탈로그와 로컬 실행 분리

[UI render](<../southpaw_tools/ui.py#L357>)와 [실행/설치 선택](<../southpaw_tools/ui.py#L542>)에서 로컬 설치 읽기·EXE 검사와 카탈로그 release 비교를 나눴다.

- 같은 release_id의 서버 해시 충돌이 있어도 검증된 로컬 설치 버전은 그대로 표시하고 실행 가능.
- 서버 접속 실패/목록 오류는 신규 설치·업데이트를 차단하고 현재 설치 실행은 유지.
- 충돌한 서버 목록은 cache나 active 포인터에 덮어쓰지 않음.
- EXE/필수 파일 누락·변조는 복구 필요로 표시하고 정상 실행으로 오인하지 않음.
- 카탈로그의 package_name/package_type에 잘못된 타입이 올 때 예상 가능한 LauncherError로 거부하도록 입력 검증도 소폭 보강.

## 7. 연결 상태 최소 개선

큰 레이아웃이나 Markdown 렌더링은 바꾸지 않았다. 상단 상태 문구를 다음 사실로 분리했다.

- 서버: 마지막 health 응답 확인/접속 실패/확인 중/재확인 필요와 마지막 확인 시각.
- 목록: 캐시/초기 목록, 검증 성공(서명 없음), 조회 실패/충돌/설정 오류.
- 패키지: 미시도, 다운로드·검증 성공, 다운로드/검증 실패, 수신 검증 성공 후 설치 실패.
- 접속 대상 경로: URL 기준 로컬(loopback) 또는 LAN(IP). VPN/OS의 실제 라우팅 홉을 측정한 것은 아님.
- 서버 LAN ON/OFF: 마지막 health의 listener 설정이며 현재 client가 LAN을 통과했다는 뜻과 분리.

다운로드 실패만으로 서버 전체가 OFF라고 단정하지 않는다. 재확인이 필요하다고 표시하고 다음 설치에는 새 조회를 요구한다. 마지막 성공이 현재 접속을 계속 보장하지 않는다는 문구를 사용한다. 별도 자동 heartbeat는 이번 범위에서 추가하지 않았다.

## 8. 카탈로그 보안 검토

서명된 카탈로그·고정 공개키·개인키 관리자 전용 보관·키 회전·만료/sequence·TLS 서버 진위 검증의 구현 가능성과 검증 기준을 [CATALOG_TRUST_DESIGN.md](<CATALOG_TRUST_DESIGN.md>)에 기록했다. HttpProvider에도 현재 unsigned HTTP의 신뢰 한계를 명시했다. 새 암호화 의존성/실키/인증서 발급은 추가하지 않았다.

실제 프로그램 일반 배포 보류는 유지한다. 제한된 LAN 시험은 승인된 더미 전용이며 실제 LAN/인터넷 공개를 이번 수정에서 진행하지 않았다.

## 9. 테스트 및 실패 주입 결과

**기존42 + 신규36 = 총78개, failures0/errors0/skipped0, PASS(19.182초).** Windows11 build26200, Python3.13.7, PySide6/Qt6.11.0. 기존 tests 파일은 수정하지 않았다.

| 요구 | 재현/검증 결과 |
|---|---|
| A 제거 파일 삭제 실패 | EXE 삭제 후 asset 삭제 거부→EXE 복원, 오류 안내, 다음 제거 재시도 성공. 백업 복사 실패/포인터 삭제 실패도 원본 복원 |
| B EXE 없음/포인터만 있음 | 실행 거부→같은 승인 배포본 복구 설치 성공, 설정 이전·미등록 작업 보존. UI 복구 필요/복구 설치 확인 |
| C 활성화 직전 중단 | 단계별 SystemExit와 자식 프로세스 os._exit 전후 시험. 이전 버전 유지, 소유 orphan 보존 후 같은 작업 재시도 성공 |
| D 활성 전환 실패 | rename 거부, malformed pointer, 새 EXE 소실, 포인터 저장 직후 예외. 가능한 이전 상태 복원 또는 실제 성공 검증. 다른 포인터는 덮어쓰지 않고 복구 필요 |
| E 사후 정리 오류 | 다운로드 unlink 거부·완료 기록 저장 거부·경고 로그 쓰기 불가에서 실제 활성 버전 검증 후 성공+경고. 다음 업데이트/정리 재시도 성공 |
| F 카탈로그/서버 오류 | 초기/refresh 충돌, 목록 조회 실패, 잘못된 응답·설정, 다운로드 실패 후에도 정상 로컬 실행 가능. cache/active 원문 보존 |
| G 기존 보안 방어 | 기존42개에서 ZIP 탈출/해시 불일치/실제 loopback HTTP 중단·취소/읽기 전용 API/인터넷 거부 등 유지 |
| H 동시 요청 | 동일 앱 설치·제거·실행 잠금 거부, 실제 thread 경쟁과 별도 Python process 잠금 확인 |
| 보존 충돌 | 복원 대상에 사용자가 새 내용을 쓰면 덮어쓰지 않고 기록/백업 보존 |

프로세스 중단 시험은 테스트가 생성한 Python 자식이 자기 자신을 os._exit(73)로 종료한다. 다른 PID 종료/프로세스 검색 후 kill은 하지 않았다. 기존 5개 도구 EXE·Photoshop·Aseprite는 실행하지 않았다.

추가로 기존 무해한 콘솔 더미 r1/r2를 새 .test-results/stability-rehearsal에 복사해 loopback HTTP 설치→서버 중단→실제 오프라인 실행을 재검증했다. 두 빌드 모두 종료코드0, 같은version/다른ID 업데이트, 선언 설정 이전, 이전 미등록 파일 보존 확인. 기존 감사 fixture를 재사용했고 새 정식 EXE/ZIP 빌드는 하지 않았다.

Qt offscreen 100/125/150%에서 창 생성/5개 등록 성공. 기존 UI 테스트의980×700/1240×820/1600×1000 버튼 경계 검사도 통과했다. [상태 문구 화면](<../.test-results/stability-ui.png>)을 시각 확인했다. 실제 물리 모니터·회사 LAN·보안 제품·Windows10·실제5개 앱 기능 QA는 미실행이다.

근거:

- [전체 테스트 JSON](<../.test-results/unit-tests.json>), [로그](<../.test-results/unit-tests.log>)
- [엔진 신규27개](<../tests/test_recovery.py>), [UI 신규9개](<../tests/test_recovery_ui.py>)
- [실제 더미 오프라인 실행](<../.test-results/stability-rehearsal/local-rehearsal.json>)
- [DPI 결과](<../.test-results/stability-dpi.json>)

## 10. 수정 파일·기존 프로그램 보존

기존 파일 수정6개:

- [installer.py](<../southpaw_tools/installer.py>): 작업 기록, 복구/수리, 제거 백업·복원, 커밋 결과와 정리 경고 분리.
- [ui.py](<../southpaw_tools/ui.py>): 로컬 실행 독립화, 복구 확인/복구 설치, 상태 문구.
- [catalog.py](<../southpaw_tools/catalog.py>): 잘못된 package 필드 타입 거부.
- [providers.py](<../southpaw_tools/providers.py>): 현 신뢰 경계 docstring만 보완, HTTP 동작 변경 없음.
- [README.md](<../README.md>), [DATA_POLICY.md](<DATA_POLICY.md>): 현재 복구/보존/배포 보류 안내.

새 파일4개: 엔진/UI 회귀 테스트2개, 이 보고서와 카탈로그 신뢰 설계 문서. 기존 미커밋 원문은 baseline에 보존했다. 이전 감사 문서/원래42개 테스트/등록부/ROADMAP/서버 코드/카탈로그JSON/배포 ZIP은 변경하지 않았다. 기계 판독 보존 대조는 위 stability-preservation.json을 따른다.

기존5개 repo baseline 대상292개 파일 해시, HEAD/태그/Git 상태 모두 동일. 원본 승인 ZIP4개와 런처 distribution 복사본도 카탈로그의 고정 SHA-256과 일치. Tag Master 승인 ZIP은 여전히 미확보이며 설치 비활성 유지. ignored 원본 파일 전체의 전수 검증을 의미하지는 않는다.

## 11. Git·제한 준수와 다음 단계 판정

Git은 master, 커밋 없음, remote 없음, 기존과 같이 untracked 개발본이다. **staged 파일0, stage/commit/push0, 원격 변경0, 정식 빌드0, 정식 배포0.** Windows Use0, 실제 사용자 설치 경로 변경0, LAN listener0, 실제 사용자 프로그램 실행0. 검증 server는127.0.0.1만 사용했고 종료했다. 방화벽·공유기·네트워크 프로필을 변경하지 않았다.

**판정:** 이번 실패 주입 범위의 안정성 수정과 재검증은 통과했다. 별도 승인 후 더미만 사용하는 첫 LAN 시험 준비는 가능하다. 실제 LAN 성공을 확인했다고 보고하지 않으며 이번 턴에서 다음 단계로 자동 진행하지 않는다. 서명·서버 진위 검증과 실제 PC QA가 남아 있으므로 일반 팀원 실제 도구 배포/인터넷 공개는 계속 보류한다.

ROADMAP의 LAN/설치 안정화→관리자 배포→런처 자체 업데이트→인터넷 옵션→UI 완성도 방향은 유지한다. Pixel Effect Maker와 중단 Pixel Motion Studio는 제외한다. 회사 GitHub→개인 계정 이전은 소유권과 회사 승인 전 진행하지 않는다.
