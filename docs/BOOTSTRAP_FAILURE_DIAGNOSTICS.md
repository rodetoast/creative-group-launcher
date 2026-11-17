# Bootstrap 접근 거부 정밀 진단

이번 변경은 원인 식별을 위한 진단 전용이다. B14의 실제 WinError 5 원인은 아직 미확정이며, health owner 삭제·프로세스 종료 간주·retry/sleep·복구 초기화·서명/ready 검증 완화를 추가하지 않는다.

## 기록 위치와 호환성

기존 `launcher-home/bootstrap-runs/<실행ID>.json`의 failed 이벤트와 `launcher-home/bootstrap-errors/<오류ID>.json`에 `diagnostics` 필드를 추가한다. 기존 events/phase/error_type/error 필드는 유지한다. error는 임의 예외 문자열 대신 예외 클래스와 errno/winerror의 안전한 요약이다. 원문 메시지가 토큰·nonce·파일 내용·전체 사용자 경로를 포함할 수 있기 때문이다. 기존 진단 CLI는 phase와 error_type을 계속 읽을 수 있다.

단계는 events의 phase와 diagnostics.failure.operations의 호출 경계로 구분한다. operation은 마지막 전역 상태가 아니라 실제 예외가 통과한 함수 경계에서 붙는다. 가장 안쪽 작업이 failure.operation이고, 바깥 호출은 operations에 추가된다. JSON 읽기처럼 LauncherError로 래핑된 경우 바깥 오류와 cause의 실제 I/O를 각각 기록한다. 알 수 없는 지점은 unclassified로 남기며 추정한 API를 기록하지 않는다.

예시(합성 실패, 실제 B14 재현 아님):

```json
{
  "error_type": "PermissionError",
  "error": "Bootstrap 작업 실패: PermissionError (errno=13, winerror=5)",
  "diagnostics": {
    "schema_version": 1,
    "captured_at": "UTC ISO8601",
    "failure": {
      "operation": "process_identity_open",
      "exception_class": "PermissionError",
      "errno": 13,
      "winerror": 5,
      "operations": [
        {"operation":"process_identity_open","api":"OpenProcess","pid":2920,"access":1052672},
        {"operation":"probe_owner_identity","api":"still_same","pid":2920}
      ]
    }
  }
}
```

실제 결과에는 최초 annotation 시각 occurred_at, traceback의 모듈·함수·줄, 가장 안쪽 Python 호출 python_call, 가린 filename/filename2, cause/context/suppress_context, secondary가 포함된다. occurred_at이 없는 미분류 예외도 captured_at으로 기록 시각을 구분할 수 있다.

## 구현 범위

- `bootstrap_diagnostics.py`: 명시적인 예외별 provenance, 안전한 직렬화, 보조 오류, 크기 제한. 스스로 파일을 쓰지 않는다.
- `windows_process.identity`: OpenProcess/WaitForSingleObject/GetProcessTimes/QueryFullProcessImageNameW의 기존 실패 반환 지점에 API/PID/access 기록. 조회 권한이나 87 처리, 신원 비교는 유지한다. 일반 세션 조회에도 쓰이는 함수이므로 process_identity_*라는 이름을 사용한다.
- `bootstrap.py`: owner 존재/읽기/신원, retained 검증, session mkdir/context, 세션 생성, recovery 호출, 각 이벤트 쓰기와 최종 오류 기록. 파일/프로세스 실행 순서는 유지한다.
- `self_update.py`: current 검증·current/proof/manifest 읽기·복구 경계를 표시한다.
- `common.py`: digest 파일 open/read, JSON stat/read, atomic mkdir/temp/write/flush/fsync/replace/cleanup, 잠금 open/초기화/획득/해제/close. 같은 순서와 API를 사용하며 성공 경로에 추가 파일 I/O가 없다.

정리나 failed 로그 쓰기가 원래 실패 도중 다시 실패하면 원래 예외를 재발생시키고 secondary에 보조 오류를 남긴다. 원래 오류가 없는 상태의 정리 실패는 그대로 실패한다. 실제 실패를 성공으로 바꾸지 않는다. 이 변경으로 과거 cleanup/unlock 오류가 원래 오류를 덮던 경우에는 원래 오류가 최상위가 된다.

failed 이벤트 저장도 실패하면 main의 기존 bootstrap-errors 기록에 원래 오류와 failed_log_write 보조 오류를 함께 보존한다. 오류 기록 경로까지 모두 쓰기 불가라면 파일 생성을 보장할 수 없다. 그 경우에도 오류 반환 1과 기존 GUI 오류 안내를 유지하며 기록 실패를 알린다. 파일을 만들기 위해 다른 사용자 폴더로 몰래 옮겨 쓰거나 권한을 변경하지 않는다.

## 개인정보와 상한

- 예외 원문·locals·명령행·임의 객체 속성·파일 본문을 저장하지 않는다.
- 경로는 `<launcher-home>`, `<data-root>`, `<source>`, `<python-runtime>` 별칭으로 바꾼다. 알려지지 않은 외부 경로는 `<outside-known-roots>`로 가린다. 세션/거래의 긴 hex ID와 원자 기록 임시명도 가린다.
- 오류별 operation 최대12, secondary 최대3, chain 깊이6/전체 예외 노드16, traceback 노드별 최근16프레임. JSON 진단 블록은 48KiB 초과 시 원래 오류의 상세를 우선 보존하고 chain을 생략한다.
- 기존 오류 이벤트/오류 파일을 재사용하므로 별도 상시 로그 파일이나 앱별 진단 파일을 추가하지 않는다. 기존 이력 보존을 위해 자동 삭제/회전도 하지 않는다.
- 콘솔 없는 직원용 PE Subsystem 2 빌드 옵션과 CREATE_NO_WINDOW는 유지한다.

## 테스트와 실행 경계

신규 `tests/test_bootstrap_diagnostics.py`는 합성 임시 파일·mock native API·mock 프로세스로 지점 식별, owner 보호, 예외 보존, 개인정보, 크기 제한, 정상 run 흐름을 검사한다. 기존 Setup 로그 테스트는 추가 필드를 허용하면서 초기 실패 로그와 traceback 보존을 확인하도록 갱신했다. 테스트 skip이나 예외 무시는 추가하지 않았다.

기존 Windows Bootstrap 회귀는 승인된 기존 무해한 fixture/Bootstrap 빌드의 전체 파일 해시를 대조해 사용한다. 새 진단 frozen EXE의 SPENT03 lifecycle 검증을 대신하지 않는다. 회사 앱/Dummy Tool EXE는 실행하지 않는다.

## SPENT03용 후보 제작 절차 — 이번에는 게시하지 않음

1. 이번 소스를 별도의 빌드 작업 사본으로 고정하고 해시 목록을 저장한다. 기존 운영/시험 서명 ZIP을 변경하지 않는다.
2. 승인된 시험 직원용 묶음에서 관리형 채널 `managed-channel.json`, 공개키 정책 `trusted_catalog_keys.json`, 기존 서명 seed를 그 사본에 복사한다. 저장소·공개키·최소 순번은 원래 시험 채널을 유지한다. 운영 키 생성/채택이나 새 카탈로그는 필요하지 않다.
3. 기존 `tools.build_windows`로 bootstrap role만 `--bootstrap-windowed` 및 승인 ICO 옵션으로 새 경로에 빌드한다. `CGLBootstrap.exe` 한 파일만 복사하지 말고 `_internal` 등 onedir 전체를 포함한다. seed/채널과 함께 새로운 직원용 진단 후보 폴더로 조립한다.
4. 이번 로컬 bare 빌드는 컴파일 확인용이다. 채널/seed가 없으므로 그대로 직원에게 전달하거나 기존 설치 폴더에 덮어쓰지 않는다. 버전 메타데이터는 기존 0.1.4이며 새 제품 버전을 확정한 것이 아니다.
5. 기존 `.test-results/ui-diagnostics-014-20261112/build-candidates.py`의 setup_payload 구성 및 `tools/build_setup.py`의 compile_setup을 재사용할 수 있다. 과거 build-candidates.py 전체를 그대로 재실행하면 키 접근/카탈로그 생성까지 수행하므로 진단 전용 포장 부분만 별도로 검토해 실행해야 한다. build_setup.prepare도 공식 0.1.1 seed 고정이므로 현재 0.1.4 시험 인계에 무조건 적용하지 않는다.
6. 새 Setup 후보는 별도 격리 등록/설치 경로를 사용하고, 기존 v0.1.4 설치·B14 원본을 덮어쓰지 않는다. Setup 버전/태그/카탈로그 순번 및 GitHub 전달은 후속 작업에서 결정한다. 이번에는 Setup/ZIP/Release를 제작·게시하지 않는다.
7. SPENT03에서는 새 격리 환경에서 업데이트→정상 GUI 종료→같은 Bootstrap 재실행을 확인한다. company 앱은 실행하지 않고 active/receipt·설정·합성 작업 파일 해시만 비교한다. 실패 시 bootstrap-runs/errors, current/거래 요약과 소스 해시를 기존 증거 수집 도구로 검토해 전달한다. context.json/nonce/토큰은 올리지 않는다.

GUI 업데이트 ZIP만 교체하면 고정 영역 CGLBootstrap.exe가 바뀌지 않는다. 후속 전달물에 진단 Bootstrap이 실제 포함됐는지 EXE SHA256과 PYZ 모듈 목록으로 확인해야 한다. B14 PID2920과 GUI PID2404는 과거 기록이며 새 PC의 현재 PID 조회 대상으로 사용하지 않는다.
