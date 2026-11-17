# 더미 전용 LAN 시험 환경 준비 결과 및 실행 절차

현재 제품 방향은 Creative Group Launcher의 비용0원·회사 LAN 전용이다. 본문의 loopback 결과는 과거 검증 기록이며 실제 PC 간 시험 결과가 아니다.
이번 실제 LAN 시험의 선행 조건·미실행 항목은 [CREATIVE_LAN_TRIAL_STATUS.md](CREATIVE_LAN_TRIAL_STATUS.md)를 따른다. 허용 범위와 시험 PC가 확인되기 전에는 이미 완료한 loopback을 반복하지 않고 listener를 닫아 둔다.

> 이 문서는 해당 개발 단계의 기록입니다. 이후 로컬 체크포인트 승인·검사 결과는 [LOCAL_CHECKPOINT_REVIEW.md](LOCAL_CHECKPOINT_REVIEW.md)를 따릅니다. 과거 Git 상태·제한 및 초기 설계 내용은 현재 상태와 다를 수 있습니다.

2026-11-03 KST. **준비와 loopback 검증 완료, 실제 다른 PC/LAN 연결은 미실행.** 실제 LAN listener는 별도 시험 승인 후에만 실행한다. unsigned HTTP·공유 토큰은 실사용 배포 안전성을 보증하지 않으며 실제 회사 프로그램 일반 배포는 계속 보류한다.

## 1. 준비한 환경

실제 [distribution](<../distribution>)과 다른 디렉터리에 시험 환경을 만들었다. 기존 무해한 .NET 콘솔 fixture r1/r2를 고정 SHA-256으로 확인해 재사용했고 새 EXE 빌드는 하지 않았다.

| 구성 | 개발 PC의 준비 위치 |
|---|---|
| 시험 전체 루트 | [lan-lab](<../.test-results/lan-lab>) |
| 서버의 배포 루트 | [repository](<../.test-results/lan-lab/repository>) |
| 시험 목록 | [repository/catalog.json](<../.test-results/lan-lab/repository/catalog.json>) — lan-smoke 하나, 현재 r1 |
| 더미 입력 v1/v2 | [inputs](<../.test-results/lan-lab/inputs>) — 기존 감사 ZIP 복사본 |
| 비밀 서버 설정 | [server.local.json](<../.test-results/lan-lab/server.local.json>) — 시험용 임의 토큰, LAN OFF/인터넷 OFF |
| 전달 준비용 소스 묶음 | [client-bundle](<../.test-results/lan-lab/client-bundle>) — 더미 초기 목록, 토큰/ZIP/사용자 설정 없음 |
| 검증용 설치 루트 | [verification-final/client](<../.test-results/lan-lab-verification-final/client>) — 실제 사용자 설치 경로와 분리 |

이 구조는 별도 Windows 계정/VM/ACL 보안 경계를 만든다는 뜻은 아니다. 파일 경로·카탈로그·패키지와 HTTP 접근 경계를 분리했다. 같은 OS 계정의 로컬 파일 쓰기 권한자는 여전히 신뢰 대상이다.

v1/v2는 빌드 lan-smoke-r1/r2이며 표시 버전은 둘 다0.0.1이다. 새 release_id만으로 업데이트되는 조건까지 확인한다. 콘솔 앱은 빌드 이름만 출력하고 종료한다. Python/PySide6와 .NET Framework 실행 환경/회사 EDR 허용은 시험 PC에서 별도 확인해야 한다.

## 2. 기존 구현 재사용과 접근 차단

[audit/lan_lab.py](<../audit/lan_lab.py>)는 준비·시작 전 검사 도구다. 설치/복구/서버를 다시 구현하지 않는다. [admin.publish](<../southpaw_tools/admin.py#L16>)가 이미 --root/명시 승인/ZIP·EXE 검증/원자적 게시를 지원해 그대로 재사용했다. 시험 앱 초기 등록은 catalog seed로 하고 실제 게시부터 기존 CLI/API가 담당한다.

시작 전 검사는 다음 조건을 확인한다.

- 시험 루트는 Git 제외 .test-results의 독립 하위 폴더, 시험 표식 필수. 실제 distribution을 지정하면 거부.
- app_id=lan-smoke 하나만 허용. 알려진 두 ZIP/EXE 해시, 실행/cwd/필수/보존 경로만 허용.
- repository/packages에 알 수 없는 ZIP·디렉터리·변조 파일이 있으면 거부. 링크/정션도 거부.
- 전달 후보에는 실제5개 목록·ZIP/EXE/DLL·사용자 settings/cache/active/receipt·로컬 설정·시험 토큰을 넣지 않음.
- LAN 설정이 ON이어도 --approve-lan을 명시하지 않으면 backend를 호출하기 전에 거부.

가드는 시작 시점 검사다. 시작 후 신뢰된 로컬 관리자가 디스크를 임의 수정하는 것까지 서명 없이 방어하는 시스템은 아니다. 기본 southpaw_tools.server를 직접 실행하면 이 시험 가드를 우회하므로 이 절차에서는 반드시 audit.lan_lab serve 진입점을 사용한다.

## 3. 이번 사전 점검 결과

- IP/프로필/포트는 읽기 전용 PowerShell 조회. [로컬 상세 결과](<../.test-results/lan-network-preflight.local.json>)에 실제 IP와 프로필을 기록했고 Git에서 제외한다.
- 이더넷의 사설 IPv4와 gateway가 있는 인터페이스를 후보로 식별했다. Bluetooth의169.254 주소는 후보에서 제외했다. 회사망 소속·시험 PC 라우팅은 아직 확인하지 않았다.
- 현재 이더넷 프로필은 **Public**이다. 임의로 Private 전환하거나 Public 전체 허용 규칙을 만들지 않는다. 회사 담당자가 올바른 시험 인터페이스와 제한적 허용 정책을 먼저 확인해야 한다.
- 조회 시점8765 점유0. 실제 loopback127.0.0.1:8765 바인딩→중지→재사용을 검증했다. 향후 시험 직전 재확인이 필요하다.
- LAN ON 시 loopback+정확한 사설IP를 요청하는 계약, 설정 수정만으로 live 상태가 바뀌지 않는 점, 재시작 후 OFF 적용은 **소켓 없는 모의 listener**로 검증했다. 실제 LAN 주소 bind 성공이나 다른 PC 연결을 증명한 것은 아니다.

## 4. 실행 검증 결과

정식 회귀 테스트 **78개, 실패0/오류0/skip0,19.492초 PASS**. 기존78개 코드·엔진·UI·서버는 이번에 변경하지 않았다. journal 복구·제거 실패 복원·활성화 중단 재시도·오프라인 실행·후처리 경고·파일 보존·앱 잠금 검증을 유지했다.

추가 제한 검사 결과: [lan-preparation-checks.json](<../.test-results/lan-preparation-checks.json>).

| 검사 | 결과 |
|---|---|
| 준비한 OFF config의 실제 바인딩 | 127.0.0.1:8765 하나 |
| 실제 앱5개의 /api/apps 조회 | 모두404 |
| 실제 승인 패키지4개의 이름으로 다운로드 | 모두200 아님. 배포 루트 밖 경로/입력 ZIP 접근도 차단 |
| 더미 v1 설치 후 서버 중지·실제 실행 | 종료코드0 |
| 기존 admin으로 v2 게시→업데이트→서버 중지·실제 실행 | 종료코드0. 같은version/다른ID 갱신, settings 이전, 이전 작업 파일 보존 |
| 인증 정책(loopback에서 LAN handler 모의) | 무인증403/오토큰403/정상 토큰200 |
| 토큰 노출 검사 | 요청 중 stdout/stderr에 시험 토큰 없음. 소스 전달 묶음에도 없음 |
| 시작 가드 | 알 수 없는ZIP/실제 앱 목록/사용자 설정 혼입 및 별도 승인 없는 LAN 시작 거부 |
| 서버 중지 | 신규 접속 실패 및8765 재바인딩 성공 |

최종 검사에서는 무해한 더미 EXE2회 실행. 이전 검사 초안도 같은 더미로만 수행했다. 실제 도구 실행0, LAN listener0, Windows Use0. 승인 ZIP4개를 새로 설치하거나 다시 패키징하지 않았다. audit/mvp_probes.py는 실행하지 않았다. 관리형 롤백·자체 업데이트·TLS·서명·인터넷 옵션은 구현하지 않았다.

## 5. 개발 PC: 승인 전 loopback 실행

현재 준비된 환경은 r1이며 검증용 r2 환경과 별도다. 토큰이 있는 전체 lan-lab 폴더를 팀원에게 전달하지 않는다.

~~~powershell
$Project = (Get-Location).Path  # 저장소 루트에서 실행
$Python = (Get-Command python -ErrorAction Stop).Source  # 승인된 환경 활성화 후
Set-Location -LiteralPath $Project
$Lab = Join-Path $Project '.test-results\lan-lab'
& $Python -B -m audit.lan_lab check --root "$Lab"
& $Python -B -m audit.lan_lab serve --root "$Lab"
~~~

별도 PowerShell에서 Get-NetTCPConnection -State Listen -LocalPort8765를 확인한다(실제 명령은 아래). UI를 개발 PC에서 시험할 때도 새 설치 루트를 지정한다.

~~~powershell
Get-NetTCPConnection -State Listen -LocalPort 8765
Invoke-RestMethod 'http://127.0.0.1:8765/api/health'
& $Python -B -m southpaw_tools --catalog "$Lab\client-bundle\audit-catalog.json" --data-dir "$Lab\developer-client"
~~~

토큰을 출력하지 않는다. localhost 접속은 토큰 없이 가능한 기존 정책이다. 이것을 실제 LAN 인증 통과라고 기록하지 않는다. Ctrl+C로 서버를 중지한다.

## 6. 별도 승인 후 실제 LAN 시험

아래는 **미실행 수동 절차**다. 사용자/회사 담당자는 시험 PC1대, 해당 IP·인터페이스·프로필·시간과 제한적 방화벽 허용 필요 여부를 확인한다. 현재 Public 프로필은 승인 선행 조건이다. 방화벽·프로필을 이 도구가 변경하지 않는다. 실제 IP는 시험 직전 다시 확인한다.

서버를 중지한 상태에서 담당자가 server.local.json의 lan_host에 승인한 개발 PC 사설IPv4, lan_enabled=true를 넣는다. 기존 임의 토큰은 유지하거나 새 시험 토큰으로 교체하고 UTF-8 BOM 없이 저장한다. 토큰은 회사 승인 비밀 전달 수단으로 시험 담당자에게만 전달한다. stdout/채팅/화면 캡처/Git에 남기지 않는다.

~~~powershell
# 회사·사용자 시험 승인을 받은 뒤에만
& $Python -B -m audit.lan_lab serve --root "$Lab" --approve-lan
~~~

기대: 127.0.0.1:8765와 선택한 사설IPv4:8765만 listen. LAN ON 출력은 서버 설정 증거이며 다른 PC 접속 성공 증거가 아니다.

시험 PC 담당자가 승인된 수단으로 **client-bundle 내용만** 별도 폴더에 복사한다. 이번 작업에서 실제 전송/PC 조작은 하지 않았다. 해당 PC에 승인된 Python>=3.12/PySide6==6.11.0을 준비하고 .NET Framework 더미 실행 가능 여부를 확인한다. 설치/실행 환경을 자동 설치하지 않는다.

~~~powershell
# 시험 PC에서 담당자가 실행, 경로는 해당 PC의 실제 경로로 입력
$Python = Read-Host '승인된 python.exe 절대 경로'
$Bundle = Read-Host '더미 client-bundle 절대 경로'
$ServerIP = Read-Host '승인된 개발 PC 사설IPv4'
Test-NetConnection -ComputerName $ServerIP -Port 8765
$TrialData = Join-Path $env:LOCALAPPDATA ('SouthpawGames\LanLabTrial-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
& "$Bundle\start_dummy.ps1" -Python "$Python" -DataDirectory "$TrialData"
~~~

UI 연결 설정에서 http://개발PC_IP:8765, LAN 연결 체크, 별도 전달한 시험 토큰을 입력한다. 업데이트 확인→더미 한 개만 표시→설치. 무인증/잘못된 토큰의403과 정상 인증200은 [기존 상세 절차의 인증 명령](<LAN_TEST_RUNBOOK.md>)도 참고한다. 토큰을 커맨드라인 인자로 넣어 프로세스 목록에 노출하지 않는다. SecureString 입력도 HTTP 전송 자체를 암호화하지는 않는다.

### v2 게시 및 갱신

v1 설치 후 개발 PC 서버를 중지하고 시험 PC에서 오프라인 실행을 확인한다. UI는 자동 heartbeat가 없으므로 업데이트 확인으로 실패를 반영한 뒤 실행한다. 새 console 출력은 빠르게 닫힐 수 있어 상세 runbook의 engine.launch/종료코드 확인 방법을 함께 사용한다.

개발 PC에서 아래 기존 관리자 CLI로 **더미 v2만** 게시한다. 승인 실제 ZIP의 경로나 기본 --root를 사용하지 않는다.

~~~powershell
& $Python -B -m southpaw_tools.admin --root "$Lab\repository" --app-id lan-smoke --zip "$Lab\inputs\r2.zip" --version 0.0.1 --release-id lan-smoke-r2 --exe LanSmoke.exe --sha256 9908efac1b1fecc3a23628f9370a7285c8f14249308c25a70488bb9df985ae99 --exe-sha256 7a3e3a37c96ebae4f6afa366b120564949f2801012e6dc77e2a71f7ffa198dd1 --notes-file "$Lab\inputs\r2.md" --approve
& $Python -B -m audit.lan_lab check --root "$Lab"
& $Python -B -m audit.lan_lab serve --root "$Lab" --approve-lan
~~~

시험 PC에서 업데이트 확인→r2 식별자와 업데이트 버튼 확인→갱신. 서버를 다시 중지하고 r2 오프라인 실행을 확인한다. r1으로 되돌리는 관리형 롤백은 없으며, 시험을 다시 시작하려면 **새 시험 루트와 새 client 데이터 폴더**를 준비한다.

### LAN OFF 재시작 및 종료

개발 PC 서버 중지→server.local.json의 lan_enabled=false 저장→serve 실행(--approve-lan 불필요). 설정 파일 수정만으로 live listener가 꺼지지 않으므로 반드시 중단·재시작한다.

기대: 개발 PC127.0.0.1 health 성공/LANfalse, 시험 PC 신규 TCP/health/ZIP 요청 실패.403 응답이 오는 경우 LAN listener가 응답하는 것이므로 OFF 합격으로 처리하지 않는다. 이미 수락된 다운로드의 즉시 취소까지 보장한 것은 아니다. 설치한 더미는 계속 오프라인 실행할 수 있어야 한다.

시험 종료 후 Ctrl+C, 해당 server listener 종료 확인. 담당자가 별도 승인으로 만들었던 시험 방화벽 예외가 있다면 그 예외만 승인 절차에 따라 정리한다. 프로세스 전체 종료·방화벽 비활성화·실제 프로그램 제거·알 수 없는 작업 파일 삭제는 하지 않는다.

## 7. 남은 보안·Git·변경 범위

서명된 카탈로그/고정 공개키/키 회전/만료·재전송 방어/TLS 서버 진위 검증/토큰 보호는 미구현이다. 공유 토큰과 SHA-256은 게시자 인증이 아니다. [신뢰 설계](<CATALOG_TRUST_DESIGN.md>)의 배포 차단을 유지한다. 무인증 성공, 실앱 목록 노출, 해시 불일치, LAN OFF에서 응답하면 시험을 중단한다.

첫 commit의 포함/제외·조건부 검토 목록은 [GIT_CHECKPOINT_REVIEW.md](<GIT_CHECKPOINT_REVIEW.md>)에 있다. 첫 commit/stage/원격 등록/push는 하지 않는다.

이번 새 파일: audit/lan_lab.py, audit/verify_lan_lab.py, examples/lan-lab.server.example.json, 이 문서, Git 검토 문서. 기존 README와 LAN_TEST_RUNBOOK에는 현재 절차 링크만 추가했다. **기존 엔진/서버/admin/UI/78개 테스트/등록부/ROADMAP/실제 패키지는 수정하지 않았다.** 생성된 토큰·소스 묶음·ZIP·설치·검사 결과는 .test-results에만 있다.

보존·git status·staging·실제 ZIP 대조는 [최종 보존 검사](<../.test-results/lan-preparation-preservation.json>)를 따른다. 기존5개 프로젝트의 검사 대상292개와 Git 상태·원본 ZIP4개를 재확인했다. Pixel Effect Maker/중단 Pixel Motion Studio는 계속 제외한다. 회사 GitHub→개인 이전은 소유권·회사 승인 전 진행하지 않는다.

실제 다른 PC 접속은 미검증이다. 다음 행동은 **사용자가 시험 PC/회사 승인/네트워크 정책을 확인하고 위 수동 절차를 시작하는 것**이며 이번 작업에서 자동으로 진행하지 않는다.
