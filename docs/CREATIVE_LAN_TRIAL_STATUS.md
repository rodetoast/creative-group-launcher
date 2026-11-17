# Creative Group Launcher — 실제 LAN 시험 사전 조건 점검

## 최신 확인: 두 PC 시험 범위 승인, 방화벽 변경 승인 대기

사용자가 현재 개발PC와192.168.0.19 사이의 TCP8765, 더미v1/v2, 실제 시작부터 최대30분 시험을 허용했다. 다른 PC를 대상으로 접근/시험하지 않는다.
현재 개발PC 사설IP 후보/이더넷 Up/Public/8765 listener0을 다시 확인했다. 현재 Python Public TCP 규칙은 모든 주소·포트를 허용한다.
기존 규칙을 수정하지 않고 승인된 시험PC 외 접근을 제한하기 위해, 해당 Python/serverIP/TCP8765에만 적용되는 임시 차단 규칙1개를 제시하고 별도 승인을 요청했다.
추가/삭제 스크립트는 Git 제외 .test-results/lan-approved-192168019 아래 있으며 아직 실행하지 않았다. 현재 실행 토큰은 일반 사용자 권한이다.
방화벽 승인/적용 및 실제 클라이언트 실행 준비를 확인한 뒤에만 시험을 시작한다. 서버·30분 타이머는 아직 시작하지 않았고 방화벽/프로필/기존 규칙을 변경하지 않았다.
이하 표는 이전 단계의 미확인 상태 기록으로 보존한다. 최신 권한 범위는 위 내용과 로컬 preflight.local.json을 따른다.

2026-11-03 KST. **실제 LAN 시험은 시작하지 않았다.** 회사 담당자의 허용 범위와 별도 Windows 시험 PC의 준비/IP가 아직 확인되지 않았다. 이 두 조건이 확인되기 전에는 더미 LAN listener도 열지 않는다.

## 1. 이번에 확인한 사실

현재 개발 PC의 이더넷은 Up이고 gateway가 있는 사설IPv4 후보를 확인했다. 현재 주소·프로필·시간은 Git 제외 .test-results/creative-lan-preflight.local.json에 기록했다. 주소를 고정 IP로 가정하지 않는다. Bluetooth는 Disconnected/169.254 주소여서 후보에서 제외했다.

- Windows 프로필:Public. 임의로 Private 전환하지 않았다.
- TCP8765 listener:조회 시0개.
- 현재 더미 root:.test-results/lan-lab, 실제 root:distribution으로 분리.
- 더미 catalog:lan-smoke 하나, release_id=lan-smoke-r1. v2 입력은 별도 inputs/r2.zip에 보존.
- LAN OFF/인터넷 OFF 설정. 시험 토큰은 ignore된 server.local.json에 있으며 출력·수정·외부 전달하지 않았다.
- client-bundle에는 더미 초기 catalog만 있고 실제 프로그램 ZIP/EXE·토큰·사용자 설정이 없음을 기존 가드로 재확인.
- 실제 승인 ZIP4개의 고정 SHA-256 일치와, 해당 이름에 대한 시험 Distribution.package 거부를 읽기/정적 경계 검사로 재확인. HTTP나 PC 간 LAN 접근 실험을 한 것은 아니다.
- 설치/업데이트/Journal 복구/관리자 게시 엔진은 수정하지 않았다. 기존 admin.py와 시험 가드를 재사용한다.

상세 격리 결과는 Git 제외 .test-results/creative-lan-isolation.local.json에 있다. 이 단계는 네트워크 연결 성공을 입증하지 않는다.

## 2. 실제 시험 결과 구분

| 보고 항목 | 이번 작업 결과 |
|---|---|
| 1 시험 전 환경 | IP/이더넷 Up/Public/8765/더미 구성 읽기 전용 확인 |
| 2 실제 시험 PC 연결 | 시험 PC의 준비·IP·담당자 실행 가능 여부 미확인, 접속 미실행 |
| 3 LAN OFF 타 PC 차단 | 미실행. listener0이나 설정false만으로 타 PC 실측 성공으로 처리하지 않음 |
| 4 LAN ON 타 PC 연결 | 미실행, 사설IP listener를 열지 않음 |
| 5 토큰 인증 | 이번 실제 LAN 검사 미실행. 이전 loopback의403/200 결과와 구분 |
| 6 더미v1 다운로드·설치 | 시험 PC에서 미실행. 이전 loopback 결과는 기존 보고서에 보존 |
| 7 더미v2 갱신 | 실제 게시/시험 PC 갱신 미실행. 기존v1 환경과 입력 ZIP 그대로 |
| 8 서버 종료 후 실행 | 이번에는 server/설치를 시작하지 않아 실험 미실행. 이전 더미 오프라인 결과 보존 |
| 9 오류·복구 | 이번 설치 작업 없음. WinError5 최초 원인은 미확정, 기존 조사·회귀3개 보존 |
| 10 방화벽 변경 | 없음. 규칙 제안/적용도 권한·시험PC 확인 전 하지 않음 |
| 11 종료 상태 | 시험 server 시작0, 설정 변경0, 프로필 변경0,8765 listener0 |
| 12 자동 테스트 | 기존 기록81개 PASS, 실패0/오류0/skip0,19.762초. 이번에는 런타임 소스가 같고 문서만 바꿔 반복하지 않음 |
| 13 Git | master/HEAD32afb846d0bc69b38203a259dad71180cd4a14b5 유지, stage/commit/remote 변경/push 없음 |
| 14 기존5개·ZIP | baseline 대상292개 해시·HEAD·태그·상태 및 원본 ZIP4개 동일, launcher 복사본4개 해시도 일치 |
| 15 실제 LAN 성공 여부 | 아직 판정 불가. 다른 PC의 실제 요청이 없음 |
| 16 다음 단계 | 담당자 허용 범위＋시험PC 준비 확인 후에만 기존 절차로 진행 가능 |

이미 완료한 loopback 설치·업데이트·실행과 모의 bind를 이번 실제 LAN 결과처럼 반복 집계하지 않았다. 이전 검증은 [LAN 환경 준비](LAN_ENVIRONMENT_PREPARATION.md), 최신81개 근거는 [WinError5 조사](WINERROR5_PREFLIGHT_REPORT.md)를 따른다.

## 3. 사용자가 확인할 최소 사항

다음 두 정보를 먼저 확인하면 된다.

1. 회사 네트워크 관리자 또는 권한 있는 담당자의 시험 허용 여부와 범위:개발PC/시험PC, TCP8765, 허용 시간. Public 프로필의 현재 회사 정책을 확인하되 프로필을 임의 변경하지 않는다.
2. 별도 Windows 시험 PC1대의 사설IP와 사용자가 직접 명령/런처를 실행할 수 있는지 여부. 승인된 Python>=3.12/PySide6==6.11.0과 더미 .NET 실행 환경을 확인한다. 기존 사용자 프로그램을 종료할 필요는 없다.

시험 PC에서 담당자가 직접 준비 여부를 확인할 읽기 전용 명령:

~~~powershell
Get-NetIPConfiguration
python --version
python -c "import PySide6; print(PySide6.__version__)"
~~~

Codex는 별도 PC를 우회 조작하지 않는다. 허용·PC 준비 정보가 확인된 후 사용자가 [기존 시험 절차](LAN_ENVIRONMENT_PREPARATION.md)의 client-bundle 전달·격리 데이터 경로·인증/설치/갱신 명령을 직접 수행한다. 전체 lan-lab 폴더나 비밀 설정을 전달하지 않는다.

## 4. 조건 확인 후 재사용할 시작·종료 절차

아래는 아직 실행하지 않은 명령이다. 저장소 루트에서 승인된 Python 환경을 선택한다.

~~~powershell
$Python = (Get-Command python -ErrorAction Stop).Source
$Lab = Join-Path (Get-Location) '.test-results\lan-lab'
& $Python -B -m audit.lan_lab check --root "$Lab"
# 승인된 시험을 시작할 때만:우선 server.local.json이 LAN OFF인지 확인
& $Python -B -m audit.lan_lab serve --root "$Lab"
~~~

이때 localhost 동작과 타 PC의 접근 실패를 **실측**한다. 이후 서버를 Ctrl+C로 중지하고 담당자가 server.local.json에 현재 승인된 사설IP/lan_enabled=true를 저장한다. 시험 토큰은 별도 승인된 비밀 전달 수단을 사용하며 일반 다운로드 인증정보로 재사용하지 않는다.

~~~powershell
# 회사 허용 범위와 별도 PC 준비가 확인된 후에만
& $Python -B -m audit.lan_lab serve --root "$Lab" --approve-lan
~~~

표시된 endpoint만으로 LAN 성공이라 하지 않는다. 시험PC의 Test-NetConnection/올바른·잘못된 토큰 요청/목록·해시·설치·업데이트·오프라인 실행을 기존 절차에 따라 기록한다. v2 게시도 기존 admin.py에 명시적인 더미 --root/--zip을 사용한다. 기본 실제 배포 root를 사용하지 않는다.

방화벽 때문에 실패하면 오류와 범위만 확인하고 멈춘다. 담당자 정책 확인 뒤 정확한 program 경로/TCP8765/로컬IP/가능하면시험PC IP/프로필/기간을 제안하고 **실제 규칙 변경 전에 별도 사용자 승인**을 받는다. 방화벽 전체/Defender/백신 해제, Public→Private 임의 전환, 포트포워딩, SMB/터널 개방은 하지 않는다.

종료는 시험 server에서 Ctrl+C→기존 LAN OFF 설정 복원→필요한 OFF 재시작과 타 PC 신규 접속 실패 확인→최종 server 종료/8765 listener 없음 확인 순서다. 이번 시험용으로 승인받아 추가한 규칙만 담당자 승인 범위에서 정리한다. 설정 변경은 server 재시작 후 반영된다. 사용자 데이터/기존 규칙을 임의 삭제하지 않는다.

## 5. 개발 방향 및 미해결 항목

비용0원·기존 Windows PC·회사 LAN 전용 방향을 ROADMAP/README/ARCHITECTURE/CATALOG_TRUST_DESIGN에 반영했다. 기존 인터넷 구상은 과거 기록으로 남기고 현재 개발 목록에서 제외했다. 직원 런처/로컬 관리자 게시 분리와 기존 엔진을 유지한다. 유료 서비스/VPN/Cloudflare/OAuth/SSO/DRM/복잡한PC 인증을 추가하지 않는다.

공유 토큰과 SHA-256은 완전한 서버/게시자 인증이 아니다. Ed25519 서명된 catalog는 후속이며 이번에 구현하지 않았다. 실제 프로그램의 일반 팀원 자동 배포는 계속 보류한다. 최초 WinError5의 주체도 미확정이다. 같은 오류가 나면 시간/경로/journal 단계/active/사용자 데이터 상태를 기록하고 시험을 중단해 복구 가능 여부를 확인한다. sleep/무제한 재시도로 숨기지 않는다.

## 6. 보존과 이번 파일 변경

기존 미커밋 WINERROR5_PREFLIGHT_REPORT.md와 test_journal_sharing.py는 원문 해시를 보존했다. 이전 소스/문서60개 원문은 Git 제외 creative-direction-baseline에 복사했다.

이번 tracked 변경은 README.md, ROADMAP.md, docs/ARCHITECTURE.md, docs/CATALOG_TRUST_DESIGN.md, docs/LAN_ENVIRONMENT_PREPARATION.md의 방향 설명뿐이다. 새 문서는 이 파일이다. 프로그램 소스·기존 테스트·실제 배포 파일·runtime 설정은 바꾸지 않았다. 보존 비교는 Git 제외 creative-lan-final.local.json에 기록한다.

Windows Use0, 실제 사용자 프로그램 실행/종료0, 인터넷 공개0. GitHub의 공개 저장소에는 업로드하지 않았고 첫 commit을 수정하지 않았다. Pixel Effect Maker/중단 Pixel Motion Studio는 계속 제외한다. 코드·자료의 공개/소유권 이전은 별도 승인 사항이다. 결과 보고 후 다음 개발 단계로 자동 진행하지 않는다.
