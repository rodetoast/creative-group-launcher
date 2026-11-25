# Southpaw 도구 런처 개발 현황

확인일 2026-11-25 · 기본 브랜치 `main` · [개발 브랜치](https://github.com/rodetoast/creative-group-launcher/tree/codex/workspace-refinement-20261125) · [이전 운영 조사 기준 소스 커밋](https://github.com/rodetoast/creative-group-launcher/commit/c1d39e1552456ca2b443287ea0ddc70544d21004)

사내 직원이 제작 도구를 설치·실행·업데이트하는 통합 런처입니다.

- 제품 표시명 **Southpaw 도구 런처** · 런처 app_id `creative-group-launcher`
- 기술 구성 Python, PySide6/Qt Quick(QML), Windows Bootstrap/NSIS
- 구현 기능 도구 5개 관리, 서명 카탈로그 검증, GUI·Bootstrap 관리형 교체와 복구, Toast → Rod 전환, 설정과 테마

## 배포 상태

**0.2.2** · `rodetoast-launcher-0.2.2` · `creative-group-launcher--rodetoast-launcher-0.2.2.zip` (onedir) · 실행 파일 `CreativeGroupLauncher.exe`. [Rod 운영 카탈로그](https://github.com/rodetoast/creative-group-releases/releases/tag/rodetoast-catalog-000015)

신규 직원은 [Rod Setup 0.1.6.0](https://github.com/rodetoast/creative-group-releases/releases/tag/employee-setup-0.1.6.0)을 사용합니다. 기존 직원은 바로가기와 업데이트 버튼을 사용합니다. [Toast9](https://github.com/toast-source/creative-group-releases/releases/tag/production-catalog-000009)의 Bridge 0.1.6이 기존 설치의 Rod 진입 경로입니다.

소스 저장소의 독립 Latest Release는 확인되지 않았습니다.

## 개발과 검증

0.2.2 운영. 프로그램 관리와 설정 개선 다음에 헤더 공식 회사 심볼을 적용했습니다.

**알려진 제약과 미검증** 과거 Bootstrap WinError 5의 정확한 원인은 미확정입니다. Windows 설치 목록 비노출은 기존 보고서의 제약입니다. 직원별 업데이트 완료는 미확인입니다.

이번 확인에서는 원격 Git과 공개 서명 카탈로그를 대조했습니다. 기능 시험과 패키징은 기존 보고서의 범위를 따릅니다.

## 작업 공간 후속 개발 (2026-11-25)

[설계·검증 기록](WORKSPACE_REFINEMENT.ko.md) · [Windows UI 검토 갤러리](ui-reviews/workspace-refinement-20261125/README.md)

- 전체·설치됨·업데이트 가능 필터와 목록 정렬을 저장합니다. 최근 업데이트순은 검증된 카탈로그의 개별 게시일을 사용합니다.
- 외부 도구 실행을 설치 경로로 감지하고 Windows가 허용할 때 기존 창으로 이동합니다. 설치 완료 안내 또는 상세 패널에서 새 Bootstrap의 버전 독립 바로가기를 만들 수 있습니다.
- Bootstrap 잠금 진입 순서를 수정해 확인된 중복 실행을 정상 안내로 처리합니다.
- 개발 PC의 소스 검증과 Windows Qt 화면을 확보했습니다. 서명된 패키징 Bootstrap을 통한 다섯 도구별 전환과 작업 표시줄 그룹화는 검증 대기입니다.
- 후속 마감에서는 정렬 화살표 대비, 설치 완료 소형 안내, 이중 상태 칩, 아이콘 액션 행과 실제 EXE 기반 안정 ICO 경로를 반영했습니다. [후속 UI 갤러리](ui-reviews/workspace-followup-20261125/README.md) · [독립 Windows 시험 인계](WORKSPACE_WINDOWS_HANDOFF.ko.md)
- 격리 Windows 시험용 GUI·Bootstrap 및 합성 도구 v1/v2를 작성하고 시험 저장소 인증 전용 Draft로 운송했습니다. 개발 PC에서 실제 구 Bootstrap worker의 0.2.2 → 시험 0.2.3 커밋을 확인했습니다. 새 Bootstrap 첫 v3 자동 교체와 작업 표시줄 검증은 별도 PC에서 진행합니다.

## 패키징과 다음 단계

Windows PyInstaller 관리형 GUI 빌드 및 launcher-package.json. Setup은 별도 산출물입니다. [공통 배포 절차](https://github.com/rodetoast/southpaw-development-hub/blob/main/docs/RELEASE_GUIDE.md)

**다음 단계** 다음 배포 후보가 승인되면 격리 Windows 환경에서 패키징된 GUI와 새 Bootstrap으로 중복 실행, 실제 도구 창 전환과 바로가기의 릴리스 전환을 확인합니다.

[README.md](https://github.com/rodetoast/creative-group-launcher/blob/c1d39e1552456ca2b443287ea0ddc70544d21004/README.md) · [docs/ARCHITECTURE.md](https://github.com/rodetoast/creative-group-launcher/blob/c1d39e1552456ca2b443287ea0ddc70544d21004/docs/ARCHITECTURE.md) · [docs/LAUNCHER_UI_AND_STARTUP.ko.md](https://github.com/rodetoast/creative-group-launcher/blob/c1d39e1552456ca2b443287ea0ddc70544d21004/docs/LAUNCHER_UI_AND_STARTUP.ko.md) · [docs/GITHUB_OWNER_COMPATIBILITY.ko.md](https://github.com/rodetoast/creative-group-launcher/blob/c1d39e1552456ca2b443287ea0ddc70544d21004/docs/GITHUB_OWNER_COMPATIBILITY.ko.md) · [개발 허브 요약](https://github.com/rodetoast/southpaw-development-hub/blob/main/projects/launcher.md)
