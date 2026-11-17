# GitHub owner 이전 호환성 — 구현과 배포 경계

2026-11-17. 작업 브랜치 `codex/github-owner-compat-20261117`, 보존 기준
`c498016b23f2497b67b1820a8dc033a358cfbe34`. 원본 master/미커밋 코드는 유지하고
별도 `C:/Dev/CGL-OwnerCompat-20261117`에서 수정했다. 이 문서는 운영 이전 승인이 아니다.

## 구현

| 변경 | 적용한 제한 |
|---|---|
| `github_channels.py` | 운영 ID `1447701732`, 시험 ID `1452413703`를 고정. 해당 두 저장소의 toast-source/rodetoast 네 이름만 같은 채널로 인정 |
| `github_provider.py` | 고정 채널은 `/repositories/ID/releases/latest`로 조회. 일반 API/LAN `NoRedirect`는 유지 |
| 자산 URL 검증 | 같은 채널·같은 Release tag·같은 파일명의 두 owner URL만 허용. 다른 repo/owner/tag/파일/쿼리 거부 |
| 자산 리디렉션 | 정확한 toast-source→rodetoast URL 한 방향과 기존 HTTPS CDN 경로만 허용. 역방향·다른 채널·임의 호스트는 거부 |
| `managed_update.py` | 위 네 채널의 명시적 패키지 설정만 수락. 키·최소 순번·현재 포인터·신뢰 상태는 변경하지 않음 |

저장소 ID는 기존 인증 인벤토리에서 확인한 값이다. 네트워크 응답에서 새 ID나 신뢰키를
자동 등록하지 않는다. 미등록 저장소의 기존 명시적 Provider 기능은 유지하되 owner alias를
추가하지 않는다. repo 이름 재생성으로 다른 ID가 생겨도 이 채널의 대상으로 채택하지 않는다.

이미 이전된 소스 저장소의 옛 API에서 실제 HTTP301 및
`/repositories/1443813273/releases/latest` Location을 관측했다. 배포 저장소를 옮겨 관측한
것은 아니다. GitHub 공식 [REST 리디렉션 설명](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api#follow-redirects)을 참고하되,
이 제품은 불특정 리디렉션 수락 대신 확인된 저장소 ID로 직접 조회한다.

## GUI, Bootstrap, Setup, 서명의 차이

| 구분 | 현재 구현/필요 조치 |
|---|---|
| A. 새 GUI 업데이트 | 새 Provider와 채널 검사 코드를 담은 후속 GUI에서 적용 가능. 기존 toast-source 채널 문자열을 유지해도 ID 조회와 두 owner 자산 검증이 작동. 이미 배포된 0.1.4 EXE에는 소급 적용되지 않음 |
| B. 기존 안정 Bootstrap | Bootstrap 소스·ready/confirmed·worker/rollback 프로토콜은 이번에 수정하지 않음. 옛 Bootstrap은 옛 고정 채널을 계속 사용하고 새 GUI가 네트워크 준비를 담당하는 경로가 가능하다는 코드/합성 근거가 있으나, 실제 구 Bootstrap+후속 GUI 조합은 SPENT03 검증 전 보장하지 않음 |
| B. 새 owner를 직접 설정한 Bootstrap | 기존 Bootstrap의 채널 allowlist는 새 owner를 수락하지 않으므로 새 모듈/채널 검사를 포함한 Bootstrap 빌드 필요. GUI ZIP은 안정 Bootstrap 자체를 교체하지 않음 |
| C. 직원용 Setup | 신규 설치자는 호환 GUI seed와 검증된 Bootstrap을 포함한 후속 Setup 필요. 기존 0.1.4.1의 재설치를 일반적인 업그레이드·복구로 안내할 수 없음 |
| D. 서명/sequence | 기존 Ed25519 키·catalog_id·서명 바이트·SHA-256 검증을 그대로 사용. 같은 home/data와 catalog-trust.json을 유지하며 owner 변경을 이유로 순번을 낮추거나 신뢰 상태를 새로 만들지 않음 |

`SelfUpdater._provider()`의 repository 문자열·동일 키 정책·동일 신뢰 파일 경로 검사는
그대로 유지했다. 패키지의 옛 채널 문자열을 몰래 바꾸지 않는다. old 설정은 old 설정 그대로
같은 ID를 조회하고, 명시적으로 new 설정을 가진 새 패키지는 같은 채널의 new 이름으로 동작한다.
운영/시험 저장소 이름과 정책은 서로 교환하지 않는다.

**현재 Setup은 바뀐 Bootstrap을 덮어쓰는 업그레이더가 아니다.**
`setup_support.check()`는 incoming manifest와 기존 관리 파일 해시가 다르면 중단하고,
NSIS는 `SetOverwrite off`를 사용한다. `managed_update.initialize()`도 기존 current가 있으면
새 seed를 강제 활성화하지 않는다. 두 조건은 합성 파일 테스트로 확인했다.
“새 Setup 재설치만 하면 기존 버전이 전환된다”는 성공 근거는 없다.

## 기존 설치본의 안전한 전환 조건

1. 아직 toast-source 배포 저장소가 유지되는 동안, **실제 후속 버전**의 호환 GUI를
   기존 운영 키와 더 높은 sequence로 배포할 준비를 한다. 이번 작업에서는 빌드/재서명/게시하지 않는다.
2. 기존 클라이언트가 옛 주소에서 그 GUI를 먼저 받을 수 있어야 한다. 실제 직원 설치자 수는
   현재 근거로 미확인이다. 링크 공개/시험 PC 성공을 직원 설치0명으로 간주하지 않는다.
3. 옛 안정 Bootstrap·옛 채널을 유지한 자체 업데이트, 정상 종료·재실행을 SPENT03에서 확인한다.
   이 경로가 통과해도 Bootstrap 파일이 새 버전으로 바뀌었다고 표현하지 않는다.
4. 아직 호환 GUI를 받지 못한 PC와 과거 버전으로 rollback된 PC를 처리할 검증된 지원 경로를
   확보한다. 옛 0.1.4 Provider는 이전 후 API redirect/새 owner URL을 수락하지 못한다.
   현재 구현만으로 모든 과거 EXE를 사후 자동 전환시킬 수는 없다.
5. Bootstrap/Setup 교체가 필요하면 기존 관리 파일과 current를 보존하는 별도 설치 전환 경로를
   구현·검증해야 한다. 현재는 그 자동 전환 방법이 검증되지 않았다. 파일/레지스트리/신뢰 상태를
   수동 삭제·초기화하거나 새 경로에 몰래 재설치하는 우회를 제안하지 않는다.

따라서 이번 소스 수정이 통과했어도 **운영 Transfer는 아직 실행하면 안 된다.** 호환되지 않는
설치본이 남으면 기존 계정을 유지하고 Transfer를 미룬다. 기존 이름의 저장소를 새로 만들어
옛 주소 리디렉션을 깨뜨리는 작업도 하지 않는다.

## 개발 PC에서 완료한 검증

- 신규15개(Provider/서명·ZIP·sequence·오프라인 버전 선택14개 + 실제 GUI callback offscreen1개),
  기존 관련127개: **142개 통과, 실패0·오류0·skip0**. 전체319개 회귀는 반복하지 않았다.
- 실제 ZIP/Installer/합성 설정·작업 파일을 사용했다. 다운로드 EXE나 제품 Bootstrap은 실행하지 않았다.
  GUI callback에서는 정상 종료 요청20과 requested journal을 확인했으며 실제 프로세스 재시작은 아니다.
- 실제 HTTPS 조회 구성4종(API 요청4회, 카탈로그/서명 요청8회; CDN redirect 별도):
  old/new owner 설정 각각 운영seq7·시험seq10 서명 확인.
  운영 catalog SHA-256은 `33ff87e524fafe6dda7050644c86d5d671631e484033da44af0a546fda20a4d7`로 일치했다.
  키 정책 파일 불변, 채널별 동일 신뢰 파일에서 owner 설정 변경 전후 상태 바이트 불변도 확인했다.
- new 설정의 실제 API는 고정 ID이고 실제 자산은 아직 toast-source URL이다.
  **rodetoast로 배포 저장소를 실제 이전한 시험이 아니다.** 이전 후 자산 owner URL과 CDN 연결은
  합성 HTTPS handler/서명 fixture로 검증했으며 실제 이전 관측은 남아 있다.
- 예상하지 않은 WinError5는 관측하지 않았다. 기존 B14/catalog 교체 WinError5 근본 원인 해결을 뜻하지 않는다.

로그/JSON은 `.test-results/owner-compat-20261117/`의 `new-owner`, `owner-gui`,
`setup-boundary`, `related`, `live-catalog-verification`에 있다. 원격 인증정보나 CDN signed query는
기록하지 않는다. 시험키는 임시 fixture이며 운영 신뢰로 등록하지 않았다.

## SPENT03의 최소 후속 실기동 검증

- 새 후보 제작·시험 게시가 승인된 후, 기존 Setup0.1.4.1/옛 Bootstrap의 새 격리 설치에서
  호환 후속 GUI로 **이전 전** 업데이트한다. 5개 앱/설정/합성 데이터 해시와 home/data·순번을 유지한다.
- 정상 종료·동일 Bootstrap 재실행, 실제 GUI·EXE 해시·ready/confirmed·current/journal을 확인한다.
- 별도 승인된 시험 저장소 이전 뒤 옛 설정과 새 설정에서 실제 ID API·자산 URL·HTTPS CDN·서명·크기를
  확인하고 후속 다운로드를 수행한다. 이번 작업은 실제 이전을 하지 않았으므로 생략할 수 없는 조건이다.
- 시작 실패/서명·해시 실패 시 이전 활성 버전과 데이터 보존을 확인한다. rollback된 구 GUI에서
  업데이트가 불가능한 경우를 “완전 호환”으로 처리하지 말고 승인된 지원/설치 전환 경로로 중단한다.
- 후속 Setup이 필요하면 신규 설치와 **기존 current/관리 파일이 남은 상태의 전환**을 각각 확인한다.
  현재의 재설치 guard 차단을 회피하지 않는다. 회사 앱 내부 기능이나 전체 과거 시험은 반복하지 않는다.

## Transfer 시작 조건과 남은 차단

- 시험 저장소: 호환 후보/구 Bootstrap 실기동과 보존·복구 및 되돌릴 수 있는 담당자 지원이 준비된 뒤
  별도 승인으로 먼저 시험한다. 아직 실제 rodetoast 배포 자산 조회 결과는 없다.
- 운영 저장소: 위 시험 통과, 실제 설치자 파악/미전환·rollback PC 처리, 검증된 후속 설치 링크와
  전환 절차가 필요하다. 기존 운영 주소·Release·Latest·서명 asset은 이번에 변경하지 않았다.
- 관리자 게시 도구의 `admin_github.py`는 아직 toast-source repository/login guard를 유지한다.
  reader 수정은 관리자 쓰기 권한 변경이 아니며, 신규 owner 게시 경로는 별도 범위로 검증해야 한다.
- 비공개 증거 도구도 이번에 수정하지 않았다. `scripts/evidence.py`의 exact repository/login,
  private/권한·origin·clean-main·manifest·CRLF·원격 무결성 guard를 유지한다.
  private ID/정확한 owner·계정 쌍과 수신 권한을 별도로 검증하는 guard 수정 및 관련 테스트 전에는
  증거 저장소 Transfer도 불가하다. 임의 repo/계정 허용으로 해결하지 않는다.
- 기존 immutable 0.1.4/과거 Setup에 이 수정이 들어 있다고 간주하면 안 된다. 제품 버전·Setup·키·순번을
  이번에 바꾸거나 가짜 성공 빌드를 만들지 않았다. 소스 브랜치 보존은 배포 승인이 아니다.
