# Southpaw Tools Launcher — v0.1.0 등록부

2026-11-03 KST. 사용자가 이번 개발 착수 요청에서 지정한 팀 승인 기준만 사용한다.
**최신 소스/원격 main이 배포 승인이라는 의미는 아니다.**
등록 정보: `distribution/catalog.json`, 초기 클라이언트 목록: `southpaw_tools/data/catalog.json`.

## 확정 대상

| app_id | 공식 표시 이름 | 승인 기준 | 로컬 개발 서버 등록 |
|---|---|---|---|
| tilenamer | TileNamer | v0.1.6 RC3 | published / 검증 ZIP 복사 |
| ase-viewer | ase_viewer | v0.5.8.3 with-examples | published / 검증 ZIP 복사 |
| tag-master | AsepriteTagMaster | 기존 v0.4.0 / 7263f8d | unpublished / 승인 ZIP 미확인 |
| ps2ase | Ase-PS Bridge Pro | v0.3.6 | published / 검증 ZIP 복사 |
| pivot-fixer | Pivot_Fixer | v0.3.3 | published / 검증 ZIP 복사 |

여기서 published는 개발자 PC의 테스트용 읽기 전용 API가 해당 승인 파일을 제공할 수 있다는 뜻이다.
정식 외부 서비스 공개·GitHub Release·런처 EXE 배포를 수행했다는 뜻이 아니다.
Pixel Effect Maker와 Pixel Motion Studio는 포함하지 않는다.

## TileNamer

- 원본 ZIP: `Desktop/TileNamer/release/TileNamer_v0.1.6_RC3_win64.zip`
- release_id: `0.1.6-rc3-8ba7a1e`
- 기준 커밋: `8ba7a1e47d84888c06ea3913482c79db9b72eb02`
- 크기: 54,046,715 bytes
- ZIP SHA-256: `aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4`
- EXE SHA-256: `0d8f758fa17b821b1add4d4259aa98f3f30f06a1bd4d0ba17c1a236835dc2349`
- ZIP 항목 3개: `TileNamer.exe`, `README.md`, `RELEASE_v0.1.6_RC3.md`
- 실행 상대 경로: `TileNamer.exe` / cwd: `.` / Onefile
- 타일 규칙·Guide·Qt 리소스는 승인된 EXE 내부에 번들된 기준이다. 이번에는 EXE를 실행하지 않으며 바깥 ZIP/EXE 해시로 동일성을 확인한다.
- 설정: QSettings `SOUTHPAW GAMES/TileNamer`.
- 사용자 프로젝트 `.tilenamer.json`, 원본 이미지, TileImages 출력 폴더는 사용자가 선택한 외부 위치.
- RC3 이후 UI 미커밋 변경은 포함하지 않는다.

## ase_viewer

- 원본 ZIP: `Desktop/AI/ase_viewer_v0.5.8.3_with_examples.zip`
- release_id: `0.5.8.3-team-7841e60`
- 연결 기준 커밋/태그: `7841e60fe3d4bb908a0c5f1b488049f9fa2ba63f` / v0.5.8.3
- 크기: 20,612,661 bytes
- ZIP SHA-256: `7f5d7b75014cc355d5dc7d06499429b3be7a3342fe8514871c4ce57622dd05b8`
- EXE SHA-256: `299ef579a110c76c85a4122a6363b81e9360a41957e2d2ad7efe001f877d0dbf`
- ZIP 항목 17개: 루트 EXE/문서, `resources/examples`의 원본 캐릭터 2개·배경 7개·README·디렉터리 항목.
- 실행 상대 경로: `ase_viewer.exe` / cwd: `.` / Onefile + 외부 예제 리소스
- 필수 외부 리소스 10경로를 catalog에 명시해 한글 파일명까지 검증한다.
- EXE 옆 `config.json`, `ase_settings.json`, `ase_project.json`, `ase_debug.log`를 보존·이전.
- 외부 Aseprite.exe 및 사용자 소스가 필요할 수 있다.
- 발견된 v0.5.8.4 ZIP과 v0.5.8.5 소스를 사용하지 않는다.
- 런처의 Viewer 아이콘은 기존 도구의 Icon.png 복사본이다. 기존 EXE나 ZIP의 아이콘 리소스를 바꾸지 않는다.

## AsepriteTagMaster

- 승인 기준: v0.4.0 / `7263f8d6107be76363d329c6962cd46dd15d4068`
- 과거 기록의 ZIP 이름: `AsepriteTagMaster_v0.4.0_20260710_7263f8d.zip`
- 과거 ZIP SHA-256: `80865038ddab9a1b9050d04cbb48cb777edf4e6419caafb05b8b51c0f6962299`
- **지정 ZIP을 이번에 확보하지 못했으므로 published=false, 설치 비활성.**
- 확인된 기존 EXE: `Desktop/AsepriteTagMaster_Source/dist/AsepriteTagMaster.exe` 및 `Desktop/AsepriteTagMaster_Archive/AsepriteTagMaster_v0.4.0_7263f8d_Release/AsepriteTagMaster.exe`.
- 두 EXE SHA-256: `5b55cff02880d5c02ac7f1c2c323b8125273f056f8a774beb246cc0d4dd0aee6`.
- 예정 실행 상대 경로: `AsepriteTagMaster.exe` / cwd: `.` / Onefile.
- 필수 동반 파일: `custom_dictionary.json`, `VERSION.txt`.
- 보존: 사용자 사전·settings.json·오류 로그. 원본 인접 `.aseprite_backup`은 런처가 건드리지 않음.
- 새 분할 엔진을 기존 EXE에 포함된 기능으로 취급하지 않는다. 임의 재압축으로 승인 ZIP을 대체하지 않는다.

## Ase-PS Bridge Pro

- 원본 ZIP: `Desktop/AI TS/dist/Ase-PS-Bridge-Pro_v0.3.6_Windows.zip`
- release_id: `0.3.6-team-6e84645`
- 기준 커밋: `6e846459cb240ab5942e2ffa65d3b51d64648972`
- 크기: 66,252,089 bytes
- ZIP SHA-256: `1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9`
- EXE SHA-256: `203c7fffe32726b7851edf0ad3e20d1bf1963f10124deb976992895dd21584fe`
- ZIP 항목 2개: `bridge_ui.exe`, `RELEASE_v0.3.6.md`.
- 실행 상대 경로: `bridge_ui.exe` / cwd: `.` / Onefile, 스크립트는 승인 EXE 번들 기준.
- 설정: `%APPDATA%/Ase-PS-Bridge/bridge_settings.json`.
- EXE 옆 `temp`의 데이터만 이전. 코드 확장자는 자동 이전하지 않음.
- `%APPDATA%/Aseprite/scripts`, 단축키·Trust 상태는 프로그램 자체 정책이다. 런처 설치만으로 승인하거나 변경하지 않는다.
- v0.3.7 호환성·Splash·원본 보호 개발 변경은 포함하지 않는다.

## Pivot_Fixer

- 원본 ZIP: `Desktop/Pivot Fixer/dist/Pivot_Fixer_v0.3.3.zip`
- release_id: `0.3.3-team-80b84c9`
- 연결 기준 릴리즈 커밋: `80b84c99f6e9865beb26d8b184e8d400781e9d07`.
- 크기: 20,709,116 bytes
- ZIP SHA-256: `214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361`
- EXE SHA-256: `620c7dffb32810fc6427b57ed467ba042b6e2893afc21b03b70a79f1218c295b`
- ZIP 항목 1,073개. 원본 ZIP의 역슬래시 Windows 경로를 검증 후 정규화하며 원본 바이트는 변경하지 않음.
- 실행 상대 경로: `Pivot_Fixer_v0.3.3/Pivot_Fixer_v0.3.3.exe`
- cwd: `Pivot_Fixer_v0.3.3` / Onedir.
- `_internal` 전체를 유지하며 필수 `tkinterdnd2` 디렉터리를 검사.
- 보존: cwd의 `pivot_fixer_settings.json`과 `_internal/pivot_fixer_settings.json`.
- 사용자 원본·출력·`_aseprite_backup`은 외부 위치이며 런처가 변경하지 않음.

## 검증 근거

- ZIP 크기·SHA-256·CRC, EXE 상대 경로·SHA-256, 필수 경로와 전체 압축 항목을 읽어 검증.
- 원본을 이동/수정/삭제하지 않고 이 프로젝트 distribution/packages로 복사.
- `tools/import_approved.py`가 고정 승인 해시·버전을 명시.
- `docs/package-audit.local.json`에 실제 원본 절대 경로와 결과를 기록하며 Git에서 제외.
- `tools.verify_distribution`은 실제 loopback 다운로드·격리 설치·오프라인 경로 해석만 검증. 도구 실행은 하지 않음.
- 이 문서의 설정 위치는 기존 소스/문서 정적 분석 근거다. 해당 승인 EXE의 실제 런타임 쓰기 위치는 후속 수동 QA에서 확인한다.
