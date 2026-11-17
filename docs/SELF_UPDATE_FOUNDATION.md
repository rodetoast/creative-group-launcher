# 런처 자체 업데이트 기반 구현·검증 보고서

2026-11-05. 격리 더미 전용 구현. 운영 키·실제 런처 EXE·직원 배포는 적용하지 않았다.

## 기존 구조 조사

현재 실행은 `southpaw_tools/__main__.py`의 Python 모듈 진입점이며 버전은
`southpaw_tools/__init__.py`의 0.1.0이다. 실제 EXE 패키징 방식과 안정 bootstrap EXE는 아직 확정되지 않았다.
사용자 데이터 기본 경로는 기존 AppPaths의 `%LOCALAPPDATA%\SouthpawGames\ToolsLauncher`다.
다섯 앱 설치·설정·작업 파일과 런처 프로그램 파일을 같은 자체 업데이트 대상으로 다루지 않는다.

기존 Installer는 서명된 AppRelease와 Provider를 받아 다운로드 크기/SHA256, ZIP 안전 경로·CRC,
EXE 해시·MZ·필수 리소스, staging, receipt, 버전별 폴더, journal 복구를 제공한다.
HttpProvider/CatalogVerifier는 고정 공개키와 서명 원본 바이트·순번을 검증한다.
새 자체 업데이트는 이 경로를 재사용하며 게시·서명·설치·복구 엔진을 수정하지 않았다.

## 선택한 최소 폴더 구조

```text
launcher-home/                         프로그램과 업데이트 제어 전용
  layout.json                         현재는 더미 시험 표식과 분리된 데이터 경로
  test-public-policy.json             시험용 공개키만 있음
  catalog-trust.json                  기존 검증기의 서명 캐시·최고 순번
  current.json                        실제 실행 버전을 가리키는 별도 포인터
  locks/update.lock                   준비·적용·복구 직렬화
  locks/running.lock                  런처 생명주기 동안 유지할 OS 잠금
  transactions/<id>.json             old/new·서명 증거·단계·오류·시각
  health/<id>.json                    해당 트랜잭션의 시작 확인 응답
  store/                              기존 Installer 전용 독립 루트
    apps/creative-group-launcher/
      active.json                     준비 저장소의 메타데이터; 실행 포인터가 아님
      releases/<release_id>/
        receipt.json
        payload/Launcher.exe
        payload/launcher-package.json
        payload/<라이브러리·리소스>
    downloads/ staging/ locks/ ...

user-data/                            launcher-home과 겹치지 않는 별도 루트
  settings.json
  apps/<기존 다섯 프로그램>/...
  사용자 작업 파일
```

버전 폴더는 덮어쓰거나 자동 삭제하지 않는다. 준비 저장소의 active.json이 후보를 가리키더라도
실제 실행은 current.json을 사용하므로 다운로드 준비만으로 실행 버전이 바뀌지 않는다.
현재 구현은 두 루트 모두 `.test-results` 하위이며 서로 겹치지 않을 때만 허용한다.
실제 AppData, 프로젝트/Git, 관리자 저장소를 자체 업데이트 대상으로 지정할 수 없다.

향후 운영 경로 후보는 별도 `%LOCALAPPDATA%\SouthpawGames\ToolsLauncherRuntime`와 기존 사용자 데이터 루트다.
이번에는 해당 디렉터리를 만들지 않았다. 실제 운영용 경로·bootstrap 패키징은 별도 결정 사항이다.
특정 PyInstaller onefile/onedir 형식에 결합하지 않았다. ZIP에는 manifest와 EXE 상대 경로,
필요한 파일이 있으면 되며 라이브러리 디렉터리도 manifest에 명시할 수 있다.

## 패키지 manifest와 업데이트 식별

카탈로그 앱 ID는 다섯 도구와 별도인 `creative-group-launcher`다.
버전은 major.minor.patch 정수 3개로 비교하며 안정 버전만 지원한다. RC/개발 버전 순서는 구현하지 않았다.
현재 버전보다 낮은 버전과 동일 release_id는 거부한다. 같은 표시 버전의 다른 서명된 빌드는 허용한다.
적용 프로세스에서도 버전 조건을 다시 확인한다.

필수 파일 launcher-package.json:

```json
{
  "schema_version": 1,
  "app_id": "creative-group-launcher",
  "release_id": "launcher-r2",
  "version": "1.1.0",
  "files": {"Launcher.exe": "64자리 SHA256", "assets/layout.json": "64자리 SHA256"}
}
```

manifest 자체를 제외한 모든 실제 파일의 목록·해시가 정확히 일치해야 한다.
manifest 자체도 서명된 ZIP 해시와 설치 영수증의 파일 해시로 보호된다.
미등록 추가 파일, 누락·해시 불일치, 링크/정션, 사용자 설정·앱 데이터·Git/배포/제어 경로를 거부한다.
preserve_paths는 비어 있어야 한다. 런처 자체 업데이트에서 사용자 데이터 이전을 시도하지 않는다.
기존 안전 ZIP 추출 검사를 유지한다. EXE 파일명은 예시이며 특정 빌더 파일명으로 고정하지 않았다.

## 실행 순서와 확인 경계

1. 초기 시험 설치는 별도 create/bootstrap API로 서명된 r1을 검증해 만든다. 운영 초기 설치 기능이 아니다.
2. 기존 런처의 current.json과 receipt·manifest·실제 파일을 검증해 현재 릴리스를 읽는다.
3. prepare()가 기존 HttpProvider로 서명된 새 릴리스를 확인한다. unsigned LocalProvider는 거부한다.
4. 고정 정책과 격리된 신뢰 상태 경로가 맞는지 확인하고 기존 검증기의 재전송 방어를 사용한다.
5. 기존 Installer로 새 버전을 준비한다. 기존 current와 이전 버전은 유지한다.
6. 파일 목록/manifest까지 검증한 뒤 prepared journal을 기록한다.
7. 호출자는 사용자 적용 확인을 받아 request_apply(id, approved=True)를 호출한다.
   False면 cancelled이며 활성 버전은 바뀌지 않는다. 실제 런처 GUI의 확인 버튼은 아직 연결하지 않았다.
8. 기존 런처를 정상 종료한다. 안정 bootstrap은 런처 전체 수명 동안 running() OS 잠금을 유지해야 한다.
9. 종료 후 별도 `self_update_worker apply`를 실행한다. 잠금이 남아 있으면 변경 없이 거부한다.
10. 작업자는 서명 증거·현재 신뢰 목록·버전·파일을 다시 확인하고 switching을 먼저 기록한다.
11. current.json만 원자적으로 새 버전으로 전환한 뒤 probing을 기록한다. 실행 중 EXE를 덮어쓰지 않는다.
12. 별도 더미 시작 확인 프로세스의 종료 코드와 릴리스/EXE 해시/트랜잭션/nonce 응답을 확인한다.
13. 확인 성공 후 committed를 기록한다. 실패하면 이전 포인터로 복구한다.

이번 probe는 프로젝트의 신뢰된 Python 모듈이다. 다운로드 ZIP 안의 EXE나 Python 코드를 실행하지 않는다.
더미 payload 무결성과 시작 확인 프로토콜만 시험하며 실제 Qt 런처/DLL 초기화를 확인한 것은 아니다.
실제 EXE의 health-check 연동, 프로세스 인계와 최종 GUI 재시작은 패키징 전에 구현·검증해야 한다.

## Windows 잠금·중단·복구

포인터와 journal은 기존 atomic_json의 파일 flush/fsync 및 os.replace를 사용한다.
의도 기록 후 전환하므로 별도 recover 또는 다음 running() 진입이 미확정 전환을 복구한다.
prepared/requested는 자동 적용하지 않는다. preparing 중단은 준비 실패로 표시하고,
switching/probing/rollback_required는 검증된 이전 버전으로 보수적으로 되돌린다.
내부 준비 저장소의 미완료 작업은 기존 Installer.recover에 위임한다.
최종 committed 기록 쓰기가 실패해도 새 버전 성공으로 추정하지 않고 이전 버전으로 복구한다.

current가 old/new 어느 쪽도 아니거나 형식이 손상됐으면 자동 덮어쓰지 않는다.
journal 손상·복원 파일 잠금으로 복구하지 못하면 양쪽 버전과 journal을 보존하고 오류를 보고한다.
파일 잠금은 한 번 실패하면 자동 sleep/무제한 재시도를 하지 않는다. 잠금 해제 후 명시적으로 다시 요청한다.
새 버전 확인 프로세스가 시간 초과하면 해당 작업자가 생성한 Popen 객체의 자식만 종료한다.
기존 런처나 사용자 프로세스를 강제 종료하지 않는다.

이는 프로세스 중단 대응 기반이며 실제 전원 차단·저장장치 캐시 손실을 시험한 것은 아니다.
파일 시스템이나 저장장치 장애로 포인터 자체가 사라지면 자동 버전 선택을 하지 않고 수동 검토가 필요하다.
간헐적인 기존 journal WinError 5의 원인을 해결하거나 우회했다고 주장하지 않는다.

기술 근거:
[Python os.replace](https://docs.python.org/3/library/os.html#os.replace),
[Windows 파일 공유 및 삭제/이름 변경 잠금](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).

## 신뢰·운영 제한

새 서명 방식이나 독립 PKI를 만들지 않았다. 기존 Ed25519 정책/키 ID/서명된 카탈로그/순번 캐시를 사용한다.
준비한 서명 증거와 최신 로컬 신뢰 목록이 후보와 일치하지 않으면 적용하지 않는다.
오프라인 적용은 이미 검증한 준비물에 한정되며 서명 없는 패키지로 후퇴하지 않는다.
이전 버전 복구는 네트워크의 낮은 버전 수락이 아니라 실패한 전환의 원래 버전을 복원하는 것이다.

운영 공개키 목록은 여전히 비어 있고 실제 런처 UI/시작 경로를 변경하지 않았다.
운영 네트워크 자체 업데이트는 활성화하지 않았다. 실제 운영 키 생성·채택·직원 배포는 없다.
현재 worker의 hold/probe/강제 중단 옵션은 격리 경로를 강제하는 개발 시험 기능이다.
운영 helper로 전환할 때 이 인터페이스를 그대로 열면 안 되며 별도 검토가 필요하다.
동일 사용자 계정이 프로그램·포인터·신뢰 상태 전체를 변조하는 공격까지 방어하는 구조는 아니다.
HTTP/TLS 한계와 Windows SAC 코드서명 문제는 기존 서명 보고서의 미해결 항목으로 유지한다.

## 재현과 증거

```powershell
python -B -m unittest tests.test_self_update -v
```

의존성은 프로젝트 requirements를 사용한다. 이번 개발은 기존 격리 cryptography 경로로 실행했다.
테스트 fixture는 테스트 키와 MZ 더미 파일만 만들며 실제 프로그램 ZIP 없이 재현된다.
FileHttpProvider는 실제 HttpProvider 서명/다운로드 검증을 수행하되 파일로 응답하므로 소켓을 열지 않는다.
worker는 별도 Python 프로세스, probe는 그 자식 프로세스다. mock만으로 프로세스 전환을 주장하지 않는다.

`.test-results/self-update-20261105/rehearsal/RESULTS.local.json`에 별도 Windows 실파일 증거를 보존했다.
정상 전환은 r2/committed, 실제 포인터 파일 잠금은 WinError 5/r1/rolled_back,
전환 직후 os._exit(74)는 별도 복구 프로세스 후 r1/rolled_back,
시작 실패는 r1/rolled_back으로 확인했다. 사용자/다른 앱 시험 데이터 해시는 모두 유지됐다.
각 시나리오의 프로그램·journal·버전 폴더도 같은 rehearsal 아래에 남겼다.

실제 열린 핸들로 더미 EXE의 직접 교체가 차단되는 것도 검증했지만 이는 EXE 실행/메모리 매핑이 아니다.
자체 업데이트는 해당 더미 파일을 교체하지 않고 별도 버전의 포인터만 바꿨다.
실제 제품 EXE·SAC·설치된 Qt/DLL 잠금·직원 PC 성공을 주장하지 않는다.

## 변경 및 실제 패키징 전 남은 작업

추가: southpaw_tools/self_update.py, southpaw_tools/self_update_worker.py,
tests/self_update_support.py, tests/test_self_update.py, docs/SELF_UPDATE_FOUNDATION.md.
수정: README.md 안내만 추가. 기존 실행·게시·서명·앱 설치 엔진은 유지한다.

남은 작업은 안정 bootstrap/helper의 실제 EXE 패키징·신뢰 배포, 프로그램/데이터 최종 경로,
전체 런처 수명의 OS 잠금 연결, 사용자 확인 UI와 정상 종료/작업자 인계, 실제 EXE health-check와 재시작,
실제 DLL/EXE 잠금 및 전원 차단 검증, 운영 키·최소 순번·키 교체·복구 정책의 별도 승인이다.
고배율 GUI·SAC·백신·클린 Windows·장기 오프라인도 실제 직원 배포 전 확인해야 한다.
이번 구현을 실제 자동 업데이트 운영 준비 완료로 표시하지 않는다.

## 최종 검증·보존 결과

기존 125개 + 신규 24개, 총 **149개 테스트 통과**, 41.425초. Windows 전용 잠금 시험도 실행됐다.
기존 테스트를 제거하거나 건너뛰지 않았다. 기존 GUI 회귀는 Qt offscreen,
기존 HTTP 회귀는 loopback 임시 포트만 사용했다. 자체 업데이트 시험은 파일 전송 방식이라 소켓을 열지 않았다.

신규 검증은 정상 서명 준비·별도 작업자 적용, 서명/해시 불일치, 버전 후퇴와 같은 버전의 새 빌드,
사용자 취소·미승인 적용, 부분 다운로드, 실제 runtime 잠금, 실제 pointer WinError 5,
실제 더미 EXE 핸들 잠금, 세 전환 지점의 프로세스 강제 종료, 시작 실패/응답 불일치/시간 초과,
미등록/사용자 파일, 준비 후 변조, 복구 실패 후 재복구, 손상 journal/예상 외 포인터,
서명 증거 변조 및 committed 기록 실패의 보수적 복구를 포함한다.
준비 중단 단계 일부는 합성 journal 상태로 시험했고, 실제 프로세스 중단은 전환 세 지점에서 수행했다.
기존 Installer의 프로세스 중단 회귀도 그대로 유지했다.

보존 확인:

- 기존 다섯 프로젝트 292개 파일 및 HEAD/tags/status 동일.
- 존재하는 원본 승인 ZIP 4개 SHA256 동일. TagMaster 승인 ZIP은 이전과 같이 없어 미확인이다.
- 이전 LAN·서명·GUI 시험 증거와 distribution 기준 파일 952개 해시 동일.
- 이전 버전·다른 앱의 합성 설치 데이터·사용자 설정·작업 파일은 신규 시험에서도 해시 동일.
- 기존 실행/게시/서명/설치 엔진 파일과 기존 미커밋 변경을 보존했다.
- master / HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5`, remote 없음.
  새 파일과 README 안내는 작업 트리에만 남겼다. stage/commit/push/remote 변경 없음.
- 최종 읽기 전용 조회: 관리자 False, TCP8765 리스너 0개·시험 규칙 0개.
- 실제 사용자 설치·직원 PC·원본 ZIP·운영 키·LAN/방화벽·SAC·ACL·네트워크 정책 변경 없음.
- Windows Use 미사용. 다음 개발·실제 배포는 시작하지 않았다.

세부 로그는 `.test-results/self-update-20261105/full-tests.log`,
최종 파일/Git 대조는 FINAL_VERIFICATION.local.json,
외부 원본 대조는 existing-projects-verification.local.json에 있다.
