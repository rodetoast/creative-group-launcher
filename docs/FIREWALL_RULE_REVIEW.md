# 더미 LAN 시험 방화벽 초안 검토 — 미승인·미적용

2026-11-03 KST. 검토 대상은 Git 제외 .test-results/lan-approved-192168019의 proposed-firewall-add.ps1 및 proposed-firewall-remove.ps1이다. **두 파일을 실행하거나 수정하지 않았다.** 서버/시험 타이머를 시작하지 않았고 기존 규칙·프로필·첫 commit을 보존했다.

## 적용 범위

추가 초안의 조건은 모두 AND 관계다:Inbound, Block, Enabled, Public, 지정된 Python313/python.exe, IPv4 로컬192.168.0.17, TCP 로컬8765, 원격IPv4 두 범위. RemotePort는 제한하지 않아 시험 client의 임시 source port를 허용할 수 있다.

프로그램 경로는 C:/Users/<개발PC 사용자>/AppData/Local/Programs/Python/Python313/python.exe에 고정돼 있다. 실제 정확한 원문은 해당 ps1에 있으며 다른 .venv/pythonw.exe/다른 Python 설치에는 적용되지 않는다. 실행 전 실제 server PID의 executable 경로를 대조해야 한다.

원격 범위0.0.0.0–192.168.0.18과192.168.0.20–255.255.255.255는 수치 계산상 **192.168.0.19 하나를 제외한 모든 IPv4**를 포함한다. 이 계산은 IP 주소 상수만 비교했으며 다른 PC로 패킷을 보내지 않았다. 제안 규칙은 승인 client를 차단하지 않지만, 통신 성공을 보장하는 새 Allow 규칙도 아니다.

현재 Python Public TCP Allow 규칙은 로컬/원격 주소·포트가 Any인 상태다. 현재 유효한 Public Inbound Block2개는 다른 실행 파일에 대한 TCP/UDP 규칙이어서 이 Python과 일치하지 않았다. 차단 규칙은 충돌한 허용 규칙보다 우선하므로 제안의 주소 예외가 중요하다. 근거: [Microsoft Firewall rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules).

이전 허용 규칙·현재 조사만으로 회사 EDR/GPO/시험 PC 방화벽/라우팅까지 성공으로 판정하지 않는다. IP 제한은 PC의 암호학적 신원 확인이 아니다. 192.168.0.19의 실제 요청은 아직 없다.

## 다른 프로그램/서비스 영향

- 실행 파일 경로 조건이므로 PID별 격리가 아니다. 같은 python.exe의 다른 프로세스가 같은 IPv4/포트/Public 조건을 사용하면 함께 제한된다.
- 다른 실행 파일, 다른 TCP 로컬 포트, 다른 로컬IP, UDP, Outbound 통신은 이 초안과 일치하지 않는다. 기존 Python UDP Allow 규칙을 수정하지 않는다.
- 현재8765 listener0이나 향후 다른 프로세스가 사용하지 않을 것까지 보장하지 않는다. 시작 직전 재확인하고 이미 다른 서비스가 점유하면 임의 종료하지 않고 시험을 중단한다.
- 관리자가 전역 Python 규칙을 바꾸는 방식이 아니라 새로 추가한 단일 scoped rule을 쓰는 구상이다. 그렇다고 다른 서비스에 절대 영향이 없다고 주장하지 않는다.

## IPv6와 인터페이스

- 이 초안의 LocalAddress/RemoteAddress는 IPv4이므로 IPv6를 차단하지 않는다.
- 실제 ThreadingHTTPServer.address_family는 AF_INET이고 ServerController는127.0.0.1과 명시적 사설IPv4만 bind한다. 따라서 현재 코드에서 직접적인 IPv6/:: wildcard listener는 만들지 않는다. 이것은 방화벽의 IPv6 차단 보장이 아니라 현재 server bind 조건이다.
- 이더넷 IPv4는192.168.0.17이고 IPv6 link-local 주소가 있다. 다른 조회 인터페이스인 Bluetooth는 disconnected/169.254 IPv4이며, 해당 주소로 server를 bind하지 않는다.
- 규칙에 InterfaceAlias/InterfaceType은 지정되지 않았다. 같은 로컬IP가 다른 인터페이스에서 사용되거나 경로/프로필이 바뀌는 환경까지 물리 NIC 격리를 보장하지 않는다. 시작 직전 IP/인터페이스/프로필과 bind 주소를 다시 확인하고 바뀌었으면 중단한다.
- portproxy show all은 비어 있었다. NAT static mapping 조회는 provider 오류로 확인하지 못했다. 외부 공유기/프록시 설정까지 없다고 단정하지 않는다. 라우터/다른 PC에는 접근하지 않았다.
- 승인 후 실제 listener는127.0.0.1:8765와192.168.0.17:8765만 있어야 한다. 0.0.0.0,::,다른IP가 보이면 시험을 중단한다. 다른 Python/server 명령으로 우회하지 않는다.

## 적용 전 기록과 한계

읽기 전용 snapshot을 Git 제외 firewall-review-before 아래에 저장했다.

- snapshot.local.json:유효 프로필/기본 정책, 인터페이스, rule header656개,8765 listener0, 제안 이름의 규칙 부재.
- python-rules.local.json:기존 Python TCP/UDP2개 규칙의 이름·상태·action·profile·주소·포트·프로그램.
- public-inbound-blocks.local.json:현재 유효 Public inbound block2개의 범위.

전체 ActiveStore PortFilter/AddressFilter 열거는 Access Denied였다. 따라서 첫 snapshot은 완전한 firewall export가 아니다. 관련 rule을 통한 association 조회로 Python 규칙과 Public block의 세부 범위는 확인했으나, 실제 적용 승인 후 관리자 권한에서 변경 직전 snapshot/새 규칙 부재를 다시 확인해야 한다. 모든 규칙을 import해 되돌리는 복구는 하지 않는다.

## 초안의 운영상 공백

1. add의 존재 검사에 SilentlyContinue가 있어 조회 권한 오류와 실제 부재를 확실히 구분하지 않는다.
2. add는 ErrorAction Stop/생성 후 filter 검증/생성 성공 기록이 없다. 일부 오류가 난 상태를 정상 완료로 간주하면 안 된다.
3. remove는 정확한 Name 하나만 지정하므로 광범위 삭제는 없지만, 이 시험이 생성한 규칙인지 fingerprint/생성 기록을 확인하지 않는다. 현재 부재라는 관측만으로 미래의 동일 이름 객체를 무조건 삭제해도 된다는 뜻은 아니다.
4. 이름의 날짜와 설명은 자동 만료가 아니다. 초안에는30분 후 자동 server 종료나 규칙 삭제가 구현돼 있지 않다. 실제 시험 시작 전 시간 제한/정리 담당과 종료 확인을 갖춰야 한다.

**판정:범위 제한 의도는 타당하지만, 현 초안을 그대로 적용한 뒤 오류가 나도 안전하게 정리된다고 확정하지 않는다.** 권한 오류를 중단 처리하고, 새 규칙의 생성 증거와 정확한 filter를 확인하는 절차를 보완한 적용본을 다시 검토·승인해야 한다. 이번에는 초안 파일을 바꾸지 않고 결과만 제시한다.

## 승인 후 적용/실패/복구 절차 제안 — 미실행

### 적용 전

관리자 권한에서 현재IP/프로필/8765 비점유/해당Name 부재와 조회 성공을 확인한다. 기존2개 Python 규칙과 프로필을 파일로 저장한다. 이번 고유 Name·설명 marker·전체 scope와 생성 예정 시각을 기록한다. 조회 실패나 이름 충돌이면 아무 것도 추가/삭제하지 않고 멈춘다. server는 아직 시작하지 않는다.

### 추가 성공 또는 실패

- 생성은 오류를 중단 처리하고 결과 객체를 저장한다. 새Name/실행 파일/주소/포트/action/profile이 승인 범위와 정확히 같은지 재조회한다. 일치 확인과 생성 성공 기록이 있을 때만 server를 일반 사용자 권한으로 시작한다.
- 생성 명령 실패 후에는 성공이나 무변경을 추정하지 않는다. 그Name이 실제 존재하는지와 filter를 읽는다. 없다면 server를 열지 않고 오류를 보고한다.
- 존재하면 변경 전 부재 기록·방금 반환한 객체·고유marker·전체 scope를 대조한다. 이번에 생성한 객체임이 확실할 때만 그 객체 하나를 제거하고 부재를 재확인한다. 동일 이름이지만 범위/소유 기록이 다르면 자동 삭제하지 말고 담당자 확인을 받는다.

### 시험 종료와 삭제 실패

- 성공/실패 여부와 무관하게 시험 server부터 종료하고8765 listener0을 확인한다.
- 생성 기록과 현재 rule fingerprint가 일치할 때만 이번 rule 하나를 지운다. 이름 패턴/DisplayName wildcard나 기존 Python 규칙 전체를 대상으로 삭제하지 않는다.
- 삭제 후Name 부재와 기존2개 Python 규칙·프로필이 변경 전과 같은지 대조한다. 무관한 동시 정책 변경을 임의로 되돌리지 않는다.
- 삭제 권한/오류가 발생하면 server를 종료한 채 두고, 잔여Name/범위/오류를 기록해 관리자에게 같은 단일 규칙 삭제를 요청한다. 성공으로 보고하거나 server를 재시작하지 않는다.
- 현재 PowerShell token은 일반 사용자 권한이다. 관리자 권한·정책 승인이 필요하며 방화벽 전체 해제/프로필 변경/백신 종료로 우회하지 않는다.

첫commit32afb846d0bc69b38203a259dad71180cd4a14b5·기존 프로그램·패키지·기존 규칙을 보존했다. 실제 규칙 적용/삭제·LAN 시작·다른PC 접속·stage/commit/push는 하지 않았다.
