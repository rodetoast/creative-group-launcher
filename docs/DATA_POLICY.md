# 기존 프로그램 보호 및 데이터 정책

기존 Desktop 소스/배포물은 읽기 전용입니다. 이 프로젝트는 승인 ZIP을 검증하고 복사할 뿐
소스 수정·재빌드·태그 변경·기존 실행/설치 폴더 수정·원본 이동/삭제를 하지 않습니다.

| 앱 | 원래 데이터 정책 | 런처 업데이트 보존 경로 (cwd 기준) |
|---|---|---|
| TileNamer | QSettings: SOUTHPAW GAMES/TileNamer; 사용자 선택 .tilenamer.json, 출력 폴더 | 외부 QSettings·프로젝트·출력은 건드리지 않음 |
| ase_viewer | EXE 옆 JSON·로그, 외부 소스 참조 | config.json, ase_settings.json, ase_project.json, ase_debug.log |
| AsepriteTagMaster | EXE 옆 사용자 사전·설정·로그; 원본 인접 백업 | custom_dictionary.json, settings.json, aseprite_tag_master_error.log |
| Ase-PS Bridge Pro | %APPDATA%/Ase-PS-Bridge 설정, EXE 옆 temp; Aseprite 설치 스크립트 | temp 데이터 복사; 코드 확장자 이전 제외. 외부 AppData는 건드리지 않음 |
| Pivot_Fixer | __file__ 기준 설정; 원본/선택 출력·백업 폴더 | pivot_fixer_settings.json, _internal/pivot_fixer_settings.json |

### 중요한 의미

- 기존 프로그램 코드를 수정하지 않아 데이터 경로를 일괄 LocalAppData로 강제 변경하지 않습니다.
- 런처 설치 위치는 LocalAppData지만 앱이 EXE 옆에 쓰는 파일은 해당 release payload에 생깁니다.
- 등록된 경로는 이전·새 배포본 양쪽에 선언돼 있을 때만 복사합니다.
- 사용자 사전은 기존 사용자 내용을 우선합니다. 새 기본 사전과 자동 병합하지 않습니다.
- .exe/.dll/.py/.pyw/.bat/.cmd/.ps1/.lua/.jsx는 설정 이전에서 제외합니다.
- 미등록 사용자 작업물과 사용자가 바꾼 리소스는 이전 버전 폴더에 보존합니다.
  새 활성 버전에 자동 복사하지 않으므로 필요한 작업물은 기존 위치에서 사용하거나 명시적으로 옮겨야 합니다.
- 프로젝트 내부 상대 경로가 이전 폴더를 가리킬 수 있습니다. 이전 버전 자동 정리는 구현하지 않습니다.
- 제거는 설치 영수증의 원본 해시와 같은 관리 파일만 삭제합니다.
  명시된 사용자 데이터·수정된 파일·알 수 없는 파일은 보존하며 남은 폴더 경로를 표시합니다.
- 초기에는 기존 Desktop 설치본의 사용자 설정을 자동 가져오지 않습니다. 복사하려면 별도 승인된 이전 절차가 필요합니다.

설정·작업물의 보존은 모든 앱의 새/구버전 사이 데이터 호환성을 보장한다는 뜻은 아닙니다.
새 배포본 게시 전 해당 프로그램의 데이터 호환성과 보존 목록을 검토해야 합니다.

### MVP 안정성 보완(2026-11-03)

제거 대상 관리 파일은 먼저 앱별 recovery/<작업 ID>/files에 복사하고 SHA-256을 확인합니다.
모든 백업 검증 후 원본 관리 파일을 삭제하며, 중간 실패 시 빠진 파일을 복원합니다.
복원 대상에 다른 내용의 파일이 나타나면 사용자 변경을 덮어쓰지 않고 복구 필요로 중단합니다.
제거 완료는 관리 파일 부재와 active.json 제거 후 확정합니다. 실패를 성공으로 안내하지 않습니다.

미등록 파일·설정·수정 파일은 기존 보존 정책을 유지합니다. 제거 백업은 자동 삭제하지 않으므로
복구 사본의 EXE 등이 보존 영역에 남을 수 있습니다. 이것은 활성 설치나 관리형 롤백을 뜻하지 않습니다.
복구 설치에서는 기존 payload 전체를 recovery/<작업 ID>/previous-release에 보존합니다.
등록된 사용자 설정만 새 payload로 복사하고 미등록 작업물은 보존 폴더 위치를 경고로 알립니다.
중단된 새 release/staging도 작업 소유권을 확인해 격리 보존하며 임의의 기존 폴더는 덮어쓰거나 삭제하지 않습니다.

복구 기록은 apps/<app_id>/transactions 아래에 있습니다. 다음 설치/제거/실행 요청과 UI 복구 확인은
동일한 앱 잠금 아래 기록과 실제 파일을 대조합니다. 완료 후 다운로드 임시 파일 정리 실패는 경고로
기록하고 후속 작업에서 재시도합니다. 디스크/권한/백업 손상 등으로 복원이 불가능하면 기록과 사본을 보존합니다.
자세한 상태와 미검증 범위는 [STABILITY_FIX_REPORT.md](<STABILITY_FIX_REPORT.md>)를 따릅니다.
