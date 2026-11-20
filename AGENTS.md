## 지속적인 개발·기획 기록 (2026-11-17)

프로젝트: **Southpaw 도구 런처** — 사내 제작 도구 설치·실행·업데이트.

새 세션은 이 지침과 아래 문서를 읽고 `git status`, branch/HEAD/remote를 확인한다. 문서에 근거 날짜·커밋·실제 배포 버전을 구분하고, 충돌하는 과거 기록을 현재 상태로 간주하지 않는다.

### 기록 위치

- [README.md](README.md): 기존 개요; 오래된 개발 단계 설명은 아래 현행 기준과 구분.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): 기존 구조.
- [docs/BOOTSTRAP_FAILURE_DIAGNOSTICS.md](docs/BOOTSTRAP_FAILURE_DIAGNOSTICS.md): Bootstrap 진단.
- [docs/BOOTSTRAP_SUPPORT_AND_LIMITED_PILOT.ko.md](docs/BOOTSTRAP_SUPPORT_AND_LIMITED_PILOT.ko.md): 장애 대응·데이터 보존.
- [docs/WINDOWS_SETUP.md](docs/WINDOWS_SETUP.md): Setup 구조.
- [docs/pilot/PILOT_RELEASE_DECISION.ko.md](docs/pilot/PILOT_RELEASE_DECISION.ko.md): 과거 BD13 판단 기록; 현재 정식 직원 배포 지시가 아님.

### 작업과 Git 기록 규칙

- 중요한 기획·설계 결정은 실제 전달받은 내용, 이유·대안/영향과 함께 위 개발 기록에 남긴다. 접근하지 못한 대화의 내용을 만들지 않는다.
- 의미 있는 작업 완료 시 관련 코드와 문서를 함께 커밋한다. 테스트 명령·결과·환경·미검증 범위, 완료/미완료와 다음 작업을 구분한다. 대화 메시지마다 커밋하지 않는다.
- Release 후 위 현행 상태 문서와 기존 CHANGELOG/릴리스 기록에 버전·태그/URL·검증 결과를 갱신한다. CHANGELOG가 없으면 지정한 개발 기록에 누적하고 같은 내용을 여러 문서에 복제하지 않는다.
- 안전하고 승인된 개발 브랜치에서 공개 범위·계정·remote·충돌·민감정보를 확인하고 정상 push한다. 거절/불일치가 나면 강제 push·reset·clean·기존 변경 덮어쓰기로 해결하지 않는다.
- 기존 미커밋 작업을 한꺼번에 포함하지 말고 관련 파일/hunk를 명시한다. 분리가 어려우면 원본을 보존한 격리 체크포인트를 사용하고 제외/미반영 범위를 기록한다.
- 개인키·토큰·개인/직원 자료·실행 데이터·무분별한 빌드 산출물을 소스 커밋에 넣지 않는다. 로컬 커밋, 원격 push, 검증 통과, 정식 Release 공개는 각각 별도 상태다.
- 소스 push는 제품 운영 Release·카탈로그·Latest 변경 승인이 아니다. 계정 이전 호환성이 확인되기 전 toast-source 고정 주소·신뢰키·guard를 바꾸거나 배포 저장소를 Transfer하지 않는다.

### 현재 배포 기준 (2026-11-17 확인)

운영 GUI0.1.4 / 직원 Setup0.1.4.1 / production-catalog-000007(sequence7), 기존 운영 저장소는 toast-source/creative-group-releases다. BD13은 진단 시험 이력이며 일반 직원용 배포본이 아니다. README의 v0.1.0 및 과거 미실행 문구는 개발 당시 기록이다. 운영 공개 완료와 로컬 개발 변경의 Git 원격 보존 완료를 혼동하지 않는다. B14 Bootstrap WinError5 및 간헐적인 catalog 교체 WinError5 근본 원인은 미확정이다.


## 소스 저장소 이전 및 개발 재개 (2026-11-17)

- 실제 소스 저장소: https://github.com/rodetoast/creative-group-launcher (ID1443813273, Public 유지). 이전 주소: https://github.com/toast-source/creative-group-launcher. 소유권 변경 확인 후 기록한 주소다.
- 개발 PC의 원본 작업 경로: `C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기`. 원본은 `master`/`32afb846d0bc69b38203a259dad71180cd4a14b5`와 기존 미커밋 작업을 보존했다. 원격 보존을 위해 원본을 checkout/reset/강제 병합하지 않는다.
- 보존 개발 브랜치: `codex/migration-checkpoint-20261117`. 소스·기획 기록 보존 기준 commit은 `b8253013df74c4916d076bde9ce54239ae49c4c3`; 이후 변경은 주소·진입 문서 정리다. 현재 실제 commit은 `git log -1` 및 원격 branch ref로 확인한다. 최초 비어 있던 원격 main에도 같은 검토 소스를 올리며, 향후 main 변경은 별도로 검토한다.
- 새 세션: 이 AGENTS → 아래 현행 배포 기준/연결 문서 → `git status`/현재 branch/remote/최근 log 순으로 확인한다. 개발 브랜치는 원본 master와 다르므로 원본 미커밋 작업을 버리고 무조건 branch 전환하지 않는다.
- 새 소스 push 대상은 위 rodetoast 저장소의 검토된 개발 브랜치다. 로컬 소스 보존 commit은 정식 배포 승인 소스나 이번 회귀 검증 완료를 의미하지 않는다. 이번 이전에서 빌드·기능 테스트·직원 설치를 실행하지 않았다.
- `.test-results`, 기존 서명 제품/Setup/회사 ZIP·개인키·실행 데이터·사용자 설정은 소스 push 대상이 아니다. 별도 보존 결과와 실제 운영 Release를 참조하고, 개발용 빈 신뢰키를 운영 신뢰 정책으로 오인하지 않는다. 이 소스만으로 기존 서명 제품 바이트를 재현했다고 주장하지 않는다.
- 운영/시험 배포 저장소와 증거 저장소는 이전하지 않았다. 직원용 GUI0.1.4/Setup0.1.4.1/catalog7, 회사 app_id, 서명과 신뢰 상태, Bootstrap/Installer 동작은 변경하지 않는다. `toast-source`의 다운로드/업데이트 주소·NoRedirect·owner allowlist·evidence guard를 일괄 치환하지 않는다.
- 기존 README의 초기 단계 설명은 개발 이력이다. 현재 상태는 이 AGENTS 및 실제 서명 Release/검증 기록을 기준으로 구분한다. 과거 기획/설계 이유와 미해결 문제는 삭제하지 않는다.


## 현재 owner 호환성 작업 (2026-11-17)

작업 브랜치: `codex/github-owner-compat-20261117`, 격리 작업 경로 `C:/Dev/CGL-OwnerCompat-20261117`.
[GITHUB_OWNER_COMPATIBILITY](docs/GITHUB_OWNER_COMPATIBILITY.ko.md)에 실제 변경·검증·GUI/Bootstrap/Setup 경계와 Transfer 차단 조건을 기록했다.
기존 보존 브랜치/main을 바꾸거나 원본 master의 dirty 코드를 교체하지 않는다. 소스 commit/push와 제품 빌드·운영 공개는 구분한다.
신규15 + 관련 기존127 =142 통과(실패/오류/skip0), 공개 카탈로그 old/new 설정4종 실제 HTTPS 읽기 성공. 전체 회귀·SPENT03 제품 EXE 실기동·Setup 교체는 미실시다.
기존 Setup은 다른 Bootstrap 덮어쓰기와 기존 current의 새 seed 강제 전환을 지원하지 않으므로 재설치만으로 이전된다고 안내하지 않는다.
운영/시험/증거 저장소는 아직 이전하지 않으며 증거·관리자 쓰기 guard도 그대로다. GUI 후속 후보를 먼저 기존 채널에서 검증·배포하고 미전환/rollback 설치본과 설치 전환을 해결하기 전 원격 Transfer를 실행하지 않는다.


## 0.1.5 시험 빌드·S11 현황 (2026-11-17)

제품 소스 __version__0.1.5는 owner 호환성 시험용 후속 버전이다. 실제 운영은 여전히 GUI0.1.4/Setup0.1.4.1/catalog7이다.
[SPENT03 인계](docs/SPENT03_OWNER_COMPAT_TRIAL.ko.md)를 읽고 현재 실제/미실시 범위를 구분한다. trial-catalog-000011만 공개했고 Bootstrap/Setup/회사 앱5개 원본은 변경하지 않았다.
GUI ZIP SHA256 0de18d053875d5503d07bfb7182e6c69756f81c0791e97b94738165c839f7eb9, EXE SHA256 7a4a9187bd16bb4ea469cb80bd09214d4fc4b46efd6e26ccf5a4aa4e6415986e.
기존 Provider 실제 HTTPS와 옛 source engine의 prepared는 검증했으나 SPENT03 frozen Bootstrap→새 GUI 실제 적용·재실행은 아직 수행하지 못했다. Transfer NO. 여기서 실제 결과를 만들어 내거나 전체 회귀/제품 재빌드/운영 게시를 반복하지 않는다.


## 시험 저장소 Transfer 후속 (2026-11-17)

사용자 보고로 SPENT03 사전 GUI0.1.4→0.1.5 시험은 통과했고 별도 승인/수락 후 시험 저장소만 rodetoast로 실제 이전됐다. ID1452413703·Public·Release15/태그15·Latest11·모든 자산ID/digest 보존 및 최신8자산 실제재다운로드 SHA/서명 확인. 호환 source Provider의 old/new owner 조회·실제ZIP 다운로드도 통과했다. [이전 후 SPENT03 인계](docs/SPENT03_OWNER_COMPAT_TRIAL.ko.md)의 최신 절을 읽는다. 이전 후 Windows 구Bootstrap/GUI실기동은 아직 SPENT03에서 확인해야 하며 같은seq11로 신규 managed update 적용 성공을 주장하지 않는다. 운영/증거 저장소는 이전하지 않았고 운영7/Setup0.1.4.1·기존 guard는 그대로다. 과거 Transfer NO 문구는 당시 상태이며 시험 저장소 실제 이전 사실은 이 절이 최신이다.


## 운영 전환 후보 (2026-11-18)

공식Setup 설치직원이 있다고 사용자확인. 제품코드변경 없이 운영GUI0.1.5/production-catalog-000008 로컬서명후보를 준비했다. [기존호환문서](docs/GITHUB_OWNER_COMPATIBILITY.ko.md)의 최신 운영전환 절을 읽는다. 원격게시/운영Transfer/Bootstrap·Setup교체는 아직 실행하지 않았다. 구Bootstrap 자체는 네트워크검색주체가 아니며 기존GUI의선행업데이트가필요하다. 직원미전환/rollback0.1.4는이전전처리하고 신규설치용호환Setup/링크도필요하다. SPENT03 이전후조회/재실행통과는사용자보고, 별도ZIP60초timeout은미완료. 시험8자산 개발PC검증과구분한다.


## 운영 호환 Release8 공개 완료 (2026-11-18)

사용자 승인으로 toast-source/creative-group-releases의 production-catalog-000008을 실제공개/Latest8로지정했다. GUI0.1.5 운영후보8자산을Draft/공개HTTPS재다운로드 SHA·운영서명·manifest 검증. catalog7/Setup0.1.4.1/Bootstrap/회사5개원본은유지. 운영Transfer/새Setup게시없음. [기존호환문서](docs/GITHUB_OWNER_COMPATIBILITY.ko.md)의최신게시결과와SPENT03운영대표검증프롬프트를읽는다. 현재SPENT03실제운영GUI업데이트와직원전환은미검증이므로완료로주장하지말고전체직원안내/Transfer를보류한다. 이전의운영Latest7 문구는당시이력이다.


## 단계별 자율 진행 (2026-11-18)

- 명시적으로 승인된 목표·안전 조건 안에서는 조사→최소 구현→관련 검증/오류 수정→후보 빌드→무결성 확인→기록→안전한 개발 브랜치 commit/push→다음 인계를 연속 수행한다. 작은 단계가 끝났다는 이유로 승인을 반복 요청하지 않는다.
- 기존 결과는 코드·조건이 같으면 재사용하고 변경 관련 검증을 우선한다. 동일 조건의 무의미한 재시도·관성적인 전체 회귀·중복 보고서를 피한다. 실제 GUI는 필요한 PC에서만 확인한다.
- 승인 범위 밖의 운영 공개, Repository Transfer/삭제, 실제 직원 PC 변경, 데이터 삭제·초기화, 중대한 키/신뢰·보안 정책 변경, 기존 업데이트 연결 단절 위험 또는 사용자 제품 결정이 필요하면 그 지점에서 멈추고 구체적으로 보고한다. 소스 push는 제품 공개 승인이 아니다.
- 다른 PC의 자동 공유/원격 제어를 가정하지 않는다. 정확한 출발 상태·GitHub 자산·실행할 시험·판정 기준·자료 보호·로그 위치를 인계하고 실제 수행/미검증을 구분한다. 승인 범위 내 실패 수정/재검증은 결과를 받은 뒤 계속한다.
- 의미 있는 목표 단위로 목적·결정 이유·변경·검증/미검증·실제 배포 버전·미해결·다음 작업과 진입 문서를 기존 기록에 남긴다. 원본 dirty 작업/다른 프로젝트 변경을 섞거나 main을 강제로 덮어쓰지 않는다.


## 신규직원Setup0.1.5.0 후보 (2026-11-18)

운영GUI0.1.5/카탈로그8 seed의Setup0.1.5.0 RC1과초기ZIP을로컬준비/파일검증했다. 기존Bootstrap c15f48a0…는동일바이트재사용. 새Setup공개/설치/운영Transfer없음. 기존호환문서의최신절에파일해시/검증/초기Win623증거/프로젝트별정책commit/미검증범위를기록했다. SPENT03은기존0.1.4에서운영카탈로그8 업데이트를먼저검증하며새Setup으로출발상태를바꾸지않는다. 새Setup Windows설치시험은별도원격운송승인후진행한다.


## 운영 업데이트 대표검증 완료·RC1 Draft 인계 (2026-11-18)

SPENT03 공식운영Bootstrap/키/카탈로그8의GUI0.1.4→0.1.5 실제업데이트·검증·committed·정상종료/재실행·합성자료보존을사용자가통과보고했다. 완료로재사용하고반복하지않는다. Setup0.1.5.0 RC1은시험저장소의운송전용Draft ID449518343에EXE/sha두자산을그대로업로드/인증재다운로드검증했다. 공개Release/Latest변경없음. [기존호환문서](docs/GITHUB_OWNER_COMPATIBILITY.ko.md) 최신절에권한있는Codex용다운로드·충돌차단/실제설치/바로가기/제거/자료보존·직원문구/확인절차를정리했다. RC1Windows실기동은SPENT03대기,직원별업데이트완료는미확인이다. 기존정상등록/바로가기있으면Setup시험을강행하지않는다. 새Setup정식공개·직원직접변경·운영/증거Transfer는별도승인경계다.


## 직원별 확인 생략·기존 채널 병행 (2026-11-18)

사용자가직원별업데이트확인을생략하되구0.1.4접속유지를요구했다. B안(신규Rod기준운영repo준비+Toast전체호환채널기한없이유지)을선택했다. 원본운영Transfer/삭제/이름변경금지,기존0.1.4/0.1.5가옛repoID를계속쓴다는사실을유지한다. 신규repoID라우팅은미구현이며새repo생성/게시도하지않았다. 완전복제계획도구12합성시험/로컬서명8계획과증거guard58고유시험·Private개발브랜치보존을완료했다. [기존호환문서](docs/GITHUB_OWNER_COMPATIBILITY.ko.md) 최신절과 [SPENT03 통합인계](docs/SPENT03_OWNER_COMPAT_TRIAL.ko.md) 최신독립환경절을읽는다. sw204등록/바로가기충돌·Draft인증부재로RC1은미실시이며독립환경/공식웹로그인으로만시험한다. 직원별완료확인/메시지/접근은요청·실행하지않는다. 운영업데이트합격은재사용한다.


## 신규Rod 운영자산 복제본 (2026-11-18)

사용자승인으로 rodetoast/creative-group-releases Public(ID1462539740)과production-catalog-000008 복제Release(ID449720497)를생성했다. 정확한8자산을Draft/공개HTTPS재다운로드 SHA·운영서명/seq8로검증했다. Toast원본8Release/38자산·tag/commit·Latest8·Setup0.1.4.1은유지. 신규repo LatestAPI도8을반환하지만현재GUI0.1.5/Bootstrap은여전히Toast ID1447701732를사용한다. 실제독립신규채널/전사전환/과거전체이력이전완료가아니다. [기존호환문서](docs/GITHUB_OWNER_COMPATIBILITY.ko.md) 최신복제결과를읽는다. 구지원클라이언트보호를위해Toast전체채널을계속유지하며원본/증거Transfer·새Setup공개는하지않았다.


## 신규직원 Rod 채널 구현 기준 (2026-11-18)

별도브랜치 codex/rodetoast-channel-20261118에서GUI0.1.6 신규후보를준비한다. 기존0.1.5/Bootstrap/Setup/Toast채널은변경하지않는다. 새채널은명시적 repository_id1462539740 + rodetoast/creative-group-releases + 전용서명catalog_id creative-group-launcher-rodetoast-1462539740 + 최소seq9를함께요구한다. 기존Ed25519키/서명domain/schema/ZIP SHA/고수위/rollback보호는유지하며namespace가서로다르면같은키의유효서명도거부한다. 기존catalog8복제는새채널로채택하지않는다.

초기GUI0.1.6·새고정채널Bootstrap·Setup0.1.6.0 로컬후보를만든다. 신규기본루트는프로그램 %USERPROFILE%/CGL-Rodetoast, 데이터 %LOCALAPPDATA%/SouthpawGames/ToolsLauncherRodetoast이며기존ToolsLauncher와분리한다. 일반직원제품명/app_id/AppUserModelID/바로가기/등록키는유지해기존설치와겹치면자동전환/덮어쓰지않고차단한다. 초기Setup은기존채널홈/신뢰자료/비어있지않은미소유데이터를자동흡수하지않는다. 구Setup0.1.5.0 RC1은Toastseed용이력으로보존한다.

신규GUI·Bootstrap은서로같은새채널정책을탑재해야하므로기존ToastBootstrap을새Setup에그대로재사용하지않는다. 기존직원Bootstrap교체를시도하는것이아니다. GUI/새Setup의실제Windows시험은독립환경에서SPENT03이수행하며현재sw204설치를변경하지않는다. 새로운운영카탈로그/GUI/Setup의정식공개는별도승인전실행하지않는다.


## 전체 역사 보존·신규채널 RC2 (2026-11-18)

과거7Release/30자산을추가복제해Rod/Toast의8Release38자산을보존검증했고Latest8은유지했다. Git객체/원본역사는보존하되main·production-catalog-000008의원래이름2충돌은archive/toast-source refs에보존하고강제교체하지않았다. 신규직원후보는GUI0.1.6/Bootstrap0.1.6/Setup0.1.6.0 RC2,명시적repoID1462539740/전용signed catalog_id/최소9/새프로그램·데이터루트다. 기존직원자동채널전환없음. frozen신규GUI의비관리직접실행은기존Data접근전에거부한다. 관련고유80개/파일·서명·manifest·경로예산검증통과지만실제Windows설치/온라인9는미검증. [현재통합보고](docs/GITHUB_OWNER_COMPATIBILITY.ko.md) 최신절과 [단일SPENT03 RC2인계](docs/SPENT03_OWNER_COMPAT_TRIAL.ko.md)를읽는다. 이번9/GUI/Setup의정식공개·원격운송·직원변경·Toast/증거Transfer는실행하지않았다. 기존구채널은기한없이유지하며과거8복제와달리앞으로두namespace운영카탈로그를서로혼용하지않는다.


## RC2 Windows 시험 운송 (2026-11-19)

기존 Setup 0.1.6.0 RC2와 해시 파일을 시험 저장소 Draft 450851743에서 인증 재다운로드로 검증했다. 시험·운영 Latest는 그대로다. docs/SPENT03_OWNER_COMPAT_TRIAL.ko.md 최신 절에 다운로드와 독립 환경 시험 절차가 있다. SPENT03 실설치와 카탈로그9 온라인 시험은 대기 중이다.


## Rod 운영 Latest9 (2026-11-19)

Rod 저장소 ID 1462539740의 운영 Latest는 [카탈로그9](https://github.com/rodetoast/creative-group-releases/releases/tag/rodetoast-catalog-000009)다. Release ID 450977319. RC2 seed와 동일한 기존 서명 자산을 게시했고 실제 HTTPS 다운로드 및 Qt offscreen GUI 소스의 온라인 갱신을 검증했다. SPENT03 RC2 설치 검증은 사용자 보고에 따라 완료 기록을 재사용한다. 신규 직원용 Setup 0.1.6.0은 정식 공개 승인 대기 중이다. Toast 운영 채널은 Latest8을 유지한다.


## 신규 직원용 Rod Setup 0.1.6.0 정식 공개 (2026-11-19)

[정식 Release](https://github.com/rodetoast/creative-group-releases/releases/tag/employee-setup-0.1.6.0)와 [직접 다운로드](https://github.com/rodetoast/creative-group-releases/releases/download/employee-setup-0.1.6.0/SouthpawToolsLauncherSetup-0.1.6.0.exe)를 공개했다. 신규 직원의 첫 설치에는 이 링크를 사용한다. 기존 Toast 직원은 현재 설치된 런처를 계속 사용한다. 자세한 경로와 검증 결과는 [운영 인계 문서](docs/GITHUB_OWNER_COMPATIBILITY.ko.md)의 최신 절에 있다.


## 기존 직원의 Rod 전환 Bridge (2026-11-19)

개발 브랜치는 codex/toast-rod-bridge다. [운영 인계](docs/GITHUB_OWNER_COMPATIBILITY.ko.md)와 [SPENT03 인계](docs/SPENT03_OWNER_COMPAT_TRIAL.ko.md)의 최신 절을 사용한다. Toast Bridge와 Rod 0.1.7은 로컬 후보이며 Windows 실기동 검증 및 게시 승인이 남아 있다.



## SPENT03 Bridge 시험 운송 (2026-11-19)

서명 후보 운송 Draft 451033277과 시험 도구를 준비했다. [SPENT03 인계](docs/SPENT03_OWNER_COMPAT_TRIAL.ko.md) 최신 절에 실행 범위와 운영 게시 조건이 있다. 실제 Windows 결과는 대기 중이다.

## Rod 카탈로그10 운영 공개 (2026-11-20)

[Rod 카탈로그10/GUI0.1.7](https://github.com/rodetoast/creative-group-releases/releases/tag/rodetoast-catalog-000010)이 실제 Latest다. 공개 HTTPS 자산 8개·Ed25519·Rod 0.1.6의 9→10 조회/다운로드/롤백 방어를 확인했다. Toast Latest8/Setup0.1.4.1은 유지한다. 기존 SPENT03은 stage-rod를 사용한 Windows 인계였으며, 후속 격리 확인은 stage-rod 없는 실제 HTTPS 자동 준비까지 통과하고 자식 프로세스 실행 경계만 대체했다. 전체 운영 흐름은 Toast9 게시 승인 뒤에 확인할 범위다. [운영 공개 기록](docs/GITHUB_OWNER_COMPATIBILITY.ko.md)의 최신 절을 먼저 읽는다.

## Toast Bridge Windows 전환 검증 완료 (2026-11-20)

Toast 0.1.5 소스 GUI에서 한 번 승인하고 기존 Windows Bootstrap과 서명된 Bridge EXE로 공개 Rod Latest10의 0.1.7을 자동 다운로드·검증·기동했다. Rod 홈 사전 준비나 stage-rod 없이 실제 창과 confirmed를 확인했다. Toast 9는 격리 시험 프로세스에서만 제공했다. [운영 기록](docs/GITHUB_OWNER_COMPATIBILITY.ko.md)의 최신 절을 읽는다. 다음 승인 대상은 Toast production-catalog-000009 / Bridge 0.1.6 정식 게시다.

## Toast Bridge 운영 전환 공개 완료 (2026-11-20)

Toast Latest는 [production-catalog-000009 / Bridge 0.1.6](https://github.com/toast-source/creative-group-releases/releases/tag/production-catalog-000009), Rod Latest는 10이다. 실제 배포 Toast 0.1.5 EXE의 업데이트 확인을 격리 Windows에서 한 번 승인해 공개 Toast9 → Bridge → 공개 Rod10 → 실제 GUI 0.1.7 실행과 정상 종료를 확인했다. 기존 직원은 기존 바로가기와 업데이트 버튼을 사용한다. 신규 설치는 Rod Setup 0.1.6.0이다. 미전환 설치를 위해 Toast 채널을 유지한다. [운영 공개·검증 기록](docs/GITHUB_OWNER_COMPATIBILITY.ko.md)의 최신 절을 읽는다.
