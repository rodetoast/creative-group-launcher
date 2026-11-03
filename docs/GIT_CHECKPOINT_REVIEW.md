# 첫 Git 체크포인트 포함·제외 검토 — 아직 stage/commit 안 함

> 이 문서는 해당 개발 단계의 기록입니다. 이후 로컬 체크포인트 승인·검사 결과는 [LOCAL_CHECKPOINT_REVIEW.md](LOCAL_CHECKPOINT_REVIEW.md)를 따릅니다. 과거 Git 상태·제한 및 초기 설계 내용은 현재 상태와 다를 수 있습니다.

2026-11-03 KST. 현재 master, 첫 commit 없음, remote 없음. 이 문서는 목록과 위험 검토이며 저장소 소유권/공개/이전 승인이 아니다. 실제 stage/commit/원격 등록/push는 수행하지 않는다.

## 포함 후보

| 범위 | 판단 |
|---|---|
| [런처/서버 소스](<../southpaw_tools>) | installer journal/복구, UI, server, admin, provider, paths/common/archive/catalog 등. 현재 일반 배포 보류 상태를 함께 기록 |
| [정식 테스트](<../tests>) | 기존78개와 안전한 더미 support. 실제 사용자 프로세스를 종료하지 않는 실패 주입 포함 |
| [감사 도구](<../audit>) | 새 lan_lab/verify_lan_lab와 기존 local_rehearsal/prepare_lan_fixture. mvp_probes는 수정 전 결함 재현 자료라고 명확히 구분 |
| [도구 코드](<../tools>) | 실행 결과/원본 ZIP은 제외하고 코드만. import_approved/verify_distribution은 원본 경로를 사용하는 운영 도구이므로 일반 시험 명령과 구분 |
| [예제 설정](<../examples/lan-lab.server.example.json>) | 실제 토큰·IP 없음, LAN OFF/인터넷 OFF. 실키로 바꾼 파일을 이 경로에 저장하지 않음 |
| [배포 메타데이터](<../distribution/catalog.json>), [기본 설정](<../distribution/server.json>), [초기 client 목록](<../southpaw_tools/data/catalog.json>) | 실제 ZIP/토큰을 포함하지 않는 등록 정보만 후보. published=true를 정식 외부 공개나 서명 인증으로 오인하지 않도록 문서 동봉 |
| [README](<../README.md>), [registry](<../PROJECT_REGISTRY.md>), [ROADMAP](<../ROADMAP.md>), [docs](<.>) | 조건부 후보: 기존 보고서의 사용자명/로컬 절대 경로/회사 내부 정보와 오래된 수치의 시점을 검토 |
| [pyproject](<../pyproject.toml>), [requirements](<../requirements.txt>), 실행 배치, [.gitignore](<../.gitignore>) | 소스 실행/의존성/제외 규칙. 최종 런처 EXE/설치 프로그램은 없음 |

실제 개별 파일 목록은 [git-checkpoint-candidates.txt](<../.test-results/git-checkpoint-candidates.txt>), 검사 결과는 [git-checkpoint-inventory.json](<../.test-results/git-checkpoint-inventory.json>)에 있다. Git의 untracked/nonignored 목록을 읽어 생성했으며 index에 올리지 않았다.

## 조건부 검토와 남은 위험

- 기존 docs는 사용자 프로필 절대 경로를 포함한다. 이번에는 과거 근거 문서를 보존했으며, 첫 commit/특히 공개 저장소로 보내기 전에 사용자명·내부 경로·회사 정보 비식별화와 링크 이식성을 검토해야 한다. 문서가 nonignored라는 이유만으로 공개 안전을 확정하지 않는다.
- [기존 앱 아이콘](<../southpaw_tools/assets>)과 [화면 자료](<screenshots>)는 비밀 키는 아니지만 회사 자산/배포 권한·표시 정보를 검토해야 한다. 회사→개인 저장소 이전 권한을 이번 작업으로 추정하지 않는다.
- audit/lan_lab는 기존 .test-results/lan-rehearsal의 고정 fixture를 재사용한다. 해당 생성 ZIP/EXE는 Git에 넣지 않는다. 새 clone에서 바로 시험 환경을 준비하려면 신뢰 가능한 별도 fixture 전달이 필요하다. 기존 prepare_lan_fixture로 재컴파일하면 해시가 달라질 수 있어 검토 없이 allowlist를 바꾸지 않는다. 이식성 제한을 숨기지 않는다.
- 서명/TLS/서버 신원 검증/관리형 롤백은 미구현이다. 이 체크포인트를 “정식 배포 가능”으로 표시하지 않는다.
- 실제 시험 토큰이 nonignored 후보에 포함되지 않았는지 byte 비교하고 대표 credential 패턴도 검사했다. 이것은 모든 종류의 비밀 탐지를 보장하지 않는다. 운영자가 새 .env/private key 파일을 추가하면 현재 ignore 규칙이 자동으로 모든 이름을 막아주지는 않으므로 별도 검토가 필요하다.
- 테스트의 반복문자 토큰/invalid-token 문자열은 더미 검사 값이다. 실제 운영 토큰으로 교체하거나 파일에 붙여넣지 않는다.

## 제외 대상

| 대상 | 현재 위치/처리 |
|---|---|
| 실제 시험 토큰·개인 설정 | .test-results/lan-lab/server.local.json 등, 전부 .test-results ignore. distribution/server.local.json도 기존 개별 ignore |
| 사용자 설치·작업 데이터 | 시험 client/기본 LOCALAPPDATA 등. 이번 시험은 별도 데이터 폴더만 사용하며 commit 후보에 넣지 않음 |
| 실제 승인 ZIP4개 복사본 | distribution/packages/ 기존 ignore. 원본 Desktop EXE/ZIP·다른 repo는 범위 밖 |
| 더미 ZIP/EXE·전달 소스 복사본 | .test-results/lan-lab/inputs, repository/packages, client-bundle, verification-* 전부 ignore. 새 audit 소스/예제만 후보 |
| 테스트 결과·backup·journal·downloads·logs | .test-results/, docs/*.local.json, docs/baseline.local.json, *.log 등 기존 ignore. 원본 경로가 든 기계 보고서 제외 |
| 환경·빌드 캐시 | .venv/, __pycache__/, *.pyc, .pytest_cache/, build/, dist/ 기존 ignore |

개별 생성물에 git check-ignore를 적용해 실제 제외 여부를 확인한다. “ignore로 되어 있을 것”이라는 추정만으로 분류하지 않는다. staged 파일은 비어 있어야 하며 현재도0개다.

## 이후 승인 전 확인

회사 코드 소유권과 자산 재배포 권한, 문서의 내부 정보, 후보 파일의 비밀정보, 의존성·배포 고지, 미구현 보안 경계를 검토한다. 첫 commit 메시지/브랜치/원격은 별도 승인 범위다. 회사 GitHub→개인 계정 이전은 기존 ROADMAP에 유지하고 소유권·회사 승인 전 수행하지 않는다.
