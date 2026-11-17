# 세 프로그램 우선 배포 준비와 ase_viewer B안 후보 검증

2026-11-06. 로컬 후보 준비 작업만 수행했다. 실제 GitHub 게시, 운영 키 생성·채택, 승인 ZIP 승격, 직원 배포 및 회사 프로그램 실행은 하지 않았다.

## 1. 산출물 위치

기준 폴더: `C:\Users\SOUTHPAW GAMES\Documents\ChatGPT\통합 클라이언트 만들기\.test-results\local-release-candidates-20261106`

- `three-program-bundle/`: 원본과 동일한 ZIP 3개를 `packages/`에 복사하고 미서명 `catalog.json`, 후보 표식 `CANDIDATE_ONLY.json`을 준비했다.
- `three-program-manifest.json`: 원본 위치, 복사본 위치, ZIP 크기·해시, EXE 해시, release_id, 필수 경로.
- `ase-viewer-B-candidate/`: 별도 후보 ZIP, 미게시 상태의 `catalog.candidate.json`, 수정 전후 전체 파일·해시 대조 `file-diff.json`.
- `artifact-manifest.json`: 세 프로그램 묶음과 B안 ZIP의 크기·SHA-256.
- `checks/`, `result.json`: 관리자 검사, 로컬 설치·파일·정상 상태 복구 결과.
- `failure.json`, `path-length-diagnosis.json`: Pivot_Fixer의 최초 긴 경로 실패와 비교 진단. 실패 자료는 보존했다.
- 짧은 경로 비교 설치 및 B안 설치 증거: `C:\Dev\cgl-candidate-checks-20261106`.

묶음을 다시 압축한 전송용 ZIP은 만들지 않았다. 준비된 폴더 안에 기존 ZIP 원본 바이트를 그대로 복사했으므로 불필요한 이중 압축은 없다.

## 2. 세 프로그램 후보 ZIP

| 프로그램 | 패키지 파일명 | 크기(바이트) | SHA-256 |
|---|---|---:|---|
| TileNamer 0.1.6 RC3 | `tilenamer--0.1.6-rc3-8ba7a1e.zip` | 54,046,715 | `aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4` |
| Ase-PS Bridge Pro 0.3.6 | `ps2ase--0.3.6-team-6e84645.zip` | 66,252,089 | `1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9` |
| Pivot_Fixer 0.3.3 | `pivot-fixer--0.3.3-team-80b84c9.zip` | 20,709,116 | `214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361` |

세 ZIP의 합계 용량은 141,007,920바이트다. 원본 위치와 전체 메타데이터는 manifest에 기록했다.

## 3. 미서명 카탈로그 초안

기존 `AppRelease`와 schema_version 1 형식을 유지했다. 세 프로그램의 버전·release_id·build_id·ZIP/EXE 해시·실행 경로·필수 경로·설정 보존 경로·릴리스 노트를 기존 카탈로그에서 재사용했다.

- `published=true`: tilenamer, ps2ase, pivot-fixer. **로컬 초안의 게시 대상 표시**이며 GitHub 공개를 뜻하지 않는다.
- `published=false`: ase-viewer, tag-master. 각각 후보 검증·승인 대기와 승인 ZIP 부재 사유를 표시했다. 해당 ZIP은 세 프로그램 묶음에 포함하지 않았다.
- Dummy 앱·시험 키·개인키·토큰은 포함하지 않았다.
- `sequence=0`은 미서명 작업 초안용 임시값이다. 공개용 순번이 아니며, 향후 서명 직전에 실제 최신 순번보다 큰 값으로 정해야 한다.
- `catalog.sig.json`은 만들지 않았다. 기존 기본 검증기에 전달했을 때 거부됐고 신뢰 상태 파일도 생성되지 않았다. 미서명 카탈로그를 자동 신뢰하는 호환 경로를 추가하지 않았다.
- 현재 초안 SHA-256: `7c115a32c29cc9272863b68da47ee21765831fcc07543fd58eb54779d7a89ece`.

## 4. ase_viewer B안 후보의 정확한 변경

파일: `ase-viewer-B-candidate/ase_viewer_v0.5.8.3_public_noexamples_CANDIDATE.zip`

- 크기: **17,867,191바이트**
- SHA-256: **`ec887d27f2631671b66d3b5cc362994025128a16e4f70917ecb9ea05cadf1e92`**
- 후보 release_id: `0.5.8.3-public-noexamples-candidate1`. 원본 release_id를 덮어쓰지 않았다.
- 버전은 `0.5.8.3`을 유지하고 별도 패키징 후보임을 문서에 표시했다.

원본의 파일 14개에서 후보 3개로 정리했다. 디렉터리 항목은 별도로 생략했다.

| 구분 | 변경 |
|---|---|
| 그대로 유지 | `ase_viewer.exe` 1개. SHA-256 `299ef579a110c76c85a4122a6363b81e9360a41957e2d2ad7efe001f877d0dbf` 동일 |
| 제외 | `resources/examples/`의 캐릭터 Aseprite 2개, 배경 PNG 7개, 내부 출처 README 1개 |
| 제외 | 개발용 `MANUAL_TEST_CHECKLIST.md` 1개 |
| 교체 | 최상위 `README.md`, `RELEASE_v0.5.8.3.md` 2개를 후보 안내로 정리. 사용자 절대 경로와 개발·복구 이력을 제거하고 예제 기능 손실을 명시 |
| 카탈로그 | 별도 B안 후보의 `required_paths`에서 예제 관련 10개를 제거해 `[]`로 설정. EXE 경로·해시 및 사용자 데이터 보존 경로는 유지 |

전체 차이는 `file-diff.json`에 파일별 원본/후보 크기·SHA-256으로 기록했다. 원본 ZIP, 원본 소스, DLL·내장 리소스는 변경하지 않았다. EXE 내장 바이트까지 제거하거나 새로 빌드한 것이 아니며, 이전 조사에서 확인한 외부 예제 파일만 제외했다.

B안 후보 카탈로그는 `published=false`다. 관리자 검사 함수가 검사용으로 만든 설치 메타데이터만 격리 설치에 사용했다. 이 메타데이터는 회사 승인이나 전자서명으로 간주하지 않는다. 세 프로그램 초안에 B안을 게시 상태로 추가하지 않았다.

## 5. 관리자 검사·Installer 결과

기존 `AdminSession.inspect()`의 경로·CRC·ZIP 구조·EXE·필수 리소스 검사를 재사용했다. 게시용 `review()` 및 `publish()`는 호출하지 않았다. Inspector는 기존 기본 운영 잠금 상태를 유지하며 로컬 ZIP 검사만 수행했다.

기존 `Installer.install()`을 기존 테스트용 로컬 파일 Provider와 실제 ZIP·파일시스템으로 실행했다. 네트워크 Provider를 우회해 운영 설치를 허용한 것이 아니라, 격리 검증 입력을 로컬에서 제공했다. 서명·GitHub 다운로드 검증은 이번 결과에 포함하지 않는다.

| 후보 | 관리자 ZIP 검사 | 실제 로컬 설치·파일 검사 | journal·복구 |
|---|---|---|---|
| TileNamer | 통과 | 3개 파일, ZIP/EXE 해시 및 active/receipt 일치 | journal 0, 복구 대기 없음 |
| Ase-PS Bridge Pro | 통과 | 2개 파일, ZIP/EXE 해시 및 active/receipt 일치 | journal 0, 복구 대기 없음 |
| Pivot_Fixer | 통과 | 긴 경로에서는 실패, 짧은 비교 경로에서 1,071개 파일과 해시 일치 | 성공 설치는 journal 0·복구 대기 없음. 최초 실패 자료 별도 보존 |
| ase_viewer B안 | 통과 | 3개 파일, 원본 EXE 해시 및 active/receipt 일치 | journal 0, 복구 대기 없음 |

각 성공 설치 뒤 합성 작업 메모를 별도 시험 데이터 영역에 작성했다. `Installer.recover()`를 정상 완료 상태에서 한 번 호출하고 설치 파일·메타데이터·합성 메모의 전체 해시가 유지되는 것을 확인했다. 이는 **정상 상태에서 복구 호출이 불필요하게 변경하지 않는다는 검사**다. 새 버전 업데이트 시 preserve_paths 이전, 실제 사용자 데이터, 전원 종료·파일 잠금·복구 실패는 이번에 검증하지 않았다.

실행 방지용 `Processes.start()` 경계를 두고 호출되면 즉시 실패하도록 했다. 설치 과정의 실제 프로세스 조회는 기존 구현을 사용했다. 실행 파일의 존재·해시·작업 디렉터리를 확인하는 `resolve_launch()`는 프로세스를 생성하지 않는다. 네 후보의 EXE는 모두 실행하지 않았다.

## 6. Pivot_Fixer 긴 경로 실패

최초 실패는 Installer의 `extract_checked()`에서 `tkinterdnd2/tkdnd/linux-arm64/tkdnd_generic.tcl`을 생성하는 단계의 **FileNotFoundError / errno 2**다. journal 교체 WinError 5와 구분한다. 처음 만든 설치 루트가 길어 전체 파일 경로가 260자에 도달했다.

같은 Python에서 별도 합성 파일로 비교했다. 261자 일반 경로 생성은 errno 2로 실패하고, 동일 경로의 Windows 확장 경로 표기는 성공했다. 이어 제품 코드·정책·ZIP을 바꾸지 않고 짧은 `C:\Dev\cgl-candidate-checks-20261106`에서 Pivot_Fixer를 한 번 비교 설치했으며 통과했다. 반복 실행으로 우연히 통과한 결과가 아니라 경로 조건을 바꾼 비교다. 확장 경로 표기를 제품 엔진에 추가하지 않았다.

최초 실패 설치는 엔진이 미완료 파일 21개를 자기 `recovery/`에 보존했다. 활성 포인터는 없고 journal은 정상 실패 처리 뒤 0개다. 이 폴더와 오류 로그를 삭제·복구·재설치하지 않았다.

**긴 설치 루트 제약은 새로 관측한 배포 전 확인 항목이다.** 짧은 경로 성공을 모든 직원 경로에서의 성공으로 확대하지 않는다. 직원 기본 데이터 경로 및 최장 패키지 경로에서 검증하거나, 필요 시 별도 범위에서 경로 처리의 최소 변경을 검토해야 한다. 이번에는 제품 코드를 수정하지 않았다.

## 7. B안 기능 손실과 최소 후속 제안

EXE가 동일하므로 EX1/EX2 버튼 코드는 남는다. 기존 기준 소스에서 버튼 그리기(9620~9622행), 입력 처리(9745~9747행), `_prepare_example()`의 누락·해시 검사와 `_load_example()`의 오류 처리(7533~7634행)를 확인했다. 필요한 외부 예제 파일이 후보에 없으므로 정상 예제 적용은 불가능하다.

코드상 예상 동작은 버튼 표시 → 예제 파일 누락 안내 → 현재 프로젝트 유지다. **이번에 EXE를 실행해 버튼 화면이나 오류 창을 직접 관측하지는 않았다.** 기존 정적 의존성 분석과 동일 EXE의 과거 무예제 검사 기록을 재사용했다. 따라서 예제 기능이 완성됐거나 기본 GUI·사용자 파일 작업이 실기동 검증됐다고 표시하지 않는다.

최소 후속 선택지는 다음과 같다.

1. B안의 기능 축소를 수용하고 별도 실행 승인 범위에서 기본 시작·사용자 소유 파일·종료·예제 누락 시 기존 합성 프로젝트 유지 여부를 실제 확인한다.
2. 사용자가 누를 수 없는 상태를 원한다면 원본 프로젝트의 EX1/EX2 두 버튼 표시·입력 경로만 비활성화하고 이유를 안내하는 최소 변경·재빌드가 필요하다. 이번에는 하지 않았다.
3. 예제를 계속 제공하려면 공개 허가를 받은 대체 자산, 고정 해시, 태그·프로필 매핑과 예제 테스트를 함께 변경해야 한다. 원본 이름의 자산만 교체해서는 기존 해시 검사를 통과하지 못한다.

## 8. 남은 승인·검증과 보존

- 세 프로그램의 공개 배포 승인, 운영 키의 별도 생성·보관·백업·신뢰키 채택, 실제 증가 순번·서명 및 게시 직전 전체 자산 검증이 필요하다. 현재 미서명 초안은 직원용 Provider에서 설치할 수 없다.
- B안은 후보일 뿐이며 회사 승인본으로 승격하지 않았다. 실제 실행·기능 축소 수용 또는 최소 UI 수정·재빌드 결정이 남는다. TagMaster는 계속 제외한다.
- 긴 경로 제약과 기존 journal/폴더 WinError 5는 배포 전 안정성 항목으로 남는다. 이번 검사에서 WinError 5는 발생하지 않았으나 근본 원인 해결을 뜻하지 않는다.
- 전체 테스트는 불필요하게 반복하지 않았다. 기존 243개 중 242개 통과·1개 오류라는 미합격 결과를 유지한다. 이번 파일 기반 검사는 전체 회귀 합격을 대체하지 않는다.
- 제품 코드·기존 다섯 프로젝트·원본 승인 ZIP 4개·기존 시험 기록을 보존한다. GitHub Release·운영 키·실제 AppData·SAC·ACL·방화벽·LAN 설정을 변경하지 않았다.
- 사후 파일·Git 대조 결과는 기준 폴더의 `preservation-after.json`, `existing-projects-after.json`, `git-after.txt`에 별도 기록한다. stage/commit/push 및 remote 변경은 하지 않았다.

사후 대조에서 기존 6,923개 파일의 변경·누락은 0개였고, 산출물 manifest의 크기·해시도 모두 일치했다. 외부 다섯 프로젝트 292개 파일과 HEAD·태그·Git 상태, 원본 승인 ZIP 4개는 동일했다. 런처 Git은 master / HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5` / remote 없음 / staging 없음을 유지한다. 기존 미커밋 상태의 삭제·변경 없이 이 보고서만 새 미추적 문서로 추가됐다.
