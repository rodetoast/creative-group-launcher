# 파일럿 배포 후보 선정안

작성 기준: 2026-11-13. **선정 권고이며 직원 배포 실행 승인은 아직 아니다.** 이 문서가 패키지·채널·해시의 단일 기준이다. 진행 체크리스트는 [운영 계획](PILOT_PLAN.ko.md), 직원 절차는 [직원 안내](PILOT_EMPLOYEE_GUIDE.ko.md)를 따른다.

## 결론

**첫1명 동행·새 분리 환경의 파일럿에는 기존 BD13 진단 Setup을 변경 없이 재사용하는 안을 추천한다.** SPENT03 성공과 정밀 진단이 함께 확보된 후보이기 때문이다. 이름이 SPENT03이라는 이유만으로 추천한 것이 아니다. 실제 패키지/NSIS/채널을 검토했으며 제품 실행에 SPENT03 컴퓨터명 제한은 없다.

단, 이것은 **시험 채널·격리 등록·담당자 지정 데이터 경로를 사용하는 진단 후보**다. 일반 직원용 정식 Setup으로 승격하거나 무인 설치로 배포하지 않는다. 직원이 다운로드 파일을 임의로 더블클릭해 기본 설치하도록 안내하지 않는다.

다음 조건을 승인하면 첫 파일럿에 새 빌드·서명·카탈로그·Release는 필요 없다.

- 참여 PC는 기존 런처 설치·테스트 등록과 겹치지 않는 신규·분리 환경. 기존 직원 설치 이전/공용 데이터 병합은 제외.
- 담당자가 일반 권한의 짧은 I/D 경로를 확정하고 /DATA 및 설치 위치를 명시한다. 기존 실제 AppData나 다른 설치 데이터를 붙이지 않는다.
- 파일럿 기간 시험 채널의 Latest를 현재 순번10으로 유지하는 운영 방침을 정한다. 클라이언트에 Release를 고정하는 새 기능이 있는 것은 아니다. 다른 실험의 Latest 변경을 병행해야 한다면 이 재사용안을 승인하지 않는다.
- 과거 WinError5 미해결·자동 복구 미검증·설치 목록 미표시 가능성을 참여자가 알고 지원 담당자/대체 업무 수단을 확보한다.

## 실제 존재하는 후보 비교

GitHub API의 현재 Release/자산 메타데이터를 읽기 전용 확인하고 로컬 빌드 보고서와 대조했다. 실행 시험·대용량 자산/증거 재다운로드는 하지 않았다. 파일 보관 저장소와 런처 내부 연결 채널을 구분해야 한다.

| 후보 | 검증·진단 | 채널/등록과 충돌 | 그대로 쓸 수 있는 범위·판정 |
|---|---|---|---|
| 운영 employee-bootstrap-0.1.1의 CGL-Employee-0.1.1-Windows-x64.zip + production-catalog-000004 | S7계열 자체 업데이트·회사 앱 배포 근거 있음. 후속 직원 UI와 정밀 Bootstrap 진단은 없음 | 운영 채널, seed/카탈로그순번4. ZIP은 NSIS Setup·제거 등록을 제공하는 자산이 아님. 기본 데이터/기존 폴더와 혼용 주의 | 실제 운영 자산으로 보존. 최신 진단과 설치/제거 동선을 평가할 첫 파일럿의 최선 후보는 아님 |
| setup-trial-0.1.3.0 일반 Setup |0.1.3 GUI·설치/제거/재설치 및 이전 시험 업데이트 근거. 정밀 진단 없음 | 일반 Setup 내부는 운영 채널/일반 HKCU 제거 키. 배포 파일 자체는 시험 저장소에 있음. 기존 운영 설치와 충돌 가능 | 기존 검증 자산으로 유지. 시험 GUI가 실제 운영 Latest를0.1.3으로 바꾼 것은 아님. 첫 추천 아님 |
| 같은0.1.3.0의 UpgradeTrialSetup | 초기0.1.2→시험0.1.3 업데이트용. 정밀 진단 없음 | 시험 채널/Upgrade013 격리 등록. 같은 사용자별 시험 경로를 재사용하면 충돌 가능 | 과거 업데이트용 자산. 최신 진단 파일럿을 위해 되돌아갈 필요 없음 |
| setup-trial-0.1.4.0 일반/Isolated Setup |0.1.4 UI·패키징 근거. 정밀 진단 이전 Bootstrap | 일반 파일은 운영 채널/일반 등록, Isolated는 같은 운영 payload에 시험 등록. 로컬0.1.4 seed 카탈로그순번7은 현재 운영Latest4와 다름 | 파일명이 일반 Setup이라고 현재 운영 채널의 최종 배포 구성이 확정됐다고 보지 않음. 순번/신뢰 상태를 낮춰 맞추지 않음 |
| 같은0.1.4.0의 UpgradeTrialSetup |0.1.3→0.1.4 성공 뒤 B14 재실행 WinError5가 관찰된 계열. 원인 미확정, 정밀 진단 없음 | 시험 채널/Upgrade014 격리 등록. 정상 설치목록 표시는 확인되지 않음 | 정확한 장애 관측을 돕는 새 진단 후보가 있어 우선 사용하지 않음 |
| **BD13 bootstrap-diagnostics-spent03-20261113 Setup** | 최신 사용자 보고상 SPENT03의0.1.3→0.1.4, 동일 Bootstrap 재실행·정상 종료·제거/데이터 보존 성공. **정밀 진단 포함** | 시험 채널, 기존 signed seed9→Latest10. BDiagSP031113 전용 HKCU/바로가기. 설치목록 비노출. 기본 I/D를 그대로 쓰면 별도 설치와 충돌 가능하므로 동행 필수 | **조건부 첫 추천.** 단일 검증 자산을 고정하고 지원 포함1인 파일럿에서 재사용. 운영 배포본으로 부르지 않음 |

모든 Setup은 기존 소유권·프로세스 잠금·서명/해시·데이터 보존 정책을 유지한다. 다른 버전 파일이 남은 기존 설치에 새 Setup을 덮어쓰는 것이 일반 업그레이드/복구라고 보장되지 않는다. 정상 Setup 재설치 근거와 B14 장애 복구 성공을 구분한다.

0.1.3 일반 Setup의 로컬 seed순번6, 0.1.4 일반 Setup의 seed순번7을 현재 운영Latest4와 혼동하지 않는다. 신뢰 상태를 편집해 낮추는 작업은 파일럿 준비에 포함하지 않는다.

## 추천 후보 식별표 — 승인 시 그대로 고정

- [Release](https://github.com/toast-source/creative-group-trial-releases/releases/tag/bootstrap-diagnostics-spent03-20261113), prerelease/Latest 아님.
- 실제 파일: `SouthpawToolsLauncher-Bootstrap-Diagnostics-SPENT03-Setup-20261113.exe`
- [실제 Setup 다운로드](https://github.com/toast-source/creative-group-trial-releases/releases/download/bootstrap-diagnostics-spent03-20261113/SouthpawToolsLauncher-Bootstrap-Diagnostics-SPENT03-Setup-20261113.exe)
- 크기:82,900,614바이트.
- Setup SHA256: `e92171c29bb2fe940ff0cd9196ad1cda06ded9af7d379289604c3a1d6c48cd5d`
- 내부 Bootstrap SHA256: `7f4184fd8a4e58d6ff254c74780b230120e90eddb6f7b15441981c87d4400ed1`
- [해시 목록](https://github.com/toast-source/creative-group-trial-releases/releases/download/bootstrap-diagnostics-spent03-20261113/SHA256SUMS.txt), [payload manifest](https://github.com/toast-source/creative-group-trial-releases/releases/download/bootstrap-diagnostics-spent03-20261113/PAYLOAD.manifest.json).
- 초기 GUI0.1.3 / trial-launcher-s9-0.1.3, 기존 서명 seed순번9.
- 최신 GUI0.1.4 / trial-launcher-s10-0.1.4, 현재 trial-catalog-000010. 신뢰 minimum_sequence5, 시험 key_id aab2e791668a8130f01435810432e6d144386fd66d9af69eb1b6b979d4d416a9.
- Setup 표시 버전0.1.4.0, 설치 목록 DisplayVersion은 seed0.1.3으로 남을 수 있음. 실제 GUI 버전은 current/진단 기준.
- 격리 등록/바로가기 suffix: BDiagSP031113. 정상 운영 등록명과 다르지만 AppUserModelID는 기존과 같으므로 동시 운영 설치·작업표시줄 고정 혼용은 파일럿에서 제외.

위 파일과 GitHub asset digest, 기존 로컬 파일 SHA256의 일치를 이번에 확인했다. 최신 SPENT03 결과는 사용자 완료 보고를 재사용했다. 공개한 자산을 직원에게 자동 배포하거나 새 서명 자산을 만들지는 않았다.

## 새 패키지가 필요한 경우와 필요 없는 경우

- **이번1인 동행·시험 채널·분리 데이터 범위:** 기존 BD13 그대로 가능. 파일명 변경, 재압축, 재서명, 새 Setup/Release가 필수는 아님.
- **운영 채널 기본값·일반 직원 등록·자가 설치까지 요구하는 범위:** BD13을 그대로 정식본으로 안내할 수 없음. 별도 패키지 구성/승인과 영향 검증이 필요. 지금 새 버전/파일명/URL을 정하거나 제작하지 않음.
- 시험 채널을 다른 개발 실험과 동시에 변경해야 한다면 재사용 조건이 충족되지 않음. 승인 범위를 먼저 바꾸고 패키지 결정을 다시 해야 하며, 기존 신뢰/순번을 조작하는 우회는 하지 않음.

## 남는 위험과 승인할 결정

B14 시작 장애와 간헐적 개발 PC catalog.json 원자교체 WinError5의 원인은 미확정이다. 둘을 같은 원인으로 보지 않는다. 파일럿은 고정된 기존 Release를 소비하므로 새 catalog 게시 실패를 시험하지 않으며, 직원 PC 파일 작업이 항상 안전하다고 보장하지도 않는다. 자동 장애 복구는 검증되지 않았다.

실제 서로 다른 회사 앱 정식 버전 간 업데이트 검증은 제한적이다. 첫 직원에게는 필요한 현재 버전만 설치하고, 실제 새 승인 버전이 없다면 업데이트 미실시로 기록한다. 버전을 위조하거나 모든 앱의 내부 기능 시험을 반복하지 않는다.

사용자 결정이 필요한 것은 ①BD13·시험채널 동행 재사용 허용 ②파일럿 동안 Latest10 유지 방침 ③첫 참여자와 담당자/연락수단 ④배포일·초기 관찰 종료/확대 판단 시점 ⑤PC별 I/D와 대체 업무 수단이다. 현재 성명·날짜·경로는 미정이다. 기존에 정한 항목이 있다면 그 기록을 재사용한다.

**시작 상태: 기술 후보 준비됨, 운영 승인/인원·일정 확정 후1명 시작 가능. 현재 자동 배포하지 않음.**

근거: 기존 `BOOTSTRAP_SUPPORT_AND_LIMITED_PILOT.ko.md`, BD13 제작·정밀 진단319개·설치목록 분석 보고서와 현재 GitHub Release 메타데이터. 상세 자산 목록은 `.test-results/pilot-preparation-20261113/verified-asset-inventory.json`. 운영 Latest는 production-catalog-000004, 시험 Latest는 trial-catalog-000010으로 읽기 전용 확인했다. 소스·Setup·서명·Release·Latest는 변경하지 않았다.
