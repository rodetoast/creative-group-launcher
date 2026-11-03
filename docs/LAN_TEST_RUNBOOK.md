# 첫 실제 LAN 시험 절차 — 더미 전용, 승인 후 수동 실행

현재 준비된 독립 환경과 시작 전 가드를 사용하는 권장 절차는 [LAN_ENVIRONMENT_PREPARATION.md](<LAN_ENVIRONMENT_PREPARATION.md>)입니다.
아래 본문은 이전 감사 fixture의 상세 인증/종료코드 확인 참고 절차로 보존합니다. 실제 승인 프로그램 배포 루트는 사용하지 않습니다.

2026-11-03 KST. **이 절차의 LAN 활성화·팀원 PC 조작·방화벽 설정은 이번 감사에서 실행하지 않았다.** 회사 담당자와 사용자의 승인을 받은 시험 PC 한 대에서만 수행한다. 기존 도구 5개를 내려받거나 실행하지 않는다. 발견 사항과 배포 보류 사유는 [감사 보고서](<MVP_LAN_AUDIT.md>)에 있다.

## 1. 준비 및 합격 조건

- 개발 PC와 팀원 PC의 사설 IPv4, 실제 연결 프로필(Domain/Private), 네트워크 담당자, 시험 시간, 허용 원격 IP를 기록한다. 두 PC가 같은 회사망이라는 사실·서로의 경로/VLAN/Wi-Fi 격리/VPN 정책을 확인한다. 사설 IP라는 사실만으로 신뢰망으로 간주하지 않는다.
- 서버 TCP8765 사용 여부와 기존 방화벽/GPO/EDR 차단을 담당자가 확인한다. 필요한 인바운드 예외는 **별도 승인 후 담당자가** 정확한 Python 실행 파일, 개발 PC 로컬 IP, TCP8765, 시험 팀원 IP, 승인된 Domain/Private 프로필로 제한해 구성한다. 이 문서는 방화벽 변경 명령을 실행하지 않는다. 방화벽 전체 끄기, Public/모든 원격 주소 허용, 포트포워딩·터널은 사용하지 않는다.
- 런처는 아직 소스 개발본이다. 팀원 PC에 승인된 Python>=3.12 및 PySide6==6.11.0이 필요하다. 이번 검증 환경은 Python3.13.7이다. 패키지 설치/개발 환경 생성도 해당 PC 담당자의 승인 절차에 따른다. Python 없는 PC에서 런처 EXE처럼 실행할 수 있다고 가정하지 않는다.
- 전용 더미는 Windows 내장 .NET Framework4 C# compiler로 만든 작은 콘솔 앱이며 build 식별자만 출력하고 종료한다. 네트워크/레지스트리/사용자 문서/기존 앱에 접근하지 않는다. 팀원 PC의 .NET/보안 정책으로 실행이 허용되는지도 확인한다.
- 모든 시험 데이터는 별도 데이터 루트를 사용한다. 기본 사용자 설치 경로와 기존 앱 폴더를 사용하지 않는다. 토큰·개인 경로를 포함한 settings.json을 채팅/스크린샷/Git에 올리지 않는다.
- 합격: LAN OFF 신규 접속 불가 → ON에서 무인증/오인증403 및 정상 인증 성공 → 목록이 더미1개 → 설치/해시 일치 → 서버 완전 중단 후 더미 실제 실행 → 재시작한 LAN OFF에서 신규 접속 불가와 로컬 접속 가능. 상태 화면은 API/실제 소켓 결과와 함께 기록한다.

방화벽 규칙의 앱 경로·프로필·로컬 정책과 조직 정책 우선순위 참고: [Microsoft Windows Firewall rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules).

## 2. 개발 PC: 더미 준비와 로컬 시작

개발 PC PowerShell A에서 프로젝트 루트로 이동한다. 아래 절대 경로는 현재 개발 PC 기준이며 다른 위치에 복사했다면 해당 승인 경로로 바꾼다.

~~~powershell
$Project = (Get-Location).Path  # 저장소 루트에서 실행
$Python = (Get-Command python -ErrorAction Stop).Source  # 승인된 환경 활성화 후
Set-Location -LiteralPath $Project
& $Python --version
& $Python -c "import PySide6; print(PySide6.__version__)"
$Fixture = Join-Path $Project '.test-results\lan-rehearsal'
~~~

이번 감사에서 다음 파일을 이미 준비했다.

- [r1 더미 카탈로그](<../.test-results/lan-rehearsal/r1/catalog.json>), [r2 더미 카탈로그](<../.test-results/lan-rehearsal/r2/catalog.json>)
- [r1 더미 ZIP](<../.test-results/lan-rehearsal/r1/packages/lan-smoke-r1.zip>), [r2 더미 ZIP](<../.test-results/lan-rehearsal/r2/packages/lan-smoke-r2.zip>)
- [로컬 리허설 결과](<../.test-results/lan-rehearsal/local-rehearsal.json>)

둘 다 표시 버전0.0.1, release_id는 lan-smoke-r1 / lan-smoke-r2이다. 이 파일은 기존 프로그램 배포본이 아니다. 기존 준비 폴더를 덮어쓰지 않는다. 다시 빌드할 때는 새 출력 디렉터리로 다음을 실행하고 생성된 새 해시를 신뢰할 수 있는 별도 경로로 전달한다. 컴파일 환경에 따라 해시가 달라질 수 있다.

~~~powershell
# 재생성이 필요한 경우만, 새 폴더 사용
& $Python -B -m audit.prepare_lan_fixture --output .test-results/lan-rehearsal-next
~~~

현재 생성된 ZIP 고정 해시:

| release | ZIP SHA-256 |
|---|---|
| r1 | 9cddb17a5a03ce5aac5241f9e1f7f2bc3296f0b7988c07abfae9a102248ccca5 |
| r2 | 9908efac1b1fecc3a23628f9370a7285c8f14249308c25a70488bb9df985ae99 |

기본 r1 설정은 LAN OFF다. 로컬 서버 시작:

~~~powershell
& $Python -B -m southpaw_tools.server --root "$Fixture\r1"
~~~

PowerShell B에서 읽기 전용 확인:

~~~powershell
Get-NetTCPConnection -State Listen -LocalPort 8765
Invoke-RestMethod 'http://127.0.0.1:8765/api/health'
Invoke-RestMethod 'http://127.0.0.1:8765/api/catalog'
~~~

기대: 127.0.0.1:8765만 listen, server_enabled=true, lan_enabled=false, internet_enabled=false, apps에 lan-smoke 하나. 승인 프로그램5개가 보이면 잘못된 repository이므로 중단한다. 다른 서버가8765를 사용하면 임의 종료하지 말고 소유자 확인 후 승인된 다른 고정 포트를 **서버와 클라이언트 양쪽에** 적용한다.

승인된 팀원 PC에서는 개발 PC의 LAN IP로 Test-NetConnection을 한 번 수행해 TcpTestSucceeded=False를 기록한다. 이 단계의 실패만으로 LAN OFF 방어를 완전히 입증할 수는 없다. ON일 때 같은 경로의 성공과 OFF 재시험을 함께 비교해야 한다.

## 3. 승인 후: LAN ON 설정과 서버 재시작

서버 A에서 Ctrl+C로 종료한다. 토큰은 무작위32바이트를 64자 hex로 생성한다. 설정 파일은 시험 디렉터리의 로컬 파일이며 평문 비밀을 포함한다. 아래를 실행하기 전에 LAN 시험·회사 정책 승인을 확인한다.

~~~powershell
$LanAddress = Read-Host '승인된 개발 PC 사설 IPv4'
$LanConfig = Join-Path $Fixture 'server.lan.local.json'
$Token = & $Python -c "import secrets; print(secrets.token_hex(32))"
$Config = [ordered]@{
  server_enabled = $true
  port = 8765
  lan_enabled = $true
  lan_host = $LanAddress
  lan_token = $Token
  internet_enabled = $false
}
[System.IO.File]::WriteAllText($LanConfig, ($Config | ConvertTo-Json), [System.Text.UTF8Encoding]::new($false))
& $Python -B -m southpaw_tools.server --root "$Fixture\r1" --config $LanConfig
~~~

기대: 127.0.0.1:8765와 정확히 선택한 LAN_IP:8765 두 개 출력. 다른 터미널에서 Get-NetTCPConnection으로 확인한다. 0.0.0.0/공개 IP listener가 없어야 한다. bind 실패·방화벽 차단은 성공으로 기록하지 않는다. 서버가 LAN ON을 출력해도 다른 PC 연결 성공을 뜻하지 않는다.

토큰은 회사가 승인한 비밀 전달 수단으로 팀원에게 전달한다. 토큰 전체 출력/녹화/채팅 붙여넣기를 시험 증거로 남기지 않는다. LAN 주소로의 HTTP 전송은 암호화되지 않으므로 이 시험은 승인된 신뢰망과 더미로 한정한다.

## 4. 팀원 PC: 신규 연결, 인증, 목록 확인

**이후는 승인된 담당자가 팀원 PC에서 직접 수행한다. 이번 감사에서 원격 조작하지 않았다.**

승인된 파일 전달 방식으로 소스 실행 묶음을 별도 폴더에 준비한다. 포함: 프로젝트의 southpaw_tools 디렉터리, requirements.txt, r1/catalog.json을 복사한 audit-catalog.json. distribution/packages의 실제 승인 ZIP4개, 사용자 settings.json, 기존 앱 소스/작업 파일은 이 더미 시험 묶음에 넣지 않는다. 파일 전달을 위해 새 공개 파일 서버/SMB 공유를 임의로 만들지 않는다.

~~~powershell
$Bundle = Read-Host '승인된 런처 소스 묶음의 절대 경로'
$Python = Read-Host '이 PC의 승인된 python.exe 절대 경로'
$ServerIP = Read-Host '개발 PC의 승인된 LAN IPv4'
$Base = "http://${ServerIP}:8765"
Set-Location -LiteralPath $Bundle
& $Python --version
& $Python -c "import PySide6; print(PySide6.__version__)"
Test-NetConnection -ComputerName $ServerIP -Port 8765
~~~

기대: TcpTestSucceeded=True. 팀원 PC의127.0.0.1은 팀원 PC 자신이므로 서버 주소에 사용하지 않는다.

~~~powershell
# 무인증: 정상 목록을 주면 실패. HTTP403이어야 함
try { Invoke-RestMethod "$Base/api/health" -ErrorAction Stop } catch { $_.Exception.Message }
# 오인증도 HTTP403이어야 함
try { Invoke-RestMethod "$Base/api/health" -Headers @{Authorization='Bearer invalid-test-token'} -ErrorAction Stop } catch { $_.Exception.Message }
$Secret = Read-Host '별도 전달받은 LAN 시험 토큰' -AsSecureString
$Headers = @{Authorization = 'Bearer ' + [System.Net.NetworkCredential]::new('', $Secret).Password}
$Health = Invoke-RestMethod "$Base/api/health" -Headers $Headers
$Catalog = Invoke-RestMethod "$Base/api/catalog" -Headers $Headers
$Health
$Catalog.apps | Select-Object app_id, version, release_id, published
~~~

기대: 서버/LAN ON, 인터넷OFF, published=true인 lan-smoke-r1 한 개. 일반 브라우저 주소창만으로는 Bearer 헤더를 넣지 못하므로403이 정상일 수 있다. 토큰이 맞는데403이면 주소·헤더·회사 프록시/출발지 확인 후 중단한다. 무인증403과 서버OFF의 연결 실패를 구분해 기록한다.

테스트 ZIP 직접 다운로드/검사도 전용 폴더만 사용한다.

~~~powershell
$Evidence = Join-Path $env:LOCALAPPDATA ('SouthpawGames\LauncherLanEvidence-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $Evidence -ErrorAction Stop | Out-Null
$Downloaded = Join-Path $Evidence 'lan-smoke-r1.zip'
Invoke-WebRequest "$Base/packages/lan-smoke-r1.zip" -Headers $Headers -OutFile $Downloaded
(Get-FileHash -LiteralPath $Downloaded -Algorithm SHA256).Hash
~~~

기대: 해시가 별도 전달한 고정 r1 ZIP 해시와 일치. 서버의 같은 HTTP 응답에 담긴 해시만 신뢰 근거로 삼지 않는다. 불일치하면 중단하고 설치하지 않는다.

## 5. 팀원 PC: 런처 설치와 서버 OFF 후 실제 오프라인 실행

매번 새로운 데이터 루트를 사용해 예전 캐시와 현재 사용자 설치에 영향을 주지 않는다.

~~~powershell
$Data = Join-Path $env:LOCALAPPDATA ('SouthpawGames\LauncherLanAudit-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
& $Python -B -m southpaw_tools --data-dir "$Data" --catalog "$Bundle\audit-catalog.json"
~~~

UI의 연결 설정에서 서버 주소 http://개발PC_IP:8765, LAN 연결 사용 체크, 토큰 입력/저장. 업데이트 확인 후 더미1개 목록·설치 버튼 확인 → 설치 승인. 설치 후 “설치 완료/실행”, version0.0.1, release_id lan-smoke-r1을 확인한다.

개발 PC A에서 Ctrl+C로 서버를 완전히 종료한다. 팀원 PC에서 새 Test-NetConnection/Invoke-RestMethod 요청이 실패하는지 확인한다. 개발 PC는 해당 프로세스 소유 listener가 사라졌는지 확인한다. 이미 수락된 다운로드가 있었다면 완료 여부를 따로 기록한다.

UI에서 “업데이트 확인”을 눌러 조회 실패가 끝날 때까지 기다린다. 기대: 오프라인 안내, 더미 “실행” 가능. **현재 구현은 서버 중단을 자동 감시하지 않는다.** UI 실행 버튼으로 더미를 실행한다. 콘솔이 빨리 닫힐 수 있으므로 아래 엔진 실행으로 종료코드도 기록할 수 있다. 소스 묶음 루트에서 같은 $Data를 사용한다.

~~~powershell
@'
import sys
from pathlib import Path
from southpaw_tools.installer import Installer
from southpaw_tools.paths import AppPaths
engine = Installer(AppPaths(Path(sys.argv[1])))
process = engine.launch('lan-smoke')
code = process.wait(timeout=10)
print('offline dummy exit:', code)
raise SystemExit(code)
'@ | & $Python -B - "$Data"
~~~

기대: Southpaw harmless LAN fixture: lan-smoke-r1; offline OK, 종료코드0. 실제 서버 중단 상태에서 실행 성공을 기록한다. 이것은 기존 도구5개의 오프라인 기능 검증을 대신하지 않는다.

선택적 동일 버전 새 빌드 시험: LAN 서버를 r2 repository로 재시작한다(--root의 r1만 r2로 바꿈, 동일 config). 클라이언트에서 업데이트 확인 후 version0.0.1이 같아도 새 release_id로 업데이트가 뜨는지 확인한다. 설치 위치 열기로 r1 payload에 시험용 settings.json과 unknown-work.txt를 직접 만든 뒤, 더미를 종료하고 업데이트한다. 기대: settings.json만 r2로 이전, unknown-work.txt는 r1에 보존. r2 서버를 중단하고 오프라인 실행하면 출력은 lan-smoke-r2여야 한다. 이전 r1로의 관리형 롤백은 아직 지원하지 않으므로 UI에서 가능하다고 가정하지 않는다.

F01 때문에 실제 프로그램 제거/장애 주입을 하지 않는다. 더미 제거 실패·전원 차단을 팀원 PC에서 일부러 만들지 않는다. 해당 경계는 격리된 자동 프로브로 확인했다.

## 6. LAN OFF 후 신규 접속 차단 및 로컬 유지

개발 PC에서 서버를 Ctrl+C로 종료한다. LAN config를 읽어 lan_enabled=false로 바꾸고 BOM 없는 UTF-8로 저장한다. 이 작업은 더미 시험 설정만 변경한다.

~~~powershell
$Config = Get-Content -LiteralPath $LanConfig -Raw | ConvertFrom-Json
$Config.lan_enabled = $false
[System.IO.File]::WriteAllText($LanConfig, ($Config | ConvertTo-Json), [System.Text.UTF8Encoding]::new($false))
& $Python -B -m southpaw_tools.server --root "$Fixture\r1" --config $LanConfig
~~~

기대: 127.0.0.1:8765만 listen, 개발 PC의 로컬 health는 성공하고 LAN false. **파일 수정만 하고 기존 서버를 계속 실행한 상태는 LAN OFF 시험이 아니다.**

팀원 PC에서 새 Test-NetConnection이 False, 새 health와 ZIP 다운로드가 정상 토큰이 있어도 연결 실패해야 한다.403이 돌아오면 LAN listener가 여전히 응답하는 것이므로 OFF 합격으로 처리하지 않는다. 팀원에게 이미 설치된 더미는 계속 오프라인 실행돼야 한다. ON 성공→OFF 신규 연결 실패 쌍을 기록한다. 같은 PC의 loopback 요청 성공만으로 이 항목에 합격을 주지 않는다.

마지막에 개발 PC 서버를 Ctrl+C로 종료하고 listener 소멸 확인. 시험용 방화벽 예외가 별도 승인으로 생성됐다면 담당자가 해당 예외만 승인 절차에 따라 정리한다. 다른 규칙/프로세스는 변경하지 않는다. 팀원 PC의 더미/캐시는 담당자가 결과를 보관한 후 전용 경로를 확인해 정리하며 사용자 기본 설치나 작업 파일을 삭제하지 않는다. 토큰은 재사용하지 않는다.

## 7. 결과 기록과 중단 기준

| 항목 | 기대 | 실측/시각/담당자 |
|---|---|---|
| LAN OFF 최초 | 로컬만 listen, 팀원 신규 연결 실패 | 미실행 |
| LAN ON | 정확한 로컬/LAN 두 listener, 팀원 TCP 성공 | 미실행 |
| 인증 | 무인증/오인증403, 정상 토큰200 | 미실행 |
| 목록 | 더미1개, 원래5개 앱 없음 | 미실행 |
| 다운로드 | 별도 공유 고정 ZIP SHA-256 일치 | 미실행 |
| 설치/갱신 | 설치 완료, 선택적으로 동일version/다른ID 업데이트 | 미실행 |
| 완전 서버OFF | 새 다운로드 실패, 더미 실제 오프라인 실행0 | 미실행 |
| LAN OFF 재시작 | 로컬200/LANfalse, 팀원 신규 연결 실패 | 미실행 |
| 실제 DPI/표준계정/보안제품 | 버튼 접근/한글/권한 동작 수동 QA | 미실행 |
| 종료 | 시험 server listener 없음, 토큰 폐기/예외 정리 | 미실행 |

오류를 우회하기 위한 방화벽 전체 해제·백신 중지·관리자 강제 실행·기존 앱 재패키징을 하지 않는다. 목록이 실제 도구로 바뀜, 해시 불일치, 무인증 성공, LAN OFF에서도 응답, 다른 PC/사용자 파일 영향이 발견되면 즉시 시험 중단하고 증거에서 토큰을 제거해 보고한다.
