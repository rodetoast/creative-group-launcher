# Southpaw 도구 런처 — 개발 소스 및 맥락 보존

현재 소스 저장소는 **rodetoast/creative-group-launcher**입니다. [AGENTS.md](AGENTS.md)에서 현재 상태·기획/설계 기록·새 세션 시작 방법을 먼저 확인하세요.

- 기본 `main`: 처음 비어 있던 원격에 검토한 개발 소스를 정상 push한 보존 기준입니다. 기존 Git 이력을 유지합니다.
- 작업 재개 브랜치: `codex/migration-checkpoint-20261117` — 최신 개발 소스와 문서 보존용이며, 정식 배포 승인·새 회귀 완료를 의미하지 않습니다.
- 실제 운영 제품: GUI0.1.4 / Setup0.1.4.1 / production-catalog-000007. [직원용 운영 Setup](https://github.com/toast-source/creative-group-releases/releases/tag/employee-setup-0.1.4.1)은 기존 채널을 유지합니다.
- 소스 저장소 이전은 운영 카탈로그·서명·배포 주소 변경이 아닙니다. 아래 초기 README 내용은 개발 당시 기록으로 보존합니다.

---

## 기존 README (개발 이력)

# Creative Group Launcher v0.1.0

[Windows onedir 빌드와 Bootstrap 시험](docs/WINDOWS_PACKAGING_BOOTSTRAP.md)을 추가했습니다.
제품 EXE는 미실행이며, 신규 native 시험 통과와 별개로 전체 회귀는 journal WinError 5로 미통과입니다.

런처 자체 업데이트의 [격리 더미 기반과 복구 검증](docs/SELF_UPDATE_FOUNDATION.md)을 추가했습니다.
실제 런처 자동 업데이트는 활성화하지 않았으며 EXE 패키징·운영 키·직원 배포는 별도 검토 사항입니다.

로컬 관리자 배포 GUI를 추가했습니다. `python -B -m southpaw_tools.admin_gui`로 실행합니다.
**운영 게시는 잠겨 있으며**, 격리 더미 저장소에서만 게시 시험을 허용합니다.
[관리자 GUI 사용·검증 보고서](docs/ADMIN_GUI_IMPLEMENTATION.md)를 확인하세요.

2026-11-05: Ed25519 카탈로그 서명과 순번 검증을 구현했습니다.
[서명 구현·키 관리·검증 보고서](docs/CATALOG_SIGNING_IMPLEMENTATION.md)를 먼저 확인하세요.
**운영 공개키는 미채택이므로 기본 네트워크 설치·업데이트는 차단됩니다.**
게시 CLI에는 `--signing-key`와 `--sequence`가 필요하며 unsigned 자동 호환은 없습니다.
이전 시험 기록과 아래의 unsigned 시점 설명은 보존합니다. TLS·SAC 코드서명은 이번 범위에서 제외합니다.

현재 방향은 **추가 서비스 비용0원·회사 내부 LAN 전용**입니다. 기존 Southpaw Tools Launcher 코드와 데이터 경로를 그대로 사용합니다.
인터넷 배포는 현재 개발 범위에서 제외하며 유료 서비스/VPN/Cloudflare/OAuth/SSO/DRM/복잡한 PC별 인증을 요구하지 않습니다.
직원 런처와 관리자 로컬 게시를 분리하고 안전한 업데이트·팀원 PC 보호를 우선합니다. 후속으로 Ed25519 카탈로그 서명을 구현합니다.
회사 담당자의 시험 범위와 별도 시험 PC가 확인되지 않으면 LAN 서버를 시작하지 않습니다.
현재 실제 시험 상태와 필요한 최소 조치는 [CREATIVE_LAN_TRIAL_STATUS.md](docs/CREATIVE_LAN_TRIAL_STATUS.md)에 있습니다.

Southpaw Games 내부 팀원이 승인된 Windows 제작 도구를 설치·실행·업데이트·제거하는 첫 개발본입니다.

2026-11-03 MVP 안정성 보완: 제거 실패 복원, 설치 중단 기록/재시도, 검증된 로컬 실행과 카탈로그 오류 분리를 추가했습니다.
[수정·재검증 보고서](<docs/STABILITY_FIX_REPORT.md>)와
[카탈로그 신뢰 설계 검토](<docs/CATALOG_TRUST_DESIGN.md>)를 먼저 확인하세요.
카탈로그 서명과 서버 진위 검증은 여전히 미구현이며 **실제 프로그램 일반 팀원 배포는 보류**합니다.
실제 LAN 시험은 별도 승인 후 더미 전용으로 진행하며 이번 작업에서 자동 진행하지 않습니다.
현재 준비된 더미 전용 서버·소스 묶음·게시/시험 절차는 [LAN 환경 준비](<docs/LAN_ENVIRONMENT_PREPARATION.md>)를 따르세요.
첫 commit 포함/제외 검토는 [Git 체크포인트 검토](<docs/GIT_CHECKPOINT_REVIEW.md>)에 있습니다. 로컬 체크포인트는 사용자 승인과 검사 통과 후에만 생성하며 원격 등록/push는 하지 않습니다.
Python 3.12 이상과 PySide6 6.11.0을 사용합니다. Windows 10/11 대상이며 이번 검증은 현재 Windows PC에서 수행합니다.

## 시작

프로젝트 루트에서 PowerShell 터미널 두 개를 사용합니다.

개발자 PC의 읽기 전용 배포 서버:

```powershell
python -B -m southpaw_tools.server
```

사용자 런처:

```powershell
python -B -m southpaw_tools
```

또는 `run_server.bat`, `run_launcher.bat`을 실행합니다. 스크립트는 패키지를 자동 설치하거나 기존 개발 환경을 변경하지 않습니다.
별도 개발 환경을 만들 때만 `python -m venv .venv`, `.venv\Scripts\python.exe -m pip install -r requirements.txt`를 사용합니다.
서버는 기본 `127.0.0.1:8765`에만 바인딩됩니다. 서버 종료는 해당 터미널에서 Ctrl+C입니다.
서버가 켜져 있으면 런처의 **업데이트 확인 → 프로그램 선택 → 설치**를 사용합니다.
설치/업데이트는 사용자가 버튼을 누르고 확인한 경우에만 진행됩니다.

팀원 PC에서는 런처의 **연결 설정**에 개발자 PC 주소를 지정합니다. 실제 LAN 사용 방법은 [SERVER.md](docs/SERVER.md)를 읽으세요.
Python이 없는 PC용 런처 EXE/Installer는 아직 만들지 않았습니다.

## 등록된 도구

| 표시 이름 | 승인 기준 | 이번 개발본 |
|---|---|---|
| TileNamer | v0.1.6 RC3 | 승인 ZIP 검증·로컬 게시 |
| ase_viewer | v0.5.8.3 with-examples | 승인 ZIP 검증·로컬 게시 |
| AsepriteTagMaster | 기존 v0.4.0 / 7263f8d | 승인 ZIP 미확인, 설치 비활성 |
| Ase-PS Bridge Pro | v0.3.6 | 승인 ZIP 검증·로컬 게시 |
| Pivot_Fixer | v0.3.3 | 승인 ZIP 검증·로컬 게시 |

Viewer v0.5.8.4/v0.5.8.5, Tag Master 분할 기능, Bridge v0.3.7, TileNamer 후속 UI 개발본은 사용하지 않습니다.
Pixel Effect Maker와 Pixel Motion Studio는 등록·설치·업데이트·개발 우선순위에서 제외합니다.
Tag Master의 기존 EXE를 임의로 다시 ZIP으로 만들거나 다른 빌드로 대체하지 않습니다.

## 동작

- 남색/보라색 PySide6 UI, 프로그램별 사이드바, 실제 아이콘 또는 기본 배지, 소개, 릴리즈 노트, 설치/서버 버전, 진행률·취소·실패 사유.
- 카탈로그 기반 프로그램 추가. `app_id`와 표시 이름 분리.
- ZIP 및 EXE SHA-256, 패키지 크기, 필수 리소스, Windows 상대 경로 검증.
- 버전 문자열 대신 `release_id + sha256` 비교. 같은 ID의 내용 변경은 거부.
- 버전별 설치, 원자적인 활성 버전 전환, 실패 시 이전 설치 유지.
- 명시된 사용자 설정 이전, 이전 버전의 미등록/변경 파일 보존.
- 런처 재시작 후에도 설치 메타데이터만으로 오프라인 실행 가능.
- 실행 중인 설치 프로그램은 업데이트·제거 보류. 기존 프로그램을 강제 종료하지 않음.
- 변경된 설치 파일과 사용자 파일을 보존하는 제거.
- 서버와 클라이언트는 별도 프로세스. HTTP API에는 게시·업로드 기능이 없음.

## 파일 위치

기본 사용자 데이터 루트는 `%LOCALAPPDATA%\SouthpawGames\ToolsLauncher`입니다.

```text
apps/<app_id>/active.json
apps/<app_id>/releases/<release_id>/receipt.json
apps/<app_id>/releases/<release_id>/payload/<원본 ZIP 구조>
downloads/                 다운로드 임시 파일, 종료/취소 시 정리
staging/                   새 설치 준비 영역
locks/                     프로세스 간 OS 잠금
apps/<app_id>/transactions/ 작업 단계별 복구 기록; 정리 실패 시 다음 작업에서 재시도
apps/<app_id>/recovery/     제거 백업·중단 설치·복구 전 payload 보존; 자동 일괄 삭제하지 않음
apps/<app_id>/recovery-warnings.log  복구/정리 경고
settings.json              서버 연결 설정; LAN 토큰은 이 사용자 파일에 저장
catalog-cache.json         이전 unsigned 캐시; 신뢰 목록으로 사용하지 않음
catalog-trust.json         서명된 카탈로그 캐시와 최고 검증 순번
```

현재 프로그램들은 서로 다른 설정 정책을 사용합니다. 기존 프로그램 코드를 변경하지 않으므로
EXE 옆에 설정을 쓰는 프로그램은 버전 폴더 안에 설정이 생깁니다.
업데이트 시 등록된 설정 파일만 복사하며, 미등록 작업물·변경된 리소스는 **이전 버전 폴더에 그대로 보존**합니다.
새 버전으로 자동 병합하지 않습니다. [DATA_POLICY.md](docs/DATA_POLICY.md)에 앱별 정책을 기록했습니다.
기존 Desktop 설치본이나 기존 사용자 프로필의 설정을 런처로 자동 가져오지 않습니다.

미완료 작업은 **복구 확인**으로 서버 없이 대조·복원할 수 있습니다. 복구 후 실행/설치를 다시 선택합니다.
작업 기록 없이 EXE만 사라진 경우, 온라인에서 설치 기록과 동일한 승인 배포본으로 **복구 설치**할 수 있습니다.
이때 기존 payload는 recovery 아래 보존하며 미등록 파일을 새 payload에 자동 병합하지 않습니다.
삭제/복원 권한이 계속 없거나 파일이 충돌하면 복구 필요로 중단합니다. 관리형 롤백 기능은 아직 없습니다.
보존 영역과 백업은 디스크 공간을 사용하며 임의로 정리하지 않습니다. 상세 정책은 수정 보고서를 따릅니다.

## 개발 검증

새 체크아웃에서 실제 배포 ZIP/EXE나 기존 사용자 데이터 없이 기본 개발·테스트 환경을 준비할 수 있습니다.
Windows에서 승인된 Python(검증 환경 3.13.7)을 사용해 저장소 루트에서 실행하세요.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -B -m tools.run_tests
python -B -m southpaw_tools --check
```

78개 정식 테스트는 tests/support.py가 격리 폴더에 더미 ZIP을 생성하므로 승인 패키지·토큰·로컬 baseline이 필요 없습니다.
네트워크 검사는 loopback만 사용하며 실제 회사 LAN/방화벽 설정을 변경하지 않습니다.
환경에 따라 loopback 허용이 필요할 수 있습니다. 테스트 실패는 우회하거나 통과로 간주하지 마세요.

실행 가능한 별도 콘솔 더미가 필요하면 Windows에 이미 있는 .NET Framework compiler를 이용할 수 있습니다.
아래 출력 경로는 새 폴더여야 하며, 생성한 ZIP/EXE는 Git에 넣지 않습니다.

```powershell
python -B -m audit.prepare_lan_fixture --output .test-results/source-only-fixture
python -B -m audit.local_rehearsal --root .test-results/source-only-fixture
```

고정 해시를 검증하는 audit.lan_lab은 별도 승인된 기존 fixture를 요구합니다. 새로 컴파일한 파일의 해시가 달라지면
자동으로 신뢰하거나 allowlist를 바꾸지 않습니다. 이 경우 기본78개 테스트와 위 loopback 리허설은 가능하지만
고정 LAN 환경 준비에는 별도 fixture 검토가 필요합니다. 로컬 검증 기록(.test-results, docs/*.local.json)은
Git에서 제외되어 새 체크아웃에는 없으며, 과거 보고서의 해당 링크는 로컬 근거용입니다.

```powershell
python -B -m unittest discover -s tests -v
python -B -m southpaw_tools --check
python -B -m southpaw_tools --check --screenshot .test-results/ui/launcher.png
python -B -m tools.verify_distribution
```

`--check`는 격리된 상태로 UI를 생성하고 종료합니다. 실제 도구 EXE는 실행하지 않습니다.
테스트는 더미 ZIP을 사용합니다. `tools.verify_distribution`만 승인 패키지 4개를 loopback HTTP로
`.test-results/approved-client-*`에 설치하고 실행 경로·오프라인 해석·UI를 검증합니다. 실제 도구를 실행하지 않습니다.
테스트 서버는 종료 시 닫힙니다. 네트워크 제한 샌드박스에서는 loopback 연결도 제한될 수 있습니다.

## 배포 저장소와 게시

`distribution/catalog.json`은 개발자 PC의 배포 원본입니다. 실제 ZIP은 `distribution/packages/`에 있으며 Git에서 제외합니다.
런처에 포함되는 `southpaw_tools/data/catalog.json`은 초기 목록이며 설치 패키지를 포함하지 않습니다.
팀원에게 초기 카탈로그만 복사해도 서버 연결 없이 설치할 수 있는 구조가 아닙니다.

현재 4개 패키지는 명시 승인된 원본 ZIP을 바이트 그대로 복사했습니다.
승인 기준 등록 도구는 `tools/import_approved.py`이며 `--approve`가 필요합니다.
다른 최신 소스나 버전을 탐색해 자동 교체하지 않습니다.

새 승인 배포본의 로컬 CLI 게시 방법은 [SERVER.md](docs/SERVER.md)에 있습니다.
카탈로그는 해시가 검증된 완성 ZIP을 준비한 뒤 마지막에 원자적으로 교체합니다.

## 제한과 다음 단계

- 인터넷 배포는 **미구성**이며 활성화를 거부합니다. TLS·인증·회사 정책·서명된 배포 메타데이터 검토가 선행됩니다.
- 실제 회사 LAN PC 간 연결, 방화벽 허용, 실제 100/125/150% Windows GUI 조작은 수동 검증 대상입니다.
- 기존 5개 도구의 실제 실행·기능 검증은 이번 작업에서 수행하지 않습니다.
- 런처 자체 업데이트는 아직 없습니다. 실행 중 EXE를 덮어쓰지 않는 별도 updater가 필요합니다.
- 자동 롤백 UI·오래된 버전 정리·Tag Master 승인 ZIP 복구·관리자 GUI는 후속입니다.
- 로컬 Git 체크포인트는 명시 승인과 검사 후에만 생성합니다. 원격 등록/push, 회사 계정 연결, 정식 배포, 런처 최종 EXE 빌드는 별도 범위입니다.

설계: [ARCHITECTURE.md](docs/ARCHITECTURE.md) · 등록부: [PROJECT_REGISTRY.md](PROJECT_REGISTRY.md) · 계획: [ROADMAP.md](ROADMAP.md)
