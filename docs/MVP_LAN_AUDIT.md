# v0.1.0 MVP 및 LAN 준비 감사

> 이 문서는 해당 개발 단계의 기록입니다. 이후 로컬 체크포인트 승인·검사 결과는 [LOCAL_CHECKPOINT_REVIEW.md](LOCAL_CHECKPOINT_REVIEW.md)를 따릅니다. 과거 Git 상태·제한 및 초기 설계 내용은 현재 상태와 다를 수 있습니다.

감사일: 2026-11-03 KST. 대상: 현재 작업 폴더의 소스 개발본. commit이 없으므로 Git revision 대신 이번 감사 시작 시점의 기존 파일 SHA-256 비교로 변경 여부를 확인한다.

**판정: 일반 팀원 대상 실제 도구 배포는 보류. 승인된 신뢰망에서 전용 더미만 사용하는 제한된 LAN 시험은 조건부로 준비됨. 실제 LAN 연결 성공은 아직 미검증이다.**

제거 실패 후 설치 상태 손상(F01), 게시자 진위 검증 부재(F02), 중단 후 재시도·상태 표시 문제(F03–F07)를 확인했다. production 코드나 UI는 수정하지 않았다. LAN·방화벽·기존 프로그램·원격 저장소를 변경하지 않았고, 정식 배포·commit·push는 수행하지 않았다.

## 1. 근거와 검증 범위

- [DEVELOPMENT_REPORT.md](<DEVELOPMENT_REPORT.md>), [PROJECT_REGISTRY.md](<../PROJECT_REGISTRY.md>), [README.md](<../README.md>), [ROADMAP.md](<../ROADMAP.md>)를 구현·기존 테스트와 대조했다.
- [서버](<../southpaw_tools/server.py>), [HTTP 클라이언트](<../southpaw_tools/providers.py>), [설치 엔진](<../southpaw_tools/installer.py>), [ZIP 검증](<../southpaw_tools/archive.py>), [UI](<../southpaw_tools/ui.py>), [기존 테스트](<../tests>)를 분석했다.
- **재현 확인**은 이번 실행에서 실제 결과를 얻은 사항, **코드 확인**은 정적 분석, **미검증/추정**은 다른 PC·운영 환경에서 추가 확인할 사항이다.
- 기존 승인 ZIP 4개 설치 결과는 [기존 검증 기록](<approved-install-verification.local.json>)을 검토했다. 이번에는 기존 도구 ZIP을 다시 설치하거나 EXE를 실행하지 않았다. 원본 ZIP SHA-256과 기존 5개 저장소의 baseline은 재검사했다.
- 추가 실패 주입은 [감사 프로브](<../audit/mvp_probes.py>)의 더미 ZIP·격리 디렉터리·loopback HTTP·Qt offscreen만 사용했다. SystemExit는 활성화 직전 비정상 종료의 모의이며 전원 차단 실험은 아니다. UI 연결 실패는 작업 예외 주입이며 실제 회사 LAN 장애 실험은 아니다.

## 2. 구현 및 문서 대조

| 항목 | 확인된 구현 | 한계/미구현 |
|---|---|---|
| 5개 등록 | TileNamer 0.1.6 RC3, ase_viewer 0.5.8.3, Tag Master 0.4.0/7263f8d, Bridge 0.3.6, Pivot 0.3.3 | Tag Master 승인 ZIP 없음, 설치 불가. 나머지 4개 published는 로컬 테스트 게시 의미 |
| 런처 UI | 프로그램 선택, 설치/업데이트/실행/제거, 진행률·취소, 연결 설정 | Markdown 렌더링 없음. 실시간 서버 감시 없음. 상태 오류 F06/F07 |
| 서버 | 읽기 전용 GET API, loopback 기본, 명시 LAN 설정/토큰 | 실제 LAN 미검증, TLS/서명/개별 사용자 인증/게시 GUI 없음 |
| 설치/업데이트 | 새 release 디렉터리, ZIP/EXE SHA-256, 필수 경로, atomic active.json | 일반 예외에서 이전 버전 유지. 모든 실패·강제 종료·제거에 대한 트랜잭션 보장은 아님 |
| 실행 중 보호 | 앱별 OS 잠금 + Windows 프로세스 경로 조회, shell=False | 관리자 권한 프로세스/외부 직접 실행과의 경쟁은 추가 QA 필요 |
| 오프라인 실행 | 설치 포인터와 로컬 EXE만으로 실제 실행 가능 | 손상 active.json 복구 없음. F07 조건에서 UI 접근 불가 |
| 데이터 보존 | 선언된 preserve_paths 교집합만 이전, 코드/링크 제외. 미등록 파일은 이전 폴더에 보존 | 모든 작업 파일을 새 버전으로 옮기는 기능 아님. 기존 Desktop 설정 가져오기 없음 |
| 복구/롤백 | 활성화 실패 시 이전 포인터 유지, 이전 release 보존 | 수동 버전 선택·관리형 롤백·손상 설치 복구 없음 |
| 런처 배포 | Python 소스와 실행 배치 | 최종 런처 EXE/installer/코드 서명/자체 업데이트 없음 |

문서는 후속 미구현을 대체로 정확히 명시한다. 다만 README의 “실패 시 이전 설치 유지”는 설치의 일반 예외 처리 범위로 한정해서 읽어야 한다. “이전 버전 보존”을 “롤백 기능 구현”으로 해석하면 안 된다. 개발 보고서의 “서버 연결 상태”는 마지막 성공 조회 시점의 상태이다. 이전 감사 결과를 덮어쓰지 않고 이 문서를 보완 근거로 남긴다.

## 3. 발견 사항

P1: 일반 배포 전에 해결하거나 명시적인 운영 제한이 필요한 사항. P2: 제한된 시험에서 기록하고 안정화 단계에서 처리할 사항. 악용·장애의 실제 발생 빈도는 측정하지 않았다.

### F01 — P1: 제거 도중 실패하면 활성 설치가 깨지고 같은 버전 재설치도 거부됨

**재현 확인.** Dummy.exe 삭제 후 asset.json 삭제에 PermissionError를 주입했다. active.json은 남고 EXE가 없어 실행이 실패했다. 동일 release 재설치도 “이미 같은 승인 배포본”으로 거부했다. 사용자 settings.json은 보존됐다. 사용자 데이터 유실을 재현한 것은 아니며 프로그램 가용성과 복구 경로의 문제다.

근거: [installer.py:151](<../southpaw_tools/installer.py#L151>)의 순차 삭제, [installer.py:186](<../southpaw_tools/installer.py#L186>)의 영수증 삭제, [installer.py:195](<../southpaw_tools/installer.py#L195>)의 마지막 포인터 삭제, [installer.py:78](<../southpaw_tools/installer.py#L78>)의 같은 release 차단. 프로브 partial_uninstall.

권고: 기존 파일을 지우기 전 복구 가능한 상태 전환/제거 상태 기록과 재시도·수리 경로를 설계한다. 이번에 임의 수정하지 않았다. 실제 도구에 대한 제거 실험은 하지 않는다.

### F02 — P1(실제 배포): SHA-256은 게시자 인증을 대신하지 못함

**코드 및 더미 재현 확인.** 카탈로그와 ZIP을 함께 바꾸고 새 release_id 및 일치하는 해시를 제공하면 관리자 게시 CLI를 거치지 않은 패키지도 받아 설치했다. HTTP 파일 무결성 검사는 통과한다. 공격자는 서버 파일 쓰기 권한 또는 HTTP 응답 변조 능력이 필요하다. 다운로드 토큰만 가진 사용자가 HTTP로 업로드할 수 있다는 뜻은 아니다.

근거: [providers.py:92](<../southpaw_tools/providers.py#L92>), [providers.py:95](<../southpaw_tools/providers.py#L95>), [catalog.py:92](<../southpaw_tools/catalog.py#L92>), [admin.py:16](<../southpaw_tools/admin.py#L16>). 프로브 unsigned_catalog_and_package_accepted. published=true와 --approve는 로컬 절차/메타데이터이지 전자서명이 아니다.

LAN은 평문 HTTP/Bearer 공유 토큰이며 클라이언트 settings.json에도 토큰을 평문 보관한다. 서버 신원 검증·서명된 카탈로그·유효기간·단조 증가 sequence·폐기/키 회전 체계가 없다. 새 ID이면 낮은 버전도 업데이트 후보가 될 수 있다. 동일 ID의 ZIP 해시 변경 방어는 있지만 최초 접속 및 새 ID의 게시자 진위/재전송 방어는 아니다.

권고: 일반 배포의 신뢰 모델을 먼저 확정한다. 제한된 시험은 회사 승인 신뢰망, 단일 시험 PC, 더미 전용 repository, 배포 파일 쓰기 권한 제한, 별도 경로로 전달한 fixture 해시 확인을 조건으로 한다. 서명된 메타데이터·안전한 전송 설계는 기존 안정화/배포 단계에서 유지한다.

### F03 — P2: 활성화 직전 중단 후 잔여 release가 재시도를 차단

**재현 확인.** stage.rename 후 _activate에 SystemExit 주입 시 이전 r1 실행 경로는 정상이나 r2 디렉터리가 남는다. 다음 r2 설치는 폴더 존재 때문에 거부된다. 실제 강제 종료 시 다운로드/staging도 남을 수 있다는 점은 코드에 따른 추정이다. 시작 시 트랜잭션 재조정/고아 release 판정 기능은 없다.

근거: [installer.py:80](<../southpaw_tools/installer.py#L80>), [installer.py:102](<../southpaw_tools/installer.py#L102>), [installer.py:108](<../southpaw_tools/installer.py#L108>). 프로브 orphan_after_interruption. 운영자 임의 폴더 삭제를 사용자 기본 복구 절차로 제공하지 않는다. 백업·포인터·영수증 대조 후 복구 기능 설계가 필요하다.

### F04 — P2: 설치 성공 뒤 임시 파일 정리 실패가 설치 실패로 전달됨

**재현 확인.** 다운로드 ZIP unlink에 PermissionError 주입 시 r2 활성화는 끝났지만 install 호출은 예외로 종료됐다. UI가 실패로 안내해도 실제 활성 버전은 바뀔 수 있다.

근거: [installer.py:106](<../southpaw_tools/installer.py#L106>) 및 [installer.py:114](<../southpaw_tools/installer.py#L114>). 프로브 post_commit_cleanup_error. 커밋 결과와 사후 정리 경고를 구분하는 것이 필요하다.

### F05 — P2/기능 공백: 이전 release 보존은 관리형 롤백이 아님

**재현 확인.** r1→r2 설치 후 r1 설치 요청은 기존 r1 폴더가 있어서 거부됐다. 이전 폴더와 데이터는 보존됐지만 공식 롤백 API/UI는 없다. 새 ID의 낮은 버전은 업데이트 후보가 될 수 있으므로 의도적인 롤백과 잘못된 후퇴도 구분하지 못한다.

근거: [installer.py:80](<../southpaw_tools/installer.py#L80>), [catalog.py:92](<../southpaw_tools/catalog.py#L92>). 프로브 managed_rollback_missing. 기존 ROADMAP의 미완료 항목이며 새로 구현됐다고 볼 근거가 없다.

### F06 — P2: 다운로드 연결 실패 후 연결됨/업데이트 상태가 남음

**재현 확인.** 업데이트 작업에서 연결 실패 예외를 주입해도 online=True, “서버 연결됨”, “업데이트” 버튼이 남았다. 오류 메시지만 바뀌었다. 4초 타이머는 render만 호출하므로 서버 중단을 자동 감지하지 않는다. “업데이트 확인”을 눌러 조회 실패가 완료되면 오프라인 실행 상태로 전환된다.

근거: [ui.py:173](<../southpaw_tools/ui.py#L173>), [ui.py:406](<../southpaw_tools/ui.py#L406>), [ui.py:432](<../southpaw_tools/ui.py#L432>). 프로브 ui_download_failure_retains_connected_state. 로컬 경로 실행 엔진의 오프라인 지원과 UI의 최신 상태 표시는 별개다.

### F07 — P2: 카탈로그 충돌이 정상 로컬 설치의 UI 실행까지 막음

**재현 확인.** 현재 설치와 같은 ID, 다른 ZIP 해시의 카탈로그를 UI 입력으로 주면 설치 버전을 “—”로 표시하고 실행 버튼을 비활성화했다. 로컬 active.json/EXE는 정상이고 엔진의 오프라인 실행 경로 해석은 성공했다. 정상 refresh는 이전 목록과 동일 ID 충돌을 먼저 거부하므로, 이 재현은 충돌한 초기/캐시 카탈로그를 읽는 조건이다.

근거: [ui.py:348](<../southpaw_tools/ui.py#L348>), [ui.py:446](<../southpaw_tools/ui.py#L446>). 프로브 ui_metadata_conflict_blocks_valid_offline_install. 업데이트 신뢰 오류와 검증된 현재 설치 상태를 UI에서 별도로 다루는 것이 필요하다.

## 4. 서버 및 LAN 보안

| 검사항목 | 사실/판정 | 근거 |
|---|---|---|
| localhost와 실제 LAN | 기본은 127.0.0.1만 listen. 같은 PC에서 LAN 주소를 호출하는 것 역시 다른 PC 검증이 아님 | [server.py:143](<../southpaw_tools/server.py#L143>) |
| LAN OFF | OFF로 **시작**하면 LAN listener 없음. 실행 중 설정 파일만 바꾸면 즉시 OFF가 되지 않음. 중단·재시작 필요 | [server.py:199](<../southpaw_tools/server.py#L199>) |
| LAN ON | loopback + 정확히 지정한 RFC1918 IPv4에 TCP listen, 기본8765. 0.0.0.0/공개 IP 거부, 토큰24자 이상 | [server.py:160](<../southpaw_tools/server.py#L160>) |
| 바인딩 실패 | 모든 listener 준비 후 시작. LAN bind 실패 시 loopback도 정리. 기존 테스트는 모의 실패 조건 | [server.py:172](<../southpaw_tools/server.py#L172>) |
| LAN 인증 | 사설/loopback 출발지 + Bearer token 비교. 개별 계정/권한/기기 인증 아님. RFC1918은 회사 소유망이라는 증거가 아님 | [server.py:69](<../southpaw_tools/server.py#L69>) |
| 관리자/다운로드 분리 | HTTP에 게시 endpoint 없음, 쓰기 method405. 로컬 게시 CLI만 존재. 관리자 OS 권한·ACL 분리는 자동 구성되지 않음 | [server.py:81](<../southpaw_tools/server.py#L81>), [admin.py:16](<../southpaw_tools/admin.py#L16>) |
| 임의 파일/경로 탐색 | 카탈로그에 게시된 단일 패키지 이름만 허용, 상대 경로/resolve 경계/링크 검사, 디렉터리 목록 없음. 관련 원래 테스트 통과 | [server.py:29](<../southpaw_tools/server.py#L29>), [server.py:88](<../southpaw_tools/server.py#L88>), [common.py:91](<../southpaw_tools/common.py#L91>) |
| 파일 SHA-256 | 서버의 크기/해시 검증, 클라이언트 다운로드 크기/해시, 압축 해제 시 EXE 해시. 서버 캐시는 stat stamp 기준. 클라이언트 재검증 유지 | [providers.py:95](<../southpaw_tools/providers.py#L95>), [archive.py:56](<../southpaw_tools/archive.py#L56>) |
| 서버 OFF | 새 조회/다운로드 불가. 설치된 로컬 프로그램은 별도 실행 가능. stop은 listener 종료이며 이미 수락한 handler까지 즉시 취소하는 보장은 없음 | [server.py:188](<../southpaw_tools/server.py#L188>), [installer.py:58](<../southpaw_tools/installer.py#L58>) |
| 인터넷 | provider/서버 ON 모두 거부. 다만 운영자가 별도 프록시/터널/포워딩을 만들면 이 정책만으로 외부 공개를 방지할 수는 없음 | [providers.py:133](<../southpaw_tools/providers.py#L133>), [server.py:151](<../southpaw_tools/server.py#L151>) |

Windows 방화벽은 해당 서버 프로세스의 정확한 실행 파일 경로, TCP8765, 개발 PC의 선택한 로컬 IP, 시험 팀원 PC의 원격 IP, 회사가 승인한 Domain/Private 프로필로 범위를 좁혀 검토한다. 방화벽 비활성화·Public/모든 주소 허용은 시험 방법으로 사용하지 않는다. 기존 허용/차단 규칙과 GPO/MDM 정책이 영향을 줄 수 있어 로컬 허용만으로 접속을 보장할 수 없다. 이번에 설정을 조회/변경해 회사 환경을 검증한 것은 아니다. 근거: [Microsoft Windows Firewall rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules).

스레드 기반 표준 http.server이며 TLS·요청률 제한·동시 접속 상한·배포 감사 로그 체계가 없다. 외부 노출/대량 서비스 용도로 평가하지 않는다. Python 공식 문서 역시 production 사용을 권하지 않는다. 근거: [Python http.server](https://docs.python.org/3.13/library/http.server.html).

## 5. 설치·업데이트·복구 안전성

| 항목 | 확인 결과 |
|---|---|
| 현재 버전/release_id | active.json의 AppRelease 사용. UI 버전은 표시용. 다른 release_id이면 같은 version도 갱신, 같은 ID/다른 ZIP 해시는 거부 |
| ZIP 탈출 | 절대/드라이브/UNC/ADS/예약명/NUL/상위경로/대소문자 충돌/링크/부모파일 충돌 차단. 크기·항목수·압축비 제한. 기존 10개 catalog/archive 테스트 통과 |
| 다운로드 중단 | 일반 연결 실패·취소 시 partial 제거 후 다음 시도 전체 재다운로드. range resume 구현 아님. 프로세스 중단 후 자동 정리/복구는 없음 |
| 해시/해제 실패 | 기존 active/payload 유지. 추가로 외부 ZIP 해시는 맞지만 내부 CRC가 깨진 ZIP에서 추출 실패·새 release 미활성화 확인 |
| 활성화 실패 | 일반 예외는 새 target 정리, 이전 포인터 유지. 강제 종료·사후 cleanup 실패는 F03/F04 |
| 실행 중 EXE | 기존 EXE 덮어쓰지 않음. 시작/최종 전환 전 실행 확인, 앱별 OS 잠금으로 설치/제거/launch 경쟁 차단. 추가 잠금 재현에서 실행 요청 거부 |
| 프로세스 탐색 | 현재 interpreter 탐색과 더미 실행은 확인. OpenProcess/QueryFullProcessImageName 접근 실패는 건너뛰므로 높은 권한 앱/외부 직접 실행 시 전수 보장은 미검증 |
| 사용자 데이터 | 선언된 설정은 새 release로 복사, 알 수 없는 작업 파일은 이전 release에 남음. 외부 데이터는 건드리지 않음. 실제 각 앱이 쓰는 모든 경로/마이그레이션 호환성은 기존 앱 실기동 전 미검증 |
| 롤백/제거 | 이전 release 보존과 실패 복원 일부만 있음. 관리형 롤백 없음, 부분 제거 실패 복구 불충분(F01/F05) |

근거: [installer.py](<../southpaw_tools/installer.py>), [archive.py](<../southpaw_tools/archive.py>), [processes.py](<../southpaw_tools/processes.py>), [DATA_POLICY.md](<DATA_POLICY.md>), [test_installer.py](<../tests/test_installer.py>).

## 6. 자동 검사 결과

| 검사 | 이번 결과 | 의미 |
|---|---|---|
| 기존 suite | 42개, 실패0/오류0/skip0, 12.078초 | 원래 검증한 동작의 회귀 없음. 모든 운영 실패 안전을 의미하지 않음 |
| 추가 실패/경계 프로브 | 9개 관찰 재현: 안전한 경계2, 한계7 | “9개 안전성 통과”가 아님. F01–F07을 실제 확인 |
| 실행 가능한 전용 콘솔 더미 | r1/r2 각각 loopback HTTP 설치→서버 종료→오프라인 실제 프로세스 종료코드0 | version0.0.1 동일, release_id만 다른 빌드 갱신·설정 이전·이전 작업 파일 유지도 확인 |
| Offscreen DPI | DPR1.0/1.25/1.5, 5개 등록, 1240×820 창 생성 성공 | 실제 화면 크기/모니터 이동/Windows DPI/접근성 QA 아님 |
| 기존 소스 보존 | 5개 repo, baseline 대상292개 해시·HEAD·태그·상태 동일 | ignored 파일 전체 보존의 전수 검증은 아님 |
| 원본 승인 ZIP | 확보된 4개 모두 고정 해시 동일 | Tag Master ZIP은 여전히 미확보 |

환경: Windows11 build26200, Python3.13.7, PySide6/Qt6.11.0. 기존 도구 실행0, 무해한 감사 더미 실행2, Windows Use0, LAN listener0. loopback만 샌드박스 네트워크 제약으로 별도 실행 권한 아래 검증했다.

근거: [원래 suite 결과](<../.test-results/unit-tests.json>), [상세 로그](<../.test-results/unit-tests.log>), [추가 관찰 JSON](<../.test-results/mvp-audit-probes.json>), [로컬 더미 실기동](<../.test-results/lan-rehearsal/local-rehearsal.json>), [DPI 기록](<../.test-results/mvp-audit-dpi.json>), [원본 보존 재검사](<existing-projects-verification.local.json>).

재현 명령(프로젝트 루트에서 Python 환경을 선택, 실제 LAN 열지 않음):

~~~powershell
python -B -m tools.run_tests
python -B -m audit.mvp_probes
# 새 출력 폴더만 허용; 이 빌드는 Windows 내장 .NET Framework csc.exe 필요
python -B -m audit.prepare_lan_fixture --output .test-results/lan-rehearsal-new
python -B -m audit.local_rehearsal --root .test-results/lan-rehearsal-new
python -B -m tools.verify_existing
~~~

## 7. UI 검토 및 수동 검증

[기존 첨부 화면](<screenshots/launcher-installed.png>)과 실제 위젯 구현을 대조했다. 기존 4개 UI 테스트는 버튼 경계, 3개 창 크기, 글꼴, 더미 설치·업데이트·오프라인 요청을 확인한다.

- 릴리즈 노트의 #, ##, backtick이 원문으로 표시됨: QPlainTextEdit.setPlainText의 실제 동작. 가독성 개선 시 안전한 Markdown 렌더링과 외부 링크 정책 검토 권고. 이번에는 변경 없음.
- “LAN ON/OFF”는 **서버 listener 설정**이다. 현재 연결이 localhost인지 LAN인지 표시하지 않는다. 서버 주소/전송 경로/최종 조회 시각을 구분하는 문구 권고. 같은 PC가 loopback으로 접속해도 서버에 LAN listener가 있으면 LAN ON으로 표시된다.
- 설치/실행/업데이트 기본 상태는 원래 UI 테스트 통과. 서버 중단과 메타데이터 충돌에는 F06/F07 불일치가 있음. “승인 배포본” 배지는 암호학적 검증 완료라는 뜻으로 해석하지 않도록 한다.
- 창 최소980×700, 초기1240×820 logical pixels이고 availableGeometry에 맞춘 축소가 없다. 예를 들어1920×1080의150%에서는 작업 영역이 약1280×720 logical보다 작아 초기 높이가 넘을 가능성이 있다(추정). 최소 창/사용 가능 영역·긴 제목·긴 오류·긴 ID 줄바꿈·키보드 접근성 확인 필요.
- 실제 100/125/150%, 물리 모니터 간 이동, 작업표시줄 포함 화면, Windows10/11, IME/한글 경로, 장시간 다운로드 취소, 팀원 표준 계정 실행, 백신/EDR, 높은 권한 외부 프로세스는 미검증이다.

첫 실제 LAN 절차와 합격 기준은 [LAN_TEST_RUNBOOK.md](<LAN_TEST_RUNBOOK.md>)에 있다. 실제 팀원 PC 조작·방화벽 변경·더미 LAN 공개는 수행하지 않았다.

## 8. 새로운 회귀 위험과 후속 우선순위

이번에 production 변경이 없어 새로운 런타임 회귀를 도입하지 않았다. 추가 프로브는 기존 구현에서 드러나지 않았던 실패 경계를 확인한 것이다. 향후 수정 시 다음 회귀를 피해야 한다.

1. 제거 복구 도입 시 사용자/수정 파일까지 삭제하지 않도록 F01 및 기존 보존 테스트를 함께 유지.
2. 고아 release 복구 시 정상 이전 버전이나 작업 파일을 자동 삭제하지 않도록 중단 시점별 검증.
3. 사후 cleanup 경고 분리 시 활성화 전 실패를 성공으로 처리하지 않도록 커밋 경계 검증.
4. UI 오프라인 보강 시 검증 실패한 업데이트 실행을 허용하지 않으면서 현재 설치 실행을 유지.
5. 서명/권한 도입 시 키 회전·구버전 client·캐시 호환성·오프라인 실행 유지 검증.

기존 방향은 **LAN 배포와 설치·업데이트 안정화 → 관리자 배포 기능 → 런처 자체 업데이트 → 인터넷 배포 옵션 → UI 완성도**로 유지한다. 먼저 F01–F04/F06–F07 재현을 안정화 근거로 삼고, 회사 승인 후 더미 LAN 시험으로 실제 네트워크 경계를 확인한다. 관리형 롤백과 진위 검증은 기존 배포 안전성 과제로 유지한다. 임의 대규모 수정이나 우선순위 재편은 하지 않았다.

자체 업데이트 준비 상태는 설계 예정이다. 현재 앱 설치 엔진을 실행 중 런처 교체에 그대로 사용하면 안 된다. 별도 updater 실행 파일, 런처 종료 확인, 서명된 업데이트 메타데이터, schema 호환성, 교체 실패 복구, 이전 updater/launcher 복원, 패키징/코드 서명이 모두 미구현이다. version 상수와 ROADMAP만으로 지원된다고 볼 수 없다.

Pixel Effect Maker와 개발 중단 Pixel Motion Studio는 계속 제외한다. 회사 GitHub→개인 계정 이전은 ROADMAP에 유지하며 코드 소유권·승인 확인 전 이전하지 않는다.

## 9. Git과 이번 변경

master, 커밋 없음, remote 없음, staging 비어 있음. 기존 v0.1.0 파일은 모두 untracked 상태로 시작했다. 그래서 git diff만으로 이번 변경을 증명할 수 없어 감사 시작 시점 기존 파일47개의 SHA-256과 종료 시점을 비교했다. 비교 결과는 [파일 보존 확인](<../.test-results/mvp-audit-preservation.json>)에 기록한다.

이번 새 파일:

- 이 문서와 [LAN 시험 절차](<LAN_TEST_RUNBOOK.md>).
- [mvp_probes.py](<../audit/mvp_probes.py>), [prepare_lan_fixture.py](<../audit/prepare_lan_fixture.py>), [local_rehearsal.py](<../audit/local_rehearsal.py>): production과 분리한 감사 재현 도구.

기존 production/UI/기존42개 테스트/README/registry/ROADMAP 수정 없음. 기존 로컬 검증 JSON은 보존 재검사 도구가 다시 기록했고 내용 동일성은 hash 비교로 확인한다. 새 실행 결과와 더미 C#/EXE/ZIP은 Git 제외 영역인 .test-results 아래에만 있다. 소스·배포 파일·Git 원격 변경, stage/commit/push, 실제 방화벽 변경, 정식 배포 없음.

## 10. 확인이 필요한 질문

- 회사 승인 시험 PC/담당자/사설 IP·사용 프로필·GPO/EDR·허용 시간은 무엇인가?
- 공유 토큰+신뢰망을 제한적 MVP 시험에 허용하는가? 실제 도구 배포 전 필요한 서명/전송·권한 기준은 무엇인가?
- 제거/업데이트 장애 발생 시 작업 파일 백업과 수동 복구를 누가 담당하는가?
- 기존 5개 앱의 실제 실행·설정 쓰기 위치 QA를 언제 별도 승인할 것인가? Tag Master 승인 원본 ZIP을 확보할 수 있는가?
- 팀원 PC에 Python/PySide6 환경이 있는가? 없다면 런처 패키징 완료까지 LAN UI 시험이 선행 조건에 걸린다.
- 회사 GitHub 저장소 이전의 코드 소유자/승인권자는 누구인가? 이전은 이번 범위에서 수행하지 않는다.
