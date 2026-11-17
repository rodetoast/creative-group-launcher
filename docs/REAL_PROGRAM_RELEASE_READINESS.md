# 실제 프로그램 GitHub 배포 준비 점검 — 2026-11-06

## 판정

**네 승인 ZIP은 기존 Installer가 사용하는 안전 추출 및 관리자 GUI 검사 입력으로 적합하다. 실제 공개·직원 배포는 아직 준비 완료가 아니다.** 운영 키 미채택, 공개 범위 승인·예제 자산 검토, 관리자 운영 게시 잠금, 전체 회귀 미합격이 남아 있다. 제품 코드를 수정하거나 운영 키를 생성하지 않았다.

현재 GitHub를 읽기 전용 조회한 결과 대상은 toast-source/creative-group-releases, Public이며 Latest는 catalog-000003이다. 공개 r1/r2/r3와 각 자산 ID·이름·크기·digest는 기존 증거와 일치했다. 실제 회사 ZIP을 업로드하지 않았다.

## 1. 승인 ZIP 개별 결과

### TileNamer

- 원본: `C:\Users\SOUTHPAW GAMES\Desktop\TileNamer\release\TileNamer_v0.1.6_RC3_win64.zip`
- 버전 / release_id: `0.1.6 RC3` / `0.1.6-rc3-8ba7a1e`
- ZIP: 54,046,715바이트, 항목 3개 / 파일 3개
- ZIP SHA-256: `aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4`
- EXE 상대 경로: `TileNamer.exe`
- EXE SHA-256: `0d8f758fa17b821b1add4d4259aa98f3f30f06a1bd4d0ba17c1a236835dc2349`
- PE machine: `0x8664`, Windows PE 확인
- 카탈로그/승인 목록 대조, CRC를 포함한 기존 안전 추출, 필수 경로, 관리자 GUI ZIP 검사 함수: 모두 통과
- 런타임 정적 존재 검사: python312.dll: 확인; Qt6Core.dll: 확인; Qt6Gui.dll: 확인; Qt6Widgets.dll: 확인; qwindows.dll: 확인; tile_names.json: 확인
- EXE 실행 및 실제 DLL 로드·앱 기능 검증: 미실시

### ase_viewer

- 원본: `C:\Users\SOUTHPAW GAMES\Desktop\AI\ase_viewer_v0.5.8.3_with_examples.zip`
- 버전 / release_id: `0.5.8.3` / `0.5.8.3-team-7841e60`
- ZIP: 20,612,661바이트, 항목 17개 / 파일 14개
- ZIP SHA-256: `7f5d7b75014cc355d5dc7d06499429b3be7a3342fe8514871c4ce57622dd05b8`
- EXE 상대 경로: `ase_viewer.exe`
- EXE SHA-256: `299ef579a110c76c85a4122a6363b81e9360a41957e2d2ad7efe001f877d0dbf`
- PE machine: `0x8664`, Windows PE 확인
- 카탈로그/승인 목록 대조, CRC를 포함한 기존 안전 추출, 필수 경로, 관리자 GUI ZIP 검사 함수: 모두 통과
- 런타임 정적 존재 검사: python312.dll: 확인; tcl86t.dll: 확인; tk86t.dll: 확인
- EXE 실행 및 실제 DLL 로드·앱 기능 검증: 미실시

### Ase-PS Bridge Pro

- 원본: `C:\Users\SOUTHPAW GAMES\Desktop\AI TS\dist\Ase-PS-Bridge-Pro_v0.3.6_Windows.zip`
- 버전 / release_id: `0.3.6` / `0.3.6-team-6e84645`
- ZIP: 66,252,089바이트, 항목 2개 / 파일 2개
- ZIP SHA-256: `1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9`
- EXE 상대 경로: `bridge_ui.exe`
- EXE SHA-256: `203c7fffe32726b7851edf0ad3e20d1bf1963f10124deb976992895dd21584fe`
- PE machine: `0x8664`, Windows PE 확인
- 카탈로그/승인 목록 대조, CRC를 포함한 기존 안전 추출, 필수 경로, 관리자 GUI ZIP 검사 함수: 모두 통과
- 런타임 정적 존재 검사: python312.dll: 확인; Qt6Core.dll: 확인; Qt6Gui.dll: 확인; Qt6Widgets.dll: 확인; qwindows.dll: 확인
- EXE 실행 및 실제 DLL 로드·앱 기능 검증: 미실시

### Pivot_Fixer

- 원본: `C:\Users\SOUTHPAW GAMES\Desktop\Pivot Fixer\dist\Pivot_Fixer_v0.3.3.zip`
- 버전 / release_id: `0.3.3` / `0.3.3-team-80b84c9`
- ZIP: 20,709,116바이트, 항목 1073개 / 파일 1071개
- ZIP SHA-256: `214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361`
- EXE 상대 경로: `Pivot_Fixer_v0.3.3/Pivot_Fixer_v0.3.3.exe`
- EXE SHA-256: `620c7dffb32810fc6427b57ed467ba042b6e2893afc21b03b70a79f1218c295b`
- PE machine: `0x8664`, Windows PE 확인
- 카탈로그/승인 목록 대조, CRC를 포함한 기존 안전 추출, 필수 경로, 관리자 GUI ZIP 검사 함수: 모두 통과
- 런타임 정적 존재 검사: python313.dll: 확인; tcl86t.dll: 확인; tk86t.dll: 확인
- EXE 실행 및 실제 DLL 로드·앱 기능 검증: 미실시

### 패키지별 해석과 부족 항목

- **TileNamer**: onefile 내 Python 3.12·Qt6Core/Gui/Widgets·qwindows, tile_names.json, guides/manifest.json과 아이콘을 확인했다. 외부 ZIP은 EXE와 문서 2개다. 현재 정적 범위에서 개인 설정·토큰·개발 빌드 파일 후보는 발견하지 않았다. 실제 실행, 외부 연동, 번들 의존성의 공개 배포 고지는 별도 확인이 필요하다.
- **ase_viewer**: Python 3.12·Tcl/Tk와 지정된 외부 예제 리소스 10경로를 확인했다. ZIP에는 캐릭터 .aseprite 원본 2개와 배경 PNG 7개가 있다. `resources/examples/README.md:5`, `README.md:53`에 로컬 사용자 절대 경로가 남아 있다. 사용자명 원문은 이 보고서에 재출력하지 않는다. 예제 README는 회사 내부 제작 작업용 자원이라고 명시한다. 파일 이름에 Public이 있다는 것만으로 공개 권리가 확인되는 것은 아니다. **이 승인본을 그대로 Public 저장소에 올리는 것은 보류해야 한다.** 예제 공개 권리와 문서 노출 허용 여부를 담당자가 확인해야 하며, 정리가 필요하면 별도 수정·재승인된 ZIP이 필요하다. 이번에는 원본을 수정하지 않았다.
- **Ase-PS Bridge Pro**: Python 3.12·Qt/qwindows·bridge_icon.ico와 scripts/aseprite_copy.lua, aseprite_paste.lua, photoshop_copy.jsx, photoshop_paste.jsx를 확인했다. numpy LICENSE.txt는 있으나 이것만으로 전체 번들 고지가 충족됐다고 판단하지 않는다. Photoshop/Aseprite 및 스크립트 설치·신뢰 설정의 실제 동작은 미검증이다.
- **Pivot_Fixer**: onedir 전체 Python 3.13·Tcl/Tk·tkinterdnd2 및 Windows x64 libtkdnd2.9.5.dll을 확인했다. 원본 ZIP의 역슬래시 경로는 기존 검증기의 정규화로 통과하며 바이트는 변경하지 않았다. 다른 OS/아키텍처의 TkDnD 벤더 파일도 포함되나 개인 파일이나 앱 개발 산출물로 판정하지 않았다. 이번에 삭제·최적화하지 않는다. 실제 드래그앤드롭·설정 경로는 앱 실행 승인 후 별도 확인이 필요하다.
- **AsepriteTagMaster**: 지정 승인 ZIP 미확인, published=false·게시 불가 유지. 대체 EXE나 최신 소스로 ZIP을 만들지 않았다.

네 EXE 모두 PE certificate table이 없어 내장 Authenticode 서명은 확인되지 않았다. 외부 카탈로그 서명과 Windows 실행 정책은 별개이며, 직원 PC의 SAC 허용을 보장하지 않는다. Windows 카탈로그 서명/평판까지 조회한 결과는 아니다.

### 민감정보·개발 산출물 검사 범위

원본 ZIP 전체 목록, 텍스트·JSON·설정·스크립트, PyInstaller CArchive 목록과 읽을 수 있는 리소스/진입 스크립트 데이터를 검사했다. 실제 비밀 값은 로그에 출력하지 않고 규칙 종류·파일명·건수만 기록했다.

- 검사 범위에서 private key 블록·GitHub 토큰·AWS 키·긴 자격정보 할당 문자열은 발견하지 않았다.
- ZIP/내장 목록의 .env·개인키·인증 파일·Git/venv·PDB/spec·백업/로그 후보 검사에서 해당 후보는 없었다.
- Pivot의 Python 소스 2개는 tkinterdnd2 벤더 런타임이다. 앱의 미커밋 개발 소스를 자동 수집한 것이 아니다.
- 확인한 라이선스 이름은 ase_viewer/Pivot의 Tcl/Tk license.terms, Bridge의 numpy LICENSE.txt 등이다. 전체 라이선스 충족 여부는 미확정이다.
- **내장 PYZ 전체 바이트코드의 모든 문자열·암호화/난독화 데이터·이미지 내부 정보·악성 동작·모든 개인정보를 확인한 것은 아니다.** 정적 검색 무검출을 비밀정보 부재나 공개 안전 인증으로 표시하지 않는다.

감사 도구 첫 실행에서 CArchiveReader 속성명이 맞지 않아 내장 목록 요약이 실패했다. 외부 ZIP 검사는 통과한 상태였으며, 실제 reader API에 맞춘 별도 읽기 전용 보완 검사로 네 내장 목록·리소스를 확인했다. 초기 로그를 지우지 않았고 최종 결과는 package-audit-complete.json이다. 제품 결함으로 분류하지 않는다.

## 2. 테스트/운영 카탈로그 분리

기존 catalog_id와 schema, AppRelease, Ed25519, sequence 방어, Installer를 그대로 유지하는 최소 방안:

1. 운영 준비 폴더는 .test-results 및 기존 distribution과 별도로 두고, 원본은 읽기만 한다. 이번에 실제 운영 저장소나 운영 카탈로그를 생성하지 않았다.
2. 운영 카탈로그는 다섯 앱의 메타데이터를 유지하되 네 앱만 published=true, TagMaster는 false로 둔다. Dummy Tool을 포함하지 않는다. 기존 승인 version/release_id/패키지·EXE 해시·required/preserve 목록을 재사용한다.
3. 한 Release에 catalog.json, catalog.sig.json, 네 승인 ZIP의 원본 바이트를 담는다. **총 자산 6개**, ZIP 합계 161,620,581바이트다. 게시 자산 이름은 기존 app_id--release_id.zip 규칙을 따른다. 원본 파일을 이동·수정하지 않는다.
4. 현재 Provider는 한 저장소의 `/releases/latest`와 그 Release 내부 자산만 지원한다. 따라서 운영 전체 목록과 테스트 전체 목록을 같은 저장소의 독립 Latest로 동시에 운영할 수 없다. 이전 r1/r2/r3는 그대로 보존하고, 실제 공개 승인 이후에만 새 운영 Release가 Latest를 대체한다. 계속 더미 시험을 병행할 필요가 생기면 시험용 별도 저장소가 별도 승인 사항이다. 채널 시스템을 새로 만들 필요는 없다.
5. 바뀌지 않은 ZIP도 해당 운영 Release에 같은 바이트로 첨부한다. 현재 Provider에 과거 Release 자산 URL을 참조하는 우회는 없다. 네 ZIP 규모에서는 이 방법이 가장 적은 변경이다.
6. 같은 catalog_id로 전환한다면 최종 운영 sequence는 현재 3보다 크게 정하고, 운영 직원용 정책 minimum_sequence도 최종 승인 순번과 맞춘다. 시험 신뢰 상태/키를 직원 데이터 루트로 복사하지 않는다.
7. admin.publish는 앱 하나마다 sequence를 증가시킨다. 예를 들어 로컬 초기 기준 3에서 네 앱을 각각 게시하면 4→5→6→7이고 최종 묶음 순번은 7이다. 실제 마지막 서명 순번에 tag를 맞춰야 하며 무조건 catalog-000004라고 정하면 안 된다. GUI의 검증된 초기 카탈로그 준비에 순번을 더 사용하면 최종 순번도 달라진다. 이번에는 순번을 소비하거나 서명하지 않았다.
8. 초안에 자산 전체를 준비한 뒤 재다운로드·해시·서명을 확인하고 정식 공개한다. GitHub도 초안 상태에서 자산을 준비하는 흐름을 지원한다. [GitHub 공식 Release 관리](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)

현재 저장소는 Public이다. 내부 승인 ZIP이라는 사실은 인터넷 공개 승인과 다르다. 회사가 사내 전용 배포를 요구한다면 현재 무인증 Public Provider 모델만으로는 충족할 수 없다. 임의로 비공개 전환하거나 직원 PAT를 추가하지 않는다. [GitHub 공개 범위 안내](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)

## 3. 운영 키에 필요한 최소 결정

- 회사가 키 소유자·게시 담당자·승인된 저장소/공개 범위·첫 운영 sequence를 확정한다. 현재 시험 키를 재사용하지 않는다.
- 승인 이후 기존 cryptography Ed25519 방식으로 운영 키 1개를 생성하고 공개키 지문을 별도 경로로 대조한다. 공개키만 직원 제품에 사전 탑재한다. 네트워크에서 받은 키를 자동 신뢰하지 않는다.
- 개인키 작업 사본은 프로젝트/Git/공개 배포/서버 디렉터리 밖의 승인된 관리자 보관 위치에 둔다. GUI 설정이나 로그에 복사하지 않는다. 기존 회사 정책에 따른 접근 제한을 사용하며 이번에 ACL을 바꾸지 않는다.
- 현재 load_private는 password=None인 PEM만 읽는다. 암호화 PEM은 그대로 사용할 수 없다. 작업 파일과 별개로 회사가 승인한 암호화 오프라인 백업을 보관하고 복원·지문 일치를 점검하는 방안을 결정한다. 암호화 PEM 직접 입력을 요구한다면 기존 로더의 최소 보완과 검증이 먼저 필요하며 이번에 구현하지 않았다. [cryptography 50.0.2 키 로딩/암호화 형식](https://cryptography.io/en/50.0.2/hazmat/primitives/asymmetric/serialization/)
- 분실 시 백업 복원, 백업도 없으면 새 키와 새 직원용 신뢰 정책을 별도 배포한다. 이전 서명만으로 새 키를 자동 채택하지 않는다.
- 유출 의심 시 게시 중단, 새 키·최소 순번·직원용 신뢰 정책 교체를 승인 절차로 진행한다. 기존 공개키 목록은 여러 고정 키를 표현할 수 있지만, 무기한 구 키 신뢰를 유지하지 않는다.
- 정상 교체에서는 구/신 키 중첩 및 캐시 전환 시점을 정한다. 기존 신뢰 캐시 자체도 이전 키로 검증되므로 구 키 제거를 먼저 하면 업데이트 신뢰 상태를 읽지 못할 수 있다. 오프라인 구형 직원 PC를 포함한 전환/복구 확인이 필요하다. 이 부분을 원격 자동 키 교체 완료 기능으로 표시하지 않는다.

키 생성·등록·채택·서명 작업은 이번에 하지 않았다. Ed25519 카탈로그 서명은 게시자 검증이며 EXE 코드서명/SAC 문제를 해결하지 않는다.

## 4. 직원의 OWNER/REPO 입력을 없애는 최소 방안

운영 저장소와 키가 확정된 후, 제품에 공개 배포 채널 기본값(저장소 문자열)을 넣고 기존 connection_defaults가 **신규 또는 미지정 환경에서만** 적용하게 하는 작은 설정 변경이 적합하다. 이미 명시한 LAN/GitHub 설정은 덮어쓰지 않는다. 개인키/PAT는 넣지 않는다.

지금 --github-repository 옵션은 있지만 기존 설정을 메모리에서 우선 변경하므로 모든 기존 사용자에게 강제 옵션을 주는 방식은 설정 보존 원칙과 구분해야 한다. 운영 정책이 비어 있는 현재 기본값을 테스트 저장소로 채우지 않았다. 직원은 최종 승인된 제품에서 저장소를 직접 입력할 필요가 없도록 할 수 있지만, 현재 미채택 키 상태의 설치 잠금은 유지한다.

## 5. 관리자 GUI 재사용 범위와 실제 남은 제한

- 네 실제 ZIP을 격리된 **미서명·미게시 검사 fixture**에 대해 기존 AdminSession.inspect로 검사했다. ZIP 선택/해시·크기/EXE/경로/필수 파일/기존 extract_checked 경로는 네 개 모두 통과했다. 운영 카탈로그를 채택한 것이 아니며 키는 없다.
- 현재 AdminSession.review는 test_mode가 아니면 운영 키 미채택으로 차단한다. 시험 모드는 더미 해시만 허용한다. GitHubPublication의 실제 전송 권한도 Dummy ID·키·ZIP·새 tag 1개/3자산으로 제한돼 있다. **현재 GUI를 그대로 실제 네 ZIP 업로더로 사용할 수 없다.**
- 실제 ZIP 해시를 더미 허용 목록에 넣거나 시험 모드를 운영으로 위장하지 않는다. 운영 승인 후 기존 ZIP 검사/서명/게시 엔진 위에 승인된 운영 키 ID·저장소·최종 sequence·자산 6개를 검증하는 좁은 운영 경계만 연결하면 된다. 새로운 게시 엔진·인증 시스템은 필요하지 않다.
- 최초 운영 GUI 흐름에는 현재 카탈로그의 서명된 초기 상태도 필요하다. 미서명 검사 fixture를 운영에 그대로 사용하지 않는다. 기존 catalog_bytes/sign/admin.publish 함수로 승인 후 준비할 수 있다.
- GUI 검사 경로는 새 게시물의 build_id를 빈 값으로 만든다. 승인 build_id 보존이 필요한 경우 기존 CLI --build-id와 GUI 전달/미리보기를 확인하는 최소 보완이 필요하다. 기존 승인 ZIP이나 현재 카탈로그의 build_id는 이번에 변경하지 않았다.
- 기존 admin.publish CLI는 실제 app_id·EXE 해시·cwd·required/preserve·외부 서명키·증가 순번으로 재사용할 수 있다. 동일 release_id/패키지 덮어쓰기를 피하려면 처음부터 별도 운영 준비 폴더를 써야 한다. 이번에는 publish/review/업로드를 호출하지 않았다.

## 6. WinError 5와 배포 전 안정성 조건

최신 전체 회귀는 **243개 중 242개 통과, journal 오류 1개, 실패/skip 0개로 미합격**이다. 이번 작업은 읽기 전용 패키지 감사와 문서 검토라 제품 코드를 수정하거나 전체 회귀를 다시 돌리지 않았다. 정적 ZIP 검사 4개 통과를 전체 회귀 합격으로 바꾸지 않는다.

직원 배포 전 최소 확인:

1. 알려진 journal/folder 전환 실패의 원인·실패 후 상태를 근거로 정리하고 전체 회귀를 오류/실패/skip 없이 통과시킨다. 우연히 한 번 통과한 결과만으로 원인 해결을 선언하지 않는다.
2. 잠금·프로세스 중단·전원 중단에 대응하는 단계별 복구, 이전 active/receipt·사용자 데이터 보존, 제거 실패 복원을 격리 Windows 경로에서 확인한다. 소유한 시험 핸들/프로세스만 사용한다.
3. 실제 패키지 규모와 경로 특성에 대한 격리 설치·업데이트·중단 후 재시도, 합성 설정 보존을 별도 승인된 범위에서 검증한다. 현재는 실제 회사 EXE 실행을 승인받거나 수행한 것이 아니다.
4. 직원 PC의 코드서명/SAC·외부 Photoshop/Aseprite 의존성·한글/긴 경로·디스크/쓰기 권한·실행 중 업데이트를 확인한다. 보안 완화로 성공시키지 않는다.
5. 실패 시 자동 재시도·삭제로 숨기지 않고 로그·journal·다운로드·이전 설치를 보존하는 담당자 절차를 준비한다. 서명 게시 중간 실패의 카탈로그/서명 불일치는 성공으로 표시하지 않고 검증된 이전 쌍의 복구 절차를 확인한다.

## 7. 보존과 실행 기록

- 제품·설치·서명·GUI 소스 변경 없음. 원본 ZIP 재빌드·변경·이동 없음. EXE/스크립트 실행 없음(감사 Python 자체와 기존 도구의 파일 검사 함수만 실행).
- GitHub CLI GET 3회만 수행했으며 모두 종료 코드 0/HTTP 200. 외부 쓰기 없음.
- 원본 ZIP/기존 배포 복사본/기존 프로젝트 Git·파일 및 이전 시험 증거를 사후 대조해 동일함을 확인했다. 기존 5,697개 파일의 변경·누락은 없고 다섯 외부 프로젝트 292개 파일·Git 상태·HEAD·tag도 동일하다. 운영 키·실제 AppData·LAN/방화벽/SAC/ACL 변경 없음.
- Git master / HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5` / remote 없음 / staging 없음. 기존 미커밋 변경을 보존했고 새 프로젝트 파일은 이 보고서 하나다. 감사 증거는 Git 제외 .test-results 아래에만 생성했다.
- 원본 경로와 전체 ZIP·EXE 해시는 위 개별 결과에 기록했다. 세부 4개 파일 목록·내장 목록·민감정보 검사 결과는 .test-results/real-package-readiness-20261106/의 package-audit-complete.json 및 앱별 inventory JSON에 보존했다. 추출 파일은 감사 전용이며 설치본이 아니다.

## 8. 다음 단계에 필요한 최소 작업

1. Public 배포 범위와 예제 자산·문서 노출을 승인 담당자가 결정한다. 특히 ase_viewer는 내부 자원/사용자 경로 검토를 먼저 마친다. 수정 필요 시 새 승인 ZIP 절차를 따르며 원본은 보존한다.
2. WinError 5 안정성 미합격을 처리하고 운영 키·sequence·직원용 저장소 기본값을 결정한다.
3. 승인 이후에만 운영 키 생성·직원 신뢰키 채택 및 관리자 GUI의 좁은 운영 게시 경계를 연결한다.
4. 실제 업로드 전에 전체 6자산과 최종 서명 카탈로그를 검증한다. Draft/정식 공개·직원 배포는 별도 승인 후 수행한다.

이번에는 운영 키 채택·실제 회사 프로그램 공개·직원 배포·다음 기능 개발을 시작하지 않았다.
