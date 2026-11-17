# 관리자 GUI 실제 GitHub Draft 검증 — 2026-11-06

## 결과

실제 관리자 GUI의 작업 스레드에서 기존 게시 엔진과 공식 gh CLI를 호출해 초안 생성, 업로드, 재다운로드 검증을 완료했다. Qt offscreen 환경에서 GUI 입력과 확인을 자동화했으며, 실제 외부 요청에는 모의 runner를 사용하지 않았다. 공개 전환은 수행하지 않았다.

- 저장소: `toast-source/creative-group-releases`
- 계정: 실제 `GET user` 결과 `toast-source`
- 시험 tag: `catalog-000003`, 서명된 sequence: 3
- 실제 Draft ID: `436091851`
- GitHub가 반환한 [초안 URL](https://github.com/toast-source/creative-group-releases/releases/tag/untagged-b0ecae9309b2e9813612) — 계정 로그인/권한 필요. 미공개 초안이라 URL에 임시 untagged 식별자가 포함된다.
- 최종 `draft=true`, Latest는 `catalog-000002` 유지.
- 기존 공개 r1/r2의 Release ID·tag·공개 상태·자산 ID·이름·크기·digest를 이전 기록과 대조해 일치 확인.

| 자산 | 바이트 | SHA-256 | 원격 자산 ID |
|---|---:|---|---:|
| catalog.json | 1143 | `627698fc19642796bb7cb3c05e0047e3c839da3318d5ee48e74de8c117b16dc8` | 715867783 |
| catalog.sig.json | 239 | `0eb3668cd5ae80a535aa5d18f60416be26f748146fc09e3ee660057273f1b5f2` | 715867815 |
| dummy--github-smoke-r3.zip | 274 | `e9986fe6efa72163d413390bbcada9dc9b1fb89694f50b0996e26eede4f518fe` | 715867842 |

정확히 위 3개만 업로드했다. 실제 GitHub 재다운로드 크기·SHA-256, 원격 asset digest, Ed25519 서명, ZIP 안전 추출 검사가 통과했다. 시험 ZIP은 기존 무해한 파일 fixture이며 EXE를 실행하지 않았다. 개인키·토큰·회사 프로그램 ZIP은 자산에 포함하지 않았다.

## 최소 연결 방식

- `admin_gui_model.py`: 명시적인 격리 표식 `github-dummy-v1`에 한해서 Dummy Tool 앱 목록을 사용한다. 기존 다섯 회사 프로그램의 APP_NAMES와 운영 메타데이터는 변경하지 않았다.
- `admin_github.py`: `DraftTransferGrant`를 명시적으로 주입한 시험 실행에서만 지정 저장소·격리 root·tag·sequence·시험 키 ID·ZIP 해시·release_id를 허용한다. GUI 설정에서 권한을 자동 로드하지 않는다.
- 기존 `AdminSession.review/publish`와 `admin.publish`로 작업 사본의 sequence 2 → 3 서명 묶음을 준비했다. 원본 r2 fixture 카탈로그는 보존했다.
- 실제 쓰기는 새 초안 1회의 POST와 그 응답으로 확인한 새 Draft ID의 자산 3개 업로드로 제한된다. 파일 경로·크기·해시를 재검사하며 중복 생성·재업로드·덮어쓰기를 차단한다.
- 기존 gh 인증을 사용한다. 토큰을 직접 조회하거나 명령행·로그·GUI 설정에 복사하지 않는다. 기존 공식 CLI 실행 파일 해시와 버전을 확인했다.
- 실제 전송 경로에서 PATCH·삭제·정식 공개·Latest 변경은 차단한다. GUI 공개 버튼도 비활성화된다. 일반 실행과 운영 게시 잠금은 유지된다.

## 실제 GUI 및 CLI

GUI의 서명 묶음 준비 → 초안 생성 → 자산 업로드 → 재다운로드 검증 버튼 경로를 실행했다. 사용자에게 이미 승인받은 확인 대화상자는 자동 응답했고, 파일 경로는 시험 자동화에서 GUI 상태에 주입했다. 기본 테마와 레이아웃은 유지했다.

- 실제 GUI 작업 CLI 호출: 15회, POST 4회(생성 1, 업로드 3), GET 11회. 모두 종료 코드 0 및 HTTP 2xx.
- 보존 확인을 위한 별도 읽기 전용 조회 2회. fixture 준비 시 읽기 전용 사전 조회는 별도 `preflight.json`에 기록.
- CLI 시간 초과/실행 실패 시 원격 반영 여부를 성공으로 단정하지 않고 로그를 보존하며 원격 상태 조회를 안내한다. 자동 재시도·삭제는 하지 않는다.
- 이번 실제 전송에서 오류·부분 업로드 없음. 실패 경계는 별도 모의 CLI 테스트로 검증했으며 실제 장애를 주입하지 않았다.
- 화면: `.test-results/admin-live-draft-20261106/gui-verified.png`
- 실제 호출·자산·작업 폴더: `live-gui-result.json`, `approved-asset-manifest.json`, `remote-preservation.json`

## 회귀 결과

- 관련 테스트 47개 통과.
- 기존 223개 + 신규 경계 테스트 10개 = 전체 233개 통과. 오류 0, 실패 0, skip 0.
- 기존 Bootstrap 12개 모두 통과. 사전 승인된 시험 EXE와 파일 해시를 다시 확인하고 격리 경로에서만 사용했다. 제품 런처 EXE·GitHub Dummy Tool EXE는 실행하지 않았다.
- 의도적 잠금 주입 4건이 관측됐으며 예상하지 못한 journal 교체 오류는 0건이었다. 간헐적 WinError 5의 근본 원인은 여전히 미확정이며 해결됐다고 판단하지 않는다.
- 신규 10개: Dummy 격리, 승인 경로/tag, 실제 전송 경계, 공개/Latest 차단, 기존 Release 쓰기 차단, 파일 변경 감지, 중복 차단, 키/권한 불일치, CLI 시간 초과, GUI 실제 전송 표시와 공개 잠금.

## 보존과 변경 파일

이번 제품 변경 3개:
- `southpaw_tools/admin_gui_model.py`
- `southpaw_tools/admin_github.py`
- `southpaw_tools/admin_gui.py`

신규:
- `tests/test_admin_live_draft.py`
- `docs/ADMIN_GITHUB_DRAFT_TRIAL.md`
- 격리 증거·시험 fixture·화면·실행 스크립트는 `.test-results/admin-live-draft-20261106/`에만 기록했다. 이 폴더는 Git 제외 대상이다.

기존 4,599개 파일의 해시와 비교해 위 제품 3개 이외의 기존 파일 변경·누락이 없었다. 이전 시험 기록, 기존 미커밋 변경과 운영 신뢰키를 보존했다. 다섯 외부 프로젝트의 292개 파일·Git HEAD·상태·tag 및 존재하는 승인 ZIP 4개 모두 기준과 일치했다. AsepriteTagMaster 승인 ZIP은 기존과 같이 미확인이다.

Git: master, HEAD `32afb846d0bc69b38203a259dad71180cd4a14b5`, remote 없음, staging 없음. 작업 트리는 기존 변경과 이번 변경이 있는 상태다. stage/commit/push/remote 변경 없음.

LAN 서버·방화벽·SAC·ACL·네트워크 프로필·실제 AppData 변경 없음. Windows Use 사용 없음. 정식 공개·직원 배포·운영 키 채택·다음 개발은 수행하지 않았다.

## 남은 경계

이 검증은 시험 공개키와 격리 Dummy Draft에 한정된다. GUI 기본 운영 게시 잠금과 실제 전송의 공개 차단은 유지된다. 실제 다섯 프로그램 게시, 운영 키 채택, 정식 공개는 별도 승인과 검증이 필요하다. 초안은 자동 삭제하지 않고 보존했다. EXE 실행과 직원 PC 배포를 검증한 결과가 아니다.
