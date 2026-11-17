# Windows 설치 경로 사전 검증

## 검사 순서

Installer는 서명된 배포 정보를 확인한 뒤 앱 잠금을 잡는다. 설치에는 `downloads/<작업 ID>.zip`, `staging/<작업 ID>/payload`, `apps/<앱>/releases/<release_id>/payload`를 사용한다. 설치 영수증과 서명 증거는 릴리스에 붙고, `active.json`과 `transactions/<작업 ID>.json`은 앱 폴더에 남는다. 복구는 중단된 staging·release와 기존 설치를 `recovery/<작업 ID>` 아래에 보관한다. 제거는 영수증이 관리하는 파일만 해당 작업의 `files/releases/…`에 복사하고 복원 시 `restore-<ID>` 임시 파일을 사용한다.

| 검사 시점 | 대상과 실패 시 동작 |
|---|---|
| 다운로드 전 | 잠금, ZIP 저장 경로, active·journal과 원자 쓰기 임시 파일, 영수증·서명 증거·ZIP 보관 위치를 검사한다. 동일 릴리스 수리 시 이동할 기존 트리도 확인한다. |
| 다운로드 후 | 크기·해시를 검증하고 기존 ZIP 안전 검사로 파일 목록을 얻는다. 추출, 최종 설치, 복구 보관, 제거 전 사본과 복원 임시 경로를 계산한다. 새 버전에 복사할 실제 보존 파일도 포함한다. |
| 제거 전 | 영수증·해시·보존 경로를 기준으로 실제 제거할 파일을 결정한 뒤, 사본과 복원 경로를 검사한다. 경로가 맞지 않으면 제거 journal을 열기 전에 중단한다. |
| 기존 작업 복구 | 중단된 트리를 보관·복원할 경로와 제거 복원 대상을 검사한다. 기존의 소유권 검사와 복구 정책을 사용한다. |

ZIP 내부 파일명은 다운로드 후에야 알 수 있다. 이 단계에서 경로 오류가 발견되면 현재 작업의 ZIP과 초기 다운로드 journal을 기존 정리 함수로 정리한다. staging 파일 추출과 활성 포인터 전환은 시작되지 않는다. 이전에 중단된 작업이 있다면 Installer는 기존 정책에 따라 그 작업을 먼저 확인한다.

작업 ID의 32자리 규칙과 CPython `mkstemp`의 8자리 후보가 들어가는 `.pending-*.json` 형식을 사용했다. 경로 길이는 드라이브 또는 UNC 절대 경로에서 UTF-16 코드 단위로 측정한다. 일반 Win32 파일 경로의 한도는 종료 문자 제외 259단위이며, 폴더 생성에는 248단위 기준을 적용한다. 파일 이름 구성 요소는 가능한 경우 대상 볼륨에서 조회하고, 조회하지 못하면 255단위를 적용한다. [Microsoft Win32 경로 한도](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation) · [볼륨 구성 요소 한도](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumeinformationw)

런처의 지원 범위는 일반 Win32 경로로 정했다. Windows 레지스트리 설정만으로 런처, 실행될 앱, 셸의 긴 경로 지원을 함께 보장할 수 없기 때문이다. 이 시험 PC의 `LongPathsEnabled`는 0이다. 현재 검사는 Windows에만 적용한다. ZIP 경로 탈출, 중복 경로, 링크, 필수 파일·서명·해시 검사는 기존 코드가 계속 수행한다.

## 원본 Pivot_Fixer v0.3.3 검증

같은 ZIP과 release_id로 실제 Installer를 실행했다. 기존 260~262자 추출 실패는 이전 증거에서 확인했고, 이번에는 동일한 긴 루트 길이를 격리 폴더에서 재현했다.

| 루트 길이 | 추출 최장 | 최종 설치 최장 | 제거 전 사본 최장 | 실제 결과 |
|---:|---:|---:|---:|---|
| 65 | 195 | 199 | 247 | 설치 성공, receipt 파일 1,071개 해시 일치 |
| 77 | 207 | 211 | 259 | 설치 및 제거 성공, 1,071개 해시 일치 및 제거 전 사본 생성 |
| 78 | 208 | 212 | 260 | 제거 전 사본 경로에서 추출 전 차단 |
| 124 | 254 | 258 | 306 | 이전에는 설치됐으나 이번에는 제거 전 사본 경로에서 추출 전 차단 |
| 138 | 268 | 272 | 320 | 중단된 추출 보관 경로에서 추출 전 차단 |

차단된 세 루트에서 새 활성 포인터, staging 내용, 다운로드 ZIP과 설치 journal이 남지 않았다. 원본 ZIP SHA-256은 시험 전후 일치했다. 77은 이 ZIP과 release_id에서 나온 경계다. [경계 시험 JSON](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/windows-install-preflight-20261110/pivot-boundaries.json>)

## 화면과 합성 데이터

Windows의 Qt 오프스크린 렌더에서 실제 직원 GUI의 업데이트 버튼과 작업 스레드를 실행했다. 긴 release_id를 가진 합성 ZIP을 검사하자 작업 단계, 파일명, 260단위와 259단위 한도가 표시됐다. 오류는 네트워크나 서명 오류로 분류되지 않았고 기존 활성 포인터 해시는 유지됐다. 화면에는 전체 설치 경로를 표시하지 않는다. [직원 GUI 오류 화면](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/windows-install-preflight-20261110/gui-path-error.png>)

신규 회귀는 UTF-16 보조 문자, 폴더 및 볼륨 이름 한도, 259단위에서의 설치·제거, 260단위에서의 업데이트 차단, 실제 이전할 사용자 파일의 복구 경로 초과, 기존 릴리스의 제거 차단을 검증한다. 실패 전후 활성 포인터, 영수증, 사용자 설정과 작업 파일을 포함한 격리 트리의 해시를 대조했다.

별도 합성 시험에서는 두 앱을 설치한 뒤 한 앱의 업데이트를 차단했다. 두 앱과 작업 파일을 포함한 12개 파일의 해시가 일치했다. 루트가 210자인 시험에서는 journal 경로 272단위를 감지해 다운로드 호출과 journal 생성 전에 중단했다. 시험 볼륨이 반환한 구성 요소 한도는 255단위였다. [합성 보존 시험](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/windows-install-preflight-20261110/synthetic-preservation.json>)

## 회귀 조정과 보존

첫 전체 회귀에서는 Bootstrap 초기 설치 12개가 차단됐다. 자체 업데이트 저장소는 Installer를 재사용하며 직원 앱 제거 기능을 노출하지 않는다. 자체 업데이트 호출에서 사용하지 않는 미래 제거 경로 계산만 제외하고, 실제 추출·설치·복구 검사는 적용했다. 이어 확인한 Bootstrap 시험 폴더의 긴 실제 복구 경로는 시험 전용 폴더 이름을 줄여 해결했다. 승인된 시험 바이너리와 12개 검증 조건을 유지했다. [첫 전체 회귀 기록](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/windows-install-preflight-20261110/full-suite.log>)

최종 전체 회귀는 기존 252개와 신규 5개를 포함해 **257개 모두 통과**했다. Bootstrap 12개, 버전 전환과 복구, ZIP 안전 검사, GitHub Provider와 서명 검증이 포함됐다. 의도적 journal 잠금 시험의 WinError 5는 기록되고 정상 처리됐다. 예상 밖 WinError 5는 최종 회귀에서 관측되지 않았으며 기존 간헐 오류의 원인은 미확정이다. [최종 전체 회귀 로그](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/windows-install-preflight-20261110/full-suite-final.log>)

기존 후보 ZIP·EXE 49개와 이전 시험 증거 6,712개의 해시가 일치했다. 다섯 프로그램 프로젝트의 HEAD·브랜치·태그·작업 트리 상태를 확인했다. 런처는 `master`의 `32afb846d0bc69b38203a259dad71180cd4a14b5`이며 stage와 remote는 비어 있다. 실험은 별도 격리 폴더에서 수행했다. [보존 대조](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/windows-install-preflight-20261110/preservation.json>)

직원 PC에서는 실제 사용자 프로필·볼륨·리디렉션과 승인된 ZIP·release_id를 기준으로 설치를 확인해야 한다. 현재 기능은 일반 Win32 경로를 사용하는 배포를 지원하며, 앱 자체가 실행 후 새로 만드는 파일이나 별도 공용 경로의 길이는 해당 앱 검증 범위다.
