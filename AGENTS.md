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
