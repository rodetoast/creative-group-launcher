# 로컬 버전 선택과 Pivot_Fixer 설치 경로 검증

2026-11-10에 현재 런처 소스를 Windows 데스크톱에서 실행했다. GUI의 설치 루트는 `C:\Dev\cgl-visible-20261110\client`였고, 격리 서명 키로 설치한 더미 r1/r2를 사용했다. 네트워크 조회는 시험 설정에서 껐다. GUI는 소스 실행으로 확인했다.

| 항목 | 실제 화면 관찰 |
|---|---|
| 버전 목록 | 두 릴리스가 같은 표시 버전 `1.0.0`이어도 현재 `r2`와 전환 후보 `r1`이 구분됐다. |
| 확인 취소 | 확인창에서 거절한 뒤 현재 버전은 `r2`로 유지됐다. |
| 오프라인 전환 | r1을 확인하자 활성 버전이 r1로 바뀌었으며 최신 r2가 있다는 안내가 남았다. |
| 재시작 | 창을 닫고 같은 데이터 루트로 재실행해 r1 선택 유지와 최신판 안내를 확인했다. |
| 복귀 | 설치된 r2를 다시 고른 뒤 `active.json`은 `r2`, `pinned=false`였다. |
| 실행 중 | 시험 프로세스 어댑터에 실행 상태를 주입하자 선택 버튼이 비활성화됐다. 이 GUI 항목은 회사 프로그램의 실제 프로세스를 실행해서 확인한 결과가 아니다. |
| receipt 손상 | 손상된 시험 receipt를 가진 r1은 선택 목록에서 제외됐다. |
| 파일 해시 불일치 | `asset.json`을 변경한 r1 전환은 확인 후 검증 단계에서 거부됐고 현재 r2가 유지됐다. |
| 서명 증거 손상 | r1 서명 바이트를 변경하자 선택 목록에서 제외됐다. |

처음 본 화면에서는 두 버전의 표시 버전이 같을 때 주 화면만 보고 활성 release_id를 구분하기 어려웠다. 선택 유지 상태에 활성 ID를 추가했다. 확인창에는 공용 작업 파일 보존과 버전 간 호환성 확인 안내를 더했다. 재시작 화면과 r2 복귀 확인창에서 두 변경을 확인했다. 손상된 receipt와 서명은 목록에서 제외되고 공통 안내가 표시되므로 화면만으로는 두 원인을 구분하기 어렵다.

## 설정과 작업 데이터

- 각 버전의 설정은 `client/apps/dummy/releases/<release_id>/payload/settings.json`, 프로젝트는 같은 payload의 `user-projects/`에 있다.
- r2에서 작성한 프로젝트는 r1 전환 후에도 존재했다. r1 선택 상태에서 추가한 프로젝트는 r2 복귀 후에도 존재했다.
- r1·r2 설정 2개와 프로젝트 2개, 릴리스 외부의 공용 작업 파일 1개를 SHA-256으로 대조했다. 모두 일치했다.
- 버전 선택은 활성 포인터를 바꾼다. 파일 형식 변환이나 작업 파일 병합은 수행하지 않는다. 실제 회사 프로그램의 버전 간 파일 형식 호환성은 이번 더미 시험 범위 밖이다.

## Pivot_Fixer 경로

실제 사용자 프로필에서 읽은 Local AppData 기준 기본 루트는 `C:\Users\SOUTHPAW GAMES\AppData\Local\SouthpawGames\ToolsLauncher`로 65자다. 원본 v0.3.3 ZIP의 최장 내부 파일 경로는 80자, 디렉터리는 66자다.

| 경로 단계 | 기본 루트에서 최장 파일 경로 |
|---|---:|
| staging 추출 | 195자 |
| 최종 설치 | 199자 |
| 이전 릴리스 복구 보관 | 230자 |
| 제거 전 복구 복사 | 247자 |

같은 길이의 격리 루트에 원본 ZIP을 설치해 1,071개 파일의 receipt 해시와 활성 포인터가 일치하고 남은 journal이 없는 것을 확인했다. 경로 124자인 격리 루트에서도 설치 단계는 완료됐다. 138자인 격리 루트에서는 262자 파일 경로에서 `FileNotFoundError`가 재현됐고 엔진이 미완료 파일을 복구 폴더에 보존했다. 기존 시험은 260자 경로에서 실패했다. [경로 시험 로그](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/visible-version-path-20261110/pivot-boundary.log>)

Windows의 일반 Win32 경로 한도는 종료 문자를 포함해 260자다. 현재 시스템에서 읽은 `LongPathsEnabled`는 0이었다. 추출기는 검증된 목적지에 일반 파일 생성 API를 사용하므로, 이 조건에서 길어진 경로의 파일 생성이 실패할 수 있다. [Microsoft Win32 경로 제한](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation)

현 패키지의 설치·복구·제거 파일 경로를 함께 고려하면 로컬 절대 데이터 루트 **77자 이하**를 운영 기준으로 삼을 수 있다. Windows UTF-16 길이 기준이며, 가장 긴 제거 전 복구 복사 경로가 이때 259자가 된다. 현재 기본 루트에는 12자의 여유가 있다. 이 수치는 현재 ZIP 및 release_id 기준의 계산값이며 모든 직원 프로필이나 미래 ZIP을 보장하지 않는다. 실제 앱 실행과 제거 전 복구 복사는 이번 경로 시험에서 별도로 실행하지 않았다.

기본 루트의 설치 결과를 근거로 추출기와 Installer의 경로 코드는 유지했다. 따라서 Windows의 긴 사용자 지정 루트 실패는 남는다. POSIX 경로 동작과 Windows 프로세스 실행 경로에 적용한 변경은 없다. Windows 정책과 원본 ZIP은 보존했다.

## 보존 및 변경

후보 ZIP·EXE 49개와 기존 증거 파일 6,712개의 SHA-256을 대조했다. 다섯 프로젝트의 HEAD·브랜치·태그·작업 트리 상태도 일치했다. 런처는 `master`의 `32afb846d0bc69b38203a259dad71180cd4a14b5`이며, 스테이지와 remote는 비어 있다. 실제 직원 AppData는 읽은 경로 값만 계산에 사용했다. [보존 및 설치 대조](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/visible-version-path-20261110/verification.json>)

제품 변경은 `southpaw_tools/ui.py`의 표시·안내 문구다. `tests/test_windows_bootstrap.py`에서는 관찰 루프가 원자 쓰기용 임시 파일을 열지 않도록 했다. 시험 수와 Bootstrap의 실행·중복 실행·업데이트 검증 조건은 유지한다.

첫 전체 회귀에서는 252개 중 251개가 통과했고, Bootstrap 중복 실행 시험에서 원자 쓰기용 `.pending-*.json`에 WinError 32가 발생했다. 관찰 루프에서 해당 임시 파일을 제외한 뒤 전체 회귀 **252개가 모두 통과**했다. Bootstrap 12개, 버전 선택·복구, ZIP 안전 검사, GitHub Provider·서명 검증이 포함됐다. [첫 전체 회귀](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/visible-version-path-20261110/full-suite.log>) · [최종 전체 회귀](<C:/Users/SOUTHPAW GAMES/Documents/ChatGPT/통합 클라이언트 만들기/.test-results/visible-version-path-20261110/full-suite-final.log>)

잠금 시험에서 의도한 WinError 5는 기록됐고 정상적으로 처리됐다. 예상 밖 WinError 5는 이번 실행에서 관측되지 않았다. 기존 간헐 오류의 원인은 미확정이다. 직원 배포 전에는 대상 프로필의 설치 루트 길이, 실제 앱의 버전 간 데이터 호환성, 운영 신뢰 키와 배포 승인을 확인해야 한다.
