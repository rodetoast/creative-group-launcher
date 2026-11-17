# 배포 카탈로그 전자서명 구현 및 검증

2026-11-05. 구현 완료, 운영 키 미채택, 실제 직원 배포 미승인.
이 문서는 이전 unsigned HTTP 설계 검토의 현재 구현 상태를 갱신한다.
Windows SAC 코드서명·TLS·런처 자체 업데이트는 구현하지 않았다.

## 기존 경로와 최소 변경

기존 `southpaw_tools/admin.py:publish`는 ZIP 감사 후 catalog.json을 원자적으로 갱신했다.
`server.py`는 `/api/catalog`에서 앱 정보를 다시 직렬화했고 `providers.py:HttpProvider.catalog`는
스키마만 검사했다. `ui.py`는 일반 catalog-cache.json을 읽고 썼다.
`installer.py:install`은 호출자가 준 AppRelease를 사용해 다운로드·크기·SHA256·ZIP 안전 추출을 검사했다.
공격자가 HTTP catalog와 ZIP을 함께 바꾸면 게시자 진위를 구별하지 못했다.

현재 서버는 catalog.json 원본 바이트를 그대로 전달한다. HttpProvider가 분리 서명을 검증하고,
설치 엔진 진입 전에 선택한 배포본을 현재 서명 목록과 대조한다. 다운로드 직전에도 다시 대조한다.
기존 ZIP/EXE 해시·크기·CRC/안전 추출·활성화·사용자 데이터 이전·복구 경로는 유지한다.
프로그램 실행은 계속 로컬 active/receipt와 파일 무결성을 기준으로 하며 서버 조회를 요구하지 않는다.

## 알고리즘과 정확한 데이터 형식

검증된 cryptography 50.0.2의 Ed25519 sign/verify API를 사용한다.
서명은 64바이트, 공개키는 32바이트다. 자체 암호 구현이나 JSON 정규화 표준 구현을 추가하지 않았다.
공식 API: https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/
고정 의존성: https://pypi.org/project/cryptography/50.0.2/

catalog.json UTF-8 원본:

```json
{
  "schema_version": 1,
  "catalog_id": "creative-group-launcher",
  "sequence": 1,
  "apps": []
}
```

서명 입력은 ASCII 도메인 `CreativeGroupLauncher catalog v1` + NUL 1바이트 + catalog.json 원본 전체다.
공백·개행·문자 표현까지 정확히 일치해야 한다. 서버가 재직렬화하거나 인코딩을 바꾸면 거부한다.
apps 전체가 포함되므로 앱/릴리스 ID, 패키지 이름·크기·해시, EXE 해시, 리소스/보존/cwd,
게시 여부·설명·릴리스 노트 등 모든 AppRelease 필드를 인증한다.
JSON 중복 키·비정상 숫자·잘못된 형식과 초과 크기를 거부한다.
카탈로그는 최대 4MiB, 분리 서명은 최대 4KiB다.

catalog.sig.json:

```json
{
  "schema_version": 1,
  "algorithm": "Ed25519",
  "key_id": "공개키 원본 32바이트의 SHA256 소문자 64자리",
  "signature": "서명 64바이트의 표준 Base64"
}
```

서버 경로는 `/api/catalog`, `/api/catalog.sig`이다. 다른 경로·키 배포 endpoint는 추가하지 않았다.
분리된 두 요청이 서로 다른 게시 시점을 만나면 서명 불일치로 실패한다. 무조건적인 재시도는 없다.

## 초기 신뢰와 개인키

`southpaw_tools/data/trusted_catalog_keys.json`은 클라이언트에 사전 탑재되는 정책이다.
catalog_id, minimum_sequence, key_id→Base64 공개키 목록을 포함한다.
현재 keys는 빈 객체다. 운영 신뢰키는 별도 승인 없이 생성·채택하지 않았다.
따라서 현재 기본 제품 클라이언트는 네트워크 목록 설치를 차단한다. HTTP가 준 키나 사용자 연결
설정의 키를 자동 채택하는 기능, unsigned 호환 모드는 없다. 테스트는 생성한 별도 키를 명시 주입한다.
순수 로컬 테스트의 LocalProvider는 네트워크 Provider가 아니며 제품의 unsigned HTTP 우회가 아니다.

개인키는 외부 Ed25519 PKCS8 PEM 파일로만 게시 함수에 전달한다. 클라이언트는 개인키를 사용하지 않는다.
게시 저장소 내부의 개인키 경로는 거부한다. 실제 운영 개인키는 프로젝트/Git/배포 ZIP/공개 디렉터리
밖의 관리자 관리 위치에 두고 파일 권한과 암호화된 백업을 운영자가 관리해야 한다.
현재 PEM 로더는 비밀번호 없는 PEM을 받는다. 암호화 PEM/하드웨어 서명 장치 연동은 구현하지 않았다.
운영 키 보관 방식이 승인될 때까지 실제 키를 만들거나 이 형식을 운영에 채택하지 않는다.
Git은 기존 *.pem/*.key 제외 규칙을 유지한다.

개인키 유출 시 게시를 중단하고 새 키를 별도 신뢰 경로로 배포한 클라이언트를 제공해야 한다.
서명키를 잃으면 임의 새 키를 서버에 게시해 복구할 수 없다. 백업 또는 승인된 클라이언트 신뢰키 교체가 필요하다.
정상 교체는 새 공개키를 사전 배포하고, 더 높은 sequence로 새 키가 서명한 목록을 채택한 뒤 옛 키를 제거한다.
전환 중 기존 캐시를 검증할 옛 키가 필요하다. 옛 키를 먼저 제거하면 보수적으로 차단된다.
유출 키로 높은 순번을 받은 상태의 복구·폐기와 로컬 상태 마이그레이션은 관리자 검토 및 별도 승인 작업이다.
자동 신뢰키 변경·자동 상태 초기화·복잡한 PKI는 구현하지 않았다.

## 게시 흐름

`southpaw_tools.admin` CLI에는 `--signing-key`와 `--sequence`가 필수다.
기존 publish API도 키/순번 없는 게시를 거부한다. 순번은 저장소 전체 기준으로 증가하며
동일/작은 순번, 동일 release_id 덮어쓰기, 공개 저장소 내부 개인키는 거부한다.
표시 버전이 같아도 다른 release_id 업데이트는 기존 정책대로 가능하다.

게시 순서는 기존 ZIP 감사 → 불변 패키지 배치 → catalog.sig.json 원자 교체 → catalog.json 원자 교체다.
둘 사이의 혼합 상태는 클라이언트가 거부한다. catalog 교체 실패 후 분리 서명이 새 상태로 남을 수
있으므로 게시 실패를 숨기지 않고 관리자가 검토해야 한다. unsigned 목록으로 후퇴하지 않는다.
기존 로컬 설치본은 이 서버 게시 실패의 영향을 받지 않는다.

승인 후 사용할 명령 형식의 예시이며 이번에 실제 운영 저장소에서 실행하지 않았다:

```powershell
python -B -m southpaw_tools.admin --root <승인된저장소> --app-id <앱ID> --zip <완성ZIP> --version <버전> --release-id <새릴리스ID> --exe <상대EXE경로> --sha256 <ZIP해시> --exe-sha256 <EXE해시> --signing-key <외부개인키PEM> --sequence <증가순번> --approve
```

`tools/import_approved.py`도 명시적 키/시작 순번을 요구한다. 이번에는 실제 승인 ZIP 가져오기를 실행하지 않았다.
`audit/lan_lab.py prepare`는 새 격리 루트에만 테스트 키와 테스트 전용 묶음을 만든다.
개인키는 lab 루트에 있고 공개 HTTP repository 및 client-bundle에는 없다.
해당 묶음의 공개키는 테스트 전용이며 TEST_ONLY.txt로 표시한다. 운영 신뢰키로 승격하지 않는다.
옛 unsigned 시험 루트·토큰·패키지·로그는 변환하거나 덮어쓰지 않았다.
옛 LAN 운영 스크립트를 새 클라이언트에 그대로 재사용하면 서명 누락으로 차단된다.
새 서명 시험 환경과 공개키가 일치하도록 다음 별도 시험을 준비해야 한다.
이전에 전달된 구버전 client-bundle이나 ZIP 자체는 변경하지 않았다. 구버전 클라이언트에는
이번 검증 기능이 자동으로 생기지 않으므로 실제 배포 전에 클라이언트 소스/의존성 갱신을 별도 검증해야 한다.
시험의 HttpProvider 직접 호출은 테스트 정책과 시험 전용 신뢰 상태 경로를 명시 주입해야 한다.
제품 기본 사용자 데이터 루트를 테스트 신뢰 상태로 사용하지 않는다.

## 클라이언트, 캐시, 실패 정책

`catalog_trust.py:CatalogVerifier`가 서명·키 ID·catalog_id·sequence·스키마를 검사한다.
`HttpProvider.catalog`는 고정 정책을 사용해 검증 후 반환한다.
`HttpProvider.validate_release`는 현재 목록과 선택한 AppRelease 전체가 같은지 검사한다.
`Installer.install`은 이 검사를 앱 잠금·journal·복구 처리 전에 실행한다.
서명 실패 시 ZIP을 받지 않고 활성 포인터·설치 파일·사용자 데이터·journal을 변경하지 않는다.

서명된 원본 catalog와 서명 문서를 Base64로 담은 catalog-trust.json이 검증 캐시이자 순번 최고 기록이다.
앱 데이터 루트 아래 고정 파일에 저장하며 URL/IP별로 나누지 않는다. 주소 변경으로 순번을 초기화하지 않는다.
별도 OS 잠금과 원자 쓰기로 여러 클라이언트 인스턴스의 순번 확인/저장을 직렬화한다.
검증 실패 시 기존 신뢰 파일을 덮어쓰지 않는다. 신뢰 파일 손상 시 자동 삭제·초기화하지 않는다.
UI는 일반 catalog-cache.json을 신뢰 목록으로 읽거나 갱신하지 않는다. 이전 파일은 삭제하지 않는다.
서명된 캐시를 다시 검증하며 서버 오류가 발생해도 설치된 앱 목록을 병합하고 로컬 실행 경로를 유지한다.
UI 오류를 통해 설치·업데이트 차단 이유를 표시한다. 오프라인 캐시만으로 신규 설치를 승인하지 않는다.

## 재전송·롤백 보장과 한계

- minimum_sequence보다 작은 목록은 최초 실행에서도 거부한다.
- 이전에 검증한 최고 sequence보다 작으면 재시작 후에도 거부한다.
- 동일 sequence의 동일 원본 바이트는 허용하고 다른 내용은 거부한다.
- 높은 sequence의 정상 서명은 수락한다. 목록 서명자의 악의적 다운그레이드까지 막는 체계는 아니다.
- 최초 사용자는 minimum_sequence 이상이지만 오래된 목록을 처음 받을 수 있다.
- 로컬 신뢰 상태 삭제/백업 복원·사용자 계정 침해·신뢰키 교체 배포물 변조는 이 파일 기반 방어 범위 밖이다.
- 네트워크 공격자의 최신 목록 차단/업데이트 동결은 감지할 수 없다. 만료시각은 도입하지 않았다.
  따라서 PC 시계 오류가 서명 검증이나 오프라인 사용을 막지 않지만 최신성 보장은 제한된다.
- 실제 운영 최소 순번과 승인된 키 배포 경로, 복구/키 폐기 절차는 운영 채택 전에 결정해야 한다.

## 시험 및 보존

최종 회귀 결과: 기존 81개와 신규 24개, 총 **105개 통과**, 19.752초.
신규 테스트는 정상 서명, 문자/메타데이터 변조, 누락/잘못된 서명·키, 순번 후퇴/동일 순번 충돌,
최초 최소 순번, 게시 세대 혼합, 중복 JSON, 캐시 손상/쓰기 실패, 설치 전 차단과 원본 보존,
서명된 r1→r2 설치, 로컬 상태, 외부 개인키/필수 인자, 게시 중단 실패를 확인한다.
기존 네트워크 테스트 fixture만 테스트 키/서명에 맞춰 연결했으며 테스트를 제거하거나 건너뛰지 않았다.
별도 새 격리 lab의 r1→r2 게시와 서명 검증도 성공했다. 이 확인은 실제 LAN 시험이 아니다.

최초 81개 실행은 샌드박스 loopback 연결 제한(WinError 10013)으로 네트워크 5개가 실패했다.
방화벽/정책을 변경하지 않고 일반 권한의 테스트 실행 범위를 사용한 최종 105개는 모두 통과했다.
기존 journal WinError 5 주입 테스트의 예상 오류 로그는 통과 결과와 구분한다.
의존성은 전역 Python을 바꾸지 않고 `.test-results/catalog-signing-20261105/deps`에 설치해 검증했다.
pip은 전역 pyOpenSSL의 버전 제약 경고를 출력했지만 설치 대상은 격리 디렉터리다.
전체 기존 개발 환경을 이 의존성 경로로 실행하도록 PATH나 전역 설치를 변경하지 않았다.

최종 보존 검사: 기존 다섯 프로젝트 292개 파일 해시와 HEAD/tags/status 동일,
존재하는 원본 승인 ZIP 4개 해시 동일. TagMaster 승인 ZIP은 기존과 같이 없어 확인 대상이 아니다.
이전 LAN 기록/패키지/토큰·실제 distribution 파일은 변경하지 않았다.
준비 전 기준의 해당 파일 720개 해시가 모두 동일하다.
최종 호스트 읽기 전용 조회는 관리자 False, TCP8765 리스너 0개·시험 규칙 0개다.
master / HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5`, remote 없음.
기존 미커밋 작업을 유지했고 이번 수정은 작업 트리에만 있다. stage/commit/push/remote 변경 없음.

이번 변경 파일:

- 추가: southpaw_tools/catalog_trust.py, southpaw_tools/data/trusted_catalog_keys.json,
  tests/test_catalog_signing.py, docs/CATALOG_SIGNING_IMPLEMENTATION.md.
- 수정: southpaw_tools/admin.py, common.py, providers.py, installer.py, server.py, ui.py.
- 수정: tests/support.py, tests/test_network_admin.py, audit/lan_lab.py, tools/import_approved.py.
- 수정: requirements.txt, pyproject.toml, .gitignore, README.md, docs/CATALOG_TRUST_DESIGN.md.
- 개발 증거/패키지: ignored `.test-results/catalog-signing-20261105`에만 보관.

세부 시험 로그는 같은 개발 증거 폴더의 final-tests.log,
외부 원본 비교는 existing-projects-verification.local.json,
전체 변경 전 파일 해시는 before-files.local.json에 있다.

실제 LAN·8765 서버·방화벽·EXE·제품 GUI는 실행하지 않았다.
기존 UI 회귀 테스트는 Qt offscreen으로, 네트워크 테스트는 격리 loopback 임시 포트로 실행했다.
이 테스트는 직원 PC에서의 EXE/GUI/SAC 호환성 검증이 아니다.
HTTP는 토큰·전송 내용 기밀성이나 서버 진위를 보호하지 않는다. TLS는 별도 후속 항목이다.
카탈로그 서명은 Windows EXE Authenticode/SAC 코드서명을 대신하지 않는다.
간헐적인 journal WinError 5 원인을 해결했다고 주장하지 않는다.
