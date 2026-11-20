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
