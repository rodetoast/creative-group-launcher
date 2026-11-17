# v0.1.0 아키텍처

> 이 문서는 해당 개발 단계의 기록입니다. 이후 로컬 체크포인트 승인·검사 결과는 [LOCAL_CHECKPOINT_REVIEW.md](LOCAL_CHECKPOINT_REVIEW.md)를 따릅니다. 과거 Git 상태·제한 및 초기 설계 내용은 현재 상태와 다를 수 있습니다.

## 현재 확정 범위 — Creative Group Launcher

추가 서비스 비용0원, 기존 Windows PC 기반 회사 LAN 전용이다. 현재 인터넷 배포 개발, 유료 서버/VPN/Cloudflare/OAuth/SSO/시디키 DRM/복잡한 기기 인증은 제외한다.
기존 직원 런처·로컬 관리자 게시·읽기 전용 다운로드 API와 설치/업데이트/Journal 복구 엔진을 재사용한다.
관리자 게시를 LAN API에 노출하지 않으며 임의 OS 명령 실행 endpoint를 추가하지 않는다. 서버는 일반 사용자 권한으로 운영한다.
실제 LAN 시험에는 더미 전용 root/catalog/client/token을 사용하고, 회사 담당자의 허용 범위와 별도 Windows PC 준비를 먼저 확인한다.
안전한 업데이트와 PC/작업 파일 보호를 우선하며 Ed25519 서명된 카탈로그는 후속 구현한다. 인터넷 거부 코드와 미구현 항목의 과거 설명은 기록으로 유지한다.
현재 복구 정책은 [STABILITY_FIX_REPORT.md](STABILITY_FIX_REPORT.md), 실제 시험 상태는 [CREATIVE_LAN_TRIAL_STATUS.md](CREATIVE_LAN_TRIAL_STATUS.md)를 따른다.

## 경계

```text
PySide6 런처 ── Provider ── 읽기 전용 HTTP API ── catalog.json / 승인 ZIP
     │                       별도 개발자 PC 프로세스
     ├── Installer / Processes
     └── 사용자별 설치·활성 버전 메타데이터

관리자 로컬 CLI ── ZIP/EXE/리소스 검증 ── immutable ZIP ── catalog 원자적 교체
```

`catalog.py`: strict typed metadata와 release identity.
`providers.py`: 로컬/LAN HTTP, timeout, 중단·취소·길이·해시 검증. 프록시 환경변수·리다이렉트를 사용하지 않음.
`archive.py`: Windows ZIP 경로 정규화, traversal/UNC/drive/ADS/예약 이름/대소문자 충돌/특수 파일 차단, CRC 검증을 수반한 추출.
`installer.py`: app별 OS 잠금, staging, 영수증, 사용자 설정 복사, 활성 포인터, 실행·제거.
`processes.py`: 추적된 Popen과 Windows 프로세스 실행 경로 탐색. 강제 종료 API 없음.
`server.py`: 상태·카탈로그·버전·노트·허용된 패키지만 제공. 디렉터리 탐색·임의 경로·쓰기 API 없음.
`admin.py`: 개발자 PC에서만 실행하는 명시 승인 CLI. 사용자 런처와 HTTP API에 노출하지 않음.
`ui.py`: QThread에서 파일/네트워크 작업, Signal로 진행률 전달. GUI thread에서 UI 갱신.

## 설치 트랜잭션

1. 등록 정보 재검증, OS app lock 획득, 설치 경로 내부 프로세스 확인.
2. UUID 다운로드 파일로 HTTP 전송. Content-Length/실제 바이트 수/SHA-256 검증.
3. 새 staging의 payload에만 추출. ZIP 경로·중복·용량·EXE 해시·리소스 검사.
4. 이전 버전의 명시된 사용자 설정 복사. 임의 실행 코드·링크는 이전하지 않음.
5. 설치 영수증에 원본 패키지 파일별 해시와 앱 메타데이터 기록.
6. 실행 중 여부와 취소 재검사 후 새 release 폴더로 rename.
7. `active.json`을 atomic replace하여 활성 버전 전환.

마지막 단계 실패 시 새 트랜잭션만 정리하고 이전 포인터·payload는 그대로 유지합니다.
다운로드 취소는 진행 중인 read timeout(최대 약 4초) 이후 반영될 수 있습니다.
이전 release를 덮어쓰거나 자동 삭제하지 않습니다. 같은 release_id를 재사용하지 않습니다.
이미 존재하는 release_id 폴더를 자동 복구/재설치하지 않고 확인을 요청합니다.

## 오프라인

실행은 서버 설정·캐시 카탈로그에 의존하지 않고 로컬 active 메타데이터와 payload를 사용합니다.
연결 실패 시 새 목록으로 기존 목록을 지우지 않습니다. 설치된 앱이 카탈로그에서 사라져도 목록에 병합합니다.
실행 전 EXE 해시·필수 리소스 존재를 확인하며 명령은 shell=False, 정확한 cwd로 전달합니다.
오프라인은 프로그램 자체의 외부 도구 요구사항(Aseprite/Photoshop)을 제거한다는 뜻이 아닙니다.

## 신뢰와 운영 범위

승인은 로컬 게시 CLI의 --approve와 승인된 파일 해시로 관리합니다.
v0.1.0은 내부 개발용 서버이며 패키지/카탈로그의 공개키 서명은 아직 없습니다.
공유 토큰을 쓰는 LAN HTTP는 암호화 통신이 아닙니다. 신뢰할 수 있는 회사 LAN과 정책 승인 범위에서만 사용합니다.
인터넷 기능은 provider 경계를 남겼지만 구현하지 않았고 서버에서도 활성화를 거부합니다.

Python 표준 HTTP 서버는 공개 인터넷용 production server가 아닙니다.
[Python 문서](https://docs.python.org/3/library/http.server.html),
[Qt 스레드 문서](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html)를 설계 근거로 참고했습니다.
