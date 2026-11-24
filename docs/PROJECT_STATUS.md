# Southpaw 도구 런처 개발 현황

확인일 2026-11-24 · 기본 브랜치 `main` · [개발 브랜치](https://github.com/rodetoast/creative-group-launcher/tree/codex/qml-product-20261120) · [조사 기준 소스 커밋](https://github.com/rodetoast/creative-group-launcher/commit/c1d39e1552456ca2b443287ea0ddc70544d21004)

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

## 패키징과 다음 단계

Windows PyInstaller 관리형 GUI 빌드 및 launcher-package.json. Setup은 별도 산출물입니다. [공통 배포 절차](https://github.com/rodetoast/southpaw-development-hub/blob/main/docs/RELEASE_GUIDE.md)

**다음 단계** 새 개발 과제가 정해지면 기존 직원의 업데이트 버튼과 시작·복구 계약을 유지합니다.

[README.md](https://github.com/rodetoast/creative-group-launcher/blob/c1d39e1552456ca2b443287ea0ddc70544d21004/README.md) · [docs/ARCHITECTURE.md](https://github.com/rodetoast/creative-group-launcher/blob/c1d39e1552456ca2b443287ea0ddc70544d21004/docs/ARCHITECTURE.md) · [docs/LAUNCHER_UI_AND_STARTUP.ko.md](https://github.com/rodetoast/creative-group-launcher/blob/c1d39e1552456ca2b443287ea0ddc70544d21004/docs/LAUNCHER_UI_AND_STARTUP.ko.md) · [docs/GITHUB_OWNER_COMPATIBILITY.ko.md](https://github.com/rodetoast/creative-group-launcher/blob/c1d39e1552456ca2b443287ea0ddc70544d21004/docs/GITHUB_OWNER_COMPATIBILITY.ko.md) · [개발 허브 요약](https://github.com/rodetoast/southpaw-development-hub/blob/main/projects/launcher.md)
