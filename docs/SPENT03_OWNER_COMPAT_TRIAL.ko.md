# SPENT03 — 기존 시험 Bootstrap의 owner 호환 GUI 업데이트

2026-11-17. 개발 PC 준비물과 SPENT03 실기동 결과는 별개다. **현재 SPENT03 미실시.**

## 게시 대상 및 신뢰

- 시험 Release: https://github.com/toast-source/creative-group-trial-releases/releases/tag/trial-catalog-000011
- 시작 전 API로 draft=false/prerelease=false/Latest=trial-catalog-000011인지 확인한다. 아직 Draft라면 시작하지 않는다.
- 후보 GUI0.1.5 / `trial-launcher-s11-0.1.5`, catalog sequence11.
- 기존 시험 채널 `toast-source/creative-group-trial-releases`, 최소순번5, key_id `aab2e791668a8130f01435810432e6d144386fd66d9af69eb1b6b979d4d416a9` 그대로다.
- 운영 GUI0.1.4/Setup0.1.4.1/catalog7과 운영 키를 변경하지 않는다. 새 시험 키를 생성/신뢰하지 않는다.
- GUI ZIP: `creative-group-launcher--trial-launcher-s11-0.1.5.zip`, 52638834바이트,
  SHA256 `0de18d053875d5503d07bfb7182e6c69756f81c0791e97b94738165c839f7eb9`.
- 새 EXE SHA256 `7a4a9187bd16bb4ea469cb80bd09214d4fc4b46efd6e26ccf5a4aa4e6415986e`. Windows x64 GUI Subsystem2, 파일188개.
- catalog SHA256 `9efb8f934bd11768997c1fecefde982391fe7c28cb836da83eb47262393f6d38`, signature SHA256 `6da87d5d5eff2ab0f18c609d4ec5a2dd2175f9e99fd76d0031f24d5151d13fc8`.
- 소스 기준609cc73, 버전 반영 commit `945d8fc7997324e7f2d70bcdb1bc90b2cde9353c`. 후속 인계 문서 commit은 소스 버전을 바꾸지 않는다.

이 공개 Latest는 다른 시험 클라이언트에서도 조회 가능하다. 사용자가 아는 범위에서 다른 직원/PC에
시험 채널을 배포하지 않았다는 확인을 바탕으로 게시한다. SPENT03 전용 하드코딩/기기 인증을 추가하지 않았다.

## 1. 대상과 시작 상태 확인·보존

1. 현재 PC가 SPENT03인지 확인한다. 개발 PC에서 이 실행 시험을 대신 수행하지 않는다.
2. 기존 **시험 채널** Bootstrap/launcher-home/current/data 위치를 좁은 범위에서 확인한다.
   기존 BD13의 알려진 위치는 `C:/Dev/SPTest/BD13/Program`, Data는 같은 작업의 Data 폴더였지만 존재를 가정하지 않는다.
3. 안정 시험 Bootstrap EXE의 검증된 해시는 `7f4184fd8a4e58d6ff254c74780b230120e90eddb6f7b15441981c87d4400ed1`다. 원본 시험 runtime/채널 파일을 변경하지 않는다.
   운영 Bootstrap `c15f48…`의 production 정책에 시험키를 주입해 같은 시험이라고 만들지 않는다.
   다른 Bootstrap이면 검증된 원본/출처·해시를 먼저 확인하고 결과에 정확히 구분한다.
4. 시작 GUI는 실제0.1.4 / trial-launcher-s10-0.1.4,
   EXE SHA256 `02bbc0531491694e1dc267fe0ab6fb320a2d75d4ece872841fdec822ad6a0137`,
   원본 ZIP SHA256 `cf7d628c811e1ae537d9070c93d6ac55671c3d1fcd032f186a3b75a487124081`이어야 한다.
5. 시험 GUI/Bootstrap이 동작 중이면 정상 종료하고 해당 PID 종료를 확인한 뒤 보존한다.
   기존 runtime 파일, current/receipt/manifest/proof/trust, 설정·앱5개 설치 데이터와 합성 작업 파일의
   상대경로·해시를 기록하고 필요한 로컬 백업을 만든다. 원본 자료를 삭제하지 않는다.
   nonce/인증정보/설정 파일 본문은 공유 보고서에 출력하지 않는다.
6. 실제 런처 AppData 전후 상태도 확인하되 시험은 지정된 격리 data-dir만 사용한다.
   기존 외부 공용 작업 파일은 읽기 전용 비교만 하고 자동 변환/이동하지 않는다.

## 2. 기존 시험 실행 파일이 제거된 경우에만 baseline 준비

가능하면 기존0.1.4 시험 설치를 그대로 쓴다. 파일이 제거돼 새 격리 baseline이 필요한 경우 다음만 수행한다.
Setup 설치/제거, 0.1.3→0.1.4 시험, 회사 앱 내부 기능 시험을 반복하지 않는다.

- 기존 공개 `bootstrap-diagnostics-spent03-20261113` Release의
  `SouthpawToolsLauncher-Bootstrap-Diagnostics-SPENT03-20261113.zip`을 GitHub에서 직접 받는다.
  SHA256 `272155c35576cdeea6edf62dc9ed9de4d8e9346a9a8adfa68e125bcf5c2f3828` 검증.
- 새 짧은 격리 Program/Data/Evidence를 선택한다(예 `C:/Dev/OC11/P`, `D`, `E`). 존재하는 경로를 덮어쓰지 않는다.
  쓰기 거부/경로 오류이면 실제 증거를 남기고 ACL/보안 정책 변경이나 무조건 재시도로 우회하지 않는다.
- 검증된 옛 ZIP의 **runtime만 원본 바이트 그대로** 새 Program에 준비한다. 옛 seed0.1.3을 실행하지 않는다.
  새 복사본의 seed에는 기존 `trial-catalog-000010`의 catalog.json, catalog.sig.json 및 위0.1.4 GUI ZIP만
  GitHub에서 받아 그대로 둔다. 기존 원격S10이나 원본 ZIP은 변경/재서명하지 않는다.
- 재사용할 기존5개 앱 데이터가 있으면 **같은 시험 키의 proof인지** 확인해 새 Data 사본으로 보존한다.
  운영 키로 설치된 데이터의 proof를 시험 키로 바꾸지 않는다. 기존 layout을 새 경로로 무작정 복사하지 않는다.
  새 home은 old Bootstrap의 정상 signed-seed 초기화로 만든다. current/receipt/proof를 수동 위조하지 않는다.
- 준비 뒤 Bootstrap 해시/런타임 파일/옛 채널 정책 불변을 확인한다. baseline 재구성 여부를 보고서에 표시한다.
  검증 가능한 기존 시험 데이터가 없다면 앱5개 설치 상태 보존을 통과로 만들지 말고 해당 범위를 미검증으로 남긴다.

이 단계의 gh 다운로드/로컬 seed 준비는 **업데이트 성공 시험이 아니다**. 다음 단계는 반드시 실제 GUI를 사용한다.

## 3. 실제 업데이트 — GUI 조작

1. 기존 Bootstrap을 `--data-dir <격리 Data>`로 실행한다. CreativeGroupLauncher.exe를 단독 더블클릭하지 않는다.
2. 실제 Windows 화면에서 GUI0.1.4/current와 기존5개 앱 상태를 먼저 확보한다.
   자동 조회가 seq11을 수락해도 아직 current는0.1.4인 것을 구분한다.
3. GUI 업데이트 확인에서 실제 GitHub Latest11 및0.1.5 안내를 확인하고 **기존 업데이트 버튼**으로 승인한다.
   `gh release download`+로컬 Installer만으로 이 단계를 대체하지 않는다.
4. HTTPS 다운로드/검증, 기존GUI 종료20, 기존 Bootstrap worker/health·ready/confirmed,
   새GUI0.1.5 실행을 로그와 PID/EXE 해시로 확인한다.
5. current/receipt/manifest/모든 파일 해시와 보관된 원본 ZIP을 카탈로그11과 대조한다.
   안정 Bootstrap과 그 채널 파일은 그대로여야 한다. 기존0.1.4 payload/회사5개 앱·설정·합성 데이터도 비교한다.
6. 회사 앱5개 목록·설치 상태·프로그램 선택/정보/노트 등 런처 기본 화면을 확인한다.
   회사 프로그램 EXE 내부 기능 시험은 하지 않는다. 실제 GUI 캡처는 필요한 핵심 지점만 남긴다.
7. GUI 정상 종료0 및 잔여 대상 프로세스를 확인하고 **동일 Bootstrap**을 다시 실행해0.1.5 유지,
   정상 GUI/로그/current를 확인한 뒤 정상 종료한다. 자동 재시도/강제 kill·state 삭제를 하지 않는다.
8. journal/transaction phase, 사용자 데이터·설정·기존 앱 및 실제 AppData 보존 여부를 확인한다.
   예상한 cache/로그/신규 런처 버전 외 변경은 별도로 설명한다.

자연 실패가 생기면 기존 diagnostic operation/API/errno/winerror/traceback과 current/receipt/journal을 보존한다.
old current/데이터 및 기존 복구 정책 결과를 확인하고 중단한다. 실행 잠금·probe-owner 삭제, 무조건 retry,
서명 완화, 강제 pointer 전환·재설치를 하지 않는다. 의도적 시작 실패 주입을 하지 않았다면 그 항목은
기존 회귀 재사용/이번 실기동 미실시로 구분하며 성공했다고 쓰지 않는다.

## 4. 저장소 이전 이후에 대한 정확한 판정

- Bootstrap이 최신 버전을 직접 조회·다운로드하는 구조가 아니다. GUI가 준비한 뒤 Bootstrap이 종료 확인·적용·시작 검증을 한다.
- 호환 GUI0.1.5가 같은 옛 채널/키/trust를 유지하면 고정 ID API와 정확한 새 owner 자산 검증을 사용한다.
  옛 Bootstrap의 owner 문자열이 남았다는 이유만으로 네트워크 준비를 막는 경로는 현재 분석에서 확인되지 않았다.
  다만 이번 성공은 **저장소 이전 전** 조합 증거이고, 실제 이전 후 자산/CDN 정상 작동을 입증하지 않는다.
- 호환 GUI를 받지 않은0.1.4, 다운로드 실패로 남은0.1.4, 시작 실패 후0.1.4로 rollback된 PC는
  이전 후 기존 Provider의 redirect/owner 검사에 막힐 수 있다. Bootstrap 교체만으로 그 GUI 코드를 고치지 못한다.
- 현재 Setup은 바뀐 관리 파일을 덮어쓰지 않고 existing current를 새 seed로 강제 교체하지 않는다.
  검증되지 않은 “새 Setup 재설치로 해결”을 안내하지 않는다. 운영 데이터나 trust 초기화도 하지 않는다.
- Transfer는 이 작업에서 실행하지 않는다. 최종 보고에 YES/NO와 근거를 쓰되,
  SPENT03 업데이트 성공만으로 모든 구버전·실패/rollback 경로와 이전 후까지 보장했다고 판정하지 않는다.

## 5. 결과 기록 및 인계

원본 로그/백업은 SPENT03의 선택한 Evidence 폴더에 보존한다. Private 증거 도구를 쓸 경우 기존 guard·검토
절차를 지키며 공개 시험 Release에 원본 로그·설정·nonce·사용자 자료를 올리지 않는다.

다음만 보고한다: 실제호스트/시작Bootstrap SHA/시작0.1.4, seq10→11 확인,
실제 GUI0.1.4→0.1.5 적용/EXE hash, 종료·동일 Bootstrap 재실행,
current/receipt/journal·5앱/설정/합성 데이터/실제 AppData 보존,
실패/미검증 및 Transfer YES/NO, 다음 작업 한 가지.

개발 PC의 결과는 빌드/정적188파일 검사와 옛 source engine의 real ZIP 준비 검사뿐이다.
개발 PC에서 SPENT03 실기동을 대신 수행하지 않았다. 제품/Bootstrap/Setup/이전 증거와 운영 Release는 보존한다.


## 개발 PC 실제 완료 및 실행 경계 (2026-11-17)

- 실제 시험 Release 공개: https://github.com/toast-source/creative-group-trial-releases/releases/tag/trial-catalog-000011 (ID448334904), 시험 Latest11 확인. 운영 Latest7과 기존S10의 ID/본문/자산 ID·크기·digest 보존.
- 정확한8개 자산은 Draft에서 재다운로드해 해시·서명·188개 GUI 파일 manifest를 확인했다. 기존5개 회사 ZIP은 원본 그대로 첨부했고 새로 빌드/기능 시험하지 않았다.
- 기존0.1.4 Provider **소스**로 실제 공개 HTTPS ZIP 다운로드와 seq10→11·서명·크기·SHA256 검증 완료.
  실제 CDN은 HTTPS release-assets.githubusercontent.com, 응답302 경로를 확인했고 signed query는 기록하지 않았다.
- 호환 Provider의 rodetoast 설정도 기존 고정 ID를 통해 현재 Toast 소유의 순번11을 읽으며 trust 상태를 초기화하지 않았다. 실제 배포 저장소는 이전하지 않았다.
- 기존0.1.4 Bootstrap **소스 엔진**으로 실제 서명·ZIP을 prepared까지 준비하고 기존 current0.1.4/합성 데이터를 보존했다. frozen EXE 실행·전환 성공으로 표현하지 않는다.
- 신규 GUI x64/Subsystem2/PE0.1.5/PYZ 모듈·DLL·정확한188파일·ZIP 구조 검사 완료. Bootstrap/Setup은 새로 빌드하지 않았다.
- 실제 오류1건: Draft 생성 후 게시용 REST tag 조회가404였다. 실제 초안 ID448334904/자산0을 읽어 확인한 뒤 동일 초안으로 이어갔다. 중복 생성/기존 자산 덮어쓰기/무조건 재시도는 하지 않았다. 제품 오류나 WinError5가 아니다.
- 실제 실행 호스트는 DESKTOP-1MK6D95. 연결된 Codex 프로젝트/최근 태스크 호스트는 local뿐이며 SPENT03 원격 실행/RDP 연결이 확인되지 않았다. 실제 SPENT03 GUI 업데이트/재실행/데이터 보존은 **미실시**.

**시험 저장소 Transfer 시작: NO.** 이 문서의 실제 SPENT03 단계를 먼저 실행하고 결과를 보존해야 한다.
다음 실제 작업 한 가지는 SPENT03의 Codex에서 이 인계서를 읽고, 기존 시험 Bootstrap+GUI0.1.4→0.1.5의 실제 GUI 업데이트를 수행하는 것이다.
운영 Bootstrap/키를 시험용으로 변조하지 않고, 다른 Bootstrap 변형을 썼다면 해시와 결과를 구분한다.

Bootstrap 교체가 필요하다는 실제 증거가 나오면 현재 Setup guard를 우회하지 않는다. 정상 종료·소유권/기존 manifest 확인·안정 파일 백업·검증된 새 안정 파일만 교체·시작 확인·실패 보존을 포함하는 별도 전환 설계가 후보일 뿐,
현재 구현·SPENT03 검증·운영 승인된 자동 교체 절차는 아니다. home/data/trust 초기화로 해결하지 않는다.


소스 보존 대조에서 Git blob(LF)과 기존 Windows git archive 출력(CRLF)의 raw hash 차이를 확인했다. 29개 모듈 모두 실제 build-source hash 일치, LF 정규화 내용 일치 및 같은 파일명으로 compile한 code object 바이트 일치를 확인했다. git config는 바꾸지 않았고 배포 ZIP/서명/버전도 다시 만들지 않았다. 정확한 raw export hash와 Git blob 내용 해시는 로컬 provenance 기록에 구분해 보존했다.


## 시험 저장소 실제 이전 완료 및 SPENT03 이전 후 확인 (2026-11-17)

사용자가 SPENT03의 기존 Bootstrap+GUI0.1.4→0.1.5 업데이트·정상종료·재실행·데이터 보존 성공을 보고하고 시험 저장소만 이전 승인했다. 이 결과는 사용자 보고이며 개발 PC가 Windows 시험을 대신 실행한 결과가 아니다.

공식 Transfer 수락 후 저장소는 https://github.com/rodetoast/creative-group-trial-releases 이며 ID1452413703·Public을 유지한다. 이전 전후 Release15개·태그15개·branch/tag commit·모든 Release/asset ID·이름·크기·digest·draft/prerelease 상태가 일치한다. Latest는 trial-catalog-000011, sequence11이다. 최신8개 자산을 새 owner에서 실제 CDN HTTPS 재다운로드했고 전부 SHA256 일치, 기존 Ed25519 signature/key_id aab2e791668a8130f01435810432e6d144386fd66d9af69eb1b6b979d4d416a9 유효. signed bytes와 자산은 수정하지 않았다.

기존 웹 URL은 새 owner로301, 기존 REST repo URL은 repositories/1452413703으로301 후200. 기존 catalog 자산 URL도 새 owner/CDN을 거쳐 동일 바이트를 반환한다. 리디렉션 존재는 구0.1.4 제품의 처리 성공을 뜻하지 않는다. 호환 소스 Provider는 기존 toast-source 설정과 새 rodetoast 설정 양쪽에서 seq11·서명을 검증했고, 기존 owner 설정으로 실제 새 owner의 GUI ZIP을 내려받아 SHA256을 검증했다. 이는 소스 transport 검증이며 SPENT03 Windows GUI/Bootstrap 이전 후 실기동은 아직 미검증이다.

기존 보존 mirror의 origin만 rodetoast 주소로 갱신하고 ls-remote branch를 확인했다. 과거 backup/inventory는 역사 기록으로 보존한다. admin_github.py 및 publish_company_release.py의 기존 guard는 여전히 이전하지 않은 운영 저장소를 보호하므로 변경하지 않았다. 증거 guard도 유지한다. 신규 owner에서 별도의 trial 게시 자동화를 사용할 때는 정확한 trial ID/rodetoast 계정/권한을 제한해 검증해야 하며 기존 운영 guard를 전역 해제하지 않는다.

운영 toast-source/creative-group-releases의 Latest production-catalog-000007 유지 확인. Setup0.1.4.1·운영/증거 저장소·서명/순번·Bootstrap·사용자 데이터는 변경하지 않았다. 게시·빌드·전체회귀·제품 실행 없음. 근거는 개발 PC 원본 프로젝트 .test-results/trial-repository-transfer-20261117/에 있다.

### SPENT03 Codex에 전달할 프롬프트

> 시험 저장소의 공식 Transfer가 완료됐다. 새 주소는 https://github.com/rodetoast/creative-group-trial-releases 이며 ID1452413703, Latest trial-catalog-000011/sequence11, GUI0.1.5다. 기존 C:/Dev/OC11/E/REPORT.ko.md와 시험 환경을 재사용하라. 기존 current.json·신뢰 상태·설정·회사5개 설치/합성자료·구 Bootstrap 해시를 먼저 읽기 전용 기준으로 보존하고, Bootstrap을 교체하거나 신뢰/순번을 초기화하지 마라. 기존 owner 설정을 먼저 유지한 채 구 Bootstrap으로 GUI0.1.5를 실제 실행하고 정상 새로고침으로 새 owner Release를 확인하라. 캐시 조회인지 실제 네트워크 조회인지 로그/응답으로 구분하라. 새 owner 자산 HTTPS 다운로드·SHA256·기존 Ed25519를 별도 격리 파일로 검증하되, 단순 HTTP/gh 다운로드를 GUI 관리형 업데이트 성공으로 표시하지 마라. GUI의 카탈로그 확인과 다운로드 동작은 각각 실제 결과와 근거를 기록하라. 필요하면 기존 정책으로 고정된 새 owner의 읽기 전용 Provider 검증을 별도로 수행하되 실제 GUI 결과와 구분하고 기존 설정을 임의로 덮어쓰지 마라. GUI 정상 종료 후 동일 구 Bootstrap을 재실행하고 실제 EXE/version/hash/current·신뢰상태·사용자자료 보존 및 owner/redirect 오류 유무를 확인하라. 같은 v0.1.5/sequence11이므로 새 버전의 실제 관리형 업데이트 적용은 이번에 검증할 수 없다고 명시하라. 이전에 설치한0.1.5의 재다운로드·강제 재설치·순번 초기화로 업데이트 성공을 만들지 마라. 미업데이트GUI0.1.4는 별도 미검증이며 알려진 redirect 비호환 가능성이 있다. 실패하면 원래 로그와 상태를 보존하고 연속 재시도·강제복구하지 마라. CLI를 우선하고 실제GUI 핵심 조작에만 Windows Use를 사용하며 끝나면 즉시 제어를 해제하라. 회사 앱 EXE 기능시험·제품빌드·새Release·운영변경은 하지 마라. 통과/실패/미검증과 실제GUI·단순HTTP·Provider 검증을 구분하여 기존 보고서에 결과를 남겨라.

이전 후 구 Bootstrap의 실제Windows 성공은 SPENT03 결과를 받기 전까지 미확정이다. 미전환/실패·rollback으로0.1.4에 남은 클라이언트는 자동전환 보장 대상이 아니다. 운영/증거 저장소 Transfer 승인이 아니며 현재 운영 이전 차단은 유지한다.


## 최신 단일 인계 — RC1 독립 Windows 환경 (2026-11-18)

목표는동일Setup RC1의실제설치→GUI0.1.5/바로가기→종료·재실행→제거·합성자료보존이다. 운영0.1.4→0.1.5 업데이트와기존바로가기재실행은이미통과했으므로반복하지않는다. 직원별업데이트확인도요청하지않는다. 기존sw204의등록/바로가기/프로그램/자료는보존한다.

1. 기존보고서와현재환경을읽고이미사용가능한Windows Sandbox,기존격리테스트VM,원래준비된충돌없는독립환경을확인한다. 기능활성화/새계정·VM생성/VM초기화·복원/권한상승/기존설치제거는하지않는다. 기존VM에다른업무자료가있으면사용하지않는다. 없으면그사실과최소필요승인만보고하고중단한다. sw204의등록값토글/옛환경비우기로진행하지않는다.
2. Draft tag `employee-setup-0150-rc1-transport-20261118`, ID449518343, 저장소rodetoast/creative-group-trial-releases, URL https://github.com/rodetoast/creative-group-trial-releases/releases/tag/untagged-2e356c394839407bb519. 기존공식gh인증을확인한다. 필요하면공식 `gh auth login --hostname github.com --web --git-protocol https`로사용자가직접로그인/2FA한다. 기존토큰/비밀번호추출·공유·로그저장/인증설정프로젝트복사는금지다. 기존인증삭제나Draft공개전환도하지않는다. 로그인후에도권한없으면정확히보고한다.
3. 인증된호스트Codex가 `gh release download employee-setup-0150-rc1-transport-20261118 --repo rodetoast/creative-group-trial-releases --dir <새다운로드폴더> --pattern SouthpawToolsLauncherSetup-0.1.5.0-RC1.exe --pattern SouthpawToolsLauncherSetup-0.1.5.0-RC1.exe.sha256`로직접받는다. size83404359,SHA256 `8d8c5940e0f08adfcf9d073fe3c29971f96de3fb06396f41f11fa5b817f56453`를대조한다. 사람이USB/파일복사/PowerShell실행을대신하도록요구하지않는다.
4. 기존Sandbox를사용하면호스트가검증한RC1폴더만read-only매핑,이번새증거출력폴더만별도writable매핑한다. 프로필/AppData/프로젝트/gh인증설정을게스트에공유하지않는다. 게스트는gh토큰이필요없다. 기존VM이면승인된기존전달방법으로검증파일만전달한다. Windows네트워크/방화벽/SAC/ACL/PATH정책은바꾸지않는다. Sandbox종료전이번합성자료·보존될launcher-home·로그를전용출력폴더로보존한다.
5. 독립환경에서도정상제품HKCU `Software\SouthpawGames\ToolsLauncherSetup`, `Software\Microsoft\Windows\CurrentVersion\Uninstall\SouthpawToolsLauncher` 및시작메뉴/바탕화면바로가기충돌이없음을확인한다. 새짧은P/D/E루트를쓰고 P와D를분리한다. 동일RC1에 `/DATA=<D>`와맨마지막 `/D=<P>`로일반권한Setup GUI설치를한다. 보안정책차단이면우회하지않고코드/화면을보존한다.
6. 설치완료→실제GUI최초0.1.5→운영카탈로그8/회사5개목록조회→정상종료→바탕화면/시작메뉴바로가기각각실제클릭재기동→정상종료. 실제EXE SHA `7a4a9187bd16bb4ea469cb80bd09214d4fc4b46efd6e26ccf5a4aa4e6415986e`, Bootstrap SHA `c15f48a0d72dd0a8bdc1ad909a75ae3327a91a2f136170dc4c3713651df6cb19`, seed서명/seq8/current/receipt/manifest를확인한다. 회사EXE/개별기능·전체회귀·설치목록추가조사는하지않는다. GUI조작과파일/로그를대조한다.
7. D에합성설정/작업파일과기준해시를만들고 GUI/Bootstrap정상종료후이번P의Uninstall.exe를실제로실행한다. 이번관리파일/바로가기/등록제거와D/launcher-home/current/receipt/합성파일보존을확인한다. 호스트sw204기존등록/파일불변도비교한다. 회사데이터가없는환경에서회사전체데이터보존을주장하지않고,게스트폐기만으로제거성공을대신하지않는다.
8. E/REPORT.ko.md에호스트/게스트독립성·다운로드해시·Setup종료코드·GUI/바로가기/프로세스·제거·보존을통과/실패/미검증으로기록한다. nonce/명령행전체/민감한자료는공유하지않는다. 실패시원로그/중간상태를보존하고연속재시도/강제복구/신뢰초기화를하지않는다. 최소GUI에만Windows Use를쓰고끝나면즉시제어를해제한다. 환경확보가안돼도과거합격시험을반복하지않는다. 결과를개발PC에돌려주면승인범위내수정/검증을이어서진행한다. 새Setup공개/Transfer/직원PC변경은하지않는다.


## 최신 단일 인계 — 신규 Rod 채널 Setup0.1.6.0 RC2 (2026-11-18)

운영Toast0.1.4→0.1.5 업데이트/재실행성공은완료이며반복하지않는다. 예전Setup0.1.5.0 RC1은구채널용이다. 이번대상은 **SouthpawToolsLauncherSetup-Rodetoast-0.1.6.0-RC2.exe**,SHA256 `405906b160b3314c225cc76cca41e610fdce40154937488a0a861b059da5bf07`. 아직원격운송/정식공개되지않았으므로예전Draft의1.5파일로대체하지말고운송승인후정확한URL/tag를추가받아GitHub에서직접다운로드한다. 수동파일복사/다른빌드/키주입/신뢰초기화금지.

- source branch codex/rodetoast-channel-20261118,GUI0.1.6,신규Bootstrap0.1.6,Setup0.1.6.0,repoID1462539740,전용catalog_id `creative-group-launcher-rodetoast-1462539740`,최소/seed9. Bootstrap SHA `152a02ce9f36f65df534da711a626474a9cc2116a5736adbfc601b33898a0a09`,GUI EXE SHA `2e17bbe8b78e513975e003726ac8d7297955c65e59e6c6a7a3a6721464476bc5`. 앞서만든미공개1.6 RC1이나기존테스트신뢰루트를재사용하지말고새P/D/E를선택한다.
- sw204기존설치/등록/바로가기/프로젝트/설정은변경하지않는다. 이미사용가능한Windows Sandbox/독립테스트VM/충돌없는기존시험사용자만확인한다. 없으면중단하고필요한최소환경승인을보고하며새계정/VM/기능활성화/정책변경/권한상승/기존제거를하지않는다. Sandbox라면검증된Setup폴더read-only와이번전용출력E폴더만매핑하고인증/실제AppData는공유하지않는다. 공개시험운송이면게스트에gh인증이필요없다. Draft운송을선택한경우에만공식브라우저인증을사용자에게요청하고토큰/비밀번호를추출하거나옮기지않는다.
- 독립환경에도정상제품HKCU/바로가기충돌이없음을확인한다. /DATA=<새D>와맨마지막/D=<새P>로일반권한Setup을실제설치한다. 기본경로는CGL-Rodetoast/ToolsLauncherRodetoast다. 초기GUI1.6,이름/아이콘/콘솔없음,바탕화면/시작메뉴바로가기실제클릭,정상종료·동일Bootstrap재기동·잔여프로세스를확인한다. 실제파일/ZIP/manifest/current/receipt/전용namespace9의서명을확인한다. 회사EXE기능/전체회귀/과거업데이트시험은하지않는다.
- 현재Rod Latest8은역사적구namespace복제이므로새클라이언트가이를서명namespace/min9에서거부하는것이맞다. seed9로GUI가시작돼도**온라인9는정식게시전미검증**이다. 이차이를원로그와함께기록하고복제8을채택시키거나cache/서명/순번을우회하지않는다. 온라인9게시승인후같은후보를정상새로고침하여새ID/전용namespace9조회·자산HTTPS검증을확인한다. 초기현재1.6=목표1.6이므로이를신규버전업데이트성공으로부르지않는다.
- D의합성설정/작업파일해시를확보하고정상종료후이번P의Uninstall.exe를실제실행한다. 이번등록/바로가기/소유파일제거,launcher-home/current/receipt와D합성자료보존,호스트기존sw204자료불변을확인한다. 게스트폐기를제거시험성공으로대신하지말고종료전시험자료/로그를E에보존한다.
- E/REPORT.ko.md에설치/GUI/바로가기/재기동/제거/자료보존/온라인9를각각통과·실패·미검증으로정리한다. CLI우선,필요GUI만Windows Use를쓰고끝나면즉시해제한다. 오류/Win5/timeout이면원로그·중간상태를보존하고연속재시도·강제복구·신뢰초기화를하지않는다. 로그에토큰/nonce/명령행전체/사용자자료본문을불필요하게넣지않는다. 실제직원PC/운영Toast/원격Release/Transfer를건드리지않는다.
