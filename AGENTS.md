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
