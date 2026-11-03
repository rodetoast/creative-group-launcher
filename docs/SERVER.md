# 개발자 PC 배포 서버

## 기본 실행과 OFF

```powershell
python -B -m southpaw_tools.server
```

`distribution/server.json`의 기본값은 전체 ON, LAN OFF, 인터넷 OFF입니다.
전체 ON은 서버 프로세스를 실행했을 때만 유효합니다. 기본 listener는 127.0.0.1:8765 하나입니다.
Ctrl+C로 종료하면 포트를 닫습니다. `server_enabled: false` 설정으로 시작하면 listener 없이 종료합니다.
설정 변경은 서버 재시작 후 반영됩니다. 켜져 있지 않은 서버를 UI 토글로 ON처럼 표시하지 않습니다.

## 명시적으로 LAN 활성화

1. 회사 네트워크 정책과 개발 PC의 사설 IPv4를 확인합니다.
2. `server.json`을 Git에서 제외되는 `distribution/server.local.json`으로 복사합니다.
3. 다음 값을 명시합니다. IP는 예시이며 실제 개발 PC의 주소를 사용해야 합니다.

```json
{
  "server_enabled": true,
  "port": 8765,
  "lan_enabled": true,
  "lan_host": "192.168.10.20",
  "lan_token": "replace-with-a-random-ascii-token-32chars",
  "internet_enabled": false
}
```

```powershell
python -B -m southpaw_tools.server --config distribution/server.local.json
```

개발 PC의 정확한 사설 IPv4에 추가 listener가 성공해야 LAN ON으로 보고합니다.
토큰 예시는 반드시 무작위의 24자 이상 ASCII 토큰으로 바꿔 별도로 전달하세요.
와일드카드 0.0.0.0, 공개 IP, loopback을 LAN 주소로 지정하는 설정, 짧거나 잘못된 토큰은 거부합니다.
LAN listener 바인딩 실패 시 앞서 준비한 로컬 listener도 닫고 실패합니다.
LAN listener는 사설/loopback 클라이언트와 Bearer 토큰을 모두 확인합니다.
서버·클라이언트 모두 LAN 연결을 명시해야 합니다. 런처 설정에서 LAN 사용·서버 주소·토큰을 저장하세요.

LAN을 끄려면 설정을 false로 바꾸고 재시작합니다. 인터넷 OFF와 독립적으로 작동합니다.
방화벽 규칙·공유기 포트포워딩·터널은 자동 생성하지 않습니다.
다른 회사 PC에서의 실제 연결/방화벽 허용 여부는 아직 검증하지 않았습니다.
공유 토큰은 사용자 launcher settings.json에 평문 저장됩니다. 외부 공개 전 암호화 저장/인증 설계를 보강해야 합니다.

## 인터넷

현재 미구성입니다. 인터넷 ON 요청은 오류로 거부하며 외부 listener를 만들지 않습니다.
HTTPS provider, TLS, 사용자 인증, 카탈로그 서명, 회사 정책 검증, 안전한 외부 연결 방식은 ROADMAP 항목입니다.
별도 클라우드·유료 도메인·데이터베이스를 필수로 요구하지 않습니다.

## 읽기 전용 API

| Method | 경로 | 내용 |
|---|---|---|
| GET | /api/health | API 버전, 실제 listener 구성 |
| GET | /api/catalog | 등록된 앱/승인 release 목록 |
| GET | /api/apps/<app_id> | 버전/패키지 메타데이터 |
| GET | /api/apps/<app_id>/notes | 릴리즈 노트 |
| GET | /packages/<package_name> | 카탈로그에서 published=true인 해시 검증 ZIP만 제공 |

POST/PUT/PATCH/DELETE는 405입니다. 디렉터리 탐색이나 관리자 API는 없습니다.
실제 디스크 파일이 카탈로그의 크기·해시와 다르면 다운로드를 거부합니다.

## 관리자 로컬 게시 CLI

관리자는 승인받은 완성 ZIP과 EXE 해시를 준비하고, 새로운 release_id로 로컬에서 실행합니다.
아래는 명령 형태를 보여주는 예시입니다. 해시는 실제 검증값으로 바꿔야 합니다.

```powershell
python -B -m southpaw_tools.admin --app-id tilenamer --zip 'D:/Approved/Tool.zip' --version '0.1.7' --release-id '0.1.7-team-build001' --exe 'TileNamer.exe' --sha256 '<ZIP SHA-256>' --exe-sha256 '<EXE SHA-256>' --notes-file 'D:/Approved/notes.md' --approve
```

Git 최신 소스나 개발 브랜치를 패키징하지 않습니다. 기존 release_id와 파일은 덮어쓰지 않습니다.
새 ZIP을 비공개 staging에서 검사 → 완성 ZIP rename → catalog atomic replace 순서입니다.
HTTP 클라이언트에는 --approve나 이 게시 기능을 노출하지 않습니다.
새 앱을 추가할 때는 초기 카탈로그 등록·설정 보존 정책 검토가 필요합니다. 관리 GUI는 후속입니다.
