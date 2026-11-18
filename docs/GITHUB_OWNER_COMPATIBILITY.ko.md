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


## 후속 0.1.5 시험 빌드·S11 준비 (2026-11-17)

사용자 승인으로 GUI만0.1.5로 빌드하고 toast-source 시험 채널 S11을 공개했다. 원본0.1.4/운영 Setup0.1.4.1/catalog7·Bootstrap은 변경하지 않았다.
[실제 자산·SPENT03 인계](SPENT03_OWNER_COMPAT_TRIAL.ko.md)에 정확한 해시/소스·서명·준비/미실시 범위를 기록했다. 기존142개 회귀는 재사용하고 이번 패키징 검증만 수행했다.
개발 PC에서 frozen GUI/Bootstrap을 실행하지 않았고 SPENT03 실제 업데이트도 미실시다. 다음 작업은 SPENT03 Codex에서 실제 GUI 검증이며 현재 Transfer 판정은NO다.


## 시험 저장소 Transfer 후속 (2026-11-17)

사용자 보고로 SPENT03 사전 GUI0.1.4→0.1.5 시험은 통과했고 별도 승인/수락 후 시험 저장소만 rodetoast로 실제 이전됐다. ID1452413703·Public·Release15/태그15·Latest11·모든 자산ID/digest 보존 및 최신8자산 실제재다운로드 SHA/서명 확인. 호환 source Provider의 old/new owner 조회·실제ZIP 다운로드도 통과했다. [이전 후 SPENT03 인계](docs/SPENT03_OWNER_COMPAT_TRIAL.ko.md)의 최신 절을 읽는다. 이전 후 Windows 구Bootstrap/GUI실기동은 아직 SPENT03에서 확인해야 하며 같은seq11로 신규 managed update 적용 성공을 주장하지 않는다. 운영/증거 저장소는 이전하지 않았고 운영7/Setup0.1.4.1·기존 guard는 그대로다. 과거 Transfer NO 문구는 당시 상태이며 시험 저장소 실제 이전 사실은 이 절이 최신이다.


## 운영 이전 최종 전환 준비 — 직원 설치 있음 (2026-11-18)

사용자는 공식 Setup0.1.4.1을 실제 설치한 직원이 있다고 확인했다. 따라서 설치0명 경로가 아닌 기존설치 보호 경로를 채택한다. 사용자는 SPENT03에서 이전 후 구Bootstrap+GUI0.1.5 실행/온라인카탈로그/종료·재실행/데이터보존 성공을 보고했다. SPENT03 별도GUI ZIP60초 timeout은 미완료이며, 개발PC에서 완료한 시험8자산/호환Provider 실제HTTPS 다운로드 검증과 구분한다. 이전 후 신규버전의 전체 관리형 업데이트 적용은 아직 검증하지 않았다.

### 실제 로컬 운영 후보

- 폴더: 개발PC 원본 프로젝트 `.test-results/production-owner-transition-20261118/`.
- 소스 commit `9cd9e2c6dcc380e332f3ce01f58af456a4a4ce06`, GUI0.1.5/production-launcher-0.1.5. 제품코드 수정 없이 기존 검증소스를 LF정규 아카이브로 추출하고 운영채널 설정만 별도빌드 사본에 주입했다.29개 제품모듈 hash가 Git blob과 정확히 같다.
- 운영 GUI ZIP `creative-group-launcher--production-launcher-0.1.5.zip`, SHA256 `493b9830479d4fc0150b230cc1b8afeae045166091290f89f38333177ce9b963`. EXE SHA256 `7a4a9187bd16bb4ea469cb80bd09214d4fc4b46efd6e26ccf5a4aa4e6415986e`. EXE는 시험0.1.5와 같고 데이터리소스(채널/키/번들카탈로그)가 운영용으로 다르므로 시험ZIP을 그대로 게시하지 않았다.188파일/manifest/필수DLL/PE x64·GUI subsystem/ZIP안전 검사 통과.
- 기존 운영카탈로그7을 번들에 유지하고 기존toast-source/creative-group-releases·최소4·운영key_id `1efdfb848bb31e3fa5c07095f952c08d920be77253261fbf2742755341f018e0`를 유지했다. 시험키/시험seq11은 포함하지 않았다.
- 실제 운영Latest7 재확인 후 새후보 production-catalog-000008/sequence8을 생성하고 기존운영DPAPI키로 로컬서명했다. 개인키 출력/복사/신규키 생성 없음.5개 회사ZIP·버전·release_id·메타데이터는7과 동일하다.8자산 정확한 목록/size/SHA는 `publish-plan.json`.
- 기존 직원Bootstrap/Setup은 빌드/교체하지 않았다. 기존운영8자산과 Setup0.1.4.1의 원본SHA가 유지됐다. 원격Release/Latest/Transfer는 실행하지 않았다.
- 기존 공식0.1.4.1 빌드소스의 엔진으로 서명오류 차단, 실제ZIP을 prepared까지 스테이징, 구WindowsUpdater 후보검증, old current/receipt/release/합성자료 불변을 확인했다. fixture HTTP이며 실제운영HTTPS 적용이나 제품EXE 실행 결과는 아니다. 운영신뢰7→8허용/8→7차단·신뢰상태보존도 확인했다. 기존142개/전체회귀는 반복하지 않았다. 이번 검사 중WinError5는 없었으나 기존근본원인 해결을 뜻하지 않는다.

### GUI/Bootstrap/Setup 판정

0.1.4 GUI는 저장소가toast-source에 있는 동안 운영키로 서명된0.1.5/8을 기존HTTPS 경로로 받을 수 있다. Bootstrap은 최신검색/다운로드 주체가 아니다. 새GUI의 ManagedSession.prepare→GitHubReleasesProvider→SelfUpdater.prepare가 다운로드하며, 안정Bootstrap은 서명증거/보관ZIP/manifest를 로컬검증하고 worker/health/ready/confirmed로 전환한다. GUI의 채널문자열을toast-source로 유지하여 구Bootstrap 정책과 일치시킨다. 새Provider만 고정repoID/정확한old-new owner쌍으로 실제신규owner자산을 허용한다.

따라서 현재 확인된Setup0.1.4.1 설치본의 owner전환만을 위해 Bootstrap을 교체할 필요는 코드상 확인되지 않았다. 시험구Bootstrap Windows실행과 운영구소스 후보검증이 근거이며, 운영키/운영제품Bootstrap의0.1.4→이새후보 실제Windows 적용과 이전후신규버전적용은 아직 미검증이다. 지원되지 않는 Bootstrap교체/강제pointer변경을 제안하지 않는다.

기존설치의GUI전환에는 새Setup이 필수는 아니다. 다만 이전후신규설치/재설치는 구GUI0.1.4를seed로하는공식Setup0.1.4.1에 의존하면 안 된다. 일반직원용 호환GUI seed의 후속Setup과 정확한설치링크를 이전 전에 별도검증/승인하여 준비해야 한다. 기존Setup은 다른Bootstrap 덮어쓰기와 existing current의 새seed 강제전환을 지원하지 않으므로 기존PC에 재설치만 하면 해결된다고 안내하지 않는다. 신규PC용Setup과 기존PC의GUI업데이트를 구분한다.

### 실제 기존직원이 있을 때의 순서

1. 이번 로컬후보의 정확한8자산 해시로 운영호환Release 게시 승인을 받는다. 승인전게시 금지. 게시직전Latest7/ownerID1447701732/태그충돌을 재확인한다.
2. **toast-source 소유를 유지한 상태**에서8자산 Draft 생성/업로드/재다운로드검증 후 카탈로그8을 공개·Latest 지정한다. 기존7/Setup/Release는 보존한다. 실패하면 원격상태보고; 같은8 덮어쓰기나7로신뢰후퇴 금지.
3. 기존공식Setup계열의 대표PC에서 운영키로 서명된본후보의 실제GUI 업데이트·Bootstrap종료/기동·ready/confirmed·정상종료·동일Bootstrap재실행을 한차례확인한다. 이미통과한시험채널시험이나회사앱기능을 반복하지 않는다. 실패시Toast운영경로를그대로두고중단한다.
4. 실제설치직원에게GUI업데이트를 안내하고 각대상current0.1.5/실제EXEhash/정상재실행 및 committed·pending문제없음을 담당자가확인한다. 단순카탈로그8조회나ZIP다운로드만으로전환완료라하지않는다. 회사앱/사용자자료는보존하고직원에게전체시험을시키지않는다. 누락·오프라인·다운로드실패·rollback0.1.4 PC가있으면Transfer보류: Toast주소가있을때복구/재업데이트한다.
5. 호환GUI seed를사용하는신규설치/재설치용후속Setup·담당자지원경로를준비한다. 기존옛설치링크의배포를중단하고새링크를확정한다. 구Setup/기록은삭제하지않는다. 새Setup인플레이스복구성공을가정하지않는다.
6. 기존설치전환확인·신규설치경로·지원준비후 **별도의운영Transfer승인**을받는다. 이전후ID/Public/모든Release/8자산SHA/서명/Latest8을확인하고대표운영PC의조회·실제다운로드·정상재실행을확인한다. 아직새버전이없으면신규managed update적용은미검증으로남긴다.

미업데이트/롤백0.1.4는301만으로작동한다고보장할수없다. 이전후자동복구를발명하지않는다. 전환확인범위밖의옛복사본까지영구지원하는호환성은없다. 설치0명으로확인되는상황이라면직원별업데이트단계는생략가능하지만현재는해당하지않는다. 설치상태가불명이면한번확인하고확인전에는설치있음으로보수적으로취급한다.

### 실제 남은 차단과 다음 승인 하나

현재 운영Transfer는 **NO**. 차단은 기존직원미전환, 운영서명후보의대표Windows적용미검증, 이전후신규설치용호환Setup/링크미준비다. Bootstrap교체필수라는새근거는없으며, 단순60초ZIPtimeout 재시험/142회귀반복은이판정의전제조건이아니다. 향후rodetoast운영게시용관리자guard는정확한repoID·계정·권한을유지해별도검증하거나공식gh의정확한대상으로승인게시해야한다. 현재toast-source운영쓰기guard는해제하지않았다.

**다음 승인 대상은 하나:** 운영소유권은Toast에유지하고이정확한production-catalog-000008 호환Release를게시해기존직원에게0.1.5업데이트를제공하는작업. Transfer/새Setup공개까지묶인승인이아니다. 후보Windows검증은승인된게시후담당자대표시험으로구분하고실패시확대를중단한다.


## 운영 호환 GUI0.1.5 실제 게시 완료 (2026-11-18)

사용자가 정확한 기존후보의 운영게시를 승인하여 `production-catalog-000008`(Release ID449405600)를 toast-source/creative-group-releases(ID1447701732)에 실제게시했다. 저장소 Transfer/Setup배포/Bootstrap교체는 승인범위밖이며 실행하지 않았다.

Release: https://github.com/toast-source/creative-group-releases/releases/tag/production-catalog-000008

운영Latest는 **production-catalog-000008 / sequence8**, GUI0.1.5 / production-launcher-0.1.5다. 운영키 식별자는 `1efdfb848bb31e3fa5c07095f952c08d920be77253261fbf2742755341f018e0`. 새서명/재빌드없이 승인후보바이트 그대로, 정확한8자산만 Draft에업로드했다. Draft8개 실제재다운로드 SHA/서명/manifest 검증 후 먼저non-Latest로공개하고, 공개CDN HTTPS에서8개를모두다시받아동일검증에통과한뒤Latest8로지정했다. 기존catalog7과employee-setup-0.1.4.1의Release metadata/asset ID·이름·크기·digest 동일성을확인했다. 회사5개ZIP·버전·release_id와시험rodetoast저장소는변경하지않았다.

| 자산 | bytes | SHA256 |
|---|---:|---|
| ase-viewer--0.5.8.4-team-3bf37dd.zip | 22085231 | `2532c273c4cf9930cf882ef1f84cae55c9a97479a69123431560b1299edec2d2` |
| catalog.json | 9432 | `dd65ae96167c31a7f63014ce6deb7152488804161f19f90b957966e7ccdb288a` |
| catalog.sig.json | 245 | `9420492936a83554e3d2429481ca8dd21254914d510c5e23b7e8c37bc4da7c1c` |
| creative-group-launcher--production-launcher-0.1.5.zip | 52638826 | `493b9830479d4fc0150b230cc1b8afeae045166091290f89f38333177ce9b963` |
| pivot-fixer--0.3.3-team-80b84c9.zip | 20709116 | `214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361` |
| ps2ase--0.3.6-team-6e84645.zip | 66252089 | `1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9` |
| tag-master--0.4.0-team-7263f8d.zip | 38813495 | `80865038ddab9a1b9050d04cbb48cb777edf4e6419caafb05b8b51c0f6962299` |
| tilenamer--0.1.6-rc3-8ba7a1e.zip | 54046715 | `aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4` |

런처 EXE SHA256 `7a4a9187bd16bb4ea469cb80bd09214d4fc4b46efd6e26ccf5a4aa4e6415986e` / manifest 포함188파일. 카탈로그·서명·ZIP바이트는승인계획과동일하다. GUI다운로드URL:
https://github.com/toast-source/creative-group-releases/releases/download/production-catalog-000008/creative-group-launcher--production-launcher-0.1.5.zip

기존공식0.1.4 source Provider로실제HTTPS /repos/toast-source/creative-group-releases/releases/latest를읽고운영키/신뢰순번7→8·GUI0.1.5제공을검증했다. 이결과는Windows제품실행/관리형업데이트실제적용이아니다. 개발PC에서제품EXE/회사EXE/새회귀/Setup설치를실행하지않았다. 게시중실패·재업로드·서명덮어쓰기·자동rollback은없었다. 근거는원본프로젝트 `.test-results/production-owner-transition-20261118/`의publication-state.json, draft-redownload, public-redownload, public-legacy-provider.json이다.

### SPENT03 Codex 인계 프롬프트

> 운영 호환 GUI0.1.5가 https://github.com/toast-source/creative-group-releases/releases/tag/production-catalog-000008 에게시됐고Latest8이다. 이문서의최신게시결과/8자산해시를기준으로, **격리된운영대표환경**에서기존운영Bootstrap+GUI0.1.4→0.1.5 실제GUI업데이트만한차례검증하라. 시험채널/시험키의기존OC11환경을운영환경으로위장하거나신뢰상태를덮어쓰지마라. 기존격리운영0.1.4환경이있으면보존후재사용하고, 없으면운영 employee-setup-0.1.4.1 Release에서 최초배포ZIP `SouthpawToolsLauncher-Employee-0.1.4-RC1-Windows-x64.zip`(SHA256 `57c3ff1f5add76d9c8e4011ca5ce89d3fea4d044b31b949fe9550241f2665338`)을GitHub에서직접받아새짧은격리프로그램경로에해제하고 별도새 --data-dir로최초실행하라. 기본AppData나기존업무설치를사용하지마라. 운영Bootstrap SHA256 `c15f48a0d72dd0a8bdc1ad909a75ae3327a91a2f136170dc4c3713651df6cb19`와초기GUI0.1.4 seed/proof를확인하라. Bootstrap교체/가짜버전/직접current편집/시험키주입금지. 초기운영ZIPURL은 https://github.com/toast-source/creative-group-releases/releases/download/employee-setup-0.1.4.1/SouthpawToolsLauncher-Employee-0.1.4-RC1-Windows-x64.zip 이다. 직원용Setup0.1.4.1은새로배포하거나재설치할필요없다.
>
> 실행전 기존격리상태를보존하고 GUI0.1.4 실제기동후업데이트승인전current/receipt/운영신뢰상태/Bootstrap해시/설정·합성작업파일 기준을확보하라. 운영카탈로그8 실제온라인조회·운영서명확인 후 GUI버튼으로0.1.5업데이트를승인하여실제HTTPS 다운로드→ZIP SHA `493b9830479d4fc0150b230cc1b8afeae045166091290f89f38333177ce9b963`→manifest/설치파일/EXE SHA `7a4a9187bd16bb4ea469cb80bd09214d4fc4b46efd6e26ccf5a4aa4e6415986e`→Bootstrap정상종료/health/ready/confirmed/재시작을확인하라. 정상종료후동일Bootstrap으로재실행해current0.1.5·receipt·운영신뢰seq8·기존설정/합성작업자료·기존설치상태보존을확인하라. 기존5개회사앱이설치돼있으면읽기전용해시/상태만비교하고, 없는경우5개설치가보존됐다고만들거나불필요하게재설치하지마라. 회사앱내부기능시험은하지마라.
>
> 실제GUI·Bootstrap적용과단순HTTP/로컬Installer검증을구분하고WinError5·timeout·실패의원로그/중간상태를보존하라. 강제복구/신뢰순번초기화/무조건재시도하지마라. 실패하면직원전체안내와운영Transfer를중단한다. CLI를우선하고핵심GUI조작에만Windows Use를사용하고바로제어를해제하라. 시험채널기존검증/전체회귀/설치목록조사는반복하지마라. 결과는기존SPENT03증거규칙에따라통과·실패·미검증과자료경로를구분하여기록하라. 사람이파일을수동복사할필요없다.

### 남은 차단

SPENT03의**운영키/실제운영후보 Windows0.1.4→0.1.5 업데이트**는아직미검증이다. 직원대상확대안내는이대표검증통과후진행한다. 실제직원이있으며전직원설치본이전환됐다는증거는없다. 운영Transfer는계속보류하며미업데이트/rollback0.1.4 PC처리와이전후신규설치용호환Setup/링크준비도필요하다. 기존직원Setup0.1.4.1의새seed강제전환/복구를보장하지않는다. 과거WinError5근본원인은미확정이다.
