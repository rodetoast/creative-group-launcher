# GitHub Releases 배포 전환 1단계

2026-11-06. GitHub 응답은 모의 데이터로 검증했다. 실제 GitHub 저장소 생성·Release 게시·자산 다운로드·계정 인증은 수행하지 않았다. 운영 키는 미채택이며 직원 GUI의 기본 LAN 연결도 변경하지 않았다.

## 전환 판단

GitHub Releases를 공개 배포 파일 전달 계층으로 사용하는 전환은 가능하다. 이번 `GitHubReleasesProvider`가 기존 서명 검증기와 Installer를 이용해 실제 더미 ZIP을 설치·업데이트하는 경로를 구현했다. 개발 PC 상시 실행, LAN 토큰 전달, 인바운드 포트·방화벽 운영이 일반 배포 경로에서 불필요해진다. 기존 LAN 기능과 모든 시험 자료는 삭제하지 않는다.

GitHub의 HTTPS는 전송 보안을 담당하고, 사전 신뢰 Ed25519 키는 카탈로그 게시자 검증을 담당한다. GitHub 로그인 여부나 API의 asset digest를 게시자 인증으로 대신하지 않는다. 이 서명은 Windows SAC 실행 파일 코드서명과 다르다.

## 기존 구조의 분류와 근거

| 분류 | 요소 | 처리·근거 파일 |
|---|---|---|
| 그대로 사용 | AppRelease, 카탈로그 스키마, 버전·release_id 비교 | `southpaw_tools/catalog.py`, `AppRelease.is_new_release` |
| 그대로 사용 | Installer, 앱 OS 잠금, journal·복구, 설정 보존 | `southpaw_tools/installer.py`, `paths.py` |
| 그대로 사용 | ZIP 크기·SHA-256·EXE 해시·안전 추출 | `southpaw_tools/archive.py`, Installer의 기존 호출 |
| 그대로 사용 | Ed25519 원본 바이트 검증, 서명 캐시·순번 방어 | `southpaw_tools/catalog_trust.py`, 키 정책 파일 변경 없음 |
| 그대로 사용 | 로컬 설치 목록·실행 경로 | `Installer.installed/installed_apps/resolve_launch/launch`; 네트워크와 분리 |
| 최소 연동 | HttpProvider 인터페이스와 validate_release | `southpaw_tools/github_provider.py`; 기존 HttpProvider의 엔진 경계 재검증을 상속, HTTPS 전송 부분은 별도 구현 |
| 후속 최소 변경 | 직원 UI Provider 생성·연결 설정·상태 문구 | `southpaw_tools/ui.py:473`의 LAN 생성 부분을 transport 선택으로 연결할 수 있음. 이번에는 미수정 |
| 그대로 사용 | 서명 캐시 선택 | UI와 GitHub Provider 기본값 모두 `catalog-trust.json`을 사용. LAN에서 전환하더라도 기존 순번 상태를 자동 초기화하지 않음. 격리 시험은 별도 verifier를 명시 주입 |
| 후속 최소 변경 | 관리자 GUI의 최종 전달 단계 | `admin_gui.py`, `admin_gui_model.py`; ZIP 검사·확인 모델을 유지하고 gh 단계만 후속 연결 |
| 보존 | 로컬 관리자 publish | `southpaw_tools/admin.py`; 승인 ZIP 검사·파일 복사·카탈로그 생성/서명 재사용. 지금은 로컬 저장소 게시만 담당 |
| 보존 | LAN 서버·토큰·방화벽 운영 파일 | `southpaw_tools/server.py`, `audit/lan_lab.py`, 기존 `.test-results/lan-*`; 일반 GitHub 배포에는 불필요하나 미삭제 |
| 보존 | 자체 업데이트·Windows Bootstrap·패키징 | `self_update.py`, `self_update_worker.py`, `bootstrap.py`, `runtime_protocol.py`, `windows_process.py`, `packaging/`, 기존 빌드·시험 결과 |
| 시험 전용 보존 | LocalProvider | 제품 Provider가 아니라 `tests/support.py`의 로컬 복사 fixture. 신뢰 우회용 운영 경로로 승격하지 않음 |

다섯 프로그램 메타데이터는 수정하지 않았다. TileNamer, ase_viewer, AsepriteTagMaster, Ase-PS Bridge Pro, Pivot_Fixer를 그대로 유지한다. TagMaster의 원본 승인 ZIP 미확인 상태도 유지하며 공개 게시를 활성화하지 않는다. Pixel Effect Maker·Pixel Motion Studio는 대상이 아니다.

## 저장소 선택

| 기준 | A. 소스 저장소 Releases | B. 배포 전용 공개 저장소 |
|---|---|---|
| 초기 관리 | 저장소 하나라 가장 단순 | 저장소 하나의 초기 준비 추가 |
| 소스와 배포 분리 | 런처 소스 태그·배포 묶음이 혼재 | 완료 ZIP·서명 목록만 명확히 분리 |
| 다섯 앱 버전 | 묶음 태그와 앱 버전 구분 필요 | 같은 구분이 필요하나 의미가 명확 |
| 릴리스 노트 | 런처 변경과 도구 변경이 섞일 수 있음 | 배포 묶음 노트 + 앱별 서명 노트 |
| 게시 권한 | 소스 저장소 쓰기 권한과 결합 | 배포 저장소 권한을 따로 관리 가능 |
| 원본 ZIP·시험 자료 | 명시적 자산 선택이 필요 | 동일. 전용 저장소여도 자동으로 안전해지는 것은 아님 |
| 공개 승인 | 소스·바이너리 각각 검토 필요 | 소스 공개 없이 바이너리 공개 여부를 따로 결정 |

**B를 권고한다.** 이름 예시는 `OWNER/creative-group-releases`이며 실제 저장소는 생성하지 않았다. 다섯 앱을 한 카탈로그로 관리하되 앱 version/release_id는 독립적으로 유지한다. GitHub Release 태그 예시는 `catalog-000001`이며 카탈로그 sequence와 일대일 대응시키는 운영 규칙을 권장한다.

공개 Releases를 비인증으로 읽을 수 있으므로 유료 서비스가 필수는 아니다. 각 자산은 2 GiB 미만이며 Releases에 총 크기·대역폭 제한은 없다고 안내되어 있다. 회사 소프트웨어 공개 승인·라이선스 확인은 별도다. 근거: [Releases 개요와 한도](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases), [공개 Releases REST API](https://docs.github.com/en/rest/releases/releases).

## 선택한 최소 배포 형식

Release 한 개는 현재 승인 배포 상태 전체를 나타내는 스냅샷이다.

```text
catalog-000001 (정식 Release)
  catalog.json
  catalog.sig.json
  tilenamer--<release_id>.zip
  ase-viewer--<release_id>.zip
  ps2ase--<release_id>.zip
  pivot-fixer--<release_id>.zip
  # TagMaster는 approved ZIP 확인 전 published=false, ZIP 없음
```

서명 형식과 AppRelease 필드는 변경하지 않았다. `package_name`, `package_size`, `sha256`, 실행 파일 상대 경로·해시, version, release_id, 릴리스 노트, 게시 상태가 기존 서명 범위다. 자산 이름·크기를 서명 내용과 대조하고, API digest가 있으면 추가 대조하며 다운로드 바이트는 항상 SHA-256을 다시 검사한다. GitHub가 자동 제공하는 Source code ZIP/tarball은 배포 ZIP으로 사용하지 않는다.

초기에는 **매 Release에 현재 published 앱의 모든 ZIP을 첨부**한다. 변경되지 않은 승인 ZIP도 바이트 그대로 복사한다. 게시자가 다섯 앱을 매번 새로 빌드하는 방식이 아니다. 과거 Release ZIP 참조는 업로드 중복을 줄이지만 앱마다 tag/asset ID/URL을 서명 스키마에 넣고 보존·삭제·다운로드 범위를 관리해야 한다. 현재 4개 ZIP 수준에서는 단일 Release 방식이 구현과 운영 검증을 단순화한다. 이전 ZIP 재사용 참조는 이번 Provider가 지원하지 않는다.

## Provider 동작과 경계

`GitHubReleasesProvider("OWNER/REPO", verifier=...)`는 공개 github.com만 지원하며 PAT·토큰 인자를 제공하지 않는다. 기존 환경의 gh 인증정보도 읽지 않는다. 시스템 프록시를 자동 사용하지 않고 기본 TLS 인증 검증을 유지한다.

1. `GET https://api.github.com/repos/OWNER/REPO/releases/latest` 조회. API 버전 `2026-03-10`.
2. GitHub가 선택한 최신 정식 Release를 사용한다. draft/prerelease 응답이면 거부하며 과거 목록으로 자동 fallback하지 않는다. 시간·태그 문자열·앱 버전으로 자체 정렬하지 않는다.
3. 자산 이름·ID 중복, 업로드 미완료, 크기·형식 오류를 거부한다. 최초 URL은 지정 저장소와 선택된 tag의 asset URL과 정확히 일치해야 한다.
4. 카탈로그 최대 4 MiB, 서명 4 KiB, API 응답 2 MiB. 1단계는 자산 최대 100개이며 목록 pagination은 구현하지 않았다.
5. raw catalog/signature 검증 후 published 앱의 ZIP 자산 이름·크기·선택적 digest를 대조한 다음에만 기존 verifier.accept로 신뢰 순번을 저장한다.
6. Installer의 기존 validate_release 경계와 download 직전 검증을 유지한다. 카탈로그 변경 중 선택한 AppRelease가 달라지면 실패한다.
7. 필요한 ZIP만 다운로드한다. HTTPS CDN redirect는 명시한 `release-assets.githubusercontent.com`/`objects.githubusercontent.com`의 GitHub release-asset 경로만 허용한다. 다른 호스트·HTTP·사용자정보 포함 주소를 거부하며 redirect 횟수도 제한한다. 실제 CDN 경로 호환성은 공개 더미 시험에서 확인해야 한다.
8. 선언 크기를 넘는 스트림·해시 불일치·취소·10분 초과를 거부하고 이 다운로드가 만든 부분 파일만 정리한다. 기존 target 파일은 삭제하지 않는다. 이후 기존 Installer가 다시 ZIP 검증·안전 추출한다.

404는 공개 저장소/정식 Release/자산 부재, 일반 403은 접근 거부, 403의 남은 호출 0 또는 Retry-After 및 429는 호출 제한으로 구분한다. 네트워크 오류도 별도 안내하며 자동 재시도를 추가하지 않았다. 비인증 API의 기본 한도는 **공인 IP당 시간당 60회**이므로 같은 회사 NAT의 직원이 한도를 공유할 수 있다. 현재 새로고침/설치 경계 검증마다 API를 재조회한다. ETag·조회 주기·호출 예산·프록시 지원은 실제 직원 UI 연동 전에 정할 사항이다. 근거: [호출 제한](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api), [자산 응답과 redirect](https://docs.github.com/en/rest/releases/assets).

기존 sequence 하한과 이전 신뢰 상태의 순번·동일 순번 바이트 불일치 방어는 그대로다. 새 클라이언트의 첫 조회나 최신 응답을 장기간 숨기는 공격에 대한 완전한 신선도 보장은 없으며 시각 만료 정책은 추가하지 않았다. 로컬 신뢰 상태 삭제/손상도 자동 복구하지 않는다. 서명·네트워크 오류가 기존 앱의 로컬 포인터·데이터를 지우지 않으며, 오프라인 설치를 자동 허용하는 fallback은 만들지 않았다.

## 로컬 더미 검증

`tests/test_github_provider.py`는 인메모리 GitHub API/HTTPS 자산 응답과 임시 테스트 키를 사용한다. 실제 ZIP·Installer·파일시스템·서명 검증은 사용하고 네트워크 소켓은 열지 않는다.

더미 r1 설치 → 합성 settings/작업 메모 생성 → 새 서명 sequence의 r2 노출 → 업데이트 감지 → r2 다운로드·설치 → active/receipt·파일 검증 → 네트워크 응답 제거 후 로컬 설치 조회를 시험한다. 합성 settings는 r2로 보존되고 작업 메모는 r1에 그대로 남는다. 실제 사용자 자료 보존·EXE 실행·오프라인 실행·GUI GitHub 연동 성공을 뜻하지 않는다.

정상·변조 서명, 알 수 없는 키, 서명 누락, 게시 세대 불일치, 자산 누락·중복·크기·digest·저장소/tag 불일치, 잘못된 ZIP 해시, 과거/동일 sequence 재전송, draft/prerelease, API 404/403/429, 네트워크 오류, 취소·초과 스트림·기존 다운로드 파일 보존·안전 redirect를 검증한다.

전체 회귀 결과는 아래 최종 검증 기록에 별도로 기재한다. 기존 journal WinError 5는 미해결이며 이번 Provider 구현으로 해결했다고 주장하지 않는다.

### 최종 검증 기록

| 검증 | 실제 결과 |
|---|---|
| 최초 신규 테스트 단독 | 24개 통과, 1.241초. 이후 서명 바이트 변조 1개 추가 |
| 최종 신규 GitHub 테스트 | **25개 모두 통과**, 전체 회귀 안에서 실행 |
| 기본 신뢰 상태 경로 최종 점검 | 기존 LAN과 같은 `catalog-trust.json` 사용을 명시하고 경로 검증 추가 후 신규 25개 재실행 통과 |
| 기존 161개 | 159개 통과·2개 오류, 기존 테스트 파일 변경 없음 |
| 전체 | **186개 실행, 184개 통과·2개 오류·skip 0**, 95.130초 |
| Windows Bootstrap | 기존 12개 모두 통과, 무해한 승인 fixture만 실행 |
| 실제 GitHub 다운로드·게시 | 미실시 |
| 실제 사용자 데이터·EXE·오프라인 실행·GitHub GUI | 이번 신규 경로에서는 미검증 |

근거: `.test-results/github-releases-20261106/github-tests.log`, `full.log`, `full-result.json`, `final-github.log`, `final-github-result.json`. 마지막 기본 경로 점검 후 전체 186개는 다시 반복하지 않았고 해당 Provider 25개만 재확인했다.

전체 오류는 `InstallerTests.test_cross_client_app_lock`의 최초 설치 download_verified 기록과 `SelfUpdateTests.test_unlisted_or_user_files_in_payload_rejected`의 setUp 최초 설치 preparing 기록에서 발생했다. 둘 다 기존 `Installer._phase → common.atomic_json/atomic_bytes → os.replace`의 실제 WinError 5이며 새 GitHub Provider를 호출하는 테스트가 아니다.

실패 후에만 관측하는 이전 조사 실행기를 새 격리 폴더에 복사해 사용했다. 예상 외 교체 오류 2건과 의도적 잠금 오류를 분리했고 `full/event-*/`의 journal 바이트·이벤트, `full/f-*/`의 테스트 파일 스냅샷을 보존했다. 새로운 진단 오류가 생겼다면 별도 로그로 취급하며 전체 통과로 바꾸지 않는다. 성공을 얻기 위한 전체 반복이나 WinError 5 제품 수정은 하지 않았다.

## gh 게시 흐름: 설계만, 실행하지 않음

현재 호스트 PATH에서 `gh`를 찾지 못했다. 설치·로그인·PAT 생성·계정 권한 조회는 하지 않았다. 따라서 **Codex+gh 게시가 이 PC에서 실증된 상태는 아니다.** 공식 CLI는 draft 생성·upload·download·최종 공개 전환을 지원한다. 후속 승인 뒤 개발자 PC에만 CLI 인증을 두고 직원 런처에는 배포하지 않는다.

게시 준비는 기존 `admin.publish`로 선택한 승인 ZIP을 별도 로컬 배포 작업 폴더에 검사·복사하고 새 version/release_id/notes와 증가 sequence를 서명하는 단계다. 개인키는 Git/작업 자산/공개 디렉터리 밖에 둔다. 현재 운영 키 미채택 상태에서는 실제 운영용 작업을 수행하지 않는다. 다섯 앱 중 변경 없는 항목은 이전 승인 메타데이터와 ZIP을 유지한다. 기존 distribution이나 이전 시험 catalog를 덮어쓰지 않는다.

아래는 **후속 승인 후 검토할 명령 형태이며 이번에 실행하지 않았다.** OWNER·검토된 commit·tag·작업 폴더는 후속 작업에서 구체화해야 한다. `--target`은 로컬 Git 원격을 변경하지 않지만 Release 생성 시 원격 tag가 생길 수 있으므로 별도 승인 범위에 포함한다.

```powershell
# 별도 승인을 받은 배포 저장소와 명시적인 원격 commit을 사용
gh release create $Tag --repo $Repo --target $ApprovedCommit --draft --latest=false --title $Title --notes-file $NotesFile

# $AssetFiles는 catalog.json, catalog.sig.json과 서명 목록의 published ZIP만 명시 열거
# 와일드카드, 프로젝트 전체 폴더, 개인키, 토큰은 사용하지 않음
gh release upload $Tag @AssetFiles --repo $Repo
gh release view $Tag --repo $Repo --json isDraft,tagName,assets

# 새로운 빈 검증 폴더로 각 자산을 내려받아 원본과 크기·SHA-256 대조
foreach ($AssetName in $ExpectedAssetNames) {
    gh release download $Tag --repo $Repo --pattern $AssetName --dir $VerifyDir
}

# 모든 파일 대조, 카탈로그 공개키 검증, 사용자 최종 확인 이후에만 공개
gh release edit $Tag --repo $Repo --draft=false --latest
```

실제 스크립트로 연결할 때는 각 gh 종료 코드를 확인하고 한 단계라도 실패하면 공개하지 않는다. `--clobber`, 무조건 재업로드·자동 재시도는 사용하지 않는다. API의 이름·크기·digest만으로 게시 전 검증을 끝내지 않고 다운로드한 바이트와 원본을 대조한다. 운영 CLI 인증 실패를 직원 PAT 추가로 해결하지 않는다. 게시 실패 초안은 자동 삭제하지 않고 상태를 보존해 보고한다.

근거: [draft 생성](https://cli.github.com/manual/gh_release_create), [자산 업로드](https://cli.github.com/manual/gh_release_upload), [다운로드](https://cli.github.com/manual/gh_release_download), [최종 공개 전환](https://cli.github.com/manual/gh_release_edit). 관리자 GUI는 ZIP 선택·검사·비교·최종 확인을 유지하고 이 전달 단계의 상태·종료 코드 표시만 후속 연결하는 것이 적절하다. 이번에는 GUI를 수정하지 않았다.

## 변경·보존과 후속 승인

신규 제품 파일은 `southpaw_tools/github_provider.py`, 신규 테스트는 `tests/test_github_provider.py`, 신규 문서는 이 보고서다. 이전 제품 파일·기존 테스트·스키마·신뢰키·requirements·UI 기본 연결을 수정하지 않았다. 진단 실행기와 결과는 `.test-results/github-releases-20261106/`에만 생성했다.

기존 소스·ZIP·시험 기록·패키징 결과의 보존은 이 폴더의 before-files/preservation 및 existing-projects 자료로 대조한다. Git master, 최초 HEAD, 기존 미커밋 변경, remote를 유지하며 stage/commit/push/branch 변경은 하지 않는다.

`existing-projects.json`은 기존 다섯 프로젝트 292개 파일·HEAD·태그·Git 상태 및 원본 승인 ZIP 4개 일치를 확인했다. TagMaster ZIP 미확인도 그대로다. 프로젝트 작업 시작 전에 해시를 저장한 4,332개 파일은 기존 제품 코드·시험 파일·이전 LAN/서명/GUI/자체 업데이트/Windows 패키징 결과를 포함한다. 최종 해시 대조와 Git 상태 차이는 `preservation.json`, `git-after.txt`, `git-final.json`에 보관한다. 이번 세 신규 파일 외에 이전 파일은 변경하지 않는다.

실제 GitHub 더미 Release 시험에는 다음 별도 승인이 필요하다: 사용할 계정·공개 더미 저장소와 권한, 무해한 더미만의 공개 게시/원격 태그 생성, 개발자 CLI 설치·정상 인증, 테스트 공개키의 격리 주입, 시험 범위·정리 방법. 운영 키 채택·회사 ZIP 공개·실제 직원 배포는 각각 별도 결정이다. 다음 단계로 자동 진행하지 않는다.
