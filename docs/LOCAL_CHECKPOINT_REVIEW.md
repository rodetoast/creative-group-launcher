# 첫 로컬 체크포인트 검사 기록

2026-11-03 KST. 사용자가 현재 개발본의 첫 **로컬** commit을 명시 승인했다. 원격 추가/push/태그/릴리즈와 실제 LAN 시험은 승인 범위가 아니다. 실제 commit SHA는 Git history와 Git 제외 로컬 결과 보고서에서 확인한다.

## 검사 결과와 한계

- 최초 전체 실행:78개 중 오류1. test_refresh_conflict_does_not_overwrite_cache_or_local_pointer의 더미 설치 준비에서 journal atomic replace가 WinError5 접근 거부로 실패했다. 코드/테스트를 바꾸어 통과시키지 않았다.
- 해당 테스트 단독 재실행:PASS. 이어서 전체78개 재실행:failures0/errors0/skipped0,19.210초 PASS.
- commit 후보 소스만 새 디렉터리로 복사하고 승인 ZIP/EXE·토큰·로컬 baseline·이전 설치가 없는 상태에서 전체78개:19.206초 PASS. 기본 개발·테스트는 실제 배포 파일 없이 재현됐다.
- 최초 오류의 직접 원인은 journal 파일 교체 접근 거부이며, 접근을 차단한 프로세스/원인은 확정하지 못했다. 재검사에서 재현되지 않았다는 사실과 근본 원인 해결은 다르다. 초기 실패 로그/JSON은 로컬에 보존한다. 이번 commit은 검증된 소스를 보존하는 체크포인트이며 간헐적 접근 거부가 해결됐다고 선언하지 않는다.
- 기존5개 프로젝트 검사 대상292개 해시·HEAD·태그·작업 상태와 원본 승인 ZIP4개 동일. launcher 쪽 승인 ZIP 복사본도 catalog SHA-256과 일치. 기존 소스/EXE/ZIP을 실행하거나 수정하지 않았다.

## 포함 및 제외

포함:런처/서버/설치·복구 소스,78개 테스트, 안전한 감사 도구 코드, 승인 메타데이터만 담은 catalog, README/registry/ROADMAP/개발 문서, 비밀 없는 예제, 기본 실행 배치와 프로젝트 설정, 아이콘/더미 설치 UI 화면 자료, .gitignore.

제외:실제 및 더미 배포 ZIP/EXE, 설치/다운로드/cache/journal/사용자 설정, 토큰·개인키·인증정보, 테스트 결과, 소스-only 검증 복사본, 원문 backup/로컬 보고서, 가상환경/로그. .gitignore는 알려진 환경 파일·키 파일·사용자 설정도 제외하도록 보완했다.

문서의 개발 PC 사용자 절대 경로는 저장소 상대 링크와 환경별 명령으로 바꿨고 원문은 Git 제외 baseline에 보존했다. 소스-only 테스트 입력은 tests/support.py가 생성한다. 별도 실행 가능한 콘솔 fixture의 source 준비는 README에 있다. 고정 해시 LAN fixture는 별도 승인 입력이 필요하며 재컴파일 결과를 자동 신뢰하지 않는다.

실제 시험 토큰과 대표 credential 패턴을 파일 내용 및 staged blob에서 검사하고 금지된 아카이브/실행 파일을 제외한다. 이미지 화면 내용과 PNG metadata도 확인했다. 일반적인 자동 검사는 모든 종류의 민감정보 탐지를 보장하지 않는다. 로컬 commit 승인은 회사 자산의 외부 공개/소유권 이전 승인과 별개다.

개별 포함 목록·제외 확인·실제 staged 검사·commit 결과는 Git 제외 .test-results/checkpoint-final.local.json에 기록한다. 초기 실패는 .test-results/checkpoint-initial-tests.json 및 .log, 최신 테스트 결과는 .test-results/unit-tests.json, 소스-only 결과는 .test-results/checkpoint-source-only/.test-results/unit-tests.json에 있다. 이 파일들은 새 clone에 포함되지 않는다.

## LAN 직전 상태와 다음 행동

읽기 전용 조회에서 사설 IPv4 후보를 확인했고 현재 이더넷 프로필은 Public이다. 실제 주소는 Git 제외 checkpoint-network.local.json에 기록한다. 조회 시8765 listener0, 기본/시험 설정 LAN OFF·인터넷 OFF, 시험 토큰과 실제 배포 root 분리 상태를 확인했다. 실제 다른 PC 연결·실제 사설 IP listen은 하지 않았다.

사용자는 회사 담당자와 시험 PC1대·IP/경로/프로필·제한적 방화벽 허용 필요 여부·시험 시간을 확인해야 한다. 방화벽/프로필은 자동 변경하지 않는다. 시작 전 가드와 서버 시작·중지는 [LAN 환경 절차](LAN_ENVIRONMENT_PREPARATION.md)를 따르고 설정은 서버 중단·재시작 후 적용한다. 시험 종료 후 listener 종료와 담당자의 시험 예외 정리·토큰 폐기가 필요하다.

unsigned HTTP/공유 토큰/SHA-256은 게시자·서버 진위 인증을 대신하지 못한다. 카탈로그 서명/TLS/서버 진위 검증은 미구현이며 실제 프로그램 일반 배포는 계속 보류한다. 관리형 롤백·자체 업데이트·인터넷 배포·관리자 UI는 추가하지 않았다.

Windows Use0, 기존 사용자 프로그램 실행·종료0, 무단 LAN 공개0. 계정 이전은 회사 코드 소유권과 승인 확인 후 별도 진행하며 이번에는 원격을 등록하지 않는다. 이 검사와 로컬 체크포인트 후 다음 단계로 자동 진행하지 않는다.
