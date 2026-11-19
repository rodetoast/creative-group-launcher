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


## 자율 진행 적용 및 신규직원 Setup0.1.5.0 로컬후보 (2026-11-18)

사용자 지시에 따라 운영카탈로그8 게시/원격검증/인계는 기존결과를 재사용하고, SPENT03 결과를 기다리는동안 독립적으로 신규직원용 후속Setup을 준비했다. 승인되지 않은 원격게시/운영Transfer/직원환경변경은 실행하지 않았다. 정책은 기존AGENTS규칙을 보존하고 덧붙였으며, 원본제품코드/미커밋소스/HEAD/branch는 유지했다.

### 실제 후보와 검증

- Setup: `SouthpawToolsLauncherSetup-0.1.5.0-RC1.exe` / version0.1.5.0 / SHA256 `8d8c5940e0f08adfcf9d073fe3c29971f96de3fb06396f41f11fa5b817f56453`.
- 초기배포ZIP: `SouthpawToolsLauncher-Employee-0.1.5-RC1-Windows-x64.zip` / SHA256 `203e9ae003e98eb76ec4c976c1a9f5f4eb53bc78906bd3f24fbd8566d29ef3c3`.
- 원본프로젝트 `.test-results/employee-015-setup-candidate-20261118/candidate-files/`에EXE/ZIP/SHA256SUMS.txt/CANDIDATE_FILES.manifest.json 존재. 로컬후보이며 아직GitHub에없다.
- 최초GUI0.1.5/production-launcher-0.1.5, 운영서명sequence8 seed. 기존공개GUI ZIP·카탈로그·서명은동일바이트로재사용했다. 시험키/seq11을포함하지않는다. Bootstrap은공식Setup0.1.4.1의기존진단포함바이트를재사용했으며 SHA256 `c15f48a0d72dd0a8bdc1ad909a75ae3327a91a2f136170dc4c3713651df6cb19` / 파일버전0.1.4. GUI와Bootstrap/Setup버전은독립적이다.
- 제품GUI/Bootstrap은재빌드하지않았다. 변경된Setupmanifest를내장하는Guard만재빌드하고 기존NSIS템플릿 그대로 일반직원등록을컴파일했다. 내부app_id/AppUserModelID·기존등록키·바로가기이름·기본경로는유지했다. SPENT03/BD13 시험접미사없음. 회사5개ZIP은Setup에넣지않고기존카탈로그로받는다.
- 로컬검증:payload39개 전체해시,Guard내장manifest일치,NSIS solid LZMA의bounded읽기에서실제payload/Guard바이트일치,직원ZIP안전검사,운영서명seq8,기존Bootstrap x64 GUI subsystem/진단모듈,실제격리파일기반GUI0.1.5 seedinitialize/old WindowsUpdater검증·두번째initialize current불변·합성자료보존 통과. 설치/제거/실제GUI/작업표시줄/운영이전후신규Setup네트워크실행은미검증이다. 전체회귀는반복하지않았다.
- 최초NSIS CreateProcess가WinError623(DLL재배치오류)로컴파일진입전실패했다. 기존로그/에러기록을보존했다. 같은compiler의일반권한·샌드박스외부/깨끗한자식환경 /VERSION성공을확인한뒤구분된환경으로컴파일1회를수행해exit0이었다. DLL/시스템PATH/정책/ACL을바꾸지않았다. 샌드박스로더와상속환경중정확한차단주체는분리되지않았고근본원인해결로주장하지않는다. 과거제품WinError5와별개다.

### 프로젝트별 지침 원격 반영

아래6개 기존격리개발브랜치에AGENTS만commit/push하고원격commit/파일내용을확인했다. 원본작업트리는AGENTS의끝에규칙만추가했고기존본문/제품소스/미커밋변경은합치지않았다.
- ase_viewer: `0d5a7d114c0bedb645c2f3cfaa57ca8c0e9aeee1` / `codex/migration-checkpoint-20261117` (AGENTS만, 원격ref/내용확인)
- Ase-PS Bridge Pro: `fee0a4e07e2131f256a1d0dda08473c85f59015d` / `codex/migration-checkpoint-20261117` (AGENTS만, 원격ref/내용확인)
- Pivot_Fixer: `8f02d60e98c609415821dd221a4611f2aa762807` / `codex/migration-checkpoint-20261117` (AGENTS만, 원격ref/내용확인)
- AsepriteTagMaster: `08d15a900fc05f4c8fe45539114c15435b1c4ed1` / `codex/migration-checkpoint-20261117` (AGENTS만, 원격ref/내용확인)
- Pixel Effect Maker: `ca7155277cd5c9c6651e2a4d1634584072633885` / `codex/migration-checkpoint-20261117` (AGENTS만, 원격ref/내용확인)
- TileNamer: `71f4080994b7bb33015dd11ac23d51529514b368` / `codex/migration-checkpoint-20261117` (AGENTS만, 원격ref/내용확인)

Pixel Motion Studio와증거도구는기존로컬전용정책체크포인트에만문서커밋했다. Pixel Motion 원격생성이나증거도구원격브랜치를임의로결정하지않았다. 해당로컬2개를원격보존완료라하지않는다. Pixel Effect 원본Git의소유권guard가동작하여Git상태조회가차단됐으나safe.directory/소유권/ACL설정은변경하지않았다. 대신원본HEAD/index/config/ref바이트불변을확인하면서AGENTS만추가했고,정상관리되는격리체크포인트에서만commit/push했다.

### 인계와 다음 경계

현재SPENT03이즉시수행할작업은앞절의 **기존운영Bootstrap+GUI0.1.4→공개카탈로그8의GUI0.1.5** 실제업데이트이다. 필요한공식초기ZIP/해시/버전/판정·보존조건은앞절에완비돼있고수동파일복사가필요없다. 이번Setup후보를그시험대신설치해출발버전을바꾸지않는다.

새Setup0.1.5.0은기존직원GUI업데이트용이아닌향후신규설치용이다. 기존current나다른소유파일을강제로덮어쓰는기능은없다. 새Setup의SPENT03최초설치/바로가기/종료·재실행/제거·자료보존 검증을위한원격운송은새게시승인후GitHub non-Latest시험Release로만준비한다. 아직원격게시승인이없으므로지금공개하거나수동복사를요구하지않는다. 설치목록비노출및B14/catalog WinError5미해결은유지한다.

운영Latest8/기존Setup0.1.4.1/기존Release·회사ZIP·서명정책·source原本은유지. 운영Transfer/새Setup공개/직원PC변경은사용자별도승인경계다. 같은목표안의통상구현·오류최소수정·후보검증은계속자율수행하고완료/타PC실행/실제결정필요시에만통합보고한다.


## 운영 업데이트 통과 반영·RC1 Draft 인계·직원 전환 확인 (2026-11-18)

사용자는 SPENT03에서 **공식 운영Bootstrap/운영키/카탈로그8의GUI0.1.4→0.1.5 실제GUI업데이트**가성공했다고보고했다. ZIP/EXE/manifest/receipt,committed거래,정상종료·동일Bootstrap재실행,합성자료보존을모두통과한것으로완료처리하고반복하지않는다. 이사실은사용자가전달한SPENT03결과이며개발PC가실행한시험이아니다. 과거시험채널/S11결과및별도ZIP60초timeout과구분한다.

### 기존 Setup RC1 전달 완료 — 공개 게시 아님

- 기존 Setup `SouthpawToolsLauncherSetup-0.1.5.0-RC1.exe` / bytes83404359 / SHA256 `8d8c5940e0f08adfcf9d073fe3c29971f96de3fb06396f41f11fa5b817f56453` 그대로. 재빌드·재패키징없음.
- 운송저장소 rodetoast/creative-group-trial-releases, ID1452413703. 운송tag `employee-setup-0150-rc1-transport-20261118`, **Draft ID449518343**.
- 실제Draft URL: https://github.com/rodetoast/creative-group-trial-releases/releases/tag/untagged-2e356c394839407bb519
- 정확히RC1 EXE와 `SouthpawToolsLauncherSetup-0.1.5.0-RC1.exe.sha256` 두자산만업로드. GitHub인증재다운로드와API digest/크기/SHA일치확인. 정식공개/공개prerelease게시를하지않았고 Draft=True이다. 일반직원에게배포할링크가아니다. 원격로그인권한없이공개URL로받을수있다고안내하지않는다.
- 시험Latest trial-catalog-000011 및 운영Latest production-catalog-000008의ID/태그불변확인. 운영Setup0.1.4.1/Bootstrap·회사5개원본·서명/순번정책변경없음.
- 기존로컬파일검증(39payload·manifest·seed0.1.5/seq8초기화·보존)은재사용한다. **RC1 실제Windows설치/바로가기/제거는아직미검증**이다.

### SPENT03 Codex가 이어서 수행할 범위

**출발 상태:** 기존운영0.1.4→0.1.5업데이트검증은완료됐으므로다시하지않는다. 기존OC11/운영업데이트시험/보고서·설치·자료는보존하고이번에는별도의신규Setup시험만한다. 실제운영채널/키·GUI0.1.5seed·기존Bootstrap을사용한다.

**GitHub에서직접받기:** 기존gh인증/도구를재사용한다. 해당Draft를볼수있는계정/저장소권한을읽기전용확인한다(토큰/비밀번호출력금지). 접근불가시권한문제로기록하고Draft를공개하거나다른자산으로대체하지않는다. `gh release view employee-setup-0150-rc1-transport-20261118 --repo rodetoast/creative-group-trial-releases --json databaseId,isDraft,assets`로ID449518343/Draft/두자산을확인한뒤새다운로드경로로 `gh release download employee-setup-0150-rc1-transport-20261118 --repo rodetoast/creative-group-trial-releases --dir <새다운로드폴더> --pattern SouthpawToolsLauncherSetup-0.1.5.0-RC1.exe --pattern SouthpawToolsLauncherSetup-0.1.5.0-RC1.exe.sha256` 를수행한다. EXE SHA `8d8c5940e0f08adfcf9d073fe3c29971f96de3fb06396f41f11fa5b817f56453`와크기를검증한다. 사람이파일을옮기거나명령을대신실행하게하지않는다.

**설치 전 보호조건 — 폴더분리만으로충분하지않음:** 이RC1은정상직원등록/바로가기를쓰는동일제품설치본이다. 현재사용자의 `HKCU\Software\SouthpawGames\ToolsLauncherSetup` 및 `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\SouthpawToolsLauncher`(관련32/64보기)의존재/InstallLocation/DataRoot와시작메뉴·바탕화면의 `Southpaw 도구 런처.lnk` 존재/대상을읽기전용확인하라. 기존등록/바로가기가있거나기존런처가작동중이면**기존환경과충돌가능성으로설치를시작하지말고**해당관측과보존상태를보고하라. 기존키/바로가기삭제·값수정·기존Setup제거·기존프로세스강제종료로빈환경을만들지마라. 이미준비된별도빈Windows사용자/VM이있으면사용가능성을보고하되새계정/VM/권한을임의만들지마라.

**새시험경로:** 보호조건이통과하면현재존재하지않는짧은루트(예 `C:/Dev/S15R1`가없을때그아래 P/D/E)를선택한다. P는설치프로그램, D는사용자데이터, E는증거로분리한다. 경로가이미있으면덮어쓰거나초기화하지말고다른짧은새이름을선택한다. 기존실제AppData런처경로의존재상태와이전시험자료기준을읽기전용보존한다. 승인된시험원본만사용한다.

**실제설치시험:** RC1을일반권한으로실행하여 `/DATA=<D>` 및 마지막인자 `/D=<P>`로새경로를명시한다. 실제Setup화면에서설치·완료/종료코드를기록한다. RequestExecutionLevel user인제품이며관리자승격이나보안차단우회를하지않는다. SAC/Windows가차단하면화면/코드만보존한다. 설치전충돌검사없이/기존등록이있는상태에서실행하지마라.

**최소사용자흐름:** 설치완료→실제GUI최초0.1.5기동→운영카탈로그8정상확인→정상종료→설치로생긴바탕화면/시작메뉴바로가기를각각실제클릭하여GUI재기동·정상종료. 과도한반복/이미통과한자체업데이트시험은하지않는다. Bootstrap `c15f48a0d72dd0a8bdc1ad909a75ae3327a91a2f136170dc4c3713651df6cb19` 및 GUI EXE `7a4a9187bd16bb4ea469cb80bd09214d4fc4b46efd6e26ccf5a4aa4e6415986e`·manifest/receipt/current·seed서명/순번8을기존도구로확인한다. 회사5개목록과실행가능상태표시는볼수있지만회사EXE/개별기능을시험하거나5개를다시설치하지않는다. 프로그램명/아이콘·콘솔창유무는핵심화면만확인하고Windows설치목록비노출의추가원인조사는하지않는다.

**제거와보존:** D에합성설정·작업파일을만들고해시를확보한다. GUI/Bootstrap정상종료후P의이번설치가생성한Uninstall.exe만실행한다. 설치관리파일/이번바로가기·등록제거,launcher-home/current/receipt·D의합성파일보존을파일/로그와함께확인한다. 회사프로그램데이터가실제로없는환경이면그보존을실증했다고쓰지말고이시험의합성자료범위로한정한다. 잔여관리형데이터를자동삭제하지마라. 제거후current만남았다고제품실행가능한상태라고표현하지마라.

**판정/증거:** 설치·GUI0.1.5·두바로가기·정상종료/잔여프로세스·제거·합성자료보존을각각통과/실패/미검증으로E/REPORT.ko.md에정리하고,해시목록·Setup/Bootstrap로그·필요최소스크린샷을E아래보존한다. WinError5/timeout/guard실패는실제오류로남기고같은조건연속재시도·강제복구/신뢰초기화/기존환경정리를하지않는다. CLI우선,실제GUI조작에만Windows Use를쓰고끝나면즉시제어를해제한다. 민감정보/nonce/토큰/사용자파일본문은공유하지않는다. 기존증거정책이확정된경우검토된사본만공유하고원본은유지한다. 합격이어도Setup정식공개/운영Transfer/직원PC변경은시작하지마라.

### 직원에게 전달할 짧은 문구 — 작성만 완료, 발송하지 않음

> Southpaw 도구 런처를 열어 런처 자체 업데이트 안내에서 0.1.5 업데이트를 진행해 주세요. 완료되면 런처를 정상 종료하고 평소 바로가기로 다시 열어 주세요. 업데이트 안내가 없거나 오류가 나면 재설치하지 말고 담당자에게 알려 주세요. 적용 여부는 담당자가 확인하겠습니다.

### 담당자 확인 — 실제 확인된 것만 체크

직원전체에게동시에보내기보다담당자가대상을정해안내한다. 이름/PC/담당자/일자는사용자가정하며개인직원목록을공개Git에올리지않는다. 직원PC접근·원격변경·메시지발송은승인전실행하지않는다.

- [ ] 실제실행된GUI가0.1.5다(관리형current/실제EXE해시/GUI상태를서로구분해확인). 카탈로그8을조회한것만으로적용완료라하지않는다.
- [ ] 정상종료후기존바로가기/동일Bootstrap으로재실행된다.
- [ ] 업데이트오류·미완료/복구대기·rollback0.1.4가없다. committed이력은정상완료이력이며삭제하지않는다.

현재확정상태는**직원설치자가있음 / 직원별완료현황미수신 / 전체전환미확인**이다. SPENT03합격은직원전체완료의대체증거가아니다. 담당자검토에서미확인PC도완료로간주하지않는다. 미업데이트/실패/rollbackPC가하나라도남으면운영Transfer가능으로표시하지않고현재toast-source주소를유지한다. 직원에게해시검사·전체시험·재설치를요구하지않는다.

### 남은 승인 경계와 작업 순서

지금은Draft운송/인계까지만완료,RC1설치시험은SPENT03실행대기다. SPENT03통과→담당자의기존직원완료확인→검증된신규Setup정식설치링크확정→운영Transfer별도승인순서다. 다음실제승인은검증후의 **새Setup정식공개**, **운영creative-group-releases Transfer**, **증거저장소Transfer**를서로구분해야한다. 증거owner/login guard는아직미전환이므로증거Transfer는독립된차단이다. 직원직접변경이나키/신뢰정책변경은포괄승인으로간주하지않는다. 현재는그승인을요청하기보다SPENT03이이인계범위를자율완료하고결과를돌려줄수있게한다. 새기능/재빌드/회귀/회사앱시험은하지않았다.


## 최신 결정: 직원별 확인 없이 기존 채널 보존 (2026-11-18)

사용자는 직원별0.1.5확인을생략하되 미업데이트직원접속은보존하도록결정했다. 과거문서의전직원확인조건은이번후속의해결책으로사용하지않는다. 메시지발송/직원PC접근/개별완료수집을하지않는다.

**B안 선택: rodetoast 기준운영저장소 준비 + toast-source 완전한호환채널 유지. A안 운영Transfer는실행하지않는다.** 구0.1.4는NoRedirect와owner검사로301을거부할수있고불변바이너리를원격에서고칠수없다. 직원확인없이원본주소를없애면서안전성을보장할근거는없다. 구클라이언트가나중에실행될수있는동안**기한없이원본주소/계정과전체자산을유지**한다. 다운로드수/시간경과로완료를추정하지않는다. 훗날명시적구버전지원종료결정전에는운영원본Transfer/삭제/이름변경을하지않는다. 따라서모든저장소소유권이전완료는아니다.

### 실제 성립하는 병행 구조

- 단순Git mirror는Release자산을복제하지않는다. Rod 신규repo는다른ID를갖는다. 현재0.1.5는Rod owner문자열로설정해도기존ID1447701732로조회하므로 새repo로전환됐다고표현하면안된다. 현재0.1.4/0.1.5와RC1은Toast원본을계속사용한다.
- 새기준repo와옛호환repo에 **같은서명카탈로그/서명/GUI와회사5개ZIP 전체8개를동일바이트**로제공한다. 옛카탈로그만남기거나옛자산을Rod URL로갈아끼우지않는다. 기존운영키/catalog_id/최소4/sequence/release_id/ZIP hash는그대로다. 최초신규repo복제는현재서명된8을재사용하며재서명하지않는다.
- 후속카탈로그N은명시적게시승인하에 Rod전체Draft/실제재다운로드검증→Rod공개→Toast동일바이트전체Draft/검증→Toast공개 순서다. 부분실패하면옛완전한Latest를유지한다. 양쪽게시는원자적이지않으며같은N을다르게재서명하거나신뢰를N-1로후퇴시키지않는다. 옛Release/자산은삭제하지않는다.
- 클라이언트의신규Rod repoID 직접라우팅은**미구현/미검증**이다. 새ID가실제로확정된뒤별도고정binding과구Bootstrap채널정책을검토한후속GUI를준비할수있다. 임의ID/자동탐색/임시키로지금활성화하지않는다. 현B안의기존접속보호에는제품GUI/Bootstrap/Setup재빌드가불필요하다.

### 실제 구현과 검증

`tools/prepare_parallel_release.py`는기존운영키·최소4·옛repoID·서명된정확한8개자산을검증하는읽기전용계획도구다. 원격쓰기기능은없다. 새repoID가없으면null/미확정으로기록하고,옛ID를신규병행ID로위장·다른owner/private/no-admin·다른서명/누락자산/변경ZIP을차단한다. 원격복제의tag/이름/크기/digest확인함수도포함한다. 기존게시엔진을대체하지않는다. 합성12개통과했고실제기존카탈로그8/8자산과원격기존Release8 metadata로 `parallel-catalog8-plan-v2.json`을로컬생성했다. 최초복제는이미공개된Toast8을수정/중복생성하지않고새Rod에만동일자산을준비한다. 원본파일/서명은불변이다.

현재Rod인증에서기존운영repo는pull만확인됐고push/admin은False였다. 신규Rod운영repo의실제ID는미확정이다. 신규repo생성/동일8자산최초운영게시승인이필요하다. 옛호환채널은기존Toast인증으로관리가능하며Rod에최소게시권한을부여할지는별도권한승인사항이다. 권한을임의바꾸지않았다. 현재코드와새계획만으로신규Rod자산실제게시완료라하지않는다.

### 증거 저장소 최소 후보

Private ID1454974908, 기존Toast/Toast로그인과이전후Rod/Rod로그인 쌍만허용하도록 `scripts/evidence.py`를수정했다. 동일ID/정확한origin/Private/visibility/push권한/clean main을검사한다. 작성자·contents/blob재다운로드·보고서URL은검증된실제repo/account에묶인다. 기존collect/validate/schema/민감정보·스크린샷검토/중복revision/CRLF무결성/원격hash는유지했다. 실제보고서는수정/재해시하지않았다.

고유58개(기존·신규57개 + 추가모의publish경계1개)통과. 합성수집→검증→dry-run과모의실행→staged bytes/작성자/contents재검증까지연결했다. 최초시험은Git루트C:/Dev안의장치설정으로기존보호가차단했으며외부TEMP로옮기고import TestCase 중복수집을고쳐통과했다. 초기오류로그는보존하고보호를완화하지않았다.

Private 개발브랜치 `codex/evidence-owner-compat-20261118`, commit `854b44b04ed98cd1f5fdd208cd19682cd42b19c0`에push/원격파일확인했다. main/기존증거/owner는유지했다. 현Rod자격증명의이전전Private조회는404로권한미확인차단이며Toast기존인증은정상이다. 실제이전전후main에후보를안전하게반영하고Rod Private수신·push권한을검증해야한다. 현재후보를운영도구적용완료로표시하지않는다.

### RC1과 다음 승인 경계

RC1 `8d8c5940e0f08adfcf9d073fe3c29971f96de3fb06396f41f11fa5b817f56453` 그대로,재빌드/재패키징없음. sw204의직원등록/바로가기충돌과Draft인증부재로설치전에중단됐다는사용자보고를**미실시**로기록한다. 기존운영업데이트와사용자직접업데이트/기존바로가기재실행성공은완료로재사용한다. [SPENT03 통합인계](SPENT03_OWNER_COMPAT_TRIAL.ko.md)의최신독립환경절하나에환경·공식로그인·시험/판정·증거보존을모았다.

실제남은차단은 (1) RC1용충돌없는독립Windows환경/공식Draft인증, (2) 신규Rod운영repo/최초완전복제승인과증거도구main적용·Rod Private권한/별도Transfer승인이다. 직원별확인대기는조건에서제외했다. 우선승인대상은 **Rod 신규Public 운영repo + 현재카탈로그8 동일8자산 최초게시**이며기존운영Transfer승인이아니다. Setup정식공개는RC1실검증후,증거Transfer는도구·권한확인후별도승인한다.

기존7개소스·시험저장소이전/개발기록은유지했다. 운영Latest8/시험Latest11/Setup0.1.4.1/RC1·원본회사ZIP은변경없음. 새운영repo생성/Release게시/Transfer/제품빌드/전체142회귀/직원환경변경은이번에하지않았다.


## rodetoast 카탈로그8 동일 자산 복제 완료 (2026-11-18)

사용자가신규Public 운영복제repo생성과카탈로그8 동일8자산게시를명시승인했다. A(파일보존·다운로드/서명검증)를완료했으며 B(직원클라이언트의독립신규업데이트채널전환)는완료하지않았다.

- 새repo https://github.com/rodetoast/creative-group-releases / ID **1462539740** / Public / rodetoast관리자권한확인. Release전용설명과최소README초기commit `0c6792ae4c92ac4264066b1f17800f0314abea9b`을생성했다. 제품소스저장소가아니다.
- 복제Release https://github.com/rodetoast/creative-group-releases/releases/tag/production-catalog-000008 / ID **449720497**, tagproduction-catalog-000008 / 정식public,prerelease=False. 신규repo/release/asset ID는원본과다르다. 전송대상은아래정확한8개뿐이다.
- 원본은 toast-source/creative-group-releases / ID1447701732, Release449405600. 원본Release8개/자산38개 metadata·ID/크기/digest·본문과전체tag/commit·Latest8을이전/이후대조해보존확인. Setup0.1.4.1은그대로다. 소유권Transfer/이름변경/삭제/원본쓰기요청은하지않았다.
- Draft업로드후8개실제인증재다운로드 hash/서명/manifest검증→새repo복제Release공개→8개전체공개CDN HTTPS재다운로드 size/SHA256/Ed25519검증을완료했다. 기존후보를재빌드/재패키징/재서명하지않고개인키를사용/복사하지않았다. 기존12개합성검증을재사용했으며전체회귀/Windows시험을반복하지않았다.
- 명시적으로 `--latest=false`로공개했지만신규repo에유일한일반Release가있어실제 `/releases/latest`는카탈로그8을200으로반환했다. 이API응답은직원런처의활성설정전환을의미하지않는다. Toast의실제활성Latest는계속카탈로그8이다.

| 복제 자산 | bytes | SHA256 |
|---|---:|---|
| ase-viewer--0.5.8.4-team-3bf37dd.zip | 22085231 | `2532c273c4cf9930cf882ef1f84cae55c9a97479a69123431560b1299edec2d2` |
| catalog.json | 9432 | `dd65ae96167c31a7f63014ce6deb7152488804161f19f90b957966e7ccdb288a` |
| catalog.sig.json | 245 | `9420492936a83554e3d2429481ca8dd21254914d510c5e23b7e8c37bc4da7c1c` |
| creative-group-launcher--production-launcher-0.1.5.zip | 52638826 | `493b9830479d4fc0150b230cc1b8afeae045166091290f89f38333177ce9b963` |
| pivot-fixer--0.3.3-team-80b84c9.zip | 20709116 | `214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361` |
| ps2ase--0.3.6-team-6e84645.zip | 66252089 | `1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9` |
| tag-master--0.4.0-team-7263f8d.zip | 38813495 | `80865038ddab9a1b9050d04cbb48cb777edf4e6419caafb05b8b51c0f6962299` |
| tilenamer--0.1.6-rc3-8ba7a1e.zip | 54046715 | `aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4` |

운영키id `1efdfb848bb31e3fa5c07095f952c08d920be77253261fbf2742755341f018e0`,sequence8/기존catalog_id유지. 카탈로그의HTTP URL필드는실제로 **0개**였다. release_id/package_name/app_id/버전/해시는원본그대로이며repoID나owner로재해석하지않았다. 복제GUI ZIP내부managed-channel.json은여전히 `toast-source/creative-group-releases`다. 현재GUI0.1.5의고정API ID는1447701732다. source의Rod owner alias도Transfer대상같은ID를가리키는기존정책이라신규별도ID1462539740를자동선택하지않는다. 서명/순번보호나Bootstrap채널을바꾸지않았다. 이번업로드성공을새Rod채널실제업데이트/관리형적용성공이라고보고하지않는다.

### 보존·통합 현황과 다음 승인

Rod에실제로추가된것은README와이번카탈로그8의8자산뿐이다. 과거 `catalog-000001、catalog-000002、catalog-000003、production-catalog-000004、employee-bootstrap-0.1.1、production-catalog-000007、employee-setup-0.1.4.1`의7개Release/30개자산과원본Git/태그이력·직원Setup은원본에보존돼있고신규repo에전부복제된것이아니다. 같은tag이름이라도신규Git태그는새repo의README commit을가리키며원본Git이력과동일하다고하지않는다. GitHub자동제공Source archives는승인8자산에포함되지않고제품설치ZIP으로사용하지않았다.

구0.1.4가나중에돌아올수있는동안Toast주소/계정/전체호환자산을기한없이유지하는B안제약은변함없다. 직원별업데이트확인을다시요구하지않는다. 새Setup정식공개·기존직원설치/자료변경·운영/증거Transfer는실행하지않았다. 증거Private/guard도유지했다.

현재복제본은Rod에서실제로보존/관리할수있지만독립클라이언트채널은미전환이다. 후속으로신규실제ID의고정binding/구Bootstrap정책·sequence/실제HTTPS관리형업데이트전환검증을준비할수있다. 신규운영카탈로그/Setup 공개,원격Transfer,지원중단은별도승인이다. 과거Release/Setup자산의추가원격복제를할경우에도이번8자산승인과구분해정확한목록/해시로승인받는다. 기존0.1.4접속을끊는Transfer는대안으로강행하지않는다.

개발PC근거: `.test-results/rodetoast-catalog8-replica-20261118/`의replication-state.json,identity-bound-copy-plan.json,catalog-reference-semantics.json,draft-redownload,public-redownload. 원본master와미커밋코드는보존했다.


## 신규직원 Rod 채널 구현 기준 (2026-11-18)

별도브랜치 codex/rodetoast-channel-20261118에서GUI0.1.6 신규후보를준비한다. 기존0.1.5/Bootstrap/Setup/Toast채널은변경하지않는다. 새채널은명시적 repository_id1462539740 + rodetoast/creative-group-releases + 전용서명catalog_id creative-group-launcher-rodetoast-1462539740 + 최소seq9를함께요구한다. 기존Ed25519키/서명domain/schema/ZIP SHA/고수위/rollback보호는유지하며namespace가서로다르면같은키의유효서명도거부한다. 기존catalog8복제는새채널로채택하지않는다.

초기GUI0.1.6·새고정채널Bootstrap·Setup0.1.6.0 로컬후보를만든다. 신규기본루트는프로그램 %USERPROFILE%/CGL-Rodetoast, 데이터 %LOCALAPPDATA%/SouthpawGames/ToolsLauncherRodetoast이며기존ToolsLauncher와분리한다. 일반직원제품명/app_id/AppUserModelID/바로가기/등록키는유지해기존설치와겹치면자동전환/덮어쓰지않고차단한다. 초기Setup은기존채널홈/신뢰자료/비어있지않은미소유데이터를자동흡수하지않는다. 구Setup0.1.5.0 RC1은Toastseed용이력으로보존한다.

신규GUI·Bootstrap은서로같은새채널정책을탑재해야하므로기존ToastBootstrap을새Setup에그대로재사용하지않는다. 기존직원Bootstrap교체를시도하는것이아니다. GUI/새Setup의실제Windows시험은독립환경에서SPENT03이수행하며현재sw204설치를변경하지않는다. 새로운운영카탈로그/GUI/Setup의정식공개는별도승인전실행하지않는다.


패키징검증중신규GUI EXE의비관리형직접실행이기존AppData기본값에접근할수있는경로를찾았다. 신규frozen채널은Bootstrap세션으로만일반기동하고,독립된 --check 진단은명시적별도data-dir가있을때만허용하도록초기UI/데이터접근전에차단했다. 기존frozen legacy직접실행은유지한다. 관련2개추가시험통과. 이전미공개RC1을보존하고GUI/manifest/Setup만RC2로재제작한다. Bootstrap실행코드는변하지않았으므로기존신규채널Bootstrap1.6바이트를재사용하고출처commit을분리기록한다.


## 운영 이력 전체 보존 및 신규 Rod 채널 최종 로컬 후보 (2026-11-18)

이번승인으로과거Release7개/30자산을추가복제했다. 기존카탈로그8의8자산은이전검증을재사용하고ID/body/digest불변을확인했다. **양쪽8개Release/38개자산 전체가보존됐고누락없음,신규Rod Latest는계속production-catalog-000008(ID449720497)**. Toast원본 ID1447701732/Latest8(ID449405600)/Setup0.1.4.1/GUI0.1.5/서명자산은읽기외변경하지않았다. 회사EXE/직원PC를실행·변경하지않았다.

### 실제 역사 복제

| tag | 원본Release ID | Rod Release ID | 자산수 |
|---|---:|---:|---:|
| catalog-000001 | 435976237 | 449777549 | 3 |
| catalog-000002 | 435981675 | 449777678 | 3 |
| catalog-000003 | 436091851 | 449777835 | 3 |
| production-catalog-000004 | 441260740 | 449777998 | 8 |
| employee-bootstrap-0.1.1 | 441261267 | 449778882 | 2 |
| production-catalog-000007 | 448100573 | 449779459 | 8 |
| employee-setup-0.1.4.1 | 448100822 | 449780278 | 3 |

각추가자산은검증된로컬캐시또는원본HTTPS에서받아원본GitHub digest/size와대조한뒤업로드했고,Rod 공개HTTPS에서다시받아동일SHA를확인했다. 역사카탈로그1/2/3은기존시험공개키정책,4/7은기존운영공개키정책으로분리서명도검증했다. 서명/카탈로그를재작성·재서명하지않았다. 제목/body/정식·prerelease·draft상태는원본과같고,GitHub가새로부여한ID·작성계정/게시시각은달라질수있으며원본/신규시각을history-state.json에보존했다. 자동Source archives는설치자산으로사용하지않았다.

| tag | 자산 | 동일 SHA256 | 원본 → 신규 asset ID |
|---|---|---|---|
| catalog-000001 | catalog.json | `a539a5a9aa9a03934c067ed4715b946513afdce4a0eb2e94f07d5de14f221501` | 715492650 → 762809486 |
| catalog-000001 | catalog.sig.json | `3538cbec96d17383c6923086388dc861e1e138b49e8e807c22f9054c7f8d42a5` | 715492678 → 762809489 |
| catalog-000001 | dummy--github-smoke-r1.zip | `30b90804d355d0d556b2766d8bd1d98a7f8edf2bd9ef6fc40b77bf31efebd931` | 715492704 → 762809490 |
| catalog-000002 | catalog.json | `2511ee2b30b674419efe9dca55685bcd08c7e749308d5d8b424c47ae137fa95e` | 715503882 → 762809872 |
| catalog-000002 | catalog.sig.json | `aea8f157f63f2605144f1c9f04d65e3644a890f111fbb0a67ac0015c7881b95c` | 715503912 → 762809867 |
| catalog-000002 | dummy--github-smoke-r2.zip | `3fe8ebf9b303015243d863d94b4f5e39a450da4ca379afb70ebf7256c4fdee6c` | 715503950 → 762809869 |
| catalog-000003 | catalog.json | `627698fc19642796bb7cb3c05e0047e3c839da3318d5ee48e74de8c117b16dc8` | 715867783 → 762810296 |
| catalog-000003 | catalog.sig.json | `0eb3668cd5ae80a535aa5d18f60416be26f748146fc09e3ee660057273f1b5f2` | 715867815 → 762810315 |
| catalog-000003 | dummy--github-smoke-r3.zip | `e9986fe6efa72163d413390bbcada9dc9b1fb89694f50b0996e26eede4f518fe` | 715867842 → 762810318 |
| production-catalog-000004 | ase-viewer--0.5.8.4-team-3bf37dd.zip | `2532c273c4cf9930cf882ef1f84cae55c9a97479a69123431560b1299edec2d2` | 734210849 → 762810704 |
| production-catalog-000004 | catalog.json | `9d690dfffd6355ade07dac5aeab6fef6a5087d5673a67e8d4cf0eac0d23caf92` | 734210848 → 762810703 |
| production-catalog-000004 | catalog.sig.json | `5f57bfa48fb883f5081a6f026a69427fc7e80758e0b2ba910d2e7fe060fe877d` | 734210874 → 762810705 |
| production-catalog-000004 | creative-group-launcher--production-launcher-0.1.1.zip | `59dbf396f866dfbabc2f0559bfb60573a3f2228a2d00a37890e4b87f5de5ab55` | 734210852 → 762810702 |
| production-catalog-000004 | pivot-fixer--0.3.3-team-80b84c9.zip | `214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361` | 734210872 → 762810701 |
| production-catalog-000004 | ps2ase--0.3.6-team-6e84645.zip | `1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9` | 734210902 → 762810738 |
| production-catalog-000004 | tag-master--0.4.0-team-7263f8d.zip | `80865038ddab9a1b9050d04cbb48cb777edf4e6419caafb05b8b51c0f6962299` | 734210910 → 762810737 |
| production-catalog-000004 | tilenamer--0.1.6-rc3-8ba7a1e.zip | `aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4` | 734211016 → 762810900 |
| employee-bootstrap-0.1.1 | CGL-Employee-0.1.1-Windows-x64.zip | `605afa20380a80e4fb5646b7b714a424b0ab9257c81076edacd8aea4b942365d` | 734213162 → 762813432 |
| employee-bootstrap-0.1.1 | SHA256SUMS.txt | `257662fd15e38d8990e1ec5bbdb1d49f33fb22e0d3ff4581701731198c9cd482` | 734213163 → 762813428 |
| production-catalog-000007 | ase-viewer--0.5.8.4-team-3bf37dd.zip | `2532c273c4cf9930cf882ef1f84cae55c9a97479a69123431560b1299edec2d2` | 757540001 → 762814832 |
| production-catalog-000007 | catalog.json | `33ff87e524fafe6dda7050644c86d5d671631e484033da44af0a546fda20a4d7` | 757539974 → 762814840 |
| production-catalog-000007 | catalog.sig.json | `def866a78769f864c87ac6135add33b3db0e2681db19c362cef550d1acd8ce70` | 757539998 → 762814830 |
| production-catalog-000007 | creative-group-launcher--production-launcher-0.1.4.zip | `6906e4eaf95ada2c4ceff9eec99c9205ec2305b1c8b2e9e46c13c980e479a4e3` | 757539975 → 762814841 |
| production-catalog-000007 | pivot-fixer--0.3.3-team-80b84c9.zip | `214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361` | 757539994 → 762814829 |
| production-catalog-000007 | ps2ase--0.3.6-team-6e84645.zip | `1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9` | 757540054 → 762814865 |
| production-catalog-000007 | tag-master--0.4.0-team-7263f8d.zip | `80865038ddab9a1b9050d04cbb48cb777edf4e6419caafb05b8b51c0f6962299` | 757540044 → 762814872 |
| production-catalog-000007 | tilenamer--0.1.6-rc3-8ba7a1e.zip | `aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4` | 757540219 → 762815022 |
| employee-setup-0.1.4.1 | SHA256SUMS.txt | `64224d734c153c15722d12d40543bd9c2fc2c7b0ca53410af4f4b0ee4ee86576` | 757540527 → 762817013 |
| employee-setup-0.1.4.1 | SouthpawToolsLauncher-Employee-0.1.4-RC1-Windows-x64.zip | `57c3ff1f5add76d9c8e4011ca5ce89d3fea4d044b31b949fe9550241f2665338` | 757540510 → 762817014 |
| employee-setup-0.1.4.1 | SouthpawToolsLauncherSetup-0.1.4.1.exe | `d73f85b2f39d31444ad45f1cb0377b35a86d439a6574ac4e4e6b018a8ff0dac3` | 757540530 → 762817008 |

### Git 이력·태그

기존보존mirror를기반으로격리작업bare repo를만들어최신원본heads/tags를별도namespace로읽고정상push했다. 원본Git 객체·도달가능commit그래프는모두Rod에서참조가능하다. 같은이름이비어있거나동일한refs는정확한이름으로보존했다. **두이름충돌은강제덮어쓰기하지않고archive ref로보존했으며원래이름의정확한교체는보류**했다:
- `refs/heads/main` → `refs/heads/archive/toast-source/main`, 원본SHA `cddb92efc0b0751796f00bfd8d7d4955f44d121a`; 기존Rod ref 유지.
- `refs/tags/production-catalog-000008` → `refs/tags/archive/toast-source/production-catalog-000008`, 원본SHA `cddb92efc0b0751796f00bfd8d7d4955f44d121a`; 기존Rod ref 유지.

따라서모든원본객체/역사는보존됐지만서로다른main을강제병합하거나기존카탈로그8의Git tag를바꾸지않았다. 과거7개Release태그는원본Git SHA를그대로가리킨다. 기존Rod main/카탈로그8태그/8개자산은그대로다. 초기Git403은Git캐시Toast와CLI Rod의인증불일치였으며명령단위로공식gh credential helper를지정해해결했다. 전역설정/기존인증/토큰출력변경없음. 초기실패기록도보존했다.

### 신규 채널 로컬 최종 후보 — 운영 미공개

- 새repoID1462539740, repository rodetoast/creative-group-releases를명시적으로고정한다. 기존owner alias의기본ID1447701732는바꾸지않고새필드 repository_id가있을때만신규ID를선택한다.
- 새서명카탈로그ID `creative-group-launcher-rodetoast-1462539740`,최소/초기sequence9. 기존운영Ed25519 key_id `1efdfb848bb31e3fa5c07095f952c08d920be77253261fbf2742755341f018e0`와서명domain/schema/SHA/고수위·rollback방어는유지한다. catalog_id 자체가서명본문에있어구채널과신규채널을분리한다. **실제운영서명끼리도old8→new정책과new9→old정책은식별자검사에서거부됨**을검증했다. 신규ID의실제API/자산URL을읽었을때현재복제8을정상적으로거부하고신뢰상태를생성하지않는것도확인했다. 이는신규9온라인설치성공이아니라올바른사전차단이다.
- GUI0.1.6 / release_id rodetoast-launcher-0.1.6 / ZIP SHA `9cf77abbb2289043e1abe882f197f5063619063cc9fc2db7e7e1ddb673c1203d` / EXE SHA `2e17bbe8b78e513975e003726ac8d7297955c65e59e6c6a7a3a6721464476bc5`.
- 신규고정채널Bootstrap0.1.6 SHA `152a02ce9f36f65df534da711a626474a9cc2116a5736adbfc601b33898a0a09`. 기존직원Bootstrap교체가아니라**새직원용초기배포구성**이다. 구Toast Bootstrap은재사용하지않았다. GUI직접실행보호패치뒤변경없는신규Bootstrap은같은바이트로RC2에재사용했다. GUI sourcecommit `0dc4fdc0b1cf7edccdf7e57d47a18f4019353fd9`,Bootstrap sourcecommit `abe04c2782749883240a24cdc7a0f84512061698`를각각검증했다.
- Setup0.1.6.0 **RC2**: `SouthpawToolsLauncherSetup-Rodetoast-0.1.6.0-RC2.exe`, SHA `405906b160b3314c225cc76cca41e610fdce40154937488a0a861b059da5bf07`. 초기ZIP SHA `bf7cba1cdb23bbf9b25e721196009504502fb5ea372cd1bd5c64a68569e9ae66`. 실제파일/8자산/서명/승인계획은원본프로젝트 `.test-results/rodetoast-history-and-channel-20261118/final-candidate/`에있다. **앞서만든미공개1.6 RC1은보존하되배포대상아님**. 공개전의local9 후보교체는새검증루트로분리했고기존신뢰상태를초기화하지않았다. 공개후같은9를다른바이트로덮어쓰면안된다.
- 새기본P `%USERPROFILE%/CGL-Rodetoast`,D `%LOCALAPPDATA%/SouthpawGames/ToolsLauncherRodetoast`. 기존직원Data/관리형home을새정책으로자동해석하지않고차단한다. 일반제품명/등록키/바로가기/app_id/AppUserModelID는유지하므로기존설치가있는같은Windows사용자에게동시자동전환설치하지않는다. frozen 신규GUI직접실행은UI/데이터접근전에차단하고Bootstrap세션기동을요구한다. 독립 --check는별도data-dir만허용한다.
- 회사5개ZIP·버전·release_id·필수경로/메타데이터는기존8과동일하다. Setup0.1.5.0 RC1은Toast/구namespace8 seed용과거후보이고이번신규채널용이아니다. 해당바이너리/Draft/미실시Windows시험상태는보존했다.

### 검증 범위

직접관련고유**80개**통과(기존+신규66,ack/GUI12,직접실행보호추가2; 변경후신규채널16개재확인). 전체142/전체회귀는반복하지않았다. GUI테스트는Qt offscreen/모의프로세스이며제품EXE실기동이아니다. 실제파일로새namespace9 seed초기GUI1.6설치·WindowsUpdater파일검사·재초기화current/합성자료불변·구운영fixture홈거부를확인했다. GUI188파일/Bootstrap34파일의Git sourcehash·PE x64 GUI subsystem·public policy/ID·manifest,Setup실물LZMA내payload39개/Guard를대조했다.

제공된개발사용자프로필기준예상기본P37/D74 UTF16길이의별도격리경로에서Setup과실제회사5 ZIP멤버의설치/복구/제거경로예산을검사해통과했다. 도구환경LOCALAPPDATA가리디렉션된별도162자관측과구분했으며실제사용자디렉터리를생성/변경하지않았다. zip파일구조안전검사는유지됐다. WinError5근본원인해결을주장하지않고,새Setup의실제Windows설치/GUI/제거·새namespace9온라인작동/실제자체업데이트는**미검증**이다.

### 이후 게시·이중 운영

정확한로컬 `final-candidate/publish-plan.json`의다음범위는승인이필요하다:
1. 필요시시험저장소non-Latest prerelease로RC2 Setup/sha만운송(아직게시안함). 공개시험운송으로Draft인증문제를피할수있지만기존sw204등록은바꾸지않는다.
2. 독립Windows Setup시험후Rod에 `rodetoast-catalog-000009`의정확한8자산을Draft/재다운로드검증→정식공개·Latest9. **Toast에는새namespace9를게시하지않는다.**
3. SPENT03가공개된9의실온라인조회·새ID자산다운로드/신뢰상태를확인한뒤 `employee-setup-rodetoast-0.1.6.0`을non-Latest로정식공개해새직원링크를확정한다. 초기GUI1.6와catalog9목표1.6은같으므로신규버전업데이트시험성공이라고하지않는다. 실제미래1.6→상위버전은추후실제릴리스가있을때검증한다.

역사카탈로그8은동일바이트복제였지만**미래운영은서로다른서명namespace/카탈로그/GUI배포묶음**이다. 이전동일N양쪽복제지침을신규namespace9활성게시에는적용하지않는다. 회사ZIP은공통원본을읽기전용재사용할수있어도Toast구namespace와Rod신규namespace를서로재게시하지않는다. 양쪽Latest/해시/원격다운로드/키교체·지원책임을각각관리해야하는부담이있다. 구0.1.4가돌아올수있는동안Toast계정/주소/전체호환Release/자산은기한없이유지하며직원별완료확인을요구하지않는다. 명시적구버전지원종료결정없이는다운로드수/시간경과로계정을없애거나Transfer하지않는다.

운영/증거Transfer·새정식게시·직원PC설치·원본앱/Setup변경은이번에하지않았다. [SPENT03 최신단일인계](SPENT03_OWNER_COMPAT_TRIAL.ko.md)의신규RC2절을사용한다.


## Rod 운영 카탈로그9 게시와 온라인 검증 (2026-11-19)

Rod 운영 저장소 ID **1462539740**의 Latest는 [rodetoast-catalog-000009](https://github.com/rodetoast/creative-group-releases/releases/tag/rodetoast-catalog-000009)이며 Release ID는 **450977319**이다. 이전 Rod Release 8개와 자산 38개를 전후 대조했다. Toast 저장소 ID 1447701732 및 Latest8 (449405600), GUI 0.1.5 배포 경로를 유지했다.

RC2에 들어 있던 seed 카탈로그·서명·GUI ZIP을 그대로 게시했다. 카탈로그 식별자는 `creative-group-launcher-rodetoast-1462539740`, 순번과 최소 순번은 9이며 Ed25519 키 ID는 `1efdfb848bb31e3fa5c07095f952c08d920be77253261fbf2742755341f018e0`이다. Draft와 공개 HTTPS에서 9개 자산의 크기와 SHA-256을 대조했다. Bootstrap ZIP은 기존 검증 런타임만 묶은 별도 자산이며 Setup, seed 및 서명 카탈로그의 패키지 항목을 포함하지 않는다. 그 ZIP의 파일들은 원본 런타임 manifest와 일치한다.

| 자산 | 바이트 | SHA-256 |
|---|---:|---|
| SouthpawToolsLauncher-Bootstrap-Rodetoast-0.1.6-Windows-x64.zip | 11,898,580 | `4ddd96d56c61e873208848bfaa642c6c1dc9632dceef9ff4d0c37081526f094b` |
| ase-viewer--0.5.8.4-team-3bf37dd.zip | 22,085,231 | `2532c273c4cf9930cf882ef1f84cae55c9a97479a69123431560b1299edec2d2` |
| catalog.json | 9,462 | `9877aae8e7b522902b55ebc2da633511ff566751f102c900d812bb80c00c56b3` |
| catalog.sig.json | 245 | `4233c23beef7238dbb008ac48bf80bf374f89bcfd1b69239ab6e215df0b78634` |
| creative-group-launcher--rodetoast-launcher-0.1.6.zip | 52,640,869 | `9cf77abbb2289043e1abe882f197f5063619063cc9fc2db7e7e1ddb673c1203d` |
| pivot-fixer--0.3.3-team-80b84c9.zip | 20,709,116 | `214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361` |
| ps2ase--0.3.6-team-6e84645.zip | 66,252,089 | `1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9` |
| tag-master--0.4.0-team-7263f8d.zip | 38,813,495 | `80865038ddab9a1b9050d04cbb48cb777edf4e6419caafb05b8b51c0f6962299` |
| tilenamer--0.1.6-rc3-8ba7a1e.zip | 54,046,715 | `aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4` |

0.1.6 Provider에서 고정 ID API로 실제 카탈로그9를 읽었다. seed9가 설정된 신뢰 상태에서 동일 순번·동일 바이트를 정상 수용했고 신뢰 상태 바이트를 유지했다. GUI ZIP을 Provider로 다운로드하고 공개 원격 자산을 격리 폴더에 초기화한 뒤 기존 WindowsUpdater에서 manifest·receipt를 검증했다. GUI EXE SHA-256은 `2e17bbe8b78e513975e003726ac8d7297955c65e59e6c6a7a3a6721464476bc5`이다. 빌드에 사용한 0.1.6 GUI 소스를 Qt offscreen에서 실행하여 실제 온라인 갱신과 앱 5개 표시 상태를 확인했다. 같은 0.1.6이므로 보류된 새 런처 업데이트는 없었다. Windows 패키지 EXE의 온라인 화면 시험은 수행하지 않았다.

사용자가 보고한 SPENT03의 RC2 설치·실행·바로가기·재실행·제거·합성 데이터 보존 성공과 sw204 보존, 임시 계정·프로필 정리 결과를 사용했다. 재시험이나 패키지 재빌드는 없었다. 신규 직원용 Setup 0.1.6.0은 기존 RC2 자산으로 공개 승인 대기 중이다. Setup SHA-256은 `405906b160b3314c225cc76cca41e610fdce40154937488a0a861b059da5bf07`이다.


## 신규 직원용 Rod Setup 0.1.6.0 정식 공개 (2026-11-19)

- [정식 Release](https://github.com/rodetoast/creative-group-releases/releases/tag/employee-setup-0.1.6.0)의 ID는 `450994875`, 설치 자산 ID는 `766655769`이다. [직원용 설치 EXE](https://github.com/rodetoast/creative-group-releases/releases/download/employee-setup-0.1.6.0/SouthpawToolsLauncherSetup-0.1.6.0.exe)는 81,300,016바이트이며 SHA-256은 `405906b160b3314c225cc76cca41e610fdce40154937488a0a861b059da5bf07`이다.
- SPENT03에서 검증한 RC2 EXE를 파일명만 바꿔 공개했다. Windows 버전 리소스의 FileVersion은 0.1.6.0, ProductVersion은 0.1.6이다. 확인한 버전 리소스와 설치 UI 설정에서 RC2 표시를 찾지 못했다.
- Draft 재다운로드 및 비인증 공개 HTTPS 재다운로드에서 동일 SHA-256을 확인했다. 공개 Release 페이지도 HTTP 200으로 확인했다. 기존 SPENT03 시험 결과를 재사용했다.
- Setup Release에 `--latest=false`를 지정했다. 비인증 Rod Latest API는 `rodetoast-catalog-000009` (450977319)를 반환했다. Rod 카탈로그9의 자산과 Toast 카탈로그8·Setup 0.1.4.1의 자산 ID, 크기, digest는 게시 전후 일치했다.
- 신규 직원은 Rod Setup으로 처음 설치한다. 기존 Toast 직원은 현재 경로를 계속 사용한다. 운영에서는 두 채널의 지원과 자산 관리를 분리한다. 증거 저장소 실제 이전과 Toast 지원 종료는 별도 결정 사항이다.
