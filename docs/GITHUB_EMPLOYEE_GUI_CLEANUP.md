# GitHub 중심 직원 GUI 정리 — 2026-11-06

## 변경 결과

신규 설정은 메모리에서 `transport=github`, `github_repository=""`를 기본값으로 사용한다. 저장소·운영 키는 자동 채택하지 않는다. 저장소 미지정 상태에서는 네트워크 요청 없이 배포 설정 대기를 표시하고 설치·업데이트를 차단한다. 테스트 저장소나 Dummy Tool, 시험 공개키를 기본값으로 등록하지 않았다.

기존 settings.json은 시작 시 다시 쓰지 않는다. 명시된 transport는 유지하며, transport가 없는 구형 파일에 서버 주소·토큰·LAN 플래그가 있으면 기존 LAN 방식으로 메모리에서만 해석한다. 기존 GitHub 설정도 유지한다. 손상된 설정 파일 역시 자동 복구·덮어쓰기하지 않는다.

일반 ConnectionDialog는 GitHub 저장소 입력만 표시한다. LAN 주소·토큰·포트 또는 LAN 방식 선택은 표시하지 않는다. 기존 LAN 사용자가 이 창을 열면 설정이 유지 중이며 저장 시 GitHub로 전환된다는 안내를 표시한다. 취소하면 변경 없고, 명시적으로 저장할 때만 전환한다. 기존 부가 설정과 LAN 값은 삭제하지 않는다.

기존 LAN 설정 UI는 `ConnectionDialog(..., legacy=True)`라는 개발 전용 명시 경로로 보존했다. 일반 직원 창에서는 호출하지 않는다. HttpProvider·서버·서명·Installer·복구 엔진은 변경하지 않았다. 기존 명시적 LAN 설정의 연결 동작과 테스트는 유지된다.

## 오류 구분

| 상황 | 표시 |
|---|---|
| 운영 저장소 미지정 | 배포 설정 대기 / 운영 저장소 미지정, 담당자에게 승인된 저장소 확인 안내 |
| HTTP 404 | 저장소 또는 Release를 찾을 수 없음 |
| HTTP 403 호출 제한·429 | GitHub 호출 제한, 요청 제한 및 나중에 확인 안내 |
| 일반 HTTP 403 | GitHub 접근 거부 |
| 네트워크·HTTPS 연결 실패 | 인터넷 연결 실패, 인터넷 또는 네트워크 확인 안내 |
| 서명·순번 검증 실패 | 서명 검증 실패, 신뢰할 수 없는 배포 정보 및 설치·업데이트 중단 안내 |
| 빈 운영 키 정책에서 알 수 없는 서명키 | 운영 키 미채택, 현재 배포물을 설치할 수 없다는 안내 |

서명 실패와 404를 인터넷 오류로 분류하지 않는다. 신뢰키가 이미 있는 시험 정책에서 다른 키를 받은 경우는 운영 키 미채택으로 분류하지 않고 서명 검증 실패로 유지한다. 호출 제한의 기존 대기 시간과 설치 시 새 검증 경로는 유지한다.

오류 분류와 별개로 기존 설치본·active/receipt를 변경하지 않는다. 새 회귀에서 각 오류 후 기존 로컬 실행 버튼이 활성 상태로 유지됨을 확인했다. 실제 회사 프로그램을 실행한 시험은 아니며 FakeProcesses 기반 검증이다. 격리 GitHub 시험 모드의 실행 차단도 유지된다.

## AsepriteTagMaster

초기 카탈로그의 description·release_notes·availability_reason만 수정했다. 개발 PC 배포 서버가 필요하다는 문구를 제거하고 승인된 완성 ZIP 미확인 때문에 설치할 수 없음을 명시했다.

앱 이름·ID·버전·release_id·빌드 ID·설치 제한·보존 경로 등 나머지 필드는 동일하다. 다른 네 앱의 메타데이터는 변경하지 않았다. 원본 ZIP을 새로 찾거나 만들지 않았다.

## 창 크기 및 DPI

개발 PC에서 수정 소스의 실제 Windows qwindows 창을 실행했다. 신규 GitHub 대기 화면, LAN 필드 없는 연결 창, TagMaster 안내, 980×700 논리 크기의 화면을 확인하고 정상 종료했다(코드 0). 회사/Dummy Tool EXE는 실행하지 않았다.

Qt offscreen 별도 프로세스에서 100%와 200%(devicePixelRatio 2.0) 배율의 980×700 화면을 렌더링했다. 모든 정보 패널 라벨 높이가 최소 힌트 이상이고 주요 버튼이 창 안에 있음을 검사했다. 창 구조·테마·최소 크기·전역 DPI 정책은 변경하지 않았다. 200% 모의 렌더링은 DESKTOP-01VCOI7의 실제 DPI 192 실기동 검증을 대신하지 않는다.

이번에는 제품 EXE를 재빌드하지 않았다. 이전 검증 EXE와 전달 ZIP은 원본대로 보존했다. 별도 PC에는 향후 이 소스를 반영한 새 격리 빌드에서 기본값·기존 설정 유지·새 연결 창·DPI 192를 다시 검증해야 한다. 이전 EXE에 이번 수정이 들어갔다고 보고하지 않는다.

## 테스트 결과

- 관련 GUI·설정 테스트: 34개 통과.
- 신규 직원 GUI 테스트: 8개 모두 통과.
- 기존 235개를 유지한 전체 회귀: **243개 중 242개 통과, 오류 1개, 실패·skip 0개**.
- 기존 승인된 Bootstrap Windows 테스트 12개 모두 통과. 시험 실행 파일의 기존 해시를 사전 확인했다.
- 초기 관련 실행에서 손상 설정의 실제 오류 문구에 대한 새 테스트 기대값 1개를 수정했고, 초기 로그와 최종 관련 로그를 모두 보존했다. 제품의 오류를 숨기거나 skip하지 않았다.

전체 회귀 오류는 기존 `test_journal_sharing.JournalSharingTests.test_persistent_lock_preserves_journal_then_recovers_after_release`의 잠금 해제 후 명시적 재설치 단계에서 발생했다. `_phase(preparing) → atomic_json/atomic_bytes → os.replace`의 예상하지 못한 WinError 5다. 임시 journal은 preparing, 대상은 download_verified, writer는 닫혔고 사후 Restart Manager 조회의 소유 프로세스는 없었다. 잠금 주체나 근본 원인은 확인되지 않았다.

의도적 잠금 주입 4건과 예상 밖 1건을 구분했다. 실패 로그·journal·파일 스냅샷을 보존하고 전체 회귀를 통과할 때까지 반복하지 않았다. sleep·자동 재시도·예외 무시·skip을 추가하지 않았다. 따라서 이번 작업을 전체 회귀 합격이나 WinError 5 해결로 표시하지 않는다.

## 변경 파일과 보존

기존 파일 변경:

- `southpaw_tools/ui.py`: 기본 연결·설정 UI·오류 안내.
- `southpaw_tools/data/catalog.json`: TagMaster 설명 3필드.
- `tests/test_ui.py`: 기존 LAN 회귀에 명시적 LAN 설정, 새 TagMaster 문구 반영.
- `tests/test_recovery_ui.py`: 기존 LAN 회귀 fixture의 명시적 LAN 설정.
- `tests/test_github_ui.py`: 빈 운영 키의 새 상태 문구 반영.

신규:

- `tests/test_employee_settings.py`: 기본값, 기존 설정 보존, LAN 비노출·개발 경로, 미지정 저장소, 오류 구분·로컬 상태, TagMaster, 손상 설정 검증 8개.
- `docs/GITHUB_EMPLOYEE_GUI_CLEANUP.md`: 이 보고서.
- `.test-results/github-employee-cleanup-20261106/`: 이전 파일 해시·변경 비교·회귀 로그·실패 스냅샷·실제 화면·배율 렌더링. Git 제외 대상.

기존 파일 5,641개를 시작 시점과 비교해 허용한 기존 5개 파일 외에는 변경 없음. 이전 시험 자료·빌드·키·LAN 자료를 보존했다. 다섯 외부 프로젝트 292개 파일과 Git HEAD·tag·상태, 승인 ZIP 4개가 기존 기준과 동일하다. TagMaster 승인 ZIP 미확인 상태 유지.

Git master / HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5` / remote 없음 / staging 없음. 기존 미커밋 변경을 보존했고 stage/commit/push/remote 변경 없음. 실제 직원 AppData 변경, 운영 키 등록, GitHub Release 쓰기, 실제 LAN 공개·방화벽·SAC·ACL 변경 없음.

실제 화면 확인에는 computer-use:computer-use 스킬을 사용했다. 소스 GUI와 격리 파일만 다뤘으며, 이번 수정 후 제품 EXE 실기동·별도 PC 재검증·직원 배포·다음 개발은 수행하지 않았다.

## 주요 증거

`.test-results/github-employee-cleanup-20261106/`:

- `native-github-settings.png`, `native-tag-master.png`, `native-minimum.png`
- `minimum-offscreen-scale-1.png`, `minimum-offscreen-scale-2.png`, `layout-scale-2.json`
- `native/process.json`, `related-final.log`, `full.log`, `full-result.json`
- `full/`의 예상 밖 WinError 5 기록·파일 스냅샷
- `preservation-after.json`, `existing-projects-after.json`, `source-changes.diff`, `git-after.txt`
