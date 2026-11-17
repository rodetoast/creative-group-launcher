# 최신 배포본 확인과 로컬 버전 선택

조사일은 2026-11-10이다. 아래 추천은 확인 가능한 완성본을 기준으로 한다. 회사 게시 승인과 실제 배포본 교체는 별도 결정이다.

| 프로그램 | 기존 런처 후보 | 확인한 최신 완성본 | 해시 대조 | 판단 |
|---|---|---|---|---|
| TileNamer | 0.1.6 RC3 | 0.1.6 RC3 | ZIP·EXE 일치 | 기존 후보 유지 |
| ase_viewer | 0.5.8.3 내부 예제 포함 | 0.5.8.4 내부 예제 포함 | ZIP·EXE 모두 다름 | 내부 배포 교체 후보. 공개용은 0.5.8.4 기준 별도 검토 |
| AsepriteTagMaster | 0.4.0 메타데이터만 등록 | 0.4.0, 빌드 7263f8d | 사전에 기록된 ZIP·EXE 해시와 일치 | 실물 확인. 런처 게시 상태 변경에는 승인 필요 |
| Ase-PS Bridge Pro | 0.3.6 | 0.3.6 | ZIP·EXE 일치 | 기존 후보 유지. 0.3.7은 최종 패키지 미확정 |
| Pivot_Fixer | 0.3.3 | 0.3.3 | ZIP·EXE 일치 | 기존 후보 유지. 긴 설치 경로 검증 필요 |

ZIP·EXE 49건의 정확한 경로, 크기, SHA-256, ZIP 항목 목록, 내부 EXE 해시, 경로·CRC 검사 결과는 [전체 인벤토리](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/latest-build-audit-20261110/build-inventory.json>)에 있다. 과거 버전과 동일 바이트의 복사본도 포함한다. TagMaster 프로젝트에 있는 캐릭터 작업용 ZIP은 앱 EXE가 없어 배포 후보에서 제외했다.

## 프로젝트별 근거

아래 경로의 공통 사용자 폴더는 `C:\Users\SOUTHPAW GAMES`다.

### TileNamer

- 프로젝트 `Desktop\TileNamer`. 로컬과 GitHub main의 HEAD는 `8ba7a1e47d84888c06ea3913482c79db9b72eb02`이며 로컬 태그는 `v0.1.6`이다. RC3에서 패키징 리소스를 수정했다. 런처 release_id는 `0.1.6-rc3-8ba7a1e`다.
- 원본 `Desktop\TileNamer\release\TileNamer_v0.1.6_RC3_win64.zip`, 54,046,715바이트. ZIP SHA-256 `aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4`. 내부와 `dist\TileNamer.exe`의 EXE SHA-256 `0d8f758fa17b821b1add4d4259aa98f3f30f06a1bd4d0ba17c1a236835dc2349`.
- Codex의 RC3 전달 기록과 패키지 릴리스 문서가 같은 파일을 가리킨다. 문서에 저장소 밖에서 MainWindow·카테고리 트리를 확인한 기록이 있다. 현재 작업 트리의 배치 창·환경설정·테마·가이드 변경은 별도 신규 ZIP과 연결되지 않았다. 사용자 참고 버전과 일치한다.

### ase_viewer

- 프로젝트 `Desktop\AI`. HEAD `54b76757ae62a18fc48f5d06f7f0c63fdae913ac`는 생성물 정리 커밋이다. 기존 승인본 빌드는 태그 `v0.5.8.3`의 `7841e60fe3d4bb908a0c5f1b488049f9fa2ba63f`, 런처 release_id는 `0.5.8.3-team-7841e60`이다.
- 기존 승인 원본 `Desktop\AI\ase_viewer_v0.5.8.3_with_examples.zip`, 20,612,661바이트. ZIP SHA-256 `7f5d7b75014cc355d5dc7d06499429b3be7a3342fe8514871c4ce57622dd05b8`, EXE SHA-256 `299ef579a110c76c85a4122a6363b81e9360a41957e2d2ad7efe001f877d0dbf`.
- 발견 원본 `Desktop\AI\ase_viewer_v0.5.8.4_with_examples.zip`, 22,085,231바이트. ZIP SHA-256 `2532c273c4cf9930cf882ef1f84cae55c9a97479a69123431560b1299edec2d2`. 내부와 `dist_v0.5.8.4\ase_viewer.exe`의 EXE SHA-256 `3bf37ddde0c1666e133d0ee1f2da9d1118f4f92cd5799a392097cc83d67cc233`. 두 값은 릴리스 문서의 빌드 기록과 일치한다. 독립된 런처 release_id는 아직 없다.
- v0.5.8.4의 실제 변경은 F9 체력 회복, 준비·회복 태그의 공격 판정 차단, 실행 아이콘 적용이다. 릴리스 문서에는 소스 테스트 429개와 선택 테스트 1개 건너뜀, 동결 EXE 검사·사이드바 검사 성공이 기록돼 있다. 이후 아이콘·공격 타이밍 보완과 v0.5.8.5 뷰포트 인스펙터는 소스 변경으로만 남았다. v0.5.8.5 문서는 EXE·ZIP을 만들지 않았다고 기록한다. 참고 목록의 0.5.8.3보다 새 완성본이 존재한다.
- 기존 B안 ZIP SHA-256 `ec887d27f2631671b66d3b5cc362994025128a16e4f70917ecb9ea05cadf1e92`는 v0.5.8.3 EXE를 그대로 쓴 예제 제외 후보이다. v0.5.8.4의 수정 사항을 담고 있지 않다. v0.5.8.4도 내부 예제를 포함한다. 공개 후보를 갱신하려면 v0.5.8.4 기준으로 외부 예제·문서·필수 경로를 따로 검토하고 기능 손실과 실기동을 확인해야 한다.

### AsepriteTagMaster

- 프로젝트 `Desktop\AsepriteTagMaster_Source`. HEAD·로컬 태그 `v0.4.0`은 `7263f8d6107be76363d329c6962cd46dd15d4068`을 가리킨다. 런처 예약 release_id는 `0.4.0-team-7263f8d`다.
- 실제 ZIP `Downloads\AsepriteTagMaster_v0.4.0_20260710_7263f8d.zip`, 38,813,495바이트. ZIP SHA-256 `80865038ddab9a1b9050d04cbb48cb777edf4e6419caafb05b8b51c0f6962299`. 내부 EXE SHA-256 `5b55cff02880d5c02ac7f1c2c323b8125273f056f8a774beb246cc0d4dd0aee6`. 두 값 모두 기존 `tools/import_approved.py`에 기록한 기대값과 일치한다. 현재 카탈로그에는 실제 게시 패키지로 등록되지 않았다.
- ZIP은 EXE·`custom_dictionary.json`·`VERSION.txt`를 포함하며 내부 버전 기록이 7263f8d를 명시한다. EXE는 원본 프로젝트 `dist\AsepriteTagMaster.exe` 및 아카이브의 v0.4.0 릴리스 폴더와 대조했다. ZIP 경로·CRC 검사도 통과했다.
- 기존 Codex 기록은 v0.4.0 기준 구문 검사와 fuzz·bug·stability 테스트 통과를 기록한다. 현재는 분할 엔진·대화상자·테스트가 작업 트리에 남아 있다. 이를 포함한 새 ZIP을 확인하지 못했다. 원격 HEAD `d4ef09394b9faf575570eb9799990ac1e8a4ce2a`의 로컬 대비 변경 범위도 확인하지 못했다. 사용자 참고 버전과 일치하며, 게시 전에 발견한 원본의 사용 승인을 확인해야 한다.

### Ase-PS Bridge Pro

- 프로젝트 `Desktop\AI TS`. 로컬 HEAD·태그 `v0.3.6`은 `6e846459cb240ab5942e2ffa65d3b51d64648972`다. Folder to Frames의 폴더 선택 처리 수정에 해당한다. 런처 release_id는 `0.3.6-team-6e84645`다.
- 원본 `Desktop\AI TS\dist\Ase-PS-Bridge-Pro_v0.3.6_Windows.zip`, 66,252,089바이트. ZIP SHA-256 `1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9`. 내부와 `dist\bridge_ui.exe`의 EXE SHA-256 `203c7fffe32726b7851edf0ad3e20d1bf1963f10124deb976992895dd21584fe`. 사용자 참고 버전과 일치한다.
- v0.3.7 문서와 Codex 기록에는 Photoshop 원본 보호, 시작 화면 및 복사 진단 보완과 소스 테스트 111개 통과가 있다. 최종 빌드와 수동 검증은 보류됐다. 현재 `dist`의 EXE는 v0.3.6 ZIP과 일치한다. 원격 HEAD `83892850446375c9716d08ff142b853f0596a655`와 로컬의 변경 범위는 확인하지 못했다.

### Pivot_Fixer

- 프로젝트 `Desktop\Pivot Fixer`. HEAD·태그 `v0.3.3`·원격 main은 `80b84c99f6e9865beb26d8b184e8d400781e9d07`로 일치하고 작업 트리는 깨끗하다. 런처 release_id는 `0.3.3-team-80b84c9`다.
- 원본 `Desktop\Pivot Fixer\dist\Pivot_Fixer_v0.3.3.zip`, 20,709,116바이트. ZIP SHA-256 `214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361`. EXE SHA-256 `620c7dffb32810fc6427b57ed467ba042b6e2893afc21b03b70a79f1218c295b`. 릴리스 문서, ZIP, dist EXE가 일치한다.
- Aseprite 파일과 PNG의 혼합 드롭 분리 및 연동도구 창 개선이 들어 있다. 수동 실행·드롭 확인은 릴리스 기록을 근거로 했다. 다운로드 폴더의 v0.3.1은 이전 버전이다. 사용자 참고 버전과 일치한다.

## 원격·개발 기록 범위

GitHub API 읽기 전용 조회에서 다섯 소스 저장소의 Release 목록은 모두 비어 있었다. Bridge Pro와 TagMaster는 GitHub HEAD가 로컬과 달랐고 비교 API는 404를 반환했다. 원격의 변경 범위나 완성 파일을 추측하지 않았다. 배포 저장소에는 서명된 카탈로그와 더미 ZIP만 들어 있는 `catalog-000001`~`catalog-000003` 세 릴리스가 있었다. [GitHub 배포 릴리스](https://github.com/toast-source/creative-group-releases/releases)

사용자 참고 표는 확보했다. 연결 문서 URL과 원본 이미지 데이터가 제공되지 않았고 이 세션에 Notion 읽기 도구가 없어 링크가 가리킨 원본과 같은 파일인지 직접 확인할 수 없었다. TagMaster는 다운로드 파일의 내부 메타데이터와 기존 기록 해시로 별도 확인했다. 확인한 Codex 기록의 관련 줄은 `.test-results/latest-build-audit-20261110/codex-release-mentions.json`에 있다. Codex 메시지가 없거나 별도 기기의 기록만 있는 경우 프로젝트 릴리스 문서·handover·Git 기록을 근거로 삼았다.

## 로컬 선택과 복구

- 런처의 **설치된 버전 선택**에서 현재 버전과 release_id를 확인하고, 보관된 다른 버전을 고른 뒤 확인한다. 최신 배포본은 기존 카탈로그와 업데이트 상태로 별도 표시한다. 사용자가 구버전을 선택한 동안 자동 목록 조회는 활성 버전을 바꾸지 않는다. 이미 설치된 최신판도 대화상자에서 선택할 수 있다.
- 서명 검증을 거친 새 설치에는 서명 카탈로그 증거와 원본 ZIP을 해당 릴리스에 보관한다. 같은 릴리스의 receipt, 현재 신뢰 키로 검증한 메타데이터, ZIP 크기·SHA-256, ZIP에서 계산한 파일 해시, 설치 파일·EXE·필수 경로를 대조한다. 보관 증거가 없는 기존 릴리스는 선택 목록에서 제외한다. 버전당 원본 ZIP 용량만큼 디스크 사용량이 증가한다.
- 전환은 앱 잠금을 획득하고 실행 중인지 확인한 뒤 기존 journal을 사용해 `active.json`과 선택 유지 표시를 한 번에 원자적으로 바꾼다. 기록 전 중단이면 이전 포인터가 그대로 남는다. 기록 후 journal 정리 전에 중단되면 복구 시 선택 대상을 재검증한다. 손상된 경우 이전 포인터를 복원하며, 포인터가 기록과 모두 다르면 복구를 보류한다.
- 전환에서는 설정이나 작업 파일을 복사·변환하지 않는다. 각 버전은 자신의 폴더 데이터를 사용한다. 검증은 등록된 `preserve_paths`의 지원 데이터 형식 변경을 허용하되 EXE와 필수 경로의 무결성을 요구한다. 그 밖의 추가·변조 파일이나 링크가 있으면 전환을 막고 파일을 보존한다. 프로그램이 다른 버전과 공용으로 쓰는 외부 파일의 형식 호환성은 별도 확인이 필요하다.
- 과거 설치 증거의 검증은 로컬 파일 선택에만 사용한다. 현재 카탈로그 최고 순번과 캐시는 변경되지 않는다.

## GitHub 과거판 다운로드 설계

현재 검증기는 v1 카탈로그 키 집합을 정확히 검사한다. 호환성을 유지하는 최소안은 같은 최신 Release에 별도의 서명된 `history.json`과 서명 자산을 추가하는 방식이다. 내역 문서는 전용 서명 도메인, 현재 카탈로그 원문 SHA-256과 순번, 승인된 과거판의 전체 AppRelease를 담는다. 새 클라이언트는 정상 최신 카탈로그 수락 후 같은 Release의 내역 서명과 바인딩을 확인한다. 과거 ZIP도 해당 Release에 포함하고 이름·크기·digest와 내려받은 SHA-256을 검사한다. 지원 자산 수 한도 안에서 보존할 버전을 관리한다.

관리자 게시 단계에는 과거판 승인·제거 선택과 불변 release_id 충돌 검사, 전체 자산 업로드·검증, 현재 목록과 내역의 일치 확인이 추가된다. 기존 클라이언트는 기존 v1 카탈로그를 사용한다. 새 클라이언트는 사용자가 명시적으로 선택한 경우에만 과거판을 설치한다. 과거 Release의 낮은 순번을 수락하는 경로는 필요하지 않다. 이 작업에서 원격 다운로드는 구현하지 않았다.

## 검증과 변경 범위

기존 243개와 신규 9개를 포함한 **252개 테스트가 모두 통과**했다. 실제 Windows Bootstrap 검사는 해시가 일치하는 기존 시험용 더미 파일만 사용했다. 신규 검사는 오프라인 r1 → r2 설치·업데이트 후 r2 → r1 → r2 선택, GUI 확인 취소와 승인, 파일·receipt 변조, 실행 중 차단, 원자 교체 실패, 중단 뒤 복구, 합성 작업 데이터 보존과 다른 앱 포인터 보존, 서명 최고 순번 유지 및 재전송 차단을 포함한다.

첫 전체 회귀에서 설치 버전 표시 문구 변경으로 기존 GUI 단언 두 개가 실패했다. 기존 표시를 복원하고 release_id는 도구 설명과 버전 선택 창에 표시하도록 수정했다. 샌드박스 소켓 오류 다섯 건은 로컬 루프백이 허용된 시험 환경에서 재검증했다. 최종 회귀의 잠금 주입 테스트는 예상대로 처리됐다. 간헐적 WinError 5는 근본 원인 미확정 상태다. [최종 전체 회귀 로그](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/latest-build-audit-20261110/full-suite-final.log>)

변경 파일은 `southpaw_tools/catalog_trust.py`, `southpaw_tools/installer.py`, `southpaw_tools/ui.py`, 신규 `tests/test_local_versions.py` 및 이 보고서다. 조사·검증 산출물은 `.test-results/latest-build-audit-20261110/`에 분리했다.

사후 대조에서 후보 ZIP·EXE 49개와 기존 시험 증거 6,712개가 해시까지 일치했다. 다섯 프로젝트의 HEAD·브랜치·태그·작업 트리 상태 및 origin 주소도 시작 기록과 일치했다. 런처는 `master`의 `32afb846d0bc69b38203a259dad71180cd4a14b5`를 유지한다. 기존 작업 트리 상태 항목을 보존했고, 새 미추적 항목은 이 보고서와 신규 테스트 파일 두 개다. 스테이지와 remote는 비어 있다. [보존 대조 결과](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/latest-build-audit-20261110/preservation-after.json>)

직원 배포 전에는 후보 승인, 실제 회사 프로그램의 별도 실기동·작업 데이터 호환성 확인, Pivot_Fixer 기본 설치 경로에서의 긴 파일 경로 검증, 운영 신뢰 키 채택이 남는다. 이번 검증에서 기존 후보와 게시 상태를 유지했으며, 회사 프로그램 EXE와 실제 직원 설치 데이터는 검사 대상에서 제외했다.
