# 업데이트 UX와 시작 화면 (2026-11-20)

기준은 운영 Toast9, Rod10과 Rod GUI 0.1.7이다. 구현은 운영 기록 커밋 `a53f761` 위의 `codex/startup-update-ux-20261120`에 있다. 운영 릴리스, 서명 자산, 직원 환경은 건드리지 않았다.

## 업데이트 확인

기존 `MainWindow.refresh()`는 GitHub 호출을 시작할 때 성공 여부에 관계없이 `_github_next_check = now + 300`을 설정했다. `render()`가 이 시각까지 버튼을 비활성화했고 `_finished()`는 작업을 비워도 그 시각을 갱신하지 않았다. 이후 4초 UI 갱신에서만 버튼을 다시 활성화할 수 있었다. HTTP 403 rate limit/429의 경우 같은 변수에 한 시간 제한을 적용했다. 앱 선택 항목이 없으면 `render()`가 버튼을 갱신하기 전에 반환하는 경우도 있었다.

수동 확인은 이전 요청 시각에 관계없이 새 Provider에서 Latest를 재조회하고 API에 `Cache-Control: no-cache`를 보낸다. 자동 확인에만 간격과 rate-limit 대기를 적용한다. 같은 창의 조회와 설치·전환 등 공유 작업이 진행 중일 때는 중복 요청을 막으며, 완료·오류·시간 초과 후 활성 상태가 복구된다. 실패 시 온라인 설치는 차단하고 검증된 기존 설치의 로컬 실행은 계속 허용한다.

런처 설치/최신 버전은 상단에, 선택 앱의 설치/최신 버전은 상세 정보에 표시한다. 오프라인의 앱 버전은 등록 버전으로 표시한다. Toast Bridge는 `Rod 채널로 업데이트` 및 `전환 단계`로 구분한다. Rod 최종 목표는 고정 저장소 ID 1462539740, 전용 catalog ID와 기존 운영 공개키를 사용한 순번 10 이상의 온라인 검증에 성공한 경우에만 표시한다. 조회에 실패하면 Rod 최신 버전 미확인으로 표시한다. 이 정보는 별도 미리보기 신뢰 상태를 쓰며, Bridge가 적용하는 서명·해시·순번과 트랜잭션은 기존 경로에서 다시 검증한다.

## 시작 로딩 창

배포된 Bootstrap은 로컬 활성 버전과 보관 ZIP·설치 파일을 검증한 후 GUI 프로세스를 띄운다. 초기 설치는 seed 등록도 수행한다. GUI의 Qt Splash만으로는 이 앞쪽 대기 시간을 덮을 수 없다.

새 빌드의 `CGLBootstrap.exe`는 PyInstaller 진입점에서 Python 업데이트 모듈과 Qt를 가져오기 전에 Win32 시작 창을 표시한다. OS가 EXE를 로드하기 전에는 화면을 표시할 수 없다. 창은 상시 최상위 또는 포커스 획득 플래그 없이 동작한다. 정상 GUI의 기존 `ready/confirmed`가 완료되면 시작 창을 닫으며 인터넷 카탈로그를 기다리지 않는다. 사용자가 업데이트한 뒤 구 GUI가 종료되면 다시 표시한다. worker와 health GUI는 별도 시작 창을 띄우지 않으며 실패한 새 GUI의 롤백 절차는 유지된다. 복구까지 실패하면 창을 닫고 기록을 남긴 후 재시도 또는 종료를 선택할 수 있다. 진행률의 분모가 없는 작업은 시작 상태 텍스트로 표현한다.

배포된 직원 Bootstrap은 GUI 업데이트가 교체하는 파일에 포함되지 않는다. 신규 GUI는 기존 Bootstrap에서도 관리형 GUI 검증 이후 Qt 로드와 화면 구성 동안 시작 창을 사용한다. 최초 프로세스 시작 직후부터 안내하려면 안정 Bootstrap 자체를 교체해야 한다. 현재 지원 가능한 선택은 기존 설치 경로와 데이터 루트를 보존하는 별도 승인된 Setup 업그레이드다. 실행 중인 EXE 덮어쓰기나 Bootstrap 자동 교체 기능은 추가하지 않았다. 원래 Toast 바로가기의 시작 구간까지 표시하려면 그 바깥쪽 Toast Bootstrap에도 적용해야 한다. Rod GUI 업데이트로 바깥쪽 Toast Bootstrap은 바뀌지 않는다.

## 차세대 UI 비교

2026-11-20 기준 공식 자료의 안정 계열은 Qt 6.12.0, React 19.3, Tauri 2.12.7, Electron 45.4.1, Windows App SDK 2.7.0이다. 이번 시험은 기존 배포용 PySide6 6.11.0으로 수행했다. 재배포 전에는 사용 모듈별 라이선스와 함께 배포하는 런타임의 제3자 고지·라이선스 파일을 확인해야 한다. [Qt 릴리스](https://doc.qt.io/qt-6/qt-releases.html) · [React 버전](https://react.dev/versions) · [Tauri 릴리스](https://github.com/tauri-apps/tauri/releases) · [Electron 릴리스](https://releases.electronjs.org/release) · [Windows App SDK](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/downloads)

| 기술 | 엔진·프로토콜 결합 및 업데이트 버튼 적용 | Windows 런타임·크기·운영 조건과 라이선스 |
|---|---|---|
| **Qt Widgets 개선** | 기존 창과 Python 엔진을 유지한다. 현재 서명된 onedir/manifest 경로로 GUI 배포 가능. 변경·위험이 가장 작다. | 기존 Python·Qt 런타임을 동봉한다. 새 브라우저 엔진이 필요 없다. PySide6/Qt의 LGPLv3/GPLv3 또는 상용 조건과 모듈별 고지를 확인한다. [Qt 라이선스](https://doc.qt.io/qt-6/licensing.html) |
| **Qt Quick / QML** | Python 프로세스와 관리 세션을 유지한다. Qt 모델·슬롯 경계로 현재 `MainWindow`의 작업 스레드와 상태 관리를 옮겨 기존 엔진을 호출한다. 현재 버튼 배포 구조를 쓸 수 있어 차세대 후보로 선정했다. | QML 플러그인·Quick DLL을 서명 패키지에 포함한다. 렌더링과 접근성, DPI, 테마 검증이 필요하다. Qt 모듈별 LGPL/GPL 또는 상용, 특별 GPL 모듈 확인. 이번 시제품에는 Quick 3D를 사용하지 않았다. [Qt Quick](https://doc.qt.io/qt-6/qtquick-index.html) |
| React + TypeScript + Qt WebEngine / WebChannel | Python 호스트가 세션과 설치를 관리하면 기존 버튼의 서명 패키지에서 교체할 수 있다. React 번들과 좁은 타입 지정 WebChannel API가 추가된다. 로컬 번들만 로드하고 임의 URL/명령을 허용하지 않아야 한다. | Chromium 엔진·보조 프로세스·리소스를 같이 배포해야 한다. QT/Chromium 패치와 제3자 고지가 추가된다. React MIT와 Qt 라이선스를 함께 확인한다. [WebEngine 배포](https://doc.qt.io/qtwebengine/qtwebengine-deploying.html) · [WebEngine 라이선스](https://doc.qt.io/qtforpython-6/overviews/qtwebengine-licensing.html) · [React 라이선스](https://github.com/react/react/blob/main/LICENSE) |
| React + TypeScript + Tauri 2 | Rust 호스트와 Python 엔진 간 명시적 IPC 또는 엔진 이전이 필요하다. Tauri 자체 갱신으로 현재 서명·거래를 대체하지 않는다. 기존 버튼 배포에는 관리 프로세스와 서명 onedir 계약의 호환 구현이 필요하다. | WebView2 Evergreen 공유 런타임 덕분에 패키지에 Chromium을 모두 담을 필요는 없으나 미설치·오프라인 환경에 대한 별도 지원이 필요하다. Tauri MIT/Apache-2.0, frontend 및 WebView2 배포 조건 확인. [Tauri 배포](https://v2.tauri.app/distribute/windows-installer/) · [WebView2 배포](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution) |
| React + TypeScript + Electron | Chromium/Node 메인 및 렌더러에서 기존 엔진을 IPC로 호출해야 한다. 세션 증명, 종료 코드, 프로세스 수명 및 복구를 별도로 맞춰야 기존 버튼 사용이 가능하다. | Chromium·Node 동봉으로 시작/메모리/배포 비용이 높을 것으로 예상한다. Electron MIT 및 Chromium·Node 제3자 라이선스, 샌드박스와 보안 업데이트 운영이 필요하다. [Electron 보안](https://www.electronjs.org/docs/latest/tutorial/security) · [Electron 라이선스](https://github.com/electron/electron/blob/main/LICENSE) |
| C# WinUI 3 또는 WPF + WebView2 | .NET 호스트에서 Python 엔진 연동 또는 재작성과 관리 프로토콜 구현이 필요하다. 기존 버튼 사용 여부는 배포 모델과 호스트 프로토콜 검증에 달려 있다. | WinUI 3는 Windows App SDK, WPF는 .NET Desktop Runtime 의존 또는 self-contained, 두 후보에서 웹 UI 사용 시 WebView2도 필요하다. 소스 라이선스와 런타임 재배포 조건을 별도로 확인한다. [SDK 배포](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/deploy-overview) · [.NET 배포](https://learn.microsoft.com/en-us/dotnet/core/deploying/) · [WebView2 배포](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution) |

**권장 순서**는 Widgets로 이번 UX를 적용하고, 다음 UI 현대화는 QML로 검토하는 것이다. 현재 `MainWindow`는 카탈로그 상태·선택·작업 스레드·설치와 연동하지만 실제 검증과 파일 작업은 `Installer`, `GitHubReleasesProvider`, `SelfUpdater`, `ManagedSession`이 맡는다. UI를 교체할 때 화면 액션을 좁은 컨트롤러로 옮기고 기존 서비스를 재사용한다. 기존 `CreativeGroupLauncher.exe` 이름과 관리형 세션, `ready/confirmed`, 업데이트 종료 코드 20, signed onedir/manifest, receipt와 데이터 경로를 유지하면 QML 또는 Qt WebEngine 기반 GUI를 기존 버튼으로 배포할 수 있다. 도입 여부는 패키징된 후보의 프로토콜과 Windows 실기동을 별도로 확인해 결정한다. React Flow, Dagre, Dockview, ProseMirror, Roslyn, Unity Player는 이번 런처 화면에 필요한 그래프 편집·도킹·문서 편집·컴파일·게임 엔진 기능이 없어 도입하지 않았다.

## 시제품 및 개발 검증

`python prototypes/qml-launcher/preview.py`로 Qt Quick 시제품을 실행한다. 회사 프로그램 5개는 샘플 데이터이며 로컬 상태·네트워크·운영 설치를 사용하지 않는다. 목록 선택, 상세, 다크·라이트 및 확인 상태가 있다. `Loader.Ready`에서 로딩 레이어가 사라지고 `--check <새 파일>`은 이후 첫 프레임에서 준비 신호를 기록한다.

| 개발 PC 격리 관측 | 시작부터 준비까지 | ZIP | onedir | EXE |
|---|---:|---:|---:|---:|
| 배포 Rod 0.1.7, 기존 Bootstrap | 메인 창·confirmed 5.05초 | 52,650,066 B | 128,189,666 B | 2,335,234 B |
| 새 Bootstrap + 기존 서명 Rod 0.1.7, 사전 설치 | Splash 0.38초, 메인 5.28초 | 기존 서명 ZIP 사용 | 기존 서명 GUI 사용 | 기존 서명 GUI 사용 |
| 새 Bootstrap + 기존 서명 Rod 0.1.7, 첫 seed 설치 | Splash 0.39초, 메인 7.69초 | 기존 서명 ZIP 사용 | 기존 서명 GUI 사용 | 기존 서명 GUI 사용 |
| Qt Quick 샘플, Essentials 기반 onedir | 첫 준비 프레임 중앙값 0.45초 (3회) | 56,622,784 B | 149,459,923 B | 1,776,532 B |

시제품은 설치/해시/세션 복구가 없으므로 첫 프레임 시간으로 제품 속도 향상을 추정할 수 없다. 제품 시간은 각 1회 관측이며 Windows 파일 캐시 차이의 영향을 받는다. 전체 PySide6 QML 디렉터리를 PyInstaller 기본 훅으로 수집하면 필요 없는 WebEngine까지 포함되어 ZIP이 163,911,047 B였다. 비교 표는 기존 `PySide6_Essentials`와 `shiboken6` wheel 파일만 격리한 뒤 같은 PyInstaller 6.22.3으로 만들고 WebEngine DLL이 없음을 확인한 결과다. 운영 프로세스 메모리의 정량 비교는 수행하지 않았다.

- 자동 44개 통과. `python -B -m unittest tests.test_github_ui tests.test_bootstrap_ack tests.test_github_provider`로 수동 재조회, 동시 요청 차단, 응답 시간 초과/실패, rate-limit 자동 대기, Rod 미리보기 신뢰 바인딩, 기존 Bootstrap ACK 및 Provider 검증을 확인했다.
- 격리 소스 Qt UI에서 공개 Toast9와 Rod10을 두 번 연속 조회해 버튼 재활성화와 Bridge/최종 버전 구분을 확인했다.
- 새 Bootstrap을 Windows에서 패키징해 정상 실행·최초 signed seed 시작, Splash의 비활성·비최상위 플래그, confirmed 후 제거와 종료 코드 0을 확인했다. 합성 초기화 오류는 재시도/종료 대화상자, 기록 파일, 종료 코드 1을 확인했다. 수동 재시도 후 성공 복구와 새 Bootstrap의 실제 온라인 업데이트 후 Splash 재표시는 이번 범위에서 실기동하지 않았다. 기존 Bridge 전체 시험은 재실행하지 않았다.
- 변경된 Widgets EXE의 격리 화면 생성과 QML 패키지 첫 준비 프레임을 확인했다. 배포할 버전·서명 ZIP과 Setup은 준비하지 않았다.

다음 결정은 Widgets UX를 GUI 업데이트로 먼저 배포할지와, 안정 Bootstrap까지 바꾸는 별도 Setup 업그레이드를 승인할지다. QML의 운영 적용은 비교 결과를 바탕으로 별도 결정한다.

## Rod GUI 0.1.8 정식 공개 (2026-11-20)

사용자 승인으로 [Rod 카탈로그11](https://github.com/rodetoast/creative-group-releases/releases/tag/rodetoast-catalog-000011)을 정식 공개하고 Latest로 지정했다. 기존 저장소 ID `1462539740`, Release ID `452397424`, 카탈로그 식별자 `creative-group-launcher-rodetoast-1462539740`, 순번 `11`이다. 기준 소스는 `2c0554c014b47e9a9ec40de63aa0f38c04c438b9`이며 격리 빌드에서 제품 버전을 0.1.8, release_id를 `rodetoast-launcher-0.1.8`로 지정했다. 공식 Windows GUI onedir 역할만 빌드했으며 Bootstrap·Setup·QML 시제품은 운영 자산에 포함하지 않았다.

기존 Ed25519 운영 공개키 ID `1efdfb848bb31e3fa5c07095f952c08d920be77253261fbf2742755341f018e0`을 사용했다. Draft와 공개 HTTPS에서 자산 8개를 다운로드하여 파일 크기, SHA-256, 서명을 확인했다. GUI EXE SHA-256은 `4cc2c8412d084284268e538af61312747a6c916554ce403f8e610a20d3fd9426`이다. Rod10 및 이전 릴리스와 Setup, Toast Latest9·직원용 Setup은 게시 전후 일치했다. 회사 앱 5개는 서명된 레코드 및 ZIP 바이트 모두 Rod10과 동일하다.

| 자산 | 바이트 | SHA-256 |
|---|---:|---|
| ase-viewer--0.5.8.4-team-3bf37dd.zip | 22085231 | 2532c273c4cf9930cf882ef1f84cae55c9a97479a69123431560b1299edec2d2 |
| catalog.json | 9502 | e50daaac2bd0292fa4edb9f845df1d5026f1d1c0ee7e7b26a0cb3b1966ca62a0 |
| catalog.sig.json | 239 | 355ee2d979bdb6bb0818ccbf84ac6b4c6e89742fa7e3a2a780ff409631287cfc |
| creative-group-launcher--rodetoast-launcher-0.1.8.zip | 52680721 | 6b2a2ab8036c52f3fcff75507c1d94310e049e8994ac55e2cef8ce2a41ffbaa4 |
| pivot-fixer--0.3.3-team-80b84c9.zip | 20709116 | 214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361 |
| ps2ase--0.3.6-team-6e84645.zip | 66252089 | 1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9 |
| tag-master--0.4.0-team-7263f8d.zip | 38813495 | 80865038ddab9a1b9050d04cbb48cb777edf4e6419caafb05b8b51c0f6962299 |
| tilenamer--0.1.6-rc3-8ba7a1e.zip | 54046715 | aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4 |

격리된 Bridge 설치의 기존 Rod Bootstrap을 사용했다. 이전 Rod 0.1.7의 코드가 순번10에서 서명된 로컬 후보11을 준비하고, 기존 Windows worker가 0.1.8을 적용해 거래를 `committed`로 기록했다. 실제 0.1.8 창을 열어 GUI 프로세스 소유의 비최상위·포커스 비획득 시작 창이 표시되고 `confirmed` 시점에는 사라진 것을 확인했다. 정상 종료 코드는 0이다. 기존 Bootstrap, Toast 포인터, Rod 0.1.7 보관 ZIP/receipt, 합성 설정과 작업 파일은 보존됐다. 실제 직원 PC와 회사 앱 설치는 이번 시험 범위에 포함하지 않았다.

게시 후에는 운영 0.1.7의 Provider 경로로 공개 Rod11을 수락하고 ZIP 해시와 11→10 롤백 차단을 확인했다. 기존 Bridge 0.1.6 코드의 공개 HTTPS 경로를 별도로 실행해 처음 Rod에 진입할 때 사전 준비 또는 중간 0.1.7 없이 0.1.8을 검증·초기화하고 기존 하위 Rod Bootstrap 호출까지 도달함을 확인했다. 이 마지막 확인은 프로세스 호출 경계만 대체했으며 실제 Windows GUI 기동은 앞의 서명 후보 시험에서 확인했다. 전체 Toast 버튼·Windows 인계는 기존 성공 증거를 재사용했다.

기존 Rod 직원은 런처에서 업데이트를 한 번 승인한다. 아직 전환하지 않은 Toast 직원은 기존 Toast GUI에서 Bridge 업데이트를 한 번 승인하면 된다. 처음 Rod로 진입하는 Bridge는 현재 0.1.8을 받는다. 배포된 구 Toast GUI의 버튼 문구는 전환 전에는 이전 방식으로 표시된다. 새 UX는 0.1.8 실행 후 적용된다.

## 안정 Bootstrap 자동 갱신 설계 경계

이번 공개는 GUI 초기화 구간의 시작 창을 제공한다. 기존 바로가기에서 Bootstrap이 서명·파일을 검증하는 구간은 안정 Bootstrap 교체 없이는 표시되지 않는다. 기존 직원에게 Setup 재설치를 요구하지 않는 자동 갱신은 별도 설계·승인 대상으로 유지한다. 사전 신뢰된 서명 정책으로 별도의 Bootstrap 패키지·manifest·파일 해시를 검증하고, 실행 프로세스가 정상 종료한 뒤 외부 교체 작업자가 기존 진입 경로를 유지해야 한다. 새 시작 확인을 받기 전까지 이전 Bootstrap을 보관하고 오류·중단 시 원복하는 경계를 설계해야 한다. 사용자 데이터·회사 앱 store·기존 단축 경로는 거래에서 제외한다. 이번에는 자동 Bootstrap 교체를 구현하거나 게시하지 않았다.

## GUI 0.1.8 시작 창 실사용 보완 (2026-11-20)

운영 GUI 0.1.8에서 시작 창은 `ManagedSession` 생성, EXE 및 활성 릴리스 검증, 실행 잠금 획득과 `current()` 재확인 뒤에서야 표시된다. 기존 Bootstrap도 그 전에 journal 복구와 활성 릴리스·보관 ZIP·설치 파일 검증을 수행한 뒤 GUI 프로세스를 생성한다. GUI의 시작 창은 `MainWindow` 생성 직후, `show()` 전 닫혔다. 따라서 GUI 초기화의 후반부만 보였으며, 사용자 보고의 약 0.1초는 코드에 설정된 표시 시간이 아니다. 운영 0.1.8 격리 로그에서 정상 GUI process→ready 간격은 1.240초, confirmed는 1.328초였으며, 이 기록은 시작 창 자체의 노출 시간을 측정한 수치가 아니다.

일반적인 직접 Rod 기동 로그는 0.1.8 세션 하나의 `starting → running → closed(0)`였다. 업데이트 승인 후 기존 GUI 종료와 worker 적용·새 GUI 생성은 정상 동작이며, Windows에서 실행 중인 EXE를 바꾸지 않는 기존 안전 경계다. 기존 Toast 바로가기는 Bridge 프로세스를 중간에 실행한다. 이미 공개된 Bridge는 자체 창을 먼저 표시하고 Rod Bootstrap을 실행하는 동안 이를 숨길 수 있으므로 짧게 사라지는 창의 다른 가능한 원인이다. 사용자가 관찰한 PC의 GUI/Bootstrap 로그를 수집하지 않았으므로 두 경로를 그 PC에서 특정하지는 않았다.

수정 GUI는 기존 Bootstrap이 프로세스를 띄운 직후, Qt·`ManagedSession` 가져오기와 서명/파일 검증 전부터 기존 Win32 시작 창을 표시한다. 가벼운 세션 파일의 제한된 읽기는 일반 시작·숨은 health·Bootstrap 자체 Splash를 구별하는 화면용 힌트다. 세션 인증이나 권한 확인을 대신하지 않는다. 메인 창을 활성화하지 않고 표시한 뒤 Windows의 창 순서에서 메인만 Splash 바로 아래에 배치한다. 첫 실제 메인 창 Paint 이벤트 처리가 끝난 뒤 Splash를 닫고 기존 `ready`를 발행한다. 기존 Bootstrap의 작업표시줄 창 열거는 그 뒤에 동작한다. 인터넷 갱신은 기존 `confirmed` 이후이며, 시작 표시의 최소 지속 시간을 추가하지 않았다. 검증 실패나 정상 종료에서는 시작 창을 정리하고 기존 오류·복구 정책을 유지한다.

### 기존 직원의 안정 Bootstrap 자동 갱신 설계

GUI 패키지만으로는 바로가기에서 Bootstrap이 시작된 시점부터 GUI가 생성되기 전까지의 구간을 표시할 수 없다. 아래는 그 구간을 해결하는 승인 전 설계이며, 기존 운영의 시작 파일에는 반영하지 않았다.

1. 새 GUI가 이해하는 **함께 적용되는 Bootstrap 후보**를 일반 업데이트에 포함한다. 다음 정식 GUI ZIP의 운영 카탈로그 서명과 ZIP SHA-256으로 Bootstrap 교체 명세·고정 도구·새 런타임 전체를 함께 보호한다. 명세에는 채널·설치 형태·기대 기존 진입 EXE 해시·대상 Bootstrap 세대·파일별 해시·허용 차기 GUI를 명시한다. GUI 업데이트 확인에서 같이 적용되는 범위를 알리고, 명세와 설치 경로 검사에 통과한 경우에만 기존 업데이트 버튼으로 준비한다. 구 UI에서 이 승인을 전달할 수 없으면 먼저 일반 GUI 업데이트로 기능을 도입한다. Setup 재설치는 요구하지 않는다.
2. 기존 바로가기가 가리키는 `CGLBootstrap.exe` 경로를 유지한다. 새 진입 EXE는 실행 파일과 DLL을 한꺼번에 부분 교체하는 대신, 같은 볼륨의 별도 버전 폴더에서 검증된 Bootstrap 런타임을 연다. 현재 레이아웃·활성 포인터·서명 증거와 `--data-dir`의 의미를 유지한다. 기존 `_internal`과 설치 영수증은 복구용으로 유지한다.
3. 서명된 고정 교체 작업자가 활성 GUI·Bootstrap·worker의 PID와 이미지 경로를 확인하고 모두 정상 종료한 뒤 같은 볼륨에서 진입 EXE만 백업을 포함한 원자적 교체로 바꾼다. 실행 중인 EXE는 덮어쓰지 않는다. 경로는 현재 설치 루트에 고정하고 기존 잠금과 새 교체 잠금으로 중복 실행을 막는다. 시작 경로의 쓰기 권한이 없거나 서명·해시·세대·파일 신원에 문제가 있으면 준비 상태로 돌아가며 기존 진입점을 유지한다.
4. 독립 Rod 설치와 Toast를 거친 설치를 별도로 식별한다. Toast Bridge에 포함된 하위 `rod/CGLBootstrap.exe`는 Bridge ZIP의 파일 해시 검사 대상이므로 덮어쓸 수 없다. 이 유형은 기존 사용자 바로가기의 **바깥 Toast 진입점**에 서명된 호환 진입 EXE를 적용하고, 기존 하위 Rod 홈과 사용자 데이터 루트에만 연결한다. 기존 Toast EXE·`_internal`, 검증된 하위 런타임과 양쪽 trust/current/receipt는 복구 동안 보관한다. 신규 런타임은 Bridge의 기존 파일 집합 검사 범위 밖에 준비한다.
5. 교체 journal은 준비→구 프로세스 종료→진입점 전환→새 Bootstrap/GUI 확인→확정으로 진행한다. 새 프로세스의 이미지·해시·nonce 및 실제 첫 Paint 이후의 `ready/confirmed`를 확인한 뒤에만 확정한다. 시작 실패·중단·재부팅으로 확인이 누락되면 외부 작업자 또는 새 진입 파일의 다음 실행 복구 경로가 이전 EXE를 복원하고 기존 활성 GUI로 기동한다. 양쪽 카탈로그 trust, 회사 앱 데이터·설치 기록, 사용자 작업 파일은 복구에서도 수정하지 않는다.

이 설계에 따라 적용 작업자와 중단 복구를 구현한 뒤 별도 승인된 후보로 확인해야 한다. 이 작업에서는 GUI 손질만 개발 브랜치에 올리고 운영 Release 및 안정 Bootstrap은 바꾸지 않았다.

### 검증 기록

개발 PC 격리 Windows에서 기존 Bootstrap 코드로 두 번의 비교 기동을 했다. 운영 기준은 기존 서명 0.1.8과 실제 운영 Bootstrap이고, 수정본은 같은 버전의 기존 Bootstrap 소스를 격리 시험 키로 빌드한 조합이다. 각 값은 1회 관측이며 직원 PC의 시간을 추정하는 기준은 아니다.

| 시점 | 운영 0.1.8 | 수정 GUI |
|---|---:|---:|
| 기존 Bootstrap 실행 → GUI 프로세스 확인 | 3.749초 | 3.705초 |
| 기존 Bootstrap 실행 → 첫 Splash | 4.500초 | 3.843초 |
| GUI 프로세스 확인 → 첫 Splash | 0.751초 | 0.138초 |
| 기존 Bootstrap 실행 → 메인 창·confirmed | 5.133초 | 5.079초 |

수정본에서 Splash 바로 아래에 메인 창이 놓이는 순서, confirmed 시점에 Splash가 사라지는 것과 기존 작업표시줄 표식이 있는 환경의 정상 종료 코드 0 및 합성 작업 파일 보존을 확인했다. 시작 창과 메인 창의 스레드를 부모/소유 관계로 묶은 첫 시험에서는 GUI가 준비되지 않아 기존 Bootstrap이 시간 초과했다. 이 방식은 제거했고, 최종본은 소유 관계 없이 창 순서만 바꾼다. 기록은 `C:/Dev/CGL-SplashHandoff-Final-20261120/native-measurements.json`에 보존했다.

`python -B -m unittest tests.test_startup_splash tests.test_bootstrap_ack tests.test_canonical_channel` 24개 통과. 일반 세션에서 조기 표시, 잘못된 세션의 창 정리, health/부모 Splash 중복 방지와 기존 ACK·채널 진입 계약을 확인했다. 운영 키 사용, 회사 앱 실행, Setup 변경 또는 전체 업데이트 회귀는 수행하지 않았다.

## Bootstrap 자동 교체 후보 (2026-11-20)

개발 기준은 GUI 시작 창 수정 `2e457d9`이며, 별도 브랜치 `codex/bootstrap-auto-update-20261120`에서 작업했다. 운영 GUI 0.1.8 / Rod11, Toast9는 유지한다.

### 적용 계약

- Rod 0.1.9 후보의 서명된 GUI 릴리스 안에 `bootstrap-upgrade.json` 및 `bootstrap-v2.zip`을 넣는다. 기존 Ed25519, 순번, 보관 원 ZIP·receipt·proof와 일치하는 현재 GUI인지 다시 확인한다. 신규 Bootstrap과 `_cgl_b2` 런타임은 이 GUI ZIP의 해시와 파일 manifest로 보호된다. 기존 진입 파일은 설치 유형별 승인 해시와 대조한다. 서명·대상·기존 파일이 일치하지 않으면 그대로 둔다.
- 기존 GUI 업데이트의 `committed` 거래 또는 첫 Toast Bridge 경로에서 확보한 서명된 Rod 증거가 있는 정상 세션이 시작 구성 요소를 준비한다. 숨은 health 실행에서는 시작하지 않는다. 기존 업데이트 승인을 사용하며 GUI에 별도 설치 단계가 없다. 준비 완료 후 GUI가 종료되며, 전환 중 한 차례 추가 자동 재시작이 있다.
- 별도 프로세스로 실행한 서명된 후보가 프로세스 신원·경로와 기존 업데이트·실행 잠금을 확인한다. 기존 GUI, Bootstrap 및 Bridge가 종료될 때까지 기다린 후 새 버전 DLL을 `_cgl_b2`에 놓고, 이전 EXE를 검증된 백업으로 보존한 다음 같은 볼륨에서 기존 `CGLBootstrap.exe`만 원자적으로 교체한다. 기존 `_internal` 및 이미 실행 중인 다른 직원 프로세스는 그대로 둔다.
- 직접 설치는 기존 `launcher-home`을 사용한다. Toast Bridge는 이미 서명된 하위 런타임의 정확한 파일 집합을 매번 확인하므로 하위 Bootstrap을 덮어쓰지 않는다. 기존 바로가기 대상인 바깥 Toast 진입점만 갱신하고, 기존 `launcher-home/rod/launcher-home`과 사용자 데이터 루트에 연결한다. 원래 바로가기 경로와 인자, 작업표시줄 표식, 설치된 앱의 데이터 영역은 유지한다.
- 새 시작은 nonce와 실제 프로세스 이미지가 일치하고 기존 GUI의 첫 Paint 및 `ready/confirmed`까지 통과해야 확정한다. 확인 전 실패 시 외부 작업자가 검증한 구 진입 EXE를 복원해 다시 실행한다. 이미 개시된 교체에서 작업자가 사라져도 새 진입점이 로드되는 경우 다음 실행에서 확인 또는 복원 작업을 수행할 수 있다. 새 진입점과 외부 작업자가 모두 실행 불능인 동시 장애, 검증할 수 없는 백업 또는 쓰기 권한 거부에서는 자동 정상화가 보장되지 않는다. 기존 데이터와 진단 기록을 유지한다. 운영 환경에서는 이 경우의 지원 경계를 함께 승인한다.

### 격리 결과와 후보

- 현재 서명·설치 엔진으로 후보를 준비해 실제 기존 계열의 Windows Bootstrap worker로 0.1.9를 적용했다. 최초 승인은 격리 테스트가 기존 승인 API를 호출하는 방식으로 준비했으며, 이후 GUI와 외부 작업자가 추가 입력 없이 새 진입점으로 전환해 `committed`에 도달했다. 동일 설치 경로, 기존 영수증, 설정과 5개 앱의 합성 작업 파일 해시가 유지됐다.
- 별도 격리 세션에서 새 Bootstrap 시험 시작 시점에만 Windows 파일 공유 잠금으로 초기화 오류를 유도했다. 외부 작업자가 이전 진입점의 SHA-256을 복원하고 기존 Bootstrap으로 GUI를 다시 열었으며, 실제 작업·설정 파일과 기존 영수증을 보존했다. GUI 0.1.9를 내리는 대신 시작 진입점만 복원했다.
- Toast Bridge 토폴로지는 이미 배포한 네이티브 외부 Bootstrap과 Bridge GUI를 격리 신뢰 자료에 연결하고 첫 Rod 다운로드 증거를 로컬 서명 seed로 구성했다. Toast → Bridge → 하위 Rod → GUI의 실제 네 프로세스가 종료된 후 바깥 진입점만 교체됐다. 기존 하위 런타임 해시, Toast/Rod 포인터와 Rod trust, 합성 사용자 설정이 일치했다. 공개 채널 연속 다운로드는 기존 결과를 재사용했다.
- 교체를 마친 동일 시작 경로와 바로가기 인자로 직접 재실행했다. 이 PC의 1회 측정에서 Win32 Splash가 약 **0.125초**에 표시됐고, **5.226초**에 실제 GUI가 보이며 confirmed가 확인됐다. 그 시점에는 시작 창이 닫혔다. 종료 코드는 0이었다.
- 관련 자동 테스트 27개가 통과했다. `python -B -m unittest tests.test_bootstrap_upgrade tests.test_startup_splash tests.test_bootstrap_ack tests.test_canonical_channel`을 사용했다. 기존 전체 업데이트 및 Setup 시험은 재수행하지 않았다.
- 네이티브 검증은 운영과 분리된 로컬 시험 키로 실행했다. 운영용 공개키와 승인 구 진입 해시를 넣은 **미서명** 0.1.9 후보는 `C:/Dev/CGL-BootstrapAuto-20261120/production-policy-unsigned/`에 있다. ZIP은 81,352,523바이트이며 SHA-256은 `9f30f7519c4f8375485a56f8b5584144fa9a10de417d0b678ffccb46d07cc90c`이다. 내부 manifest와 Bootstrap ZIP의 해시를 재검증했으며 운영 바이너리와 같은 EXE를 로컬 시험에서 사용했다. 후보 계획과 검증 로그는 해당 로컬 작업 루트에 있다. 운영 개인키, 설치 PC, 운영 Release에는 변경을 가하지 않았다.

운영 배포에는 기존 설치 두 유형의 승인 진입 EXE 해시 범위 확정, 운영 서명 및 새 순번 승인, 동일 운영 후보의 격리 확인이 필요하다. 새 Setup은 이번 경로의 선행 조건이 아니다.

## GUI 0.1.9 최종 운영 서명 후보 (2026-11-20)

기준은 Rod 저장소 ID `1462539740`, 카탈로그 식별자 `creative-group-launcher-rodetoast-1462539740`, 현재 Latest11이다. `rodetoast-catalog-000012`/순번 12를 **로컬 서명 후보**로 준비했다. 공식 Ed25519 키 ID `1efdfb848bb31e3fa5c07095f952c08d920be77253261fbf2742755341f018e0`을 기존 DPAPI 경로로 사용했다. 개인키 내보내기·보관 변경, GitHub Draft 및 Release 생성은 없다. 격리 trust에서 11→12 수락과 12→11 거부, 서명과 manifest, 원 ZIP 및 회사 앱 5개 자산과 메타데이터 일치를 확인했다.

| 지원할 정확한 진입 EXE | SHA-256 |
|---|---|
| Rod 직접 설치 Bootstrap 0.1.6, 공식 Setup 0.1.6.0 | `152a02ce9f36f65df534da711a626474a9cc2116a5736adbfc601b33898a0a09` |
| Toast Bridge 바깥 Bootstrap 0.1.4, 공식 Setup 0.1.4.1 | `c15f48a0d72dd0a8bdc1ad909a75ae3327a91a2f136170dc4c3713651df6cb19` |

Rod와 Toast Setup EXE의 원격 digest를 로컬 공개 자산/동일 빌드 바이너리와 대조했고, 각 Setup manifest와 실제 `payload/CGLBootstrap.exe`를 대조했다. Toast는 공개 초기 ZIP 내부의 동일 EXE 해시도 확인했다. Toast Bridge의 검증된 하위 Rod 런타임은 교체 대상이 아니다. 과거 별도 수동 가입 ZIP `employee-bootstrap-0.1.1`은 다른 해시의 진입점이며 이 후보에 포함하지 않는다. 허용되지 않은 해시는 시작 구성 요소 교체 준비 이전에 차단한다. 해당 GUI의 기존 업데이트 경로는 유지된다.

첫 운영 서명 격리 실행에서 관찰 도구의 진단 로그 읽기와 Windows 원자적 파일 교체가 충돌했다(WinError 32, `running_log_write`). 구 진입점은 복원됐으나 시험 GUI가 남아 재시작 잠금을 잡았고 교체 작업자가 미처리 오류 창을 띄웠다. `b748cc30fb3ce6a19d83245b0f0de5cf608ce644`에서 시험 기동 실패 시 새 GUI를 닫은 뒤 복원하는 경로와 교체 작업자 오류의 파일 로그 처리를 보완했다. 검증 도구도 실행 중 진단 로그를 폴링하지 않고 공유 삭제가 허용된 핸들로 상태만 읽도록 조정했다. Bootstrap만 다시 빌드했다. GUI EXE는 기존 미서명 후보의 동일 바이트 `46cb24034406628d0e9eecb6f979909916a6151b46b97696385be61ae5c1f421`를 사용했다. 처음 만든 순번12 로컬 서명은 이력으로 보존하며 아래 최종 자산만 공개 승인 대상이다.

대표 검증은 실제 Rod Setup 0.1.6.0의 안정 Bootstrap을 복사한 새 격리 폴더, 기존 운영 서명 카탈로그11, 최종 운영 서명 카탈로그12를 사용했다. 기존 승인 API로 거래를 준비하고 실제 구 Bootstrap worker로 GUI를 적용했다. 이후 실제 GUI와 외부 작업자가 추가 입력 없이 진입점을 바꿔 `committed` 처리했다. 새 시작 단계의 Windows 공유 잠금으로 실패를 유도한 독립 사례에서는 이전 진입 EXE를 정확한 해시로 복원하고 기존 진입점에서 GUI가 다시 열렸다. 양쪽에서 동일 바로가기 파일, 기존·신규 receipt, current 및 trust, 보관 ZIP·proof, 설정과 회사 앱 5개의 합성 작업 파일을 비교했다. 기존 Toast 바깥 진입점·하위 런타임 네이티브 검증은 직전 결과를 재사용했다. 이번에는 운영 Latest에서의 실제 0.1.9 다운로드나 SPENT03 Setup 설치 시험을 반복하지 않았다.

교체 후 같은 바로가기 인자로 실행한 개발 PC 1회 관측에서 Win32 Splash는 **0.124초**, 실제 GUI와 confirmed는 **4.581초**였다. 그때 Splash는 사라졌고 정상 종료 코드는 0이었다. 관련 교체·ACK 테스트 **11개**가 통과했다. 운영 자산과 실제 직원 PC에는 변경이 없다.

| 공개 승인 대상 자산 | 바이트 | SHA-256 |
|---|---:|---|
| ase-viewer--0.5.8.4-team-3bf37dd.zip | 22085231 | `2532c273c4cf9930cf882ef1f84cae55c9a97479a69123431560b1299edec2d2` |
| catalog.json | 9411 | `8fdffde78fddff5593dce4a6ef974c96208e4faa486045354d61d1fef7b24f6a` |
| catalog.sig.json | 239 | `88139d54d6e1e59b8c6bf521227dc8e4c94e3eb84e225a831ae275fcd352d599` |
| creative-group-launcher--rodetoast-launcher-0.1.9.zip | 81352867 | `c7e902537538439eb37fe96f13e15de03927be998b676c300da51392c1612104` |
| pivot-fixer--0.3.3-team-80b84c9.zip | 20709116 | `214c966925e9def3aeebeb0245359e355606bf3627c47b29d956a78e5ec37361` |
| ps2ase--0.3.6-team-6e84645.zip | 66252089 | `1945520ea353e584520f0984de65b4de0dbd4e3c206087fa5741ee74282a53d9` |
| tag-master--0.4.0-team-7263f8d.zip | 38813495 | `80865038ddab9a1b9050d04cbb48cb777edf4e6419caafb05b8b51c0f6962299` |
| tilenamer--0.1.6-rc3-8ba7a1e.zip | 54046715 | `aac38dc3a47dffe1a1cb7c2de3048922c4e45240df84ba6a6347107d67b9c3b4` |

최종 후보는 로컬 `C:/Dev/CGL-BootstrapAuto-20261120/rod12-final-rc/assets/`에 보존한다. `candidate-plan.json`의 SHA-256은 `e97230afc31fb74aa4d6140aa00e6a89786207f040fbbd2c62c7f56daa8828ce`이다. 새 Bootstrap EXE SHA-256은 `0a5bd2501f5a1e1338eec656197acfb8e81a42c6de8b11a49ca277e7d0544718`이다. 남은 결정은 위 8개 자산의 Rod 정식 공개와 카탈로그12 Latest 지정 승인이다.

## GUI 0.1.9 / Rod 카탈로그12 운영 공개 (2026-11-20)

사용자 승인으로 [rodetoast-catalog-000012](https://github.com/rodetoast/creative-group-releases/releases/tag/rodetoast-catalog-000012)를 정식 공개하고 Rod Latest로 지정했다. Release ID는 `452539099`, 저장소 ID는 `1462539740`, 카탈로그 순번은 `12`다. 승인 계획 SHA-256 `e97230afc31fb74aa4d6140aa00e6a89786207f040fbbd2c62c7f56daa8828ce`의 자산 8개를 그대로 사용했다. GUI ZIP SHA-256은 `c7e902537538439eb37fe96f13e15de03927be998b676c300da51392c1612104`이다.

GitHub Draft와 공개 HTTPS에서 8개 전부를 다시 내려받아 파일 크기와 SHA-256을 비교했다. 운영 Ed25519 서명, 카탈로그·ZIP 바인딩, 내부 GUI manifest와 Bootstrap ZIP의 파일별 해시, 채널 정책 및 허용 진입점 두 개를 확인했다. 새 Bootstrap SHA-256은 `0a5bd2501f5a1e1338eec656197acfb8e81a42c6de8b11a49ca277e7d0544718`이다. 이전 Rod Release 및 직원용 Setup, Toast Latest9·직원용 Setup은 게시 전후 일치했다.

기존 Rod GUI 0.1.8과 동일한 Provider 경로가 공개 Latest12를 받아들이고 이전 순번 11을 거부하는 것을 격리 trust 상태에서 확인했다. 기존 서명된 Toast9 Bridge ZIP의 Rod 정책과 비교하고, 그 Bridge의 순번 하한 10으로 동일한 공개 카탈로그12 조회를 확인했다. Bootstrap 교체와 복원, 시작 창의 실기동은 최종 서명 후보의 기존 Windows 검증을 사용했다. 이번 게시 과정에서 Setup·Windows 전체 업데이트 시험이나 실제 직원 PC 조작은 수행하지 않았다.

지원하는 기존 진입점은 공식 Rod Setup 0.1.6.0의 Bootstrap 0.1.6 (`152a02ce9f36f65df534da711a626474a9cc2116a5736adbfc601b33898a0a09`)과 공식 Toast Setup 0.1.4.1의 바깥 Bootstrap 0.1.4 (`c15f48a0d72dd0a8bdc1ad909a75ae3327a91a2f136170dc4c3713651df6cb19`)이다. 해당 직원은 기존 바로가기에서 업데이트를 한 번 승인한다. 허용 해시 밖의 진입 파일에는 Bootstrap 자동 교체가 적용되지 않는다. 새 Setup 배포나 기존 Toast 채널의 폐기는 이 작업의 범위 밖이다.

## Qt Quick 제품 GUI 0.2.0 후보 (2026-11-20)

제품 UI의 기본 화면을 `southpaw_tools/quick/Launcher.qml`로 전환했다. 기존 Windows 창과 작업표시줄 동작을 유지하기 위해 QQuickWidget을 같은 네이티브 창에 호스트했다. `LauncherSurface`는 프로그램 목록과 설치 상태, 현재 선택, 작업 상태, 승인 대화상자를 공개하고, 허용된 UI 동작을 기존 Python 런처에 전달한다. 다운로드·설치·실행·제거, 승인 버전 선택, 실행 중 보호, Ed25519 검증, 관리형 인계, Bootstrap 교체·복구는 기존 구현을 사용한다. Widgets는 격리된 `--check --widgets` 비교에 남겨 두었다. 직원의 관리형 시작이 실패하면 기존 Bootstrap이 이전의 서명된 패키지로 복원한다.

라이브러리에서 프로그램 5개와 각각의 설치 상태를 확인할 수 있다. 본문은 선택 앱의 설치 버전과 최신/등록 버전을, 헤더는 별도로 런처 설치·최신 버전과 수동 업데이트 확인을 표시한다. 주 작업 버튼은 설치·업데이트·실행 상태에 따라 바뀌며 버전 선택, 제거, 설치 위치, 진단 상세는 관리 화면에 모았다. 다운로드 크기를 아는 경우 실제 진행률을 표시하고, 길이를 알 수 없는 작업은 대기 상태를 표시한다. 테마는 기존 데이터 디렉터리의 `ui-preferences.json`에만 기록한다. 오프라인 실행, 기존 설치 레코드와 설정의 경로는 동일하다.

정상 시작은 QML 장면이 한 프레임을 렌더링하고 Windows 호스트가 첫 페인트를 처리한 뒤에만 `ready`를 작성한다. 기존 Win32 로딩 창과 `confirmed` 계약은 그대로 연결된다. 업데이트 중의 health 프로세스도 QML을 화면 밖에서 렌더링한 후에만 응답한다. QML을 읽거나 렌더링할 수 없으면 준비 신호를 반환하지 않는다.

로컬 운영 정책 후보는 `C:/Dev/CGL-QMLProduct-20261120/final-candidate/`에 있다. 관리형 ZIP은 90,173,146바이트, SHA-256 `f2e4e61ca94af7bdfd14a53c01f8c065589ae15a56f4c2d024ab8e579062b395`다. EXE SHA-256은 `36a9f0be8985afb0353c7279599dc979d2c48d15b6d0a054a2f82bec443d6a8f`다. Rod12의 운영 공개키, 저장소 ID 1462539740, 카탈로그 ID, 기존 회사 앱 5개의 배포 메타데이터를 기준으로 확인했다. 0.1.9를 건너뛰어 업데이트해도 기존 자동 교체 기능을 사용할 수 있도록 Rod12의 검증된 Bootstrap 업그레이드 명세와 ZIP을 바이트 그대로 포함했다. 운영용 서명과 순번 확정은 공개 승인 단계에 남겨 둔다.

Qt Quick Basic과 실제 사용하는 모듈만 관리형 ZIP에 포함한다. 초기 빌드는 쓰지 않는 Qt 스타일 에셋의 경로가 기존 Win32 한도를 넘었다. 모듈을 선별하고 가져오기 루트를 `_internal/q`로 줄여, 대표 Rod·Toast Bridge 경로의 추출·설치·복구 보관 경로를 최대 255 UTF-16 단위로 검증했다. 경로 한도와 검증 정책은 그대로다. Qt Quick/QML DLL과 플러그인은 패키지 내에 있고 직원의 추가 런타임 설치는 필요 없다. Qt WebEngine은 포함하지 않았다.

Windows 개발 PC에서 운영 0.1.9와 후보 0.2.0의 실제 EXE를 동일한 관리형 Bootstrap과 격리 경로로 실행했다. 시험 전용 Ed25519 공개키를 로컬 복제본에 적용했고, 바이너리와 운영 정책 후보는 별개로 보존했다. 개별 제품 버전의 1회 관측이며 장치 전반의 평균은 아니다.

| 항목 | Widgets 0.1.9 | Qt Quick 0.2.0 |
|---|---:|---:|
| 실행 후 Win32 로딩 창 | 0.417초 | 0.137초 |
| 메인 창 표시 및 준비 신호 | 7.738초 | 11.141초 |
| GUI 프로세스 작업 집합 | 143.6 MiB | 171.3 MiB |
| 관리형 ZIP (Bootstrap 교체 번들 포함) | 77.6 MiB | 86.0 MiB |

후보의 메인 화면 준비까지 3.403초 더 걸렸다. 그중 약 2.6초는 GUI 프로세스 시작 이전, 약 0.9초는 프로세스 시작부터 `ready` 사이에서 차이가 났다. 사용하지 않는 QML 스타일·리소스의 패키징을 줄였으며 기존 파일 검증을 유지했다. 두 제품의 시작 창은 준비 신호 후 사라졌고 정상 창 닫기 종료 코드는 0이었다.

직접 관련 자동 시험 19개가 통과했다. 실제 Quick 버튼으로 앱 설치·업데이트·오프라인 실행·제거, 재조회 실패 뒤 재확인, 런처 업데이트 승인 및 Bootstrap 인계를 확인했다. 실제 QML 화면은 한국어, 다크·라이트, Qt 배율 100/150/200% 및 최소 800×570으로 렌더링해 확인했다. Windows 격리 환경에서 시험 서명 후보를 기존 Bootstrap 작업자로 0.1.9에서 0.2.0으로 적용하여 `committed`, 준비·확정 신호, 기존 진입 EXE로 재실행, 설정·합성 앱 작업 파일과 기존 receipt/ZIP/proof 보존을 확인했다. 별도 격리 복제본에서 일부러 로딩 불가인 QML 후보는 `rolled_back` 처리되어 기존 0.1.9로 복원됐다. 운영 카탈로그로 이 후보를 내려받는 경로와 SPENT03 실기동은 확인 범위에 포함되지 않는다. Toast Bridge 코드와 정책은 유지했고 공개 Toast에서 새 후보로 넘어가는 추가 운영 전환은 수행하지 않았다.

별도 Setup 없이 GUI 업데이트로 교체할 수 있는 로컬 후보가 준비됐다. 승인 대상은 후보의 운영 카탈로그 서명과 새 Rod Release 공개다. 기존 Toast 및 Rod 공개 Release와 직원 설치는 이번 후보 작업 범위 밖이다.

## QML 0.2.0 시작 성능 후속 (2026-11-23)

기존 Windows 기록의 메인 화면 준비 시간은 Widgets 7.738초, 첫 QML 후보 11.141초였다. 세션 기록에서 차이 3.403초 중 약 2.6초가 GUI 프로세스 시작 이전에 발생했다. 격리 설치본에서 Bootstrap의 검증 단계를 분리해 잰 결과, 보관 ZIP·영수증·파일 검증은 Widgets 1.973초에서 QML 3.173초, 설치된 manifest·증명 검증은 0.539초에서 1.135초로 늘었다. 프로파일에서 파일 경로·링크 검사, 해시 계산과 ZIP 압축 해제가 시간을 사용했다. 별도 소스 계측에서 QML 화면 생성은 0.095초, 목록 초기화는 0.056초였다. 이 계측은 병목의 위치를 구분하는 데 사용했다.

빌드에서 실제 포함되는 EXE와 플러그인의 PE import 및 delay import를 따라 필요한 Qt DLL을 보존한다. 연결되지 않은 Qt DLL 34개와 Qt 편집기용 `.qmltypes` 12개를 제외했다. 이미 배포된 Bootstrap이 시작 전에 검사할 파일과 바이트가 줄어든다. GUI 정상 기동은 런타임 잠금을 얻은 뒤 활성 버전을 한 번 완전히 검증한다. 이전에는 잠금 양쪽에서 같은 활성 payload를 검사했다. Health는 기존 업데이트 작업자가 가진 잠금에서 활성 버전을 검증한다. 실제 QML 프레임·Windows 페인트·ready/confirmed 순서와 Bootstrap 복구 정책은 기존 계약을 사용한다.

최종 로컬 후보는 `C:/Dev/CGL-QMLStartup-20261123/final-candidate/`에 있다. 이전 후보와 버전은 모두 0.2.0이며 배포 입력은 새 해시로 구분한다. 관리형 ZIP은 84,105,579바이트(80.2 MiB), SHA-256 `fd78620383f5eff74348bef3174ff216b46a50013787f12660d5478c06add3ee`다. EXE SHA-256은 `fa4ec4bf0fde398ad9e30e4c4a128cbc88a1196be313da0203f5c99252dc4b24`다. 기존 Bootstrap 교체 번들, 운영 공개키 정책과 앱 5개 참조는 이전 후보의 것을 유지했다. 운영 서명과 카탈로그 게시는 승인 대기다.

동일 Windows 개발 PC·Bootstrap EXE·시험 공개키를 사용하고 두 후보를 A→B→B→A 순으로 실행했다. 메인 창과 준비 신호까지 이전 후보는 12.348/11.337초(평균 11.843초), 개선 후보는 9.737/9.635초(평균 9.686초)로 2.157초(18.2%) 줄었다. 세션 기록의 GUI 프로세스 시작부터 ready까지는 평균 약 3.16초에서 1.89초로 줄었다. 나머지 약 0.9초는 프로세스 시작 전 구간에서 줄었다. 시험은 두 번의 비교 측정이다. 과거 Widgets 7.738초는 별도 회차의 참고값이며, 기존 Bootstrap의 실행 전 전체 검증과 Qt 런타임 로딩 비용은 남는다.

정상 실행 두 번 모두 같은 Bootstrap에서 ready/confirmed 연동과 설정 보존, 정상 종료를 확인했다. 변경한 health 시작 경로는 기존 Bootstrap 작업자가 시험 서명으로 실제 후보를 실행하여 ready/confirmed/stopped와 거래 committed까지 확인했다. 시작 경로 자동 시험 4개가 통과했다. QML 장면·설치 엔진·업데이트 처리·복구 정책은 기존 시험 결과를 재사용한다. 운영 게시·직원 PC 변경은 이번 범위 밖이다.

## Bootstrap 시작 카드 디자인 (2026-11-23)

기존 승인된 제품 ICO와 QML의 다크 팔레트를 적용한 Win32 시작 카드를 사용한다. 420×176 논리 픽셀을 모니터 DPI에 맞게 변환하고, 한글 제목과 준비 메시지를 GDI로 그린다. 별도 UI 스레드의 30ms Win32 타이머가 double-buffered 페인트를 요청한다. 경과 시간을 기준으로 보라색 표시가 트랙을 왕복하며 실제 진행률이 없는 상태를 표시한다. Bootstrap의 검증과 파일 접근은 기존 작업 스레드에서 진행된다. Bootstrap 패키지에 제품 ICO를 넣고 Qt를 제외했다.

시작 창은 포커스를 가져오지 않는다. 자식 GUI는 부모 프로세스의 시작 카드 HWND를 확인하고 그 아래에 배치한다. 실제 첫 QML 렌더와 Windows 호스트의 첫 Paint에 기반한 ready/confirmed 순서를 유지한다. 작업자의 health 실행은 화면을 띄우지 않는다.

이번 Bootstrap 교체 후보는 3세대로 패키징했다. 운영 0.1.9가 설치한 2세대도 새 시작 카드를 적용할 수 있다. 별도 `.bootstrap-v3` 거래와 `_cgl_b3` 런타임을 사용하며 기존 2세대 거래·런타임은 롤백에 필요하므로 보존한다. 기존 공식 최초 진입점 두 개와 공식 2세대 EXE 해시를 새 manifest의 허용 목록에 유지한다. 서명, 파일 해시, 거래 승인, 실행 후 확인 및 복원 절차는 동일하다. 이전 0.2.0 후보의 구조와 최적화는 그대로 두고 새 Splash 후보를 별도 출력으로 보존한다.

개발 PC에서 실제 Win32 창을 DPI 96/144/192로 격리 렌더링하고 420×176, 630×264, 840×352 크기의 픽셀을 캡처했다. Windows 전역 배율을 변경하지 않고 테스트에서만 DPI 값을 주입했다. 16프레임씩 수집해 텍스트·로고 영역은 고정되고 진행 트랙의 픽셀만 움직이는 것을 확인했다. 캡처는 `C:/Dev/CGL-Splash-20261123/`에 보존한다.

첫 2→3 교체 시험은 기존 진입점을 그대로 둔 채 교체 전에 WinError 5로 중단됐다. 짧게 실행하는 실제 Windows 프로세스로 종료 중 이미지 조회에서 발생하는 동일 오류를 재현했다. 이미지 조회에서 접근 거부를 만나면 최대 100ms 기다려 원래 Windows 핸들이 종료를 신호한 경우에만 종료로 처리한다. 프로세스가 계속 실행되는 경우의 검사 오류는 그대로 유지한다.

최신 관리형 GUI 0.2.0 ZIP은 `C:/Dev/CGL-Splash-20261123/release-candidate/`에 있다. 67,496,976바이트(64.4 MiB), SHA-256 `bc6befd745b8b1d3b1af5f56031ca7567e776188290fe64cf35c06b7059c0982`다. Bootstrap 3세대 EXE SHA-256은 `42fc67176f36bf6f036f1c353993a340e0a04faec9e4c5833a8aee7b4ffdfa42`다. 외부 ZIP 크기는 중첩 Bootstrap 번들에서 사용하지 않는 Qt 수집을 제거해 줄었다. 기존 Qt Quick 배포 최적화는 그대로 유지했다. 운영 서명과 새 Rod 카탈로그 게시 승인을 기다린다.

최종 바이너리를 시험 서명 복제본으로 적용해 기존 2세대 진입점에서 3세대로 교체가 커밋되고 2세대 상태와 복원용 EXE가 보존되는 것을 확인했다. 측정 도구가 이전 Bootstrap 프로세스가 잠금을 해제하기 전에 시작한 한 차례는 중복 실행 방어로 종료됐다. 이전 프로세스의 종료를 확인한 뒤 정상 재실행을 계측했다. 시작 창은 프로세스 실행 후 0.081초, 메인 창은 화면에 표시되고 ready/confirmed가 확인되기까지 9.244초였다. 기존 9.686초는 앞선 비교 시험의 평균이다. 시작 창이 보이는 검증 구간에서 실제 배포 형식의 연속 7프레임을 캡처해 움직임을 확인했으며, 메인 준비 이후 시작 창이 사라지고 정상 종료 코드 0으로 끝났다. 원본 캡처는 `packaged-splash.png`, `packaged-motion.gif`다. 직접 관련 자동 시험 8개가 통과했다.
