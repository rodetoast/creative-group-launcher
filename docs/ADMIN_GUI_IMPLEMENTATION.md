# 로컬 관리자 배포 GUI 구현 보고서

2026-11-05. 운영 게시 잠금 유지, 운영 키·직원 배포 미승인.

## 재사용한 게시 경로

`southpaw_tools/admin_gui.py`는 PySide6 화면이며 기존 런처의 STYLE과 Task(QThread)를 사용한다.
`admin_gui_model.py`는 GUI 어댑터다. 최종 게시에는 기존 `admin.publish()`를 호출한다.
AppRelease.parse, archive.checked_members/extract_checked, Ed25519 검증기도 재사용한다.
새 배포 엔진·서버·권한 체계를 만들지 않았다. 기존 게시·서명·설치·복구 엔진은 수정하지 않았다.

## 화면과 사용 흐름

위쪽에는 저장소 경로·현재 순번·서명 상태, 왼쪽에는 앱·현재 게시 상태·ZIP 검사 결과를 표시한다.
오른쪽에는 새 버전·릴리스 ID·EXE 상대 경로·순번·ZIP/키 선택·릴리스 노트가 있다.
작은 창에서는 입력 영역을 스크롤한다. 아래에는 단계와 결과를 표시한다.

지원 이름은 TileNamer, ase_viewer, AsepriteTagMaster, Ase-PS Bridge Pro, Pivot_Fixer다.
등록된 앱 선택에 따라 읽기 전용 앱 ID를 표시하고 등록 여부를 검증한다.
Pixel Effect Maker와 Pixel Motion Studio는 포함하지 않는다.
AsepriteTagMaster는 승인 ZIP 미확인으로 ZIP 선택·게시를 계속 차단한다.

관리자는 앱 선택 → 완성 ZIP 명시 선택 → 새 릴리스 정보 입력 → ZIP 검사 → 승인 체크/키/순번 확인 →
최종 확인 → 게시 순서로 사용한다. 검사에서 계산한 해시만으로 회사 승인 여부를 자동 판정하지 않는다.
최종 확인창은 저장소·ZIP 파일명·이전/새 릴리스와 버전·해시·순번·공개키 ID·노트를 표시한다.
취소가 기본 버튼이며 취소하면 게시 함수를 호출하지 않는다.
검사·게시 전 검사·게시는 QThread에서 실행한다. 작업 중 입력 변경과 강제 창 종료를 막는다.

## ZIP 보호와 검사

관리자가 선택한 원본 ZIP은 읽기만 한다. 이동·덮어쓰기·자동 빌드·자동 ZIP 생성 기능은 없다.
Git HEAD·소스·dirty 상태·임의 EXE에서 배포 대상을 고르지 않는다.
ZIP/EXE SHA256, 압축·해제 크기, 내부 경로 목록, CRC, 중복/충돌/경로 탈출/링크,
MZ, 작업 디렉터리와 필수 리소스를 기존 검사기로 확인한다.
감사 추출은 ignored `.test-results/admin-gui-inspections`의 고유 임시 디렉터리에서만 수행한다.
EXE는 실행하지 않는다. 검사 후와 게시 직전에 원본 ZIP 해시를 다시 확인한다.
릴리스 입력이 바뀌면 검사 결과를 무효화하고, 최종 확인 후에도 키 ID·저장소·ZIP·카탈로그 기준을 재확인한다.

## 운영 잠금과 테스트 모드

기본 GUI는 실제 저장소 조회와 읽기 전용 ZIP 검사만 허용한다. 운영 게시 버튼은 잠긴다.
운영 공개키는 여전히 미채택이며 운영 잠금 해제 스위치는 제공하지 않는다.
`--test-mode`는 프로젝트 `.test-results` 하위의 표식 있는 repository만 허용한다.
TEST_ONLY_TRUST.json 및 더미 ZIP 고정 해시 목록에 맞는 게시만 허용한다.
시험 표식은 더미 안전 경계이며 새로운 회사 인증/승인 시스템이 아니다.

`tools/prepare_admin_gui_demo.py`는 새 경로에만 다섯 앱의 미게시 메타데이터,
무해한 MZ 더미 ZIP r1/r2, 테스트 키·공개키 정책·서명된 초기 카탈로그를 만든다.
기존 경로는 덮어쓰지 않는다. 실제 앱/승인 ZIP을 복사하거나 새로 빌드하지 않는다.
개인키는 repository 밖의 test-only-signing.pem이며 운영용이 아니다.
이 도구는 이전 LAN 환경이나 기록을 변환하지 않는다.

## 서명과 개인키

signing_key와 sequence는 기존 게시 함수와 같은 의미다. 순번은 현재보다 큰 양의 63비트 정수다.
키 누락·저장소 내부 개인키·시험 공개키와 다른 개인키·현재 서명 불일치는 게시를 차단한다.
게시 후 실제 서명·순번·앱 메타데이터·패키지 해시를 확인한 뒤에만 성공을 표시한다.
개인키 경로는 메모리에서만 사용한다. GUI 설정 파일·QSettings·개인키 복사 기능은 없다.
화면에는 개인키 내용/경로를 표시하지 않고, 토큰을 읽거나 보관하지 않는다.
오류 로그에서는 선택 개인키·패키지·홈 경로를 가린다. 공개키 ID는 비밀정보가 아니다.

## 실패 처리

단계는 ZIP 검사, 게시 전 검사, 게시 엔진 호출, 게시 후 서명·카탈로그 확인으로 구분한다.
엔진 내부 모든 OS 파일 연산에 새 단계 시스템을 추가하지 않고 기존 예외와 실제 상태를 표시한다.
실패 후 실제 순번·서명·릴리스를 다시 읽으며 자동 재시도·기존 배포물 삭제·롤백은 하지 않는다.
게시 기록은 공개 repository 밖 gui-logs의 고유 JSON에 단계·결과·앱/릴리스·순번·가린 오류를 저장한다.
로그 쓰기 자체가 실패해도 원래 오류를 숨기지 않고 화면과 실제 상태 보존을 안내한다.

예를 들어 signature 교체 후 catalog 교체가 실패하면 기존 catalog 바이트는 남지만 서명이 맞지 않을 수 있다.
이를 중간 게시 실패로 표시하고 성공으로 처리하지 않는다. 기존 엔진의 실패한 신규 패키지 정리 외에
GUI가 추가로 배포물을 제거하지 않는다. 관리자는 로그와 catalog.json/catalog.sig.json/packages를 보존해 검토한다.

## 실행 방법

의존성이 설치된 프로젝트 Python:

```powershell
python -B -m southpaw_tools.admin_gui
```

설치된 console script 이름은 `southpaw-tools-admin`이다.
이번 개발 환경에서 사용한 격리 의존성과 Python 경로:

```powershell
$Project = 'C:\Users\SOUTHPAW GAMES\Documents\ChatGPT\통합 클라이언트 만들기'
Set-Location -LiteralPath $Project
$env:PYTHONPATH = Join-Path $Project '.test-results\catalog-signing-20261105\deps'
$Python = 'C:\Users\SOUTHPAW GAMES\AppData\Local\Programs\Python\Python313\python.exe'
& $Python -B -m southpaw_tools.admin_gui
```

이는 현재 콘솔의 모듈 검색 경로만 설정하며 전역 PATH/설치를 변경하지 않는다.
새 더미 환경 준비와 GUI 실행:

```powershell
& $Python -B -m tools.prepare_admin_gui_demo --root '.test-results\admin-gui-demo-new'
& $Python -B -m southpaw_tools.admin_gui --root '.test-results\admin-gui-demo-new\repository' --test-mode
```

이미 준비한 화면 검증 환경은 `.test-results/admin-gui-20261105/demo`다.
그 안의 inputs/admin-dummy-r1.zip, EXE 경로 Demo.exe, test-only-signing.pem을 선택한다.
초기 순번은 1이므로 첫 게시 순번은 2, 버전 예시는 0.0.1이며 릴리스 ID는 고유한 새 값을 입력한다.
일반 권한으로 사용하며 LAN·방화벽·EXE 실행이 필요하지 않다.

## 검증과 변경 파일

최종 테스트·보존 수치는 아래 최종 확인 절에 기록한다.
Qt offscreen 기본/축소 화면 및 최종 확인창 PNG를 직접 확인했다.
화면 촬영에서는 게시하지 않았고 전체 게시 흐름은 격리 자동 테스트로 검증했다.
실제 앱·승인 ZIP은 GUI 시험 대상으로 사용하지 않았다.

추가: southpaw_tools/admin_gui.py, southpaw_tools/admin_gui_model.py,
tools/prepare_admin_gui_demo.py, tests/test_admin_gui.py, docs/ADMIN_GUI_IMPLEMENTATION.md.
수정: pyproject.toml(실행 진입점), README.md(사용 안내).
기존 게시/서명/설치 엔진과 기존 미커밋 작업을 보존했다.

## 실제 운영 전 필요한 사항

운영 키·보관 방식·공개키 배포 및 직원 배포 승인은 별도다. 이번 GUI는 운영 게시 경로를 열지 않았다.
운영 모드 활성화는 별도 검토가 필요하며 AsepriteTagMaster 승인 ZIP도 먼저 확인해야 한다.
실제 승인 ZIP의 운영 GUI 게시, 실제 Windows 화면/배율, EXE/SAC 호환성은 이번 검증이 아니다.
TLS·인터넷 공개·자체 업데이트·자동 빌드·새 인증·복잡한 승인 흐름을 추가하지 않았다.
다음 단계 개발과 Git stage/commit/push/remote 변경을 자동 진행하지 않는다.

## 최종 확인

- 기존 105개 + 신규 GUI 20개, 총 **125개 통과**, 20.169초. 누락/건너뛴 테스트 없음.
- 신규 검증: 잘못된 ZIP/필드/릴리스/순번/키 거부, 승인 체크, 최종 취소 시 엔진 미호출,
  정상 더미 게시, 원본 ZIP 해시·수정 시각 보존, 중간 서명 게시 실패, 로그 쓰기 실패,
  ZIP/카탈로그 변경, 운영 저장소 잠금, TagMaster 잠금, 이벤트 루프 응답 유지.
- 기존 다섯 프로젝트 292개 파일 및 HEAD/tags/status 동일.
- 존재하는 원본 승인 ZIP 4개 해시 동일. TagMaster 원본 승인 ZIP은 기존과 같이 없음.
- 이전 시험/서명 개발 증거 및 distribution의 기준 파일 932개 해시 동일.
- 기존 게시·서명·설치·업데이트·복구 엔진 파일은 이번 작업에서 변경 없음.
- master / HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5`, remote 없음.
  기존 미커밋 변경 보존, 이번 GUI 파일은 작업 트리에만 남김. stage/commit/push/remote 변경 없음.
- 최종 읽기 전용 조회: 관리자 False, TCP8765 리스너 0개, 시험 규칙 0개.
- Windows Use 미사용. 실제 LAN·방화벽·실제 EXE·운영 게시·SAC 변경 없음.

세부 증거는 `.test-results/admin-gui-20261105`의 final-tests.log,
FINAL_VERIFICATION.local.json, existing-projects-verification.local.json에 있다.
화면은 admin-inspection-final.png, admin-confirmation-final.png, admin-compact-final.png다.
GUI 검증을 실제 직원 PC에서의 실행/운영 준비 완료로 확대 해석하지 않는다.
